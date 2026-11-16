import type { Config, Context } from "@netlify/functions"
import { randomBytes } from "node:crypto"
import { autorizado, naoAutorizado } from "../lib/auth.mts"
import { fotosStore } from "../lib/motos.mts"

const TIPOS: Record<string, string> = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" }
const CHAVE = /^[A-Za-z0-9_-]+\.(jpg|png|webp)$/
const MAX_BYTES = 4 * 1024 * 1024

// GET    /fotos/:chave     -> exibe a foto (público)
// POST   /api/fotos        -> envia uma foto (admin) — corpo = bytes da imagem
// DELETE /api/fotos/:chave -> apaga uma foto (admin)
export default async (req: Request, context: Context) => {
  const store = fotosStore()
  const chave = context.params.chave

  if (req.method === "GET") {
    if (!chave || !CHAVE.test(chave)) return new Response("Não encontrada", { status: 404 })
    const foto = await store.getWithMetadata(chave, { type: "arrayBuffer" })
    if (foto === null) return new Response("Não encontrada", { status: 404 })
    return new Response(foto.data, {
      headers: {
        "content-type": (foto.metadata?.tipo as string) || "image/jpeg",
        "cache-control": "public, max-age=31536000, immutable",
      },
    })
  }

  if (!autorizado(req)) return naoAutorizado()

  if (req.method === "DELETE") {
    if (!chave || !CHAVE.test(chave)) return Response.json({ erro: "Foto inválida." }, { status: 400 })
    await store.delete(chave)
    return Response.json({ ok: true })
  }

  const tipo = (req.headers.get("content-type") || "").split(";")[0].trim()
  const ext = TIPOS[tipo]
  if (!ext) return Response.json({ erro: "Envie uma imagem JPG, PNG ou WEBP." }, { status: 415 })
  const dados = await req.arrayBuffer()
  if (!dados.byteLength) return Response.json({ erro: "Imagem vazia." }, { status: 400 })
  if (dados.byteLength > MAX_BYTES) return Response.json({ erro: "Imagem muito grande (máx. 4 MB)." }, { status: 413 })

  const nova = `${Date.now().toString(36)}-${randomBytes(6).toString("hex")}.${ext}`
  await store.set(nova, dados, { metadata: { tipo } })
  return Response.json({ url: `/fotos/${nova}` })
}

export const config: Config = {
  path: ["/fotos/:chave", "/api/fotos", "/api/fotos/:chave"],
  method: ["GET", "POST", "DELETE"],
}
