import type { Config } from "@netlify/functions"
import { getStore } from "@netlify/blobs"
import { createHash } from "node:crypto"
import { autorizado, naoAutorizado } from "../lib/auth.mts"

// GET /api/busca?modelo=fazer 250&ano=2019&precoMax=15000&uf=SP&recentes=1
//   -> anúncios encontrados na internet (via SerpAPI / Google), só para o admin
// GET /api/busca?conta=1  -> quantas buscas restam no mês (não gasta busca)

const BASE = () => Netlify.env.get("BUSCA_API_BASE") || "https://serpapi.com"
const CACHE_MS = 6 * 60 * 60 * 1000 // repete a mesma busca por 6h sem gastar cota
const SITES = ["olx.com.br", "mercadolivre.com.br", "webmotors.com.br", "mobiauto.com.br", "icarros.com.br", "facebook.com"]

const UFS: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais",
  PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte",
  RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima", SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
}

const erro = (msg: string, status = 400, extra: object = {}) => Response.json({ erro: msg, ...extra }, { status })

function lerPreco(texto: string): number | null {
  const m = texto.match(/R\$\s?(\d{1,3}(?:\.\d{3})+|\d{3,7})(?:,\d{2})?/)
  if (!m) return null
  const n = Number(m[1].replace(/\./g, ""))
  return n >= 500 && n <= 5_000_000 ? n : null
}

function nomeSite(host: string): string {
  if (host.includes("olx")) return "OLX"
  if (host.includes("mercadolivre")) return "Mercado Livre"
  if (host.includes("webmotors")) return "Webmotors"
  if (host.includes("mobiauto")) return "Mobiauto"
  if (host.includes("icarros")) return "iCarros"
  if (host.includes("facebook")) return "Facebook"
  return host.replace(/^www\./, "")
}

async function serpapi(caminho: string, params: Record<string, string>) {
  const url = new URL(caminho, BASE())
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  const r = await fetch(url, { signal: AbortSignal.timeout(20000) })
  const dados: any = await r.json().catch(() => ({}))
  if (!r.ok || dados.error) {
    const msg = String(dados.error || `HTTP ${r.status}`)
    if (/run out of searches|plan|limit/i.test(msg)) throw Object.assign(new Error("As buscas grátis do mês acabaram. Use os botões de atalho até o mês virar."), { status: 429 })
    if (/invalid api key/i.test(msg) || r.status === 401) throw Object.assign(new Error("Chave do SerpAPI inválida. Confira a BUSCA_API_KEY na Netlify."), { status: 500 })
    throw Object.assign(new Error(`O serviço de busca falhou: ${msg}`), { status: 502 })
  }
  return dados
}

export default async (req: Request) => {
  if (!autorizado(req)) return naoAutorizado()
  const chave = Netlify.env.get("BUSCA_API_KEY")
  if (!chave) return erro("A busca na internet ainda não foi ativada (falta a chave do SerpAPI).", 501, { semChave: true })

  const p = new URL(req.url).searchParams
  try {
    if (p.get("conta")) {
      const c = await serpapi("/account.json", { api_key: chave })
      return Response.json({
        restantes: c.total_searches_left ?? c.plan_searches_left ?? null,
        usadas: c.this_month_usage ?? null,
        limite: c.searches_per_month ?? null,
      })
    }

    const modelo = (p.get("modelo") || "").trim().slice(0, 80)
    const ano = (p.get("ano") || "").replace(/\D/g, "").slice(0, 4)
    const precoMax = Number(p.get("precoMax")) || 0
    const uf = (p.get("uf") || "").toUpperCase()
    const recentes = p.get("recentes") === "1"
    if (modelo.length < 2) return erro("Digite o modelo da moto.")

    const local = UFS[uf] ? ` ${UFS[uf]}` : ""
    const q = `${modelo} ${ano} moto à venda${local} (${SITES.map((s) => `site:${s}`).join(" OR ")})`.replace(/\s+/g, " ")

    // Cache: a mesma busca nas últimas 6h não gasta cota
    const cache = getStore("busca-cache")
    const id = createHash("sha256").update(JSON.stringify([q, recentes])).digest("hex").slice(0, 32)
    const guardado: any = await cache.get(id, { type: "json" })
    let resultados: any[]
    let doCache = false
    if (guardado && Date.now() - guardado.em < CACHE_MS) {
      resultados = guardado.resultados
      doCache = true
    } else {
      const dados = await serpapi("/search.json", {
        engine: "google", q, api_key: chave, google_domain: "google.com.br", gl: "br", hl: "pt-br", num: "20",
        ...(recentes ? { tbs: "qdr:m" } : {}),
      })
      resultados = (dados.organic_results || []).map((r: any) => {
        const texto = `${r.title || ""} ${r.snippet || ""} ${(r.rich_snippet?.top?.extensions || []).join(" ")}`
        let host = ""
        try { host = new URL(r.link).hostname } catch { /* link inválido */ }
        return {
          titulo: String(r.title || "").slice(0, 200),
          url: String(r.link || ""),
          site: nomeSite(host),
          trecho: String(r.snippet || "").slice(0, 300),
          preco: r.rich_snippet?.top?.detected_extensions?.price ?? lerPreco(texto),
          data: r.date || null,
          foto: typeof r.thumbnail === "string" ? r.thumbnail : null,
        }
      }).filter((r: any) => /^https:\/\//.test(r.url))
      await cache.setJSON(id, { em: Date.now(), resultados })
    }

    let escondidos = 0
    if (precoMax > 0) {
      resultados = resultados.filter((r) => {
        const fora = r.preco && r.preco > precoMax
        if (fora) escondidos++
        return !fora
      })
    }
    return Response.json({ resultados, escondidos, doCache })
  } catch (e: any) {
    return erro(e.message || "Erro na busca.", e.status || 502)
  }
}

export const config: Config = { path: "/api/busca", method: "GET" }
