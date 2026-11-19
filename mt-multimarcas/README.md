# MT Multimarcas — Site com catálogo de motos

Site estático (HTML + CSS + JavaScript puro, sem instalação) da **MT Multimarcas — Excelência em duas rodas**.

## O que tem no site

- **Catálogo** com busca e filtros por marca, categoria, condição (0 km/seminova) e preço, além de ordenação
- **Destaques da semana** e atalhos por marca
- **Página de detalhes** de cada moto (ficha técnica, opcionais, galeria de fotos e link para compartilhar)
- Botões de **WhatsApp** com mensagem pronta ("Tenho interesse na Honda CB 500F 2023…")
- **Simulador de financiamento** (entrada + 12/24/36/48x)
- Formulário **"Avaliamos sua moto"**, que manda os dados pelo WhatsApp
- Seções **Sobre** e **Contato** (endereço com link para o Google Maps, Instagram, horários)
- **Painel admin** em `/admin` para cadastrar motos e fotos pelo celular
- Layout responsivo (celular, tablet e computador) nas cores do logo, preto e dourado

## Painel admin (cadastro das motos)

Acesse **`/admin`** no endereço do site (ex.: `https://mt-multimarcas-catalogo.netlify.app/admin`) e entre com a senha.

No painel dá para, inclusive pelo celular:
- **Cadastrar moto** com fotos tiradas na hora ou da galeria (a primeira é a capa; a ⭐ troca a capa)
- **Editar**, **excluir**, marcar como **vendida** ou como **destaque**
- Buscar e filtrar entre "à venda" e "vendidas"

As mudanças aparecem no site na hora. As motos e as fotos ficam guardadas no **Netlify Blobs** do próprio site.

**Senha:** fica na variável de ambiente `ADMIN_PASSWORD` do projeto na Netlify
(Project configuration → Environment variables). Para trocar, altere o valor e publique o site de novo.
Trocar a senha desconecta quem estiver logado. O login é limitado a 10 tentativas por minuto.

## Buscar moto fora da loja (aba "Buscar moto" do painel)

- Digite modelo, ano, preço máximo e estado.
- **Já tem na sua loja:** mostra motos parecidas do próprio estoque.
- **Botões de atalho** (OLX, Marketplace, Mercado Livre, Google): abrem a busca pronta no site. Não gastam cota.
- **Anúncios encontrados na internet:** resultados do Google via **SearchApi** (searchapi.io) ou **SerpAPI**.
  O painel descobre o serviço pelo formato da chave (a do SerpAPI tem 64 caracteres; a variável `BUSCA_PROVEDOR` força um dos dois).
  A mesma busca repetida em até 6 horas não gasta cota. A chave fica na variável `BUSCA_API_KEY` da Netlify.
- **Procuras:** salve o pedido do cliente (nome e WhatsApp) e repita a busca depois com um toque.

## Atendimento (CRM de WhatsApp) — aba "Atendimento" do painel

- Cada pessoa entra com **seu usuário**: Gerente (`ADMIN_PASSWORD`) e atendentes (`ATENDENTES`, JSON
  `[{"id":"marx","nome":"Marx","senha":"..."}]`). Trocar a senha de alguém desconecta essa pessoa.
- Conversa chega em **Novas** para todos. Quem toca em **Assumir** fica dono; os outros veem
  "Fulano está atendendo" e não conseguem responder (o servidor também bloqueia). Dono ou gerente
  podem **transferir** ou **liberar**. Etapas: novo → em atendimento → proposta → vendido/perdido.
- Notas internas do cliente, respostas rápidas, enviar moto do estoque com link, aviso sonoro de
  conversa nova, resumo por atendente.
- **Modo demonstração** (enquanto o WhatsApp não está ligado): conversas de teste num armazenamento
  separado, botão "Simular cliente" e, para o gerente, "Reiniciar".

### Ligar o WhatsApp oficial (Meta Cloud API, modo coexistência)

Variáveis na Netlify (depois, publicar de novo):

| Variável | O que é |
|---|---|
| `WHATSAPP_TOKEN` | Token permanente (usuário do sistema no Meta Business) |
| `WHATSAPP_PHONE_ID` | "Phone number ID" do número da loja |
| `WHATSAPP_APP_SECRET` | "App secret" do app na Meta (confere a assinatura do webhook) |
| `WHATSAPP_VERIFY_TOKEN` | Já criado; colar o mesmo valor no campo "Verify token" da Meta |
| `WHATSAPP_API_VERSION` | Opcional (padrão `v23.0`) |

Webhook para cadastrar na Meta: `https://mt-multimarcas-catalogo.netlify.app/api/whatsapp/webhook`
(assinar os campos **messages** e, na coexistência, **smb_message_echoes**).
Com `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_ID` preenchidos, o modo demonstração some e as conversas
reais passam a aparecer.

## Dados da loja

WhatsApp, telefone, endereço, Instagram, horários e a taxa da simulação ficam em **`site/js/dados.js`** (objeto `LOJA`).
As motos que estão nesse arquivo (`MOTOS`) são só **exemplos**: aparecem enquanto nada for salvo no painel.

## Link direto para uma moto

Cada moto tem um link próprio para mandar a clientes: `/#moto=<id>`.
O botão **Compartilhar** na página da moto já copia esse link.

## Estrutura

```
mt-multimarcas/
├── site/                     o que vai para o ar
│   ├── index.html            página do site
│   ├── admin/                painel admin (index.html, admin.css, admin.js)
│   ├── css/ js/ img/         visual, scripts (dados.js = dados da loja) e logos
│   └── vendor/fontawesome/   ícones
├── netlify/
│   ├── functions/            API: login, motos, fotos, busca, procuras, conversas e /api/whatsapp/webhook
│   └── lib/                  login (token assinado) e validação das motos
├── netlify.toml              configuração da Netlify
└── package.json
```

## Publicar

O site está na Netlify (projeto `mt-multimarcas-catalogo`). Ele precisa da Netlify por causa do painel:
funções + Blobs. Abrir o `site/index.html` direto no computador mostra só as motos de exemplo.
