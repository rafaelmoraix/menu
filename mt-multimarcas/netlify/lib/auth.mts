import { createHmac, timingSafeEqual } from "node:crypto"

const VALIDADE_MS = 30 * 24 * 60 * 60 * 1000 // 30 dias

function senhaAdmin(): string | undefined {
  const s = Netlify.env.get("ADMIN_PASSWORD")
  return s && s.length >= 6 ? s : undefined
}

function assinar(dado: string, chave: string): string {
  return createHmac("sha256", chave).update(`mt-admin:${dado}`).digest("base64url")
}

function iguais(a: string, b: string): boolean {
  const ha = createHmac("sha256", "cmp").update(a).digest()
  const hb = createHmac("sha256", "cmp").update(b).digest()
  return timingSafeEqual(ha, hb)
}

/** Confere a senha e devolve um token assinado, ou null. */
export function login(senha: unknown): string | null {
  const correta = senhaAdmin()
  if (!correta || typeof senha !== "string" || !iguais(senha, correta)) return null
  const exp = String(Date.now() + VALIDADE_MS)
  return `${exp}.${assinar(exp, correta)}`
}

/** true se o pedido traz um token válido no cabeçalho Authorization. */
export function autorizado(req: Request): boolean {
  const correta = senhaAdmin()
  if (!correta) return false
  const token = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "")
  const [exp, sig] = token.split(".")
  if (!exp || !sig || !/^\d+$/.test(exp) || Number(exp) < Date.now()) return false
  return iguais(sig, assinar(exp, correta))
}

export const naoAutorizado = () => Response.json({ erro: "Sessão expirada. Entre novamente." }, { status: 401 })
