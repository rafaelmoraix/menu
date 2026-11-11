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
- Layout responsivo (celular, tablet e computador) nas cores do logo, preto e dourado

## Como atualizar

Tudo o que muda no dia a dia está em **`js/dados.js`**:

1. **Dados da loja** (`LOJA`): WhatsApp (só números, ex.: `5511999998888`), telefone, endereço, Instagram, horários e a taxa usada nas simulações.
2. **Motos** (`MOTOS`): cada bloco `{ ... }` é uma moto.
   - **Adicionar:** copie um bloco, cole e altere. O `id` precisa ser único (ex.: `"honda-cb-500f-2023"`).
   - **Vendida:** mude `status` para `"vendida"`. A moto sai do catálogo e só aparece com o filtro "Mostrar vendidas".
   - **Destaque:** `destaque: true` coloca a moto em "Destaques da semana" (no máximo 4 aparecem).
   - **Fotos:** coloque as imagens em `img/motos/` e liste no campo `fotos`:
     ```js
     fotos: ["img/motos/cb500f-1.jpg", "img/motos/cb500f-2.jpg"],
     ```
     A primeira foto é a capa. Sem fotos, o site mostra uma ilustração automática. Use fotos na horizontal (proporção 4:3 ou 16:10).

> As motos que já estão no arquivo são **exemplos**. Troque pelos dados e preços reais do estoque.

## Link direto para uma moto

Cada moto tem um link próprio para mandar a clientes: `index.html#moto=<id>`.
O botão **Compartilhar** na página da moto já copia esse link.

## Como ver e publicar

- **Ver no computador:** dê dois cliques em `index.html`.
- **Publicar grátis:** envie a pasta `mt-multimarcas` para o **Netlify** (arraste a pasta em app.netlify.com/drop) ou ative o **GitHub Pages** neste repositório.

## Estrutura

```
mt-multimarcas/
├── index.html            página do site
├── css/style.css         visual
├── js/dados.js           ← EDITE AQUI: loja e motos
├── js/app.js             funcionamento (filtros, modal, simulador)
├── img/                  logos (e a pasta motos/ para as fotos)
└── vendor/fontawesome/   ícones (incluídos para funcionar sem internet)
```
