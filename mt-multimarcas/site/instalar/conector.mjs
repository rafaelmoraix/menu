/* =========================================================
   MT Multimarcas — Conector de WhatsApp (roda na VPS)
   - Mantém o WhatsApp da loja conectado (como o WhatsApp Web)
   - Repassa as mensagens para o CRM do site
   - Envia as respostas que os atendentes escrevem no CRM
   Configuração (arquivo .env): CONECTOR_TOKEN, SITE_URL, PORTA
   ========================================================= */
import makeWASocket, { Browsers, DisconnectReason, fetchLatestBaileysVersion, useMultiFileAuthState } from "@whiskeysockets/baileys"
import QRCode from "qrcode"
import pino from "pino"
import http from "node:http"
import { createHash, timingSafeEqual } from "node:crypto"
import { rm } from "node:fs/promises"

const PORTA = Number(process.env.PORTA || 3000)
const TOKEN = process.env.CONECTOR_TOKEN || ""
const SITE = (process.env.SITE_URL || "").replace(/\/$/, "")
const PASTA = process.env.PASTA_SESSAO || "./sessao"
if (TOKEN.length < 20 || !SITE) {
  console.error("Faltam CONECTOR_TOKEN (20+ caracteres) e SITE_URL no .env")
  process.exit(1)
}

const logger = pino({ level: "warn" })
let sock = null
let estado = { conectado: false, qr: null, numero: null, desde: null, atualizado: new Date().toISOString() }
const mudar = (novo) => { estado = { ...estado, ...novo, atualizado: new Date().toISOString() } }

/* ---------------- Conexão com o WhatsApp ---------------- */
async function iniciar() {
  const { state, saveCreds } = await useMultiFileAuthState(PASTA)
  const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: undefined }))
  sock = makeWASocket({
    auth: state,
    version,
    logger,
    browser: Browsers.ubuntu("MT Multimarcas CRM"),
    markOnlineOnConnect: false, // não deixa o celular "sempre online" para os clientes
    syncFullHistory: false,
  })
  const atual = sock
  sock.ev.on("creds.update", saveCreds)

  sock.ev.on("connection.update", async (u) => {
    if (atual !== sock) return
    if (u.qr) mudar({ conectado: false, qr: await QRCode.toDataURL(u.qr, { margin: 1, width: 320 }) })
    if (u.connection === "open") {
      const numero = String(sock.user?.id || "").split(":")[0].split("@")[0]
      mudar({ conectado: true, qr: null, numero, desde: new Date().toISOString() })
      console.log(`Conectado: ${numero}`)
    }
    if (u.connection === "close") {
      const codigo = u.lastDisconnect?.error?.output?.statusCode
      const saiu = codigo === DisconnectReason.loggedOut
      mudar({ conectado: false, ...(saiu ? { numero: null, qr: null } : {}) })
      console.log(`Conexão fechada (${codigo})${saiu ? ": aparelho desconectado, gerando novo QR" : ", reconectando"}`)
      if (saiu) await rm(PASTA, { recursive: true, force: true })
      setTimeout(iniciar, saiu ? 1000 : 3000)
    }
  })

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return // ignora histórico antigo
    for (const m of messages) {
      try { await repassar(m) } catch (e) { console.error("Erro ao repassar:", e.message) }
    }
  })
}

/* ---------------- Mensagens ---------------- */
async function telefoneDe(key) {
  let jid = key?.remoteJid || ""
  if (jid.endsWith("@lid")) {
    jid = key.remoteJidAlt || (await sock.signalRepository?.lidMapping?.getPNForLID?.(jid).catch(() => null)) || ""
  }
  if (!jid.endsWith("@s.whatsapp.net")) return null // grupos, status, canais: ignora
  return jid.split("@")[0].split(":")[0]
}

function textoDe(msg) {
  const c = msg?.ephemeralMessage?.message || msg?.viewOnceMessage?.message || msg?.viewOnceMessageV2?.message
    || msg?.documentWithCaptionMessage?.message || msg
  if (!c || c.protocolMessage || c.reactionMessage || c.senderKeyDistributionMessage && Object.keys(c).length === 1) return null
  if (c.conversation) return c.conversation
  if (c.extendedTextMessage?.text) return c.extendedTextMessage.text
  if (c.imageMessage) return `📷 Foto${c.imageMessage.caption ? ": " + c.imageMessage.caption : ""}`
  if (c.videoMessage) return `🎥 Vídeo${c.videoMessage.caption ? ": " + c.videoMessage.caption : ""}`
  if (c.audioMessage) return "🎤 Áudio (ouça no celular)"
  if (c.documentMessage) return `📄 Documento${c.documentMessage.fileName ? ": " + c.documentMessage.fileName : ""}`
  if (c.stickerMessage) return "Figurinha"
  if (c.locationMessage) return `📍 Localização${c.locationMessage.name ? ": " + c.locationMessage.name : ""}`
  if (c.contactMessage) return `👤 Contato: ${c.contactMessage.displayName || ""}`
  if (c.buttonsResponseMessage) return c.buttonsResponseMessage.selectedDisplayText || "Resposta"
  if (c.listResponseMessage) return c.listResponseMessage.title || "Resposta"
  return null
}

const fila = [] // eventos que não chegaram no site (sem internet, site fora): tenta de novo
async function enviarAoSite(evento) {
  const r = await fetch(`${SITE}/api/conector/evento`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${TOKEN}` },
    body: JSON.stringify(evento),
    signal: AbortSignal.timeout(15000),
  })
  if (!r.ok) throw new Error(`site respondeu ${r.status}`)
}

async function repassar(m) {
  const tel = await telefoneDe(m.key)
  const texto = textoDe(m.message)
  if (!tel || !texto || !m.key?.id) return
  const evento = {
    tipo: "mensagem",
    id: m.key.id,
    tel,
    nome: m.key.fromMe ? "" : (m.pushName || ""),
    texto: texto.slice(0, 4000),
    em: new Date(Number(m.messageTimestamp || Date.now() / 1000) * 1000).toISOString(),
    deMim: !!m.key.fromMe, // mensagem enviada pelo celular da loja
  }
  try { await enviarAoSite(evento) } catch (e) {
    console.error("Site indisponível, guardando para tentar de novo:", e.message)
    fila.push(evento)
  }
}
setInterval(async () => {
  while (fila.length) {
    try { await enviarAoSite(fila[0]); fila.shift() } catch { break }
  }
}, 30000)

async function enviar(tel, texto) {
  if (!estado.conectado || !sock) throw Object.assign(new Error("WhatsApp desconectado. Leia o QR code no painel."), { status: 503 })
  const [r] = await sock.onWhatsApp(tel)
  if (!r?.exists) throw Object.assign(new Error("Esse número não tem WhatsApp."), { status: 404 })
  const enviada = await sock.sendMessage(r.jid, { text: texto })
  return enviada?.key?.id || ""
}

/* ---------------- API para o site (protegida por token) ---------------- */
const hash = (s) => createHash("sha256").update(String(s)).digest()
const autorizado = (req) => timingSafeEqual(hash((req.headers.authorization || "").replace(/^Bearer\s+/i, "")), hash(TOKEN))
const json = (res, status, dados) => { res.writeHead(status, { "content-type": "application/json" }); res.end(JSON.stringify(dados)) }

function lerCorpo(req) {
  return new Promise((ok, falha) => {
    let dados = ""
    req.on("data", (p) => { dados += p; if (dados.length > 64 * 1024) { req.destroy(); falha(new Error("Corpo grande demais")) } })
    req.on("end", () => { try { ok(dados ? JSON.parse(dados) : {}) } catch { falha(new Error("JSON inválido")) } })
  })
}

http.createServer(async (req, res) => {
  try {
    if (req.url === "/saude") return json(res, 200, { ok: true })
    if (!autorizado(req)) return json(res, 401, { erro: "Não autorizado" })

    if (req.method === "GET" && req.url === "/status") return json(res, 200, estado)

    if (req.method === "POST" && req.url === "/enviar") {
      const { tel, texto } = await lerCorpo(req)
      const numero = String(tel || "").replace(/\D/g, "")
      if (!/^\d{10,15}$/.test(numero) || !texto) return json(res, 400, { erro: "Telefone ou texto inválido" })
      return json(res, 200, { id: await enviar(numero, String(texto).slice(0, 4000)) })
    }

    if (req.method === "POST" && req.url === "/desconectar") {
      await sock?.logout().catch(() => {})
      return json(res, 200, { ok: true })
    }
    json(res, 404, { erro: "Rota inválida" })
  } catch (e) {
    json(res, e.status || 500, { erro: e.message || "Erro" })
  }
}).listen(PORTA, "127.0.0.1", () => console.log(`Conector ouvindo em 127.0.0.1:${PORTA}`))

iniciar()
