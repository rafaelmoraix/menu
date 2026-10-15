# 153 Filmes — site

Site estático (HTML + CSS + JS puro, sem build). Para ver localmente, abra `index.html` ou rode `npx http-server .` nesta pasta.

## Estrutura

- `index.html` — conteúdo de todas as seções
- `css/style.css` — estilos (cores e fontes em `:root`)
- `js/main.js` — interações (intro, menu, filtros, acordeão, contador, timecode)
- `assets/` — símbolo da marca, padrão do hero e logos dos parceiros

## Logos dos parceiros

Coloque o arquivo em `assets/parceiros/` (PNG/SVG com fundo transparente, de preferência) e troque, no card do parceiro em `index.html`, o `<span class="partner__word">…</span>` por:

```html
<img src="assets/parceiros/nome-do-arquivo.png" alt="Nome do parceiro" loading="lazy">
```

## Contato

Preencha `CONTACT.whatsapp` e `CONTACT.email` no topo de `js/main.js` para ativar os botões da seção "Vamos conversar".
