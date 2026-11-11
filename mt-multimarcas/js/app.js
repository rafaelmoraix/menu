/* =========================================================
   MT MULTIMARCAS — Lógica do catálogo
   (os dados ficam em js/dados.js)
   ========================================================= */
(() => {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const NUM = new Intl.NumberFormat("pt-BR");
  const brl = (v) => BRL.format(v);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- Utilidades ---------- */
  function parcela(valor, n = LOJA.parcelasPadrao, taxa = LOJA.taxaMensal) {
    if (valor <= 0) return 0;
    if (!taxa) return valor / n;
    return (valor * taxa) / (1 - Math.pow(1 + taxa, -n));
  }

  function linkWhats(msg) {
    return `https://wa.me/${LOJA.whatsapp}?text=${encodeURIComponent(msg)}`;
  }

  function nomeMoto(m) { return `${m.marca} ${m.modelo}`; }

  function msgInteresse(m) {
    return `Olá! Tenho interesse na ${nomeMoto(m)} ${m.ano} (${NUM.format(m.km)} km) anunciada por ${brl(m.preco)} no site da MT Multimarcas. Ainda está disponível?`;
  }

  function toast(texto) {
    const t = $("#toast");
    t.textContent = texto;
    t.classList.add("visivel");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("visivel"), 2600);
  }

  /* ---------- Ilustração automática quando não há foto ---------- */
  function svgMoto(categoria) {
    const grad = `<defs>
      <linearGradient id="gOuro" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#fbe39b"/><stop offset=".45" stop-color="#e8b04a"/><stop offset="1" stop-color="#9c6516"/>
      </linearGradient>
      <linearGradient id="gEsc" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#3a2f1f"/><stop offset="1" stop-color="#15110b"/>
      </linearGradient></defs>`;
    const roda = (cx) => `
      <circle cx="${cx}" cy="172" r="48" fill="#0c0a07" stroke="#2c2418" stroke-width="12"/>
      <circle cx="${cx}" cy="172" r="34" fill="none" stroke="url(#gOuro)" stroke-width="3"/>
      <circle cx="${cx}" cy="172" r="9" fill="url(#gOuro)"/>`;

    if (categoria === "Scooter") {
      return `<svg viewBox="0 0 400 240" aria-hidden="true">${grad}
        <ellipse cx="200" cy="224" rx="170" ry="8" fill="#000" opacity=".5"/>
        ${roda(92)}${roda(312)}
        <path d="M60 128 C70 100 120 92 165 100 L235 104 L250 150 L120 160 C95 160 70 150 60 128Z" fill="url(#gOuro)"/>
        <path d="M110 98 L200 96 C210 96 214 104 206 108 L118 112 Z" fill="url(#gEsc)"/>
        <path d="M232 150 L262 60 L282 60 L300 150 Z" fill="url(#gOuro)"/>
        <path d="M262 60 L254 40 L290 34 L292 46 Z" fill="url(#gEsc)"/>
        <path d="M272 120 L312 172" stroke="#3a2f1f" stroke-width="10" stroke-linecap="round"/>
        <circle cx="292" cy="74" r="8" fill="#fff6d8"/>
      </svg>`;
    }

    const alto = categoria === "Trail" || categoria === "Big Trail";
    return `<svg viewBox="0 0 400 240" aria-hidden="true">${grad}
      <ellipse cx="200" cy="224" rx="170" ry="8" fill="#000" opacity=".5"/>
      ${roda(92)}${roda(308)}
      <path d="M92 172 L190 146" stroke="#3a2f1f" stroke-width="12" stroke-linecap="round"/>
      <path d="M308 172 L272 ${alto ? 62 : 74}" stroke="#4a3c27" stroke-width="10" stroke-linecap="round"/>
      <rect x="170" y="122" width="74" height="54" rx="10" fill="url(#gEsc)" stroke="#4a3c27" stroke-width="2"/>
      <path d="M182 176 L120 150 L112 138 L186 160 Z" fill="#5b4a30"/>
      <path d="M62 ${alto ? 92 : 98} L132 104 L132 118 L92 116 Z" fill="url(#gOuro)"/>
      <path d="M118 102 L184 98 L188 116 L124 120 Z" fill="url(#gEsc)"/>
      <path d="M176 ${alto ? 92 : 98} C190 70 250 66 272 ${alto ? 80 : 86} L262 122 L182 122 Z" fill="url(#gOuro)"/>
      <path d="M262 ${alto ? 64 : 74} L296 ${alto ? 56 : 64}" stroke="#c9c2b5" stroke-width="5" stroke-linecap="round"/>
      ${alto
        ? `<path d="M262 96 L292 70 L300 104 Z" fill="url(#gOuro)"/><path d="M286 52 L298 30 L306 56 Z" fill="url(#gEsc)" opacity=".9"/>`
        : `<circle cx="290" cy="94" r="10" fill="#fff6d8"/>`}
      ${alto ? `<path d="M286 140 Q310 120 336 132" stroke="url(#gOuro)" stroke-width="6" fill="none" stroke-linecap="round"/>` : ""}
    </svg>`;
  }

  function midiaHTML(m, i = 0) {
    if (m.fotos && m.fotos.length) {
      return `<img src="${esc(m.fotos[i])}" alt="${esc(nomeMoto(m))}" loading="lazy">`;
    }
    return `<div class="ilustra"><span class="ilustra__marca">${esc(m.marca)}</span>${svgMoto(m.categoria)}</div>`;
  }

  /* ---------- Card ---------- */
  function cardHTML(m) {
    const vendida = m.status === "vendida";
    const tags = [
      m.condicao === "Nova" ? `<span class="tag tag--nova">0 km</span>` : "",
      m.destaque && !vendida ? `<span class="tag">Destaque</span>` : "",
      vendida ? `<span class="tag tag--vendida">Vendida</span>` : "",
    ].join("");

    return `
      <article class="card${vendida ? " card--vendida" : ""}" data-id="${esc(m.id)}" tabindex="0" aria-label="${esc(nomeMoto(m))} ${m.ano}">
        <div class="card__foto">
          <div class="card__selos">${tags}</div>
          ${midiaHTML(m)}
        </div>
        <div class="card__corpo">
          <span class="card__marca">${esc(m.marca)}</span>
          <h3 class="card__titulo">${esc(m.modelo)}</h3>
          <ul class="specs">
            <li><i class="fa-regular fa-calendar"></i>${m.ano}</li>
            <li><i class="fa-solid fa-gauge-high"></i>${m.km === 0 ? "0 km" : NUM.format(m.km) + " km"}</li>
            <li><i class="fa-solid fa-gear"></i>${m.cilindrada} cc</li>
            <li><i class="fa-solid fa-tag"></i>${esc(m.categoria)}</li>
          </ul>
          <div class="card__rodape">
            <div>
              <div class="preco">${brl(m.preco)}</div>
              ${vendida ? `<div class="parcela">Consulte similares</div>` :
                `<div class="parcela">ou <b>${LOJA.parcelasPadrao}x de ${brl(parcela(m.preco * 0.8))}</b>*</div>`}
            </div>
            <a class="card__whats" href="${linkWhats(vendida ? `Olá! Vi que a ${nomeMoto(m)} foi vendida. Vocês têm alguma similar?` : msgInteresse(m))}"
               target="_blank" rel="noopener" aria-label="Chamar no WhatsApp sobre ${esc(nomeMoto(m))}" data-whats-card>
              <i class="fa-brands fa-whatsapp"></i>
            </a>
          </div>
        </div>
      </article>`;
  }

  /* ---------- Filtros ---------- */
  const f = {
    busca: $("#fBusca"), marca: $("#fMarca"), categoria: $("#fCategoria"),
    condicao: $("#fCondicao"), preco: $("#fPreco"), ordem: $("#fOrdem"), vendidas: $("#fVendidas"),
  };

  const normalizar = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const unicos = (campo) => [...new Set(MOTOS.map((m) => m[campo]))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const disponiveis = () => MOTOS.filter((m) => m.status !== "vendida");

  function preencherSelects() {
    unicos("marca").forEach((v) => f.marca.add(new Option(v, v)));
    unicos("categoria").forEach((v) => f.categoria.add(new Option(v, v)));
  }

  function chipsMarcas() {
    const cont = $("#marcasChips");
    const contagem = {};
    disponiveis().forEach((m) => (contagem[m.marca] = (contagem[m.marca] || 0) + 1));
    const chips = [`<button type="button" class="chip ativo" data-marca="">Todas <small>${disponiveis().length}</small></button>`];
    Object.keys(contagem).sort().forEach((marca) =>
      chips.push(`<button type="button" class="chip" data-marca="${esc(marca)}">${esc(marca)} <small>${contagem[marca]}</small></button>`));
    cont.innerHTML = chips.join("");
    cont.addEventListener("click", (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      f.marca.value = b.dataset.marca;
      aplicar();
      document.getElementById("catalogo").scrollIntoView();
    });
  }

  function sincronizarChips() {
    $$(".chip").forEach((c) => c.classList.toggle("ativo", c.dataset.marca === f.marca.value));
  }

  function aplicar() {
    const termo = normalizar(f.busca.value.trim());
    const max = Number(f.preco.value) || Infinity;
    let lista = MOTOS.filter((m) =>
      (f.vendidas.checked || m.status !== "vendida") &&
      (!f.marca.value || m.marca === f.marca.value) &&
      (!f.categoria.value || m.categoria === f.categoria.value) &&
      (!f.condicao.value || m.condicao === f.condicao.value) &&
      m.preco <= max &&
      (!termo || normalizar(`${m.marca} ${m.modelo} ${m.categoria} ${m.cor} ${m.ano}`).includes(termo))
    );

    const ordem = {
      recentes: (a, b) => b.ano - a.ano || a.km - b.km,
      menor: (a, b) => a.preco - b.preco,
      maior: (a, b) => b.preco - a.preco,
      km: (a, b) => a.km - b.km,
    }[f.ordem.value];
    lista.sort((a, b) => (a.status === "vendida") - (b.status === "vendida") || ordem(a, b));

    $("#gradeCatalogo").innerHTML = lista.map(cardHTML).join("");
    $("#vazio").hidden = lista.length > 0;
    const n = lista.length;
    $("#contador").innerHTML = `<b>${n}</b> ${n === 1 ? "moto encontrada" : "motos encontradas"}`;
    sincronizarChips();
  }

  function limpar() {
    f.busca.value = ""; f.marca.value = ""; f.categoria.value = ""; f.condicao.value = "";
    f.preco.value = ""; f.ordem.value = "recentes"; f.vendidas.checked = false;
    aplicar();
  }

  /* ---------- Modal de detalhes ---------- */
  const modal = $("#modal");
  let ultimoFoco = null;

  function abrirModal(id, atualizarHash = true) {
    const m = MOTOS.find((x) => x.id === id);
    if (!m) return;
    ultimoFoco = document.activeElement;
    const vendida = m.status === "vendida";

    $("#mMarca").textContent = m.marca;
    $("#mTitulo").textContent = `${m.modelo} ${m.ano}`;
    $("#mPreco").innerHTML = `<div class="preco">${brl(m.preco)}</div>` +
      (vendida ? `<div class="parcela"><b>Moto vendida</b> — consulte similares</div>`
               : `<div class="parcela">ou <b>${LOJA.parcelasPadrao}x de ${brl(parcela(m.preco * 0.8))}</b> com 20% de entrada*</div>`);

    const ficha = [
      ["Ano", m.ano], ["Quilometragem", m.km === 0 ? "0 km" : `${NUM.format(m.km)} km`],
      ["Cilindrada", `${m.cilindrada} cc`], ["Categoria", m.categoria],
      ["Cor", m.cor], ["Combustível", m.combustivel],
    ];
    $("#mFicha").innerHTML = ficha.map(([k, v]) => `<li><small>${k}</small><b>${esc(v)}</b></li>`).join("");
    $("#mDescricao").textContent = m.descricao || "";
    $("#mOpcionais").innerHTML = m.opcionais?.length
      ? `<div class="opcionais">${m.opcionais.map((o) => `<span><i class="fa-solid fa-check"></i>${esc(o)}</span>`).join("")}</div>` : "";

    // Galeria
    const foto = $("#mFoto"), minis = $("#mMiniaturas");
    foto.innerHTML = midiaHTML(m, 0);
    minis.innerHTML = (m.fotos?.length > 1)
      ? m.fotos.map((src, i) => `<button type="button" data-i="${i}" class="${i === 0 ? "ativo" : ""}" aria-label="Foto ${i + 1}"><img src="${esc(src)}" alt=""></button>`).join("")
      : "";
    minis.onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      foto.innerHTML = midiaHTML(m, Number(b.dataset.i));
      $$("button", minis).forEach((x) => x.classList.toggle("ativo", x === b));
    };

    const w = $("#mWhats");
    w.href = linkWhats(vendida ? `Olá! Vi que a ${nomeMoto(m)} foi vendida. Vocês têm alguma similar?` : msgInteresse(m));
    w.innerHTML = vendida ? `<i class="fa-brands fa-whatsapp"></i> Quero uma similar` : `<i class="fa-brands fa-whatsapp"></i> Tenho interesse`;

    $("#mCompartilhar").onclick = async () => {
      const url = `${location.origin}${location.pathname}#moto=${m.id}`;
      const dados = { title: `${nomeMoto(m)} ${m.ano} | MT Multimarcas`, text: `${nomeMoto(m)} ${m.ano} por ${brl(m.preco)}`, url };
      try {
        if (navigator.share) await navigator.share(dados);
        else { await navigator.clipboard.writeText(url); toast("Link copiado!"); }
      } catch (_) { /* usuário cancelou */ }
    };

    modal.hidden = false;
    document.body.classList.add("travado");
    $(".modal__fechar", modal).focus();
    if (atualizarHash) history.replaceState(null, "", `#moto=${m.id}`);
  }

  function fecharModal() {
    if (modal.hidden) return;
    modal.hidden = true;
    document.body.classList.remove("travado");
    if (location.hash.startsWith("#moto=")) history.replaceState(null, "", location.pathname + location.search);
    ultimoFoco?.focus?.();
  }

  /* ---------- Simulador ---------- */
  function simulador() {
    const valor = $("#sValor"), entrada = $("#sEntrada"), prazos = $("#sPrazos");
    let n = 48;
    const lerValor = () => Number(valor.value.replace(/\D/g, "")) || 0;

    function calc() {
      const v = lerValor();
      const pct = Number(entrada.value);
      const ent = v * pct / 100;
      const p = parcela(v - ent, n);
      $("#sEntradaTxt").textContent = `${pct}% (${brl(ent)})`;
      $("#sParcela").textContent = `${n}x ${brl(p)}`;
      $("#sEnviar").href = linkWhats(
        `Olá! Simulei no site: moto de ${brl(v)}, entrada de ${brl(ent)} e ${n}x de aproximadamente ${brl(p)}. Podem fazer uma análise de crédito?`);
    }
    valor.addEventListener("input", () => {
      const v = lerValor();
      valor.value = v ? NUM.format(v) : "";
      calc();
    });
    entrada.addEventListener("input", calc);
    prazos.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      n = Number(b.dataset.n);
      $$("button", prazos).forEach((x) => {
        x.classList.toggle("ativo", x === b);
        x.setAttribute("aria-checked", x === b);
      });
      calc();
    });
    calc();
  }

  /* ---------- Contato ---------- */
  function contato() {
    $("#cEndereco").textContent = LOJA.endereco;
    $("#cMapa").href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(LOJA.endereco)}`;
    $("#cFone").textContent = LOJA.telefoneExibicao;
    $("#cFone").dataset.msg = "Olá! Vim pelo site da MT Multimarcas.";
    $("#cInsta").textContent = `@${LOJA.instagram}`;
    $("#cInsta").href = `https://instagram.com/${LOJA.instagram}`;
    $("#cHorarios").textContent = LOJA.horarios.join("\n");
    $("#ano").textContent = new Date().getFullYear();

    $$(".js-whats").forEach((a) => (a.href = linkWhats(a.dataset.msg || "Olá! Vim pelo site da MT Multimarcas.")));

    $("#formVenda").addEventListener("submit", (e) => {
      e.preventDefault();
      const d = new FormData(e.target);
      const msg = `Olá! Gostaria de uma avaliação da minha moto:\n• Modelo: ${d.get("modelo")}\n• Ano: ${d.get("ano")}` +
        (d.get("km") ? `\n• Km: ${d.get("km")}` : "");
      window.open(linkWhats(msg), "_blank", "noopener");
    });
  }

  /* ---------- Menu mobile ---------- */
  function menu() {
    const btn = $("#menuToggle"), nav = $("#menu");
    btn.addEventListener("click", () => {
      const aberto = nav.classList.toggle("aberto");
      btn.setAttribute("aria-expanded", aberto);
    });
    nav.addEventListener("click", (e) => {
      if (e.target.tagName === "A") { nav.classList.remove("aberto"); btn.setAttribute("aria-expanded", "false"); }
    });
  }

  /* ---------- Contadores do hero ---------- */
  function contar(el, alvo) {
    const dur = 900, ini = performance.now();
    const passo = (t) => {
      const p = Math.min(1, (t - ini) / dur);
      el.textContent = Math.round(alvo * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }

  /* ---------- Inicialização ---------- */
  function init() {
    preencherSelects();
    chipsMarcas();

    const destaques = disponiveis().filter((m) => m.destaque).slice(0, 4);
    $("#gradeDestaques").innerHTML = destaques.map(cardHTML).join("");
    $("#destaques").hidden = destaques.length === 0;

    Object.values(f).forEach((el) => el.addEventListener(el.type === "search" ? "input" : "change", aplicar));
    $("#limparFiltros").addEventListener("click", limpar);
    aplicar();

    // Abrir detalhes ao clicar no card (exceto no botão do WhatsApp)
    document.addEventListener("click", (e) => {
      if (e.target.closest("[data-whats-card]")) return;
      const card = e.target.closest(".card");
      if (card) abrirModal(card.dataset.id);
      if (e.target.closest("[data-fechar]")) fecharModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") fecharModal();
      if ((e.key === "Enter" || e.key === " ") && e.target.classList?.contains("card")) {
        e.preventDefault();
        abrirModal(e.target.dataset.id);
      }
    });

    simulador();
    contato();
    menu();

    contar($("#numEstoque"), disponiveis().length);
    contar($("#numMarcas"), new Set(MOTOS.map((m) => m.marca)).size);

    // Link direto para uma moto: index.html#moto=<id>
    const abrirPeloHash = () => {
      const h = decodeURIComponent(location.hash);
      if (h.startsWith("#moto=")) abrirModal(h.slice(6), false);
    };
    window.addEventListener("hashchange", abrirPeloHash);
    abrirPeloHash();
  }

  init();
})();
