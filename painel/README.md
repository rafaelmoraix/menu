# Painel SMM

Aplicativo web para usar a API do **baratoebom.com** (`https://baratoebom.com/api/v2`) com uma interface simples, no computador ou no celular.

## O que ele faz

- **Saldo** sempre visível no topo (clique para atualizar).
- **Serviços**: lista completa com busca, filtro por categoria, preço por 1000, mínimo/máximo e se aceita refill/cancelamento.
- **Novo pedido**: escolha o serviço, cole o link e a quantidade. Mostra o custo estimado na hora e avisa se passar do limite ou do saldo.
  - Suporta **comentários personalizados** (um por linha) e **pacotes**.
  - Suporta **drip-feed** (execuções + intervalo em minutos).
- **Pedidos**: histórico com status, contagem inicial, restante e custo, atualizado automaticamente a cada minuto.
  - **Refill** e **cancelamento** individual ou em lote (até 100 por vez).
  - Status do refill aparece abaixo do nome do serviço.
  - **Importar IDs** de pedidos feitos fora do painel para acompanhar aqui.

## Como rodar

Precisa do [Node.js](https://nodejs.org) 18 ou mais novo. Não tem dependências para instalar.

```bash
cd painel
cp .env.example .env
```

Abra o `.env` e coloque sua chave (pegue na página **Account** do site):

```
API_KEY=sua_chave_aqui
```

Depois:

```bash
npm start
```

Acesse <http://127.0.0.1:3000>.

### Modo demonstração

Sem `API_KEY` (ou com `MOCK=1`), o painel usa dados simulados: dá para testar tudo sem gastar saldo. Aparece a etiqueta **Demonstração** no topo.

```bash
npm run demo
```

## Configuração (`.env`)

| Variável       | Padrão                          | Para que serve |
|----------------|---------------------------------|----------------|
| `API_KEY`      | —                               | Sua chave da API. Sem ela, entra em modo demonstração. |
| `API_URL`      | `https://baratoebom.com/api/v2` | Endereço da API. |
| `PORT`         | `3000`                          | Porta do servidor. |
| `HOST`         | `127.0.0.1`                     | Use `0.0.0.0` para abrir no celular pela mesma rede Wi-Fi. |
| `APP_PASSWORD` | —                               | Senha para entrar no painel (o usuário pode ser qualquer um). |
| `MOCK`         | —                               | `1` força o modo demonstração. |

> **Importante:** quem acessa o painel consegue fazer pedidos com o seu saldo. Se mudar `HOST` para `0.0.0.0` ou publicar na internet, defina `APP_PASSWORD`.

## Como funciona

O navegador nunca vê sua chave. Ele conversa com o `server.js`, que adiciona a chave e repassa para a API (isso também evita bloqueio de CORS).

```
navegador  ──►  server.js (guarda a API_KEY)  ──►  baratoebom.com/api/v2
```

A API não tem um comando para listar pedidos, então o servidor salva os IDs dos pedidos feitos pelo painel em `data/history.json`. Remover um pedido da lista (botão ✕) **não** cancela o pedido.

### Rotas do servidor

| Método | Rota                   | Ação na API |
|--------|------------------------|-------------|
| GET    | `/api/balance`         | `balance` |
| GET    | `/api/services`        | `services` (cache de 5 min; `?refresh=1` força) |
| POST   | `/api/orders`          | `add` |
| GET    | `/api/orders`          | `status` (vários) + `refill_status` (vários) |
| POST   | `/api/orders/refill`   | `refill` (vários) |
| POST   | `/api/orders/cancel`   | `cancel` |
| POST   | `/api/orders/import`   | — (só adiciona IDs ao histórico) |
| DELETE | `/api/orders/:id`      | — (só remove do histórico) |
