import type { Config } from "@netlify/functions"
import { autorizado, naoAutorizado } from "../lib/auth.mts"
import { lojaStore } from "../lib/motos.mts"

// Lista de procuras: motos que clientes pediram e a loja ainda não tem.
// GET /api/procuras  |  PUT /api/procuras { procuras: [...] }   (só admin)
const txt = (v: unknown, max: number) => (typeof v === "string" ? v.trim().slice(0, max) : "")

export default async (req: Request) => {
  if (!autorizado(req)) return naoAutorizado()
  const store = lojaStore()

  if (req.method === "GET") {
    return Response.json({ procuras: (await store.get("procuras", { type: "json" })) ?? [] })
  }

  let corpo: any
  try { corpo = await req.json() } catch { return Response.json({ erro: "Dados inválidos." }, { status: 400 }) }
  if (!Array.isArray(corpo?.procuras) || corpo.procuras.length > 500) {
    return Response.json({ erro: "Lista inválida." }, { status: 400 })
  }
  const procuras = corpo.procuras.map((p: any) => ({
    id: txt(p?.id, 40).replace(/[^a-z0-9-]/gi, ""),
    modelo: txt(p?.modelo, 80),
    ano: txt(p?.ano, 4).replace(/\D/g, ""),
    precoMax: Math.max(0, Math.round(Number(p?.precoMax)) || 0),
    uf: txt(p?.uf, 2).toUpperCase(),
    cliente: txt(p?.cliente, 80),
    telefone: txt(p?.telefone, 20).replace(/[^\d]/g, ""),
    obs: txt(p?.obs, 500),
    criadoEm: txt(p?.criadoEm, 30) || new Date().toISOString(),
  })).filter((p: any) => p.id && p.modelo)

  await store.setJSON("procuras", procuras)
  return Response.json({ ok: true, procuras })
}

export const config: Config = { path: "/api/procuras", method: ["GET", "PUT"] }
