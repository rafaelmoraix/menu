import type { Config } from "@netlify/functions"
import { autorizado, login } from "../lib/auth.mts"

// POST /api/login  { senha }  -> { token }
// GET  /api/login             -> confere se o token enviado ainda vale
export default async (req: Request) => {
  if (req.method === "GET") {
    return autorizado(req)
      ? Response.json({ ok: true })
      : Response.json({ erro: "Sessão expirada. Entre novamente." }, { status: 401 })
  }

  let senha: unknown
  try { senha = (await req.json())?.senha } catch { /* corpo inválido */ }
  const token = login(senha)
  if (!token) return Response.json({ erro: "Senha incorreta." }, { status: 401 })
  return Response.json({ token })
}

export const config: Config = {
  path: "/api/login",
  method: ["GET", "POST"],
  // Freia tentativas de adivinhar a senha
  rateLimit: { windowLimit: 10, windowSize: 60, aggregateBy: ["ip", "domain"] },
}
