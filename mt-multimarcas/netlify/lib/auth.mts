import { createHmac, timingSafeEqual } from "node:crypto"

const VALIDADE_MS = 30 * 24 * 60 * 60 * 1000 // 30 dias

export type Usuario = { id: string; nome: string; papel: "gerente" | "atendente" }
type Conta = Usuario & { senha: string }

/**
 * Equipe que pode entrar no painel:
 *  - Gerente: senha na variável ADMIN_PASSWORD
 *  - Atendentes: variável ATENDENTES, um JSON como
 *    [{"id":"marx","nome":"Marx","senha":"..."}, ...]
 */
function contas(): Conta[] {
  const lista: Conta[] = []
  const adm = Netlify.env.get("ADMIN_PASSWORD")
  if (adm && adm.length >= 6) lista.push({ id: "gerente", nome: "Gerente", papel: "gerente", senha: adm })
  try {
    const extra = JSON.parse(Netlify.env.get("ATENDENTES") || "[]")
    for (const a of Array.isArray(extra) ? extra : []) {
      const id = String(a?.id || "").toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 20)
      if (!id || id === "gerente" || typeof a?.senha !== "string" || a.senha.length < 6) continue
      lista.push({ id, nome: String(a.nome || id).slice(0, 40), papel: "atendente", senha: a.senha })
    }
  } catch { /* ATENDENTES mal formatado: ignora */ }
  return lista
}

/** Lista pública da equipe (sem senhas), para a tela de login e o painel. */
export function equipe(): Usuario[] {
  return contas().map(({ id, nome, papel }) => ({ id, nome, papel }))
}

function assinar(dado: string, chave: string): string {
  return createHmac("sha256", chave).update(`mt-admin:${dado}`).digest("base64url")
}

function iguais(a: string, b: string): boolean {
  const ha = createHmac("sha256", "cmp").update(a).digest()
  const hb = createHmac("sha256", "cmp").update(b).digest()
  return timingSafeEqual(ha, hb)
}

/** Confere usuário e senha e devolve { token, usuario }, ou null. */
export function login(usuario: unknown, senha: unknown): { token: string; usuario: Usuario } | null {
  if (typeof senha !== "string") return null
  const id = typeof usuario === "string" && usuario ? usuario.toLowerCase() : "gerente"
  const conta = contas().find((c) => c.id === id)
  if (!conta || !iguais(senha, conta.senha)) return null
  const exp = String(Date.now() + VALIDADE_MS)
  return {
    token: `${conta.id}.${exp}.${assinar(`${conta.id}:${exp}`, conta.senha)}`,
    usuario: { id: conta.id, nome: conta.nome, papel: conta.papel },
  }
}

/** Usuário logado (token válido no cabeçalho Authorization), ou null. */
export function autorizado(req: Request): Usuario | null {
  const token = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "")
  const [id, exp, sig] = token.split(".")
  if (!id || !exp || !sig || !/^\d+$/.test(exp) || Number(exp) < Date.now()) return null
  const conta = contas().find((c) => c.id === id)
  // A assinatura usa a senha da pessoa: trocar a senha desconecta quem estava logado
  if (!conta || !iguais(sig, assinar(`${id}:${exp}`, conta.senha))) return null
  return { id: conta.id, nome: conta.nome, papel: conta.papel }
}

export const naoAutorizado = () => Response.json({ erro: "Sessão expirada. Entre novamente." }, { status: 401 })
