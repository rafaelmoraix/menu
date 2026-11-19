import type { Config } from "@netlify/functions"
import { getStore } from "@netlify/blobs"
import { createHash } from "node:crypto"
import { autorizado, naoAutorizado } from "../lib/auth.mts"

// GET /api/busca?modelo=fazer 250&ano=2019&precoMax=15000&uf=SP&recentes=1
//   -> anúncios encontrados na internet (via SerpAPI ou SearchApi / Google), só para o admin
// GET /api/busca?conta=1  -> quantas buscas restam no mês (não gasta busca)

// Funciona com SerpAPI (chave de 64 caracteres) ou SearchApi.io (outras chaves).
// O serviço é descoberto pelo formato da chave; BUSCA_PROVEDOR força um dos dois.
type Provedor = "serpapi" | "searchapi"
function provedor(chave: string): Provedor {
  const forcado = (Netlify.env.get("BUSCA_PROVEDOR") || "").toLowerCase()
  if (forcado === "serpapi" || forcado === "searchapi") return forcado
  return /^[a-f0-9]{64}$/i.test(chave) ? "serpapi" : "searchapi"
}
const NOMES: Record<Provedor, string> = { serpapi: "SerpAPI", searchapi: "SearchApi" }
const ROTAS: Record<Provedor, { base: string; busca: string; conta: string }> = {
  serpapi: { base: "https://serpapi.com", busca: "/search.json", conta: "/account.json" },
  searchapi: { base: "https://www.searchapi.io", busca: "/api/v1/search", conta: "/api/v1/me" },
}
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

async function chamar(prov: Provedor, tipo: "busca" | "conta", params: Record<string, string>) {
  const rota = ROTAS[prov]
  const url = new URL(rota[tipo], Netlify.env.get("BUSCA_API_BASE") || rota.base)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  const r = await fetch(url, { signal: AbortSignal.timeout(20000) })
  const dados: any = await r.json().catch(() => ({}))
  if (!r.ok || dados.error) {
    const msg = String(dados.error || `HTTP ${r.status}`)
    const nome = NOMES[prov]
    if (r.status === 429 || /run out of|credits|limit|quota/i.test(msg)) {
      throw Object.assign(new Error(`As buscas grátis do ${nome} acabaram. Use os botões de atalho enquanto isso.`), { status: 429 })
    }
    if (r.status === 401 || /invalid api key|unauthori/i.test(msg)) {
      throw Object.assign(new Error(`Chave do ${nome} recusada (resposta do ${nome}: "${msg.slice(0, 160)}"). Confira a BUSCA_API_KEY na Netlify.`), { status: 500 })
    }
    throw Object.assign(new Error(`O ${nome} falhou: ${msg.slice(0, 200)}`), { status: 502 })
  }
  return dados
}

export default async (req: Request) => {
  if (!autorizado(req)) return naoAutorizado()
  // Remove espaços, aspas e quebras de linha que vêm junto ao colar a chave
  const chave = (Netlify.env.get("BUSCA_API_KEY") || "").trim().replace(/^["']|["']$/g, "").trim()
  if (!chave) return erro("A busca na internet ainda não foi ativada (falta a chave do serviço de busca).", 501, { semChave: true })
  const prov = provedor(chave)

  const p = new URL(req.url).searchParams
  try {
    if (p.get("conta")) {
      const c = await chamar(prov, "conta", { api_key: chave })
      const a = c.account || c
      return Response.json({
        servico: NOMES[prov],
        restantes: a.total_searches_left ?? a.plan_searches_left ?? a.remaining_credits ?? null,
        usadas: a.this_month_usage ?? a.current_month_usage ?? null,
        limite: a.searches_per_month ?? a.monthly_allowance ?? null,
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
    const id = createHash("sha256").update(JSON.stringify([prov, q, recentes])).digest("hex").slice(0, 32)
    const guardado: any = await cache.get(id, { type: "json" })
    let resultados: any[]
    let doCache = false
    if (guardado && Date.now() - guardado.em < CACHE_MS) {
      resultados = guardado.resultados
      doCache = true
    } else {
      const dados = await chamar(prov, "busca", {
        engine: "google", q, api_key: chave, google_domain: "google.com.br", gl: "br", hl: "pt-br", num: "20",
        ...(recentes ? (prov === "serpapi" ? { tbs: "qdr:m" } : { time_period: "last_month" }) : {}),
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
          foto: typeof r.thumbnail === "string" && /^(https:|data:image\/)/.test(r.thumbnail) ? r.thumbnail : null,
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
