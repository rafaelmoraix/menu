import type { Config } from "@netlify/functions"
import { createHmac, timingSafeEqual } from "node:crypto"
import { limparTel, loja, registrarEntrada, registrarSaidaCelular, telValido } from "../lib/atendimento.mts"

/* Webhook do WhatsApp oficial (Meta Cloud API)
   URL para cadastrar na Meta: https://<site>/api/whatsapp/webhook
   - GET : a Meta confere o "verify token" (WHATSAPP_VERIFY_TOKEN)
   - POST: chegam mensagens, status (entregue/lida) e, no modo coexistência,
           as mensagens que alguém mandou direto pelo app do celular.
   Toda chamada POST é conferida com a assinatura da Meta (WHATSAPP_APP_SECRET). */

const STATUS: Record<string, string> = { sent: "enviada", delivered: "entregue", read: "lida", failed: "falhou" }

function textoDe(m: any): string {
  switch (m?.type) {
    case "text": return m.text?.body || ""
    case "image": return `📷 Foto${m.image?.caption ? ": " + m.image.caption : ""}`
    case "video": return `🎥 Vídeo${m.video?.caption ? ": " + m.video.caption : ""}`
    case "audio": return "🎤 Áudio (abra no celular para ouvir)"
    case "document": return `📄 Documento${m.document?.filename ? ": " + m.document.filename : ""}`
    case "sticker": return "Figurinha"
    case "location": return `📍 Localização${m.location?.name ? ": " + m.location.name : ""}`
    case "button": return m.button?.text || "Botão"
    case "interactive": return m.interactive?.button_reply?.title || m.interactive?.list_reply?.title || "Resposta"
    case "reaction": return `Reagiu ${m.reaction?.emoji || ""}`.trim()
    default: return "Mensagem (tipo não suportado — veja no celular)"
  }
}

function assinaturaOk(corpo: string, assinatura: string | null): boolean {
  const segredo = Netlify.env.get("WHATSAPP_APP_SECRET")
  if (!segredo || !assinatura?.startsWith("sha256=")) return false
  const esperado = Buffer.from(createHmac("sha256", segredo).update(corpo).digest("hex"))
  const recebido = Buffer.from(assinatura.slice(7))
  return esperado.length === recebido.length && timingSafeEqual(esperado, recebido)
}

export default async (req: Request) => {
  if (req.method === "GET") {
    const p = new URL(req.url).searchParams
    const token = Netlify.env.get("WHATSAPP_VERIFY_TOKEN")
    if (token && p.get("hub.mode") === "subscribe" && p.get("hub.verify_token") === token) {
      return new Response(p.get("hub.challenge") || "", { status: 200 })
    }
    return new Response("Verificação recusada", { status: 403 })
  }

  const bruto = await req.text()
  if (!assinaturaOk(bruto, req.headers.get("x-hub-signature-256"))) {
    return new Response("Assinatura inválida", { status: 401 })
  }

  let dados: any
  try { dados = JSON.parse(bruto) } catch { return new Response("ok") }

  for (const entrada of dados?.entry || []) {
    for (const mudanca of entrada?.changes || []) {
      const v = mudanca?.value || {}

      // Mensagens de clientes
      const nomes: Record<string, string> = {}
      for (const c of v.contacts || []) nomes[c.wa_id] = c.profile?.name || ""
      for (const m of v.messages || []) {
        const tel = limparTel(m.from)
        if (!telValido(tel) || (m.id && (await loja().get(`wa/${m.id}`)))) continue // ignora repetidas
        const em = m.timestamp ? new Date(Number(m.timestamp) * 1000).toISOString() : new Date().toISOString()
        await registrarEntrada(tel, nomes[m.from] || "", textoDe(m), em, m.id)
      }

      // Status das mensagens enviadas (✓ enviada, ✓✓ entregue, lida)
      for (const s of v.statuses || []) {
        const ref: any = await loja().get(`wa/${s.id}`, { type: "json" })
        const novo = STATUS[s.status]
        if (!ref?.chave || !novo) continue
        const msg: any = await loja().get(ref.chave, { type: "json" })
        if (msg) await loja().setJSON(ref.chave, { ...msg, status: novo })
      }

      // Coexistência: mensagem enviada direto pelo app WhatsApp Business do celular
      for (const m of v.message_echoes || []) {
        const tel = limparTel(m.to)
        if (!telValido(tel) || (m.id && (await loja().get(`wa/${m.id}`)))) continue
        const em = m.timestamp ? new Date(Number(m.timestamp) * 1000).toISOString() : new Date().toISOString()
        await registrarSaidaCelular(tel, textoDe(m), em, m.id)
      }
    }
  }
  return new Response("ok")
}

export const config: Config = { path: "/api/whatsapp/webhook", method: ["GET", "POST"] }
