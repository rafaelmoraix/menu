import type { Config } from "@netlify/functions"
import { autorizado, equipe, login } from "../lib/auth.mts"

// POST /api/login  { usuario, senha } -> { token, usuario }
// GET  /api/login                     -> confere o token enviado -> { usuario }
// GET  /api/login?equipe=1            -> nomes da equipe para a tela de login
export default async (req: Request) => {
  if (req.method === "GET") {
    if (new URL(req.url).searchParams.get("equipe")) {
      return Response.json({ equipe: equipe().map(({ id, nome }) => ({ id, nome })) })
    }
    const u = autorizado(req)
    return u
      ? Response.json({ ok: true, usuario: u })
      : Response.json({ erro: "Sessão expirada. Entre novamente." }, { status: 401 })
  }

  let corpo: any = {}
  try { corpo = await req.json() } catch { /* corpo inválido */ }
  const r = login(corpo?.usuario, corpo?.senha)
  if (!r) return Response.json({ erro: "Usuário ou senha incorretos." }, { status: 401 })
  return Response.json(r)
}

export const config: Config = {
  path: "/api/login",
  method: ["GET", "POST"],
  // Freia tentativas de adivinhar a senha
  rateLimit: { windowLimit: 20, windowSize: 60, aggregateBy: ["ip", "domain"] },
}
