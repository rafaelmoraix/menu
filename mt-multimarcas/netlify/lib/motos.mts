import { getStore } from "@netlify/blobs"

export const lojaStore = () => getStore({ name: "catalogo", consistency: "strong" })
export const fotosStore = () => getStore({ name: "fotos", consistency: "strong" })

const CATEGORIAS = ["Street", "Naked", "Trail", "Big Trail", "Esportiva", "Scooter", "Custom", "Touring", "Off-road", "Ciclomotor", "Elétrica"]

const txt = (v: unknown, max = 120) => (typeof v === "string" ? v.trim().slice(0, max) : "")
const num = (v: unknown, min = 0, max = 10_000_000) => {
  const n = Math.round(Number(v))
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : 0
}
const umDe = <T extends string>(v: unknown, opcoes: T[], padrao: T): T =>
  opcoes.includes(v as T) ? (v as T) : padrao

/** Limpa e valida uma moto vinda do painel. Retorna null se faltar o essencial. */
export function sanitizarMoto(m: any) {
  if (!m || typeof m !== "object") return null
  const id = txt(m.id, 80).toLowerCase().replace(/[^a-z0-9-]/g, "")
  const marca = txt(m.marca, 40)
  const modelo = txt(m.modelo, 60)
  if (!id || !marca || !modelo) return null
  return {
    id,
    marca,
    modelo,
    ano: num(m.ano, 1950, 2100),
    km: num(m.km, 0, 2_000_000),
    cilindrada: num(m.cilindrada, 0, 5000),
    cor: txt(m.cor, 40),
    preco: num(m.preco, 0, 10_000_000),
    categoria: umDe(m.categoria, CATEGORIAS, "Street"),
    condicao: umDe(m.condicao, ["Nova", "Seminova"], "Seminova"),
    combustivel: umDe(m.combustivel, ["Gasolina", "Flex", "Elétrica"], "Gasolina"),
    status: umDe(m.status, ["disponivel", "vendida"], "disponivel"),
    destaque: m.destaque === true,
    opcionais: (Array.isArray(m.opcionais) ? m.opcionais : []).map((o: unknown) => txt(o, 60)).filter(Boolean).slice(0, 30),
    descricao: txt(m.descricao, 2000),
    fotos: (Array.isArray(m.fotos) ? m.fotos : [])
      .filter((f: unknown) => typeof f === "string" && /^(\/fotos\/[A-Za-z0-9._-]+|img\/[A-Za-z0-9._\/-]+)$/.test(f))
      .slice(0, 20),
    atualizadoEm: new Date().toISOString(),
  }
}
