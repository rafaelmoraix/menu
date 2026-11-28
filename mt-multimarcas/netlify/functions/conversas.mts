import type { Config, Context } from "@netlify/functions"
import { autorizado, equipe, naoAutorizado } from "../lib/auth.mts"
import {
  ETAPAS, apagarDemo, atualizarConversa, enviarMensagem, limparTel, listarConversas, listarMensagens,
  loja, modo, registrarEntrada, salvarMensagem, semearDemo, telValido, type Etapa,
} from "../lib/atendimento.mts"

// GET  /api/conversas                    -> lista de conversas + equipe + modo
// GET  /api/conversas/:tel               -> conversa + mensagens
// POST /api/conversas/:tel/acao          -> { acao: assumir|liberar|transferir|etapa|notas|lida, ... }
// POST /api/conversas/:tel/mensagens     -> { texto }  envia mensagem ao cliente
// POST /api/conversas/simular            -> { nome, tel, texto }  (só demonstração)
// POST /api/conversas/reiniciar          -> recria as conversas de teste (só demonstração, gerente)

const erro = (msg: string, status = 400) => Response.json({ erro: msg }, { status })

export default async (req: Request, context: Context) => {
  const eu = autorizado(req)
  if (!eu) return naoAutorizado()
  const time = equipe()
  const nomeDe = (id: string | null) => time.find((u) => u.id === id)?.nome || "outra pessoa"
  const { alvo, sub } = context.params

  try {
    /* ---------- Lista ---------- */
    if (!alvo) {
      if (modo() === "demo" && !(await loja().get("demo-semeada"))) {
        await semearDemo(time.filter((u) => u.papel === "atendente").map((u) => u.id))
      }
      return Response.json({ modo: modo(), eu, equipe: time, conversas: await listarConversas() })
    }

    let corpo: any = {}
    if (req.method === "POST") { try { corpo = await req.json() } catch { return erro("Dados inválidos.") } }

    /* ---------- Demonstração ---------- */
    if (alvo === "simular" && req.method === "POST") {
      if (modo() !== "demo") return erro("Só funciona no modo demonstração.")
      const tel = limparTel(corpo.tel) || `55119${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`
      const texto = String(corpo.texto || "").trim().slice(0, 2000)
      if (!telValido(tel) || !texto) return erro("Informe telefone e mensagem.")
      return Response.json({ conversa: await registrarEntrada(tel, String(corpo.nome || "").trim(), texto) })
    }
    if (alvo === "reiniciar" && req.method === "POST") {
      if (modo() !== "demo") return erro("Só funciona no modo demonstração.")
      if (eu.papel !== "gerente") return erro("Só o gerente pode reiniciar a demonstração.", 403)
      await apagarDemo()
      return Response.json({ ok: true })
    }

    const tel = limparTel(alvo)
    if (!telValido(tel)) return erro("Conversa inválida.", 404)

    /* ---------- Abrir conversa ---------- */
    if (req.method === "GET") {
      const [c, mensagens] = await Promise.all([loja().get(`conv/${tel}`, { type: "json" }), listarMensagens(tel)])
      if (!c) return erro("Conversa não encontrada.", 404)
      return Response.json({ conversa: c, mensagens })
    }

    /* ---------- Ações ---------- */
    if (sub === "acao") {
      const acao = String(corpo.acao || "")
      const conversa = await atualizarConversa(tel, (c) => {
        if (!c) throw new Error("Conversa não encontrada.")
        const dono = c.atendente
        const podeMexer = !dono || dono === eu.id || eu.papel === "gerente"
        switch (acao) {
          case "assumir":
            if (dono && dono !== eu.id) throw new Error(`${nomeDe(dono)} já está atendendo esta conversa.`)
            c.atendente = eu.id
            if (c.etapa === "novo") c.etapa = "atendimento"
            break
          case "liberar":
            if (!podeMexer) throw new Error(`Só ${nomeDe(dono)} ou o gerente podem liberar.`)
            c.atendente = null
            break
          case "transferir": {
            if (!podeMexer) throw new Error(`Só ${nomeDe(dono)} ou o gerente podem transferir.`)
            const para = time.find((u) => u.id === corpo.para)
            if (!para) throw new Error("Escolha para quem transferir.")
            c.atendente = para.id
            if (c.etapa === "novo") c.etapa = "atendimento"
            break
          }
          case "etapa":
            if (!ETAPAS.includes(corpo.etapa)) throw new Error("Etapa inválida.")
            c.etapa = corpo.etapa as Etapa
            break
          case "notas":
            c.notas = String(corpo.notas || "").slice(0, 3000)
            break
          case "lida":
            c.naoLidas = 0
            break
          default:
            throw new Error("Ação inválida.")
        }
        return c
      })
      return Response.json({ conversa })
    }

    /* ---------- Enviar mensagem ---------- */
    if (sub === "mensagens") {
      const texto = String(corpo.texto || "").trim().slice(0, 4000)
      if (!texto) return erro("Escreva a mensagem.")
      const atual: any = await loja().get(`conv/${tel}`, { type: "json" })
      if (!atual) return erro("Conversa não encontrada.", 404)
      if (atual.atendente && atual.atendente !== eu.id && eu.papel !== "gerente") {
        return erro(`Esta conversa está com ${nomeDe(atual.atendente)}. Peça para transferir para você.`, 409)
      }
      const em = new Date().toISOString()
      let waId: string | undefined
      if (modo() !== "demo") waId = await enviarMensagem(tel, texto)
      const mensagem = await salvarMensagem(tel, {
        de: "loja", texto, em, atendente: eu.id, status: modo() === "demo" ? "simulada" : "enviada", waId,
      })
      const conversa = await atualizarConversa(tel, (c) => {
        if (!c) throw new Error("Conversa não encontrada.")
        if (!c.atendente) c.atendente = eu.id // quem responde primeiro assume
        if (c.etapa === "novo") c.etapa = "atendimento"
        c.naoLidas = 0
        c.ultima = { texto: texto.slice(0, 140), de: "loja", em }
        return c
      })
      return Response.json({ mensagem, conversa })
    }

    return erro("Rota inválida.", 404)
  } catch (e: any) {
    return erro(e?.message || "Algo deu errado.", 409)
  }
}

export const config: Config = {
  path: ["/api/conversas", "/api/conversas/:alvo", "/api/conversas/:alvo/:sub"],
  method: ["GET", "POST"],
}
