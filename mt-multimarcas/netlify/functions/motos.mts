import type { Config } from "@netlify/functions"
import { autorizado, naoAutorizado } from "../lib/auth.mts"
import { lojaStore, sanitizarMoto } from "../lib/motos.mts"

// GET  /api/motos  -> lista pública do catálogo ({ motos: null } se o painel nunca foi usado)
// PUT  /api/motos  -> salva a lista inteira (somente admin)
export default async (req: Request) => {
  const store = lojaStore()

  if (req.method === "GET") {
    const motos = await store.get("motos", { type: "json" })
    return Response.json({ motos: motos ?? null }, { headers: { "cache-control": "no-store" } })
  }

  if (!autorizado(req)) return naoAutorizado()

  let corpo: any
  try { corpo = await req.json() } catch { return Response.json({ erro: "Dados inválidos." }, { status: 400 }) }
  if (!Array.isArray(corpo?.motos) || corpo.motos.length > 500) {
    return Response.json({ erro: "Lista de motos inválida." }, { status: 400 })
  }

  const vistos = new Set<string>()
  const motos = []
  for (const bruto of corpo.motos) {
    const m = sanitizarMoto(bruto)
    if (!m) return Response.json({ erro: "Toda moto precisa de marca e modelo." }, { status: 400 })
    if (vistos.has(m.id)) return Response.json({ erro: `Moto repetida: ${m.id}` }, { status: 400 })
    vistos.add(m.id)
    motos.push(m)
  }

  await store.setJSON("motos", motos)
  return Response.json({ ok: true, motos })
}

export const config: Config = { path: "/api/motos", method: ["GET", "PUT"] }
