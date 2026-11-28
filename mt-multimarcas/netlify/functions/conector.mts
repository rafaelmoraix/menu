import type { Config, Context } from "@netlify/functions"
import { createHash, timingSafeEqual } from "node:crypto"
import { autorizado, naoAutorizado } from "../lib/auth.mts"
import {
  chamarConector, conectorAtivo, limparTel, loja, modo, registrarEntrada, registrarSaidaCelular, telValido,
} from "../lib/atendimento.mts"

// Ligação com o conector de WhatsApp da VPS (modo QR code)
// POST /api/conector/evento       <- a VPS avisa mensagem nova (token do conector)
// GET  /api/conector/status       -> painel: conectado? QR code? (usuário logado)
// POST /api/conector/desconectar  -> painel: desconecta o aparelho (só gerente)

const hash = (s: string) => createHash("sha256").update(s).digest()
function tokenDoConector(req: Request): boolean {
  const esperado = Netlify.env.get("CONECTOR_TOKEN") || ""
  const recebido = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "")
  return esperado.length >= 20 && timingSafeEqual(hash(recebido), hash(esperado))
}

export default async (req: Request, context: Context) => {
  const acao = context.params.acao

  /* ---------- Evento vindo da VPS ---------- */
  if (acao === "evento" && req.method === "POST") {
    if (!tokenDoConector(req)) return Response.json({ erro: "Não autorizado" }, { status: 401 })
    if (modo() !== "qrcode") return Response.json({ ok: true, ignorado: "modo " + modo() })
    let e: any
    try { e = await req.json() } catch { return Response.json({ erro: "JSON inválido" }, { status: 400 }) }
    const tel = limparTel(e?.tel)
    const texto = String(e?.texto || "").slice(0, 4000)
    const id = String(e?.id || "").slice(0, 200)
    if (e?.tipo !== "mensagem" || !telValido(tel) || !texto || !id) return Response.json({ erro: "Evento inválido" }, { status: 400 })
    if (await loja().get(`wa/${id}`)) return Response.json({ ok: true, repetida: true }) // já registrada (ex.: enviada pelo CRM)
    const em = !isNaN(Date.parse(e.em)) ? new Date(e.em).toISOString() : new Date().toISOString()
    if (e.deMim) await registrarSaidaCelular(tel, texto, em, id)
    else await registrarEntrada(tel, String(e.nome || "").slice(0, 60), texto, em, id)
    return Response.json({ ok: true })
  }

  /* ---------- Painel ---------- */
  const eu = autorizado(req)
  if (!eu) return naoAutorizado()
  if (!conectorAtivo()) return Response.json({ configurado: false })

  try {
    if (acao === "status" && req.method === "GET") {
      const s = await chamarConector("/status")
      return Response.json({ configurado: true, conectado: !!s.conectado, numero: s.numero || null, qr: s.qr || null, desde: s.desde || null })
    }
    if (acao === "desconectar" && req.method === "POST") {
      if (eu.papel !== "gerente") return Response.json({ erro: "Só o gerente pode desconectar o WhatsApp." }, { status: 403 })
      await chamarConector("/desconectar", {})
      return Response.json({ ok: true })
    }
  } catch (err: any) {
    return Response.json({ configurado: true, conectado: false, erro: err.message }, { status: 502 })
  }
  return Response.json({ erro: "Rota inválida" }, { status: 404 })
}

export const config: Config = { path: "/api/conector/:acao", method: ["GET", "POST"] }
