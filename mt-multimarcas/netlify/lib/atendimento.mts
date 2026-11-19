import { getStore } from "@netlify/blobs"
import { randomBytes } from "node:crypto"

/* ============================================================
   Atendimento (CRM de WhatsApp)
   - conv/<telefone>          dados da conversa (quem atende, etapa, notas...)
   - msg/<telefone>/<tempo>   cada mensagem (uma chave por mensagem: nunca se perde)
   - wa/<id do WhatsApp>      atalho para atualizar o status (enviada/lida)
   Sem as credenciais da Meta o sistema roda em MODO DEMONSTRAÇÃO, num
   armazenamento separado, para mostrar à equipe sem tocar no WhatsApp real.
   ============================================================ */

export const ETAPAS = ["novo", "atendimento", "proposta", "vendido", "perdido"] as const
export type Etapa = (typeof ETAPAS)[number]

export type Conversa = {
  tel: string
  nome: string
  atendente: string | null
  etapa: Etapa
  notas: string
  naoLidas: number
  ultima: { texto: string; de: "cliente" | "loja"; em: string } | null
  ultimaEntradaEm: string | null // última msg do cliente (regra das 24h do WhatsApp)
  criadoEm: string
  atualizadoEm: string
}

export type Mensagem = {
  id: string
  de: "cliente" | "loja"
  texto: string
  em: string
  atendente?: string | null // id de quem enviou (mensagens da loja)
  status?: "simulada" | "enviada" | "entregue" | "lida" | "falhou" | "celular"
  waId?: string
}

export const whatsappAtivo = () => !!(Netlify.env.get("WHATSAPP_TOKEN") && Netlify.env.get("WHATSAPP_PHONE_ID"))
export const modo = () => (whatsappAtivo() ? "whatsapp" : "demo")
export const loja = () => getStore({ name: modo() === "demo" ? "atendimento-demo" : "atendimento", consistency: "strong" })

export const limparTel = (t: unknown) => String(t ?? "").replace(/\D/g, "").slice(0, 15)
export const telValido = (t: string) => /^\d{10,15}$/.test(t)
const agora = () => new Date().toISOString()
const chaveMsg = (tel: string, em: string) => `msg/${tel}/${em.replace(/[:.]/g, "-")}-${randomBytes(3).toString("hex")}`

export async function lerConversa(tel: string) {
  return (await loja().getWithMetadata(`conv/${tel}`, { type: "json" })) as { data: Conversa; etag: string } | null
}

/**
 * Altera a conversa só se ninguém mexeu nela no meio tempo (evita, por exemplo,
 * dois atendentes assumirem a mesma conversa ao mesmo tempo).
 * `fn` devolve a conversa nova, ou lança Error para recusar.
 */
export async function atualizarConversa(tel: string, fn: (c: Conversa | null) => Conversa): Promise<Conversa> {
  const store = loja()
  for (let tentativa = 0; tentativa < 6; tentativa++) {
    const atual = await lerConversa(tel)
    const nova = { ...fn(atual ? structuredClone(atual.data) : null), atualizadoEm: agora() }
    const r = atual
      ? await store.setJSON(`conv/${tel}`, nova, { onlyIfMatch: atual.etag })
      : await store.setJSON(`conv/${tel}`, nova, { onlyIfNew: true })
    if (r.modified) return nova
  }
  throw new Error("A conversa mudou ao mesmo tempo. Tente de novo.")
}

export async function salvarMensagem(tel: string, m: Omit<Mensagem, "id">): Promise<Mensagem> {
  const id = chaveMsg(tel, m.em)
  const msg = { ...m, id }
  await loja().setJSON(id, msg)
  if (m.waId) await loja().setJSON(`wa/${m.waId}`, { chave: id })
  return msg
}

export async function listarConversas(): Promise<Conversa[]> {
  const store = loja()
  const { blobs } = await store.list({ prefix: "conv/" })
  const lista = await Promise.all(blobs.map((b) => store.get(b.key, { type: "json" }) as Promise<Conversa | null>))
  return lista.filter((c): c is Conversa => !!c).sort((a, b) => b.atualizadoEm.localeCompare(a.atualizadoEm))
}

export async function listarMensagens(tel: string): Promise<Mensagem[]> {
  const store = loja()
  const { blobs } = await store.list({ prefix: `msg/${tel}/` })
  const lista = await Promise.all(blobs.map((b) => store.get(b.key, { type: "json" }) as Promise<Mensagem | null>))
  return lista.filter((m): m is Mensagem => !!m).sort((a, b) => a.em.localeCompare(b.em))
}

/** Mensagem que chegou do cliente (WhatsApp real ou simulada). */
export async function registrarEntrada(tel: string, nome: string, texto: string, em = agora(), waId?: string) {
  await salvarMensagem(tel, { de: "cliente", texto, em, waId })
  return atualizarConversa(tel, (c) => ({
    tel,
    nome: (nome || c?.nome || "").slice(0, 60) || `+${tel}`,
    atendente: c?.atendente ?? null,
    // Cliente que volta depois de vendido/perdido reabre como novo
    etapa: !c || c.etapa === "vendido" || c.etapa === "perdido" ? "novo" : c.etapa,
    notas: c?.notas ?? "",
    naoLidas: (c?.naoLidas ?? 0) + 1,
    ultima: { texto: texto.slice(0, 140), de: "cliente", em },
    ultimaEntradaEm: em,
    criadoEm: c?.criadoEm ?? em,
    atualizadoEm: em,
  }))
}

/** Envia texto pelo WhatsApp oficial (Cloud API da Meta). */
export async function enviarWhatsApp(tel: string, texto: string): Promise<string> {
  const versao = Netlify.env.get("WHATSAPP_API_VERSION") || "v23.0"
  const r = await fetch(`https://graph.facebook.com/${versao}/${Netlify.env.get("WHATSAPP_PHONE_ID")}/messages`, {
    method: "POST",
    headers: { authorization: `Bearer ${Netlify.env.get("WHATSAPP_TOKEN")}`, "content-type": "application/json" },
    body: JSON.stringify({ messaging_product: "whatsapp", to: tel, type: "text", text: { body: texto, preview_url: true } }),
    signal: AbortSignal.timeout(15000),
  })
  const dados: any = await r.json().catch(() => ({}))
  if (!r.ok) {
    const e = dados?.error
    if (e?.code === 131047) throw new Error("Passaram 24h desde a última mensagem do cliente. O WhatsApp só deixa responder depois que ele mandar uma mensagem nova.")
    throw new Error(`O WhatsApp recusou o envio: ${e?.message || r.status}`)
  }
  return dados?.messages?.[0]?.id || ""
}

/* ---------------- Conversas de demonstração ---------------- */
function haMin(min: number) { return new Date(Date.now() - min * 60_000).toISOString() }

export async function semearDemo(ids: string[]) {
  const [a1, a2, a3] = [ids[0] ?? null, ids[1] ?? null, ids[2] ?? null]
  const roteiro: Array<{ tel: string; nome: string; atendente: string | null; etapa: Etapa; notas?: string; naoLidas: number; msgs: Array<[number, "cliente" | "loja", string, (string | null)?]> }> = [
    {
      tel: "5511987654321", nome: "Carlos Henrique", atendente: null, etapa: "novo", naoLidas: 2,
      msgs: [
        [6, "cliente", "Boa tarde! Vocês têm Fazer 250 2019?"],
        [5, "cliente", "Se tiver, aceita minha Titan 2016 na troca?"],
      ],
    },
    {
      tel: "5511976543210", nome: "Juliana Martins", atendente: null, etapa: "novo", naoLidas: 1,
      msgs: [[2, "cliente", "Oi, vi a PCX 160 no site. Ainda está disponível? Qual a menor entrada?"]],
    },
    {
      tel: "5511965432109", nome: "Rafael Souza", atendente: a1, etapa: "atendimento", naoLidas: 0,
      notas: "Quer XRE 300. Tem entrada de R$ 8 mil. Prefere cor branca.",
      msgs: [
        [95, "cliente", "Olá, a XRE 300 2023 ainda tá aí?"],
        [93, "loja", "Olá Rafael! Tá sim, branca, 11.200 km, revisada. Quer que eu mande mais fotos?", a1],
        [90, "cliente", "Quero sim! E dá pra financiar em 36x?"],
        [88, "loja", "Dá sim! Com R$ 8 mil de entrada fica em torno de R$ 820 por mês. Vou te mandar a simulação certinha.", a1],
      ],
    },
    {
      tel: "5511954321098", nome: "Patrícia Lima", atendente: a2, etapa: "proposta", naoLidas: 1,
      notas: "Proposta: Ninja 400 por R$ 35.500 à vista. Aguardando resposta.",
      msgs: [
        [300, "cliente", "Boa noite, qual o menor valor à vista na Ninja 400?"],
        [290, "loja", "Boa noite Patrícia! À vista consigo fazer por R$ 35.500, com transferência inclusa.", a2],
        [20, "cliente", "Vou conversar com meu marido e te falo amanhã cedo 😊"],
      ],
    },
    {
      tel: "5511943210987", nome: "Marcos Vinícius", atendente: a3, etapa: "vendido", naoLidas: 0,
      notas: "Vendida CG 160 Titan 0 km. Entrega feita.",
      msgs: [
        [1500, "cliente", "Fechado então, passo aí amanhã pra assinar."],
        [1490, "loja", "Perfeito Marcos! Te espero às 10h. Traz RG, CPF e comprovante de residência.", a3],
        [200, "cliente", "Moto chegou certinha, muito obrigado pela atenção!"],
        [195, "loja", "Nós que agradecemos! Boas viagens e qualquer coisa estamos aqui 🏍️", a3],
      ],
    },
    {
      tel: "5511932109876", nome: "Fernanda Rocha", atendente: a1, etapa: "perdido", naoLidas: 0,
      notas: "Comprou em outra loja (preço).",
      msgs: [
        [3000, "cliente", "Vocês têm Biz 125?"],
        [2990, "loja", "Oi Fernanda! No momento não, mas posso procurar pra você. Até quanto quer investir?", a1],
        [2900, "cliente", "Ah, já achei em outro lugar, obrigada!"],
      ],
    },
  ]

  for (const r of roteiro) {
    for (const [min, de, texto, atendente] of r.msgs) {
      await salvarMensagem(r.tel, { de, texto, em: haMin(min), ...(de === "loja" ? { atendente: atendente ?? null, status: "simulada" as const } : {}) })
    }
    const ultima = r.msgs[r.msgs.length - 1]
    const entrada = [...r.msgs].reverse().find((m) => m[1] === "cliente")
    const c: Conversa = {
      tel: r.tel, nome: r.nome, atendente: r.atendente, etapa: r.etapa, notas: r.notas || "", naoLidas: r.naoLidas,
      ultima: { texto: ultima[2], de: ultima[1], em: haMin(ultima[0]) },
      ultimaEntradaEm: entrada ? haMin(entrada[0]) : null,
      criadoEm: haMin(r.msgs[0][0]), atualizadoEm: haMin(ultima[0]),
    }
    await loja().setJSON(`conv/${r.tel}`, c)
  }
  await loja().setJSON("demo-semeada", { em: agora() })
}

export async function apagarDemo() {
  const store = getStore({ name: "atendimento-demo", consistency: "strong" })
  const { blobs } = await store.list()
  await Promise.all(blobs.map((b) => store.delete(b.key)))
}
