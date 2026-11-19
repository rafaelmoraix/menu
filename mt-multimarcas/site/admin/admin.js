/* =========================================================
   MT MULTIMARCAS — Painel admin
   Fala com as funções em /api (netlify/functions)
   ========================================================= */
(() => {
  "use strict";

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const NUM = new Intl.NumberFormat("pt-BR");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const soNumeros = (v) => Number(String(v).replace(/\D/g, "")) || 0;
  const clonar = (o) => JSON.parse(JSON.stringify(o));

  const CHAVE_TOKEN = "mt_admin_token";
  let token = null;
  let eu = null;           // { id, nome, papel } de quem está logado
  let quemEscolhido = "";  // usuário escolhido na tela de login
  try { token = localStorage.getItem(CHAVE_TOKEN); } catch (_) {}

  const estado = {
    motos: [],
    exemplos: false,   // true enquanto o painel nunca salvou nada
    filtro: "todas",
    busca: "",
    editando: null,    // id da moto aberta no formulário (null = nova)
    fotos: [],         // fotos do formulário: { url, enviando }
    enviadasAgora: new Set(), // fotos enviadas neste formulário (apagar se cancelar)
  };

  /* ---------- Utilidades ---------- */
  function toast(msg, erro = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.style.background = erro ? "var(--vermelho)" : "";
    t.style.color = erro ? "#fff" : "";
    t.classList.add("visivel");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("visivel"), 3000);
  }

  async function api(caminho, opcoes = {}) {
    const headers = { ...(opcoes.headers || {}) };
    if (token) headers.authorization = `Bearer ${token}`;
    let r;
    try {
      r = await fetch(caminho, { ...opcoes, headers, cache: "no-store" });
    } catch (_) {
      throw new Error("Sem conexão. Verifique a internet e tente de novo.");
    }
    let dados = {};
    try { dados = await r.json(); } catch (_) {}
    if (r.status === 401 && !(caminho === "/api/login" && opcoes.method === "POST")) {
      sair("Sua sessão expirou. Entre novamente.");
      throw new Error("Sessão expirada.");
    }
    if (r.status === 429) throw new Error("Muitas tentativas. Aguarde um minuto.");
    if (!r.ok) throw new Error(dados.erro || "Algo deu errado. Tente de novo.");
    return dados;
  }

  function slug(s) {
    return String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);
  }

  /* ---------- Login / sessão ---------- */
  function mostrar(tela) {
    $("#telaLogin").hidden = tela !== "login";
    $("#telaPainel").hidden = tela !== "painel";
  }

  function sair(msg) {
    token = null;
    eu = null;
    try { clearInterval(atend.timer); } catch (_) { /* ainda não iniciado */ }
    carregarEquipeLogin();
    try { localStorage.removeItem(CHAVE_TOKEN); } catch (_) {}
    fecharForm(true);
    mostrar("login");
    $("#erroLogin").textContent = msg || "";
    $("#senha").value = "";
    $("#senha").focus();
  }

  $("#formLogin").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#btnEntrar");
    btn.disabled = true;
    $("#erroLogin").textContent = "";
    try {
      const { token: t, usuario } = await api("/api/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ usuario: quemEscolhido, senha: $("#senha").value }),
      });
      token = t;
      eu = usuario;
      try { localStorage.setItem(CHAVE_TOKEN, t); } catch (_) {}
      await carregar();
    } catch (err) {
      $("#erroLogin").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  async function carregarEquipeLogin() {
    try {
      const { equipe } = await api("/api/login?equipe=1");
      const cont = $("#quemSou");
      cont.hidden = equipe.length < 2;
      if (!quemEscolhido || !equipe.some((u) => u.id === quemEscolhido)) {
        try { quemEscolhido = localStorage.getItem("mt_admin_quem") || ""; } catch (_) {}
        if (!equipe.some((u) => u.id === quemEscolhido)) quemEscolhido = equipe[0]?.id || "";
      }
      cont.innerHTML = equipe.map((u) => `<button type="button" role="radio" aria-checked="${u.id === quemEscolhido}" class="${u.id === quemEscolhido ? "ativo" : ""}" data-id="${esc(u.id)}">${esc(u.nome)}</button>`).join("");
    } catch (_) { /* sem lista: entra como gerente */ }
  }
  $("#quemSou").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    quemEscolhido = b.dataset.id;
    try { localStorage.setItem("mt_admin_quem", quemEscolhido); } catch (_) {}
    $$("#quemSou button").forEach((x) => { x.classList.toggle("ativo", x === b); x.setAttribute("aria-checked", x === b); });
    $("#senha").focus();
  });

  $("#verSenha").addEventListener("click", () => {
    const i = $("#senha");
    i.type = i.type === "password" ? "text" : "password";
    $("#verSenha i").className = i.type === "password" ? "fa-regular fa-eye" : "fa-regular fa-eye-slash";
  });

  $("#btnSair").addEventListener("click", () => sair());

  /* ---------- Carregar e salvar ---------- */
  async function carregar() {
    const { motos } = await api("/api/motos");
    if (Array.isArray(motos)) {
      estado.motos = motos;
      estado.exemplos = false;
    } else {
      estado.motos = clonar(typeof MOTOS !== "undefined" ? MOTOS : []);
      estado.exemplos = true;
    }
    mostrar("painel");
    $("#euNome").innerHTML = eu ? `<i class="fa-solid fa-circle-user"></i> ${esc(eu.nome)}` : "";
    render();
    carregarProcuras();
    iniciarAtendimento();
  }

  async function salvar(lista, msg = "Salvo! O site já foi atualizado.") {
    const { motos } = await api("/api/motos", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ motos: lista }),
    });
    estado.motos = motos;
    estado.exemplos = false;
    render();
    toast(msg);
  }

  function apagarFotos(urls) {
    urls.filter((u) => u.startsWith("/fotos/")).forEach((u) =>
      api(`/api/fotos/${u.slice(7)}`, { method: "DELETE" }).catch(() => {}));
  }

  /* ---------- Lista ---------- */
  function render() {
    const { motos } = estado;
    $("#avisoExemplos").hidden = !estado.exemplos;
    $("#rDisp").textContent = motos.filter((m) => m.status !== "vendida").length;
    $("#rVend").textContent = motos.filter((m) => m.status === "vendida").length;
    $("#rDest").textContent = motos.filter((m) => m.destaque && m.status !== "vendida").length;

    const termo = slug(estado.busca);
    const lista = motos.filter((m) =>
      (estado.filtro === "todas" || (estado.filtro === "vendida") === (m.status === "vendida")) &&
      (!termo || slug(`${m.marca} ${m.modelo} ${m.ano} ${m.cor}`).includes(termo)));

    $("#listaVazia").hidden = lista.length > 0;
    $("#lista").innerHTML = lista.map((m) => {
      const vendida = m.status === "vendida";
      const capa = m.fotos?.[0];
      return `
      <li class="item${vendida ? " item--vendida" : ""}" data-id="${esc(m.id)}">
        <div class="item__foto">${capa
          ? `<img src="${esc(capa.startsWith("/") ? capa : "../" + capa)}" alt="" loading="lazy">`
          : `<div class="ilustra"><i class="fa-solid fa-motorcycle" style="font-size:1.6rem;color:var(--ouro)"></i></div>`}</div>
        <div class="item__info">
          <h3>${esc(m.marca)} ${esc(m.modelo)}</h3>
          <p><span class="item__preco">${BRL.format(m.preco)}</span> · ${m.ano} · ${m.km ? NUM.format(m.km) + " km" : "0 km"}</p>
          <div class="item__tags">
            ${vendida ? `<span class="tag tag--vendida">Vendida</span>` : ""}
            ${m.destaque && !vendida ? `<span class="tag">Destaque</span>` : ""}
            ${m.condicao === "Nova" ? `<span class="tag tag--nova">0 km</span>` : ""}
            ${!m.fotos?.length ? `<span class="tag">Sem foto</span>` : ""}
          </div>
        </div>
        <div class="item__acoes">
          <button class="icone${m.destaque ? " ligado" : ""}" data-acao="destaque" title="Destaque" aria-label="Destaque"><i class="fa-solid fa-star"></i> <b>Destaque</b></button>
          <button class="icone${vendida ? " ligado" : ""}" data-acao="vendida" title="${vendida ? "Voltar a vender" : "Marcar como vendida"}" aria-label="Vendida"><i class="fa-solid fa-handshake"></i> <b>${vendida ? "Vendida" : "Vender"}</b></button>
          <button class="icone" data-acao="editar" title="Editar" aria-label="Editar"><i class="fa-solid fa-pen"></i> <b>Editar</b></button>
          <button class="icone icone--perigo" data-acao="excluir" title="Excluir" aria-label="Excluir"><i class="fa-solid fa-trash"></i></button>
        </div>
      </li>`;
    }).join("");
  }

  $("#lista").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-acao]");
    if (!b) return;
    const id = b.closest(".item").dataset.id;
    const m = estado.motos.find((x) => x.id === id);
    if (!m) return;
    const acao = b.dataset.acao;

    if (acao === "editar") return abrirForm(m);

    const lista = clonar(estado.motos);
    const alvo = lista.find((x) => x.id === id);
    let msg;
    if (acao === "destaque") {
      alvo.destaque = !alvo.destaque;
      msg = alvo.destaque ? "Moto em destaque na página inicial." : "Destaque removido.";
    } else if (acao === "vendida") {
      alvo.status = alvo.status === "vendida" ? "disponivel" : "vendida";
      msg = alvo.status === "vendida" ? "Marcada como vendida." : "De volta à venda.";
    } else if (acao === "excluir") {
      if (!confirm(`Excluir ${m.marca} ${m.modelo} ${m.ano}? Isso não pode ser desfeito.`)) return;
      lista.splice(lista.indexOf(alvo), 1);
      msg = "Moto excluída.";
    }
    b.disabled = true;
    try {
      await salvar(lista, msg);
      if (acao === "excluir") apagarFotos(m.fotos || []);
    } catch (err) {
      toast(err.message, true);
      b.disabled = false;
    }
  });

  $("#busca").addEventListener("input", (e) => { estado.busca = e.target.value; render(); });
  $("#abas").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.filtro = b.dataset.f;
    $$("#abas button").forEach((x) => x.classList.toggle("ativo", x === b));
    render();
  });

  $("#btnApagarExemplos").addEventListener("click", async () => {
    if (!confirm("Apagar todas as motos de exemplo? O catálogo do site ficará vazio até você cadastrar as motos reais.")) return;
    try { await salvar([], "Exemplos apagados. Agora é só cadastrar o estoque!"); }
    catch (err) { toast(err.message, true); }
  });

  /* ---------- Formulário ---------- */
  const form = $("#formMoto");
  const modal = $("#modalForm");

  function abrirForm(m = null) {
    estado.editando = m ? m.id : null;
    estado.fotos = (m?.fotos || []).map((url) => ({ url }));
    estado.enviadasAgora = new Set();
    form.reset();
    $("#erroForm").textContent = "";
    $("#tituloForm").textContent = m ? `Editar ${m.marca} ${m.modelo}` : "Nova moto";

    const v = m || { ano: new Date().getFullYear(), categoria: "Street", condicao: "Seminova", combustivel: "Gasolina" };
    form.marca.value = v.marca || "";
    form.modelo.value = v.modelo || "";
    form.ano.value = v.ano || "";
    form.preco.value = v.preco ? NUM.format(v.preco) : "";
    form.km.value = v.km ? NUM.format(v.km) : "";
    form.cilindrada.value = v.cilindrada || "";
    form.cor.value = v.cor || "";
    form.categoria.value = v.categoria || "Street";
    form.condicao.value = v.condicao || "Seminova";
    form.combustivel.value = v.combustivel || "Gasolina";
    form.opcionais.value = (v.opcionais || []).join(", ");
    form.descricao.value = v.descricao || "";
    form.destaque.checked = !!v.destaque;
    form.vendida.checked = v.status === "vendida";

    renderFotos();
    modal.hidden = false;
    document.body.classList.add("travado");
    $(".form-moto__corpo").scrollTop = 0;
    if (!m) setTimeout(() => form.marca.focus(), 50);
  }

  function fecharForm(forcar = false) {
    if (modal.hidden) return;
    if (!forcar && estado.fotos.some((f) => f.enviando)) {
      if (!confirm("Ainda há fotos sendo enviadas. Fechar mesmo assim?")) return;
    }
    // Fotos enviadas e não salvas: apaga para não ocupar espaço
    apagarFotos([...estado.enviadasAgora]);
    estado.enviadasAgora = new Set();
    modal.hidden = true;
    document.body.classList.remove("travado");
  }

  modal.addEventListener("click", (e) => { if (e.target.closest("[data-fechar]")) fecharForm(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharForm(); });
  $("#btnNova").addEventListener("click", () => abrirForm());

  // Formata preço e km enquanto digita (32900 -> 32.900)
  $$("[data-moeda]", form).forEach((i) => i.addEventListener("input", () => {
    const n = soNumeros(i.value);
    i.value = n ? NUM.format(n) : "";
  }));

  /* ---------- Fotos ---------- */
  function renderFotos() {
    const cont = $("#fotos");
    cont.innerHTML = estado.fotos.map((f, i) => `
      <div class="foto${i === 0 ? " foto--capa" : ""}${f.enviando ? " foto--enviando" : ""}" data-i="${i}">
        <img src="${esc(f.preview || (f.url.startsWith("/") ? f.url : "../" + f.url))}" alt="Foto ${i + 1}">
        ${f.enviando ? "" : `
          <button type="button" class="foto__btn foto__capa" data-foto="capa" aria-label="Usar como capa" title="Usar como capa"><i class="fa-solid fa-star"></i></button>
          <button type="button" class="foto__btn foto__remover" data-foto="remover" aria-label="Remover foto" title="Remover"><i class="fa-solid fa-xmark"></i></button>`}
      </div>`).join("") +
      (estado.fotos.length < 20 ? `<button type="button" class="foto-add" id="addFoto"><i class="fa-solid fa-camera"></i>Adicionar fotos</button>` : "");
  }

  $("#fotos").addEventListener("click", (e) => {
    if (e.target.closest("#addFoto")) return $("#inputFotos").click();
    const b = e.target.closest("[data-foto]");
    if (!b) return;
    const i = Number(b.closest(".foto").dataset.i);
    if (b.dataset.foto === "capa") {
      estado.fotos.unshift(...estado.fotos.splice(i, 1));
    } else {
      estado.fotos.splice(i, 1);
    }
    renderFotos();
  });

  // Reduz a foto no celular antes de enviar (mais rápido e leve)
  function reduzir(arquivo, max = 1600, qualidade = 0.82) {
    return new Promise((ok, falha) => {
      const img = new Image();
      const url = URL.createObjectURL(arquivo);
      img.onload = () => {
        const escala = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
        const w = Math.round(img.naturalWidth * escala), h = Math.round(img.naturalHeight * escala);
        const c = document.createElement("canvas");
        c.width = w; c.height = h;
        c.getContext("2d").drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        c.toBlob((b) => (b ? ok(b) : falha(new Error("Não foi possível ler a foto."))), "image/jpeg", qualidade);
      };
      img.onerror = () => { URL.revokeObjectURL(url); falha(new Error("Formato de foto não suportado.")); };
      img.src = url;
    });
  }

  $("#inputFotos").addEventListener("change", async (e) => {
    const arquivos = [...e.target.files].slice(0, 20 - estado.fotos.length);
    e.target.value = "";
    await Promise.all(arquivos.map(async (arq) => {
      const item = { url: "", enviando: true, preview: URL.createObjectURL(arq) };
      estado.fotos.push(item);
      renderFotos();
      try {
        const blob = await reduzir(arq);
        const { url } = await api("/api/fotos", { method: "POST", headers: { "content-type": "image/jpeg" }, body: blob });
        item.url = url;
        estado.enviadasAgora.add(url);
      } catch (err) {
        estado.fotos.splice(estado.fotos.indexOf(item), 1);
        toast(err.message, true);
      } finally {
        item.enviando = false;
        URL.revokeObjectURL(item.preview);
        delete item.preview;
        renderFotos();
      }
    }));
  });

  /* ---------- Salvar moto ---------- */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const erro = $("#erroForm");
    erro.textContent = "";

    if (estado.fotos.some((f) => f.enviando)) { erro.textContent = "Aguarde as fotos terminarem de enviar."; return; }
    const marca = form.marca.value.trim(), modelo = form.modelo.value.trim();
    const ano = Number(form.ano.value), preco = soNumeros(form.preco.value);
    if (!marca || !modelo) { erro.textContent = "Preencha marca e modelo."; return; }
    if (!ano || ano < 1950 || ano > 2100) { erro.textContent = "Informe um ano válido."; return; }
    if (!preco) { erro.textContent = "Informe o preço."; return; }

    const antiga = estado.motos.find((m) => m.id === estado.editando);
    const moto = {
      id: antiga?.id || `${slug(`${marca}-${modelo}-${ano}`)}-${Math.random().toString(36).slice(2, 6)}`,
      marca, modelo, ano, preco,
      km: soNumeros(form.km.value),
      cilindrada: Number(form.cilindrada.value) || 0,
      cor: form.cor.value.trim(),
      categoria: form.categoria.value,
      condicao: form.condicao.value,
      combustivel: form.combustivel.value,
      status: form.vendida.checked ? "vendida" : "disponivel",
      destaque: form.destaque.checked,
      opcionais: form.opcionais.value.split(",").map((s) => s.trim()).filter(Boolean),
      descricao: form.descricao.value.trim(),
      fotos: estado.fotos.map((f) => f.url),
    };

    const lista = clonar(estado.motos);
    if (antiga) lista[lista.findIndex((m) => m.id === antiga.id)] = moto;
    else lista.unshift(moto);

    const btn = $("#btnSalvar");
    btn.disabled = true;
    try {
      await salvar(lista, antiga ? "Moto atualizada no site!" : "Moto cadastrada e já está no site!");
      // Fotos tiradas da moto nesta edição: apaga do armazenamento
      if (antiga) apagarFotos((antiga.fotos || []).filter((u) => !moto.fotos.includes(u)));
      estado.enviadasAgora = new Set(); // agora fazem parte da moto
      fecharForm(true);
    } catch (err) {
      erro.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });

  /* ---------- Abas ---------- */
  function abrirAba(nome) {
    $$("#menuAdm button").forEach((b) => b.classList.toggle("ativo", b.dataset.aba === nome));
    $("#abaAtendimento").hidden = nome !== "atendimento";
    $("#abaEstoque").hidden = nome !== "estoque";
    $("#abaBusca").hidden = nome !== "busca";
    $("#abaProcuras").hidden = nome !== "procuras";
    window.scrollTo(0, 0);
  }
  $("#menuAdm").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) abrirAba(b.dataset.aba);
  });

  /* ---------- Buscar moto ---------- */
  const fBusca = $("#formBusca");
  let ultimaBusca = null;

  $$("[data-moeda]", fBusca).forEach((i) => i.addEventListener("input", () => {
    const n = soNumeros(i.value);
    i.value = n ? NUM.format(n) : "";
  }));

  function linksAtalho({ modelo, ano, precoMax, uf }) {
    const termo = `${modelo} ${ano}`.trim();
    const q = encodeURIComponent(termo);
    const olx = `https://www.olx.com.br/autos-e-pecas/motos${uf ? "/estado-" + uf.toLowerCase() : ""}?q=${q}${precoMax ? "&pe=" + precoMax : ""}`;
    const face = `https://www.facebook.com/marketplace/search/?query=${q}${precoMax ? "&maxPrice=" + precoMax : ""}`;
    const ml = `https://lista.mercadolivre.com.br/${slug(termo)}${precoMax ? "_PriceRange_0-" + precoMax : ""}`;
    const google = `https://www.google.com/search?q=${encodeURIComponent(termo + " moto à venda" + (uf ? " " + uf : ""))}`;
    return [
      ["OLX", "fa-solid fa-tag", olx],
      ["Marketplace", "fa-brands fa-facebook", face],
      ["Mercado Livre", "fa-solid fa-handshake", ml],
      ["Google", "fa-brands fa-google", google],
    ];
  }

  function lerBusca(form = fBusca) {
    return {
      modelo: form.modelo.value.trim(),
      ano: form.ano.value.replace(/\D/g, "").slice(0, 4),
      precoMax: soNumeros(form.precoMax.value),
      uf: form.uf.value,
      recentes: form.recentes.checked,
    };
  }

  function preencherBusca(b) {
    fBusca.modelo.value = b.modelo || "";
    fBusca.ano.value = b.ano || "";
    fBusca.precoMax.value = b.precoMax ? NUM.format(b.precoMax) : "";
    fBusca.uf.value = b.uf || "";
  }

  function fotoSrc(u) { return u.startsWith("/") ? u : "../" + u; }

  function renderNoEstoque(b) {
    const palavras = slug(b.modelo).split("-").filter(Boolean);
    const achadas = estado.motos.filter((m) => {
      if (m.status === "vendida") return false;
      const nome = slug(`${m.marca} ${m.modelo}`);
      return palavras.every((p) => nome.includes(p)) &&
        (!b.ano || Math.abs(Number(m.ano) - Number(b.ano)) <= 1) &&
        (!b.precoMax || m.preco <= b.precoMax * 1.1);
    });
    $("#noEstoque").hidden = achadas.length === 0;
    $("#listaNoEstoque").innerHTML = achadas.map((m) => `
      <li class="item"><div class="item__foto">${m.fotos?.[0]
        ? `<img src="${esc(fotoSrc(m.fotos[0]))}" alt="">`
        : `<div class="ilustra"><i class="fa-solid fa-motorcycle" style="color:var(--ouro)"></i></div>`}</div>
        <div class="item__info"><h3>${esc(m.marca)} ${esc(m.modelo)}</h3>
        <p><span class="item__preco">${BRL.format(m.preco)}</span> · ${m.ano} · ${m.km ? NUM.format(m.km) + " km" : "0 km"}</p></div></li>`).join("");
  }

  async function atualizarCota() {
    try {
      const c = await api("/api/busca?conta=1");
      $("#cota").textContent = c.restantes != null ? `${c.restantes} buscas restantes${c.servico ? " (" + c.servico + ")" : ""}` : "";
    } catch (_) { $("#cota").textContent = ""; }
  }

  function htmlAnuncio(r) {
    return `
      <a class="anuncio" href="${esc(r.url)}" target="_blank" rel="noopener">
        <div class="anuncio__foto">${r.foto
          ? `<img src="${esc(r.foto)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">`
          : `<i class="fa-solid fa-motorcycle"></i>`}</div>
        <div>
          <h4>${esc(r.titulo)}</h4>
          <p>${esc(r.trecho)}</p>
          <div class="anuncio__meta">
            <span class="tag">${esc(r.site)}</span>
            ${r.preco ? `<span class="anuncio__preco">${BRL.format(r.preco)}</span>` : ""}
            ${r.data ? `<span>${esc(r.data)}</span>` : ""}
          </div>
        </div>
      </a>`;
  }

  async function buscar(b) {
    ultimaBusca = b;
    $("#resBusca").hidden = false;
    renderNoEstoque(b);
    $("#atalhos").innerHTML = linksAtalho(b).map(([nome, icone, url]) =>
      `<a class="atalho" href="${esc(url)}" target="_blank" rel="noopener"><i class="${icone}"></i> ${nome}</a>`).join("");

    const res = $("#resultados");
    res.innerHTML = `<div class="carregando"><i class="fa-solid fa-spinner fa-spin"></i> Procurando anúncios...</div>`;
    const btn = $("#btnBuscar");
    btn.disabled = true;
    try {
      const qs = new URLSearchParams({ modelo: b.modelo, ano: b.ano, precoMax: b.precoMax || "", uf: b.uf, recentes: b.recentes ? "1" : "" });
      const { resultados, escondidos } = await api(`/api/busca?${qs}`);
      const acima = escondidos ? `${escondidos} anúncio(s) acima de ${BRL.format(b.precoMax)} foram escondidos.` : "";
      if (!resultados.length) {
        res.innerHTML = `<div class="aviso-busca">Nenhum anúncio encontrado. ${acima} Tente os botões acima ou tire o ano da busca.</div>`;
      } else {
        res.innerHTML = `<div class="lista-anuncios">${resultados.map(htmlAnuncio).join("")}</div>
          ${acima ? `<p class="dica">${acima}</p>` : ""}
          <p class="dica">Os anúncios vêm do Google e podem já ter sido vendidos. Para ver os mais novos, use os botões acima.</p>`;
      }
      atualizarCota();
    } catch (err) {
      const semChave = err.message.includes("ainda não foi ativada");
      res.innerHTML = `<div class="aviso-busca">${semChave
        ? "<b>A lista de anúncios aqui no painel ainda não foi ativada.</b> Enquanto isso, use os botões acima: eles já abrem a busca pronta em cada site."
        : esc(err.message)}</div>`;
    } finally {
      btn.disabled = false;
    }
  }

  fBusca.addEventListener("submit", (e) => {
    e.preventDefault();
    const b = lerBusca();
    if (b.modelo.length < 2) { toast("Digite o modelo da moto.", true); return; }
    buscar(b);
  });

  /* ---------- Procuras de clientes ---------- */
  let procuras = [];

  async function carregarProcuras() {
    try {
      ({ procuras } = await api("/api/procuras"));
      renderProcuras();
    } catch (_) { /* sem conexão: tenta na próxima vez */ }
  }

  async function salvarProcuras(lista, msg) {
    ({ procuras } = await api("/api/procuras", {
      method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ procuras: lista }),
    }));
    renderProcuras();
    if (msg) toast(msg);
  }

  function renderProcuras() {
    $("#nProcuras").textContent = procuras.length || "";
    $("#procurasVazia").hidden = procuras.length > 0;
    $("#listaProcuras").innerHTML = procuras.map((p) => {
      const tel = p.telefone ? (p.telefone.length <= 11 ? "55" + p.telefone : p.telefone) : "";
      const msg = encodeURIComponent(`Olá${p.cliente ? " " + p.cliente : ""}! Aqui é da MT Multimarcas. Sobre a ${p.modelo}${p.ano ? " " + p.ano : ""} que você procurou: `);
      const partes = [
        p.precoMax ? `Até <b>${BRL.format(p.precoMax)}</b>` : "",
        p.uf ? esc(p.uf) : "",
        p.cliente ? `Cliente: <b>${esc(p.cliente)}</b>` : "Sem cliente",
        p.telefone ? esc(p.telefone) : "",
      ].filter(Boolean).join(" · ");
      return `
      <li class="procura" data-id="${esc(p.id)}">
        <h3>${esc(p.modelo)} ${esc(p.ano)}</h3>
        <p>${partes}</p>
        ${p.obs ? `<p>${esc(p.obs)}</p>` : ""}
        <p class="dica">Salva em ${new Date(p.criadoEm).toLocaleDateString("pt-BR")}</p>
        <div class="procura__acoes">
          ${tel ? `<a class="icone icone--whats" href="https://wa.me/${tel}?text=${msg}" target="_blank" rel="noopener"><i class="fa-brands fa-whatsapp"></i> <b>Cliente</b></a>` : ""}
          <button class="icone" data-acao="rebuscar"><i class="fa-solid fa-magnifying-glass"></i> <b>Buscar de novo</b></button>
          <button class="icone icone--perigo" data-acao="apagar" aria-label="Apagar procura"><i class="fa-solid fa-trash"></i></button>
        </div>
      </li>`;
    }).join("");
  }

  $("#listaProcuras").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-acao]");
    if (!b) return;
    const p = procuras.find((x) => x.id === b.closest(".procura").dataset.id);
    if (!p) return;
    if (b.dataset.acao === "rebuscar") {
      preencherBusca(p);
      abrirAba("busca");
      buscar({ ...p, recentes: fBusca.recentes.checked });
    } else if (confirm(`Apagar a procura de ${p.modelo}${p.cliente ? " para " + p.cliente : ""}?`)) {
      try { await salvarProcuras(procuras.filter((x) => x !== p), "Procura apagada."); }
      catch (err) { toast(err.message, true); }
    }
  });

  $("#formProcura").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const b = ultimaBusca || lerBusca();
    if (!b.modelo) { toast("Faça a busca primeiro.", true); return; }
    const nova = {
      id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      modelo: b.modelo, ano: b.ano, precoMax: b.precoMax, uf: b.uf,
      cliente: f.cliente.value.trim(), telefone: f.telefone.value.replace(/\D/g, ""), obs: f.obs.value.trim(),
      criadoEm: new Date().toISOString(),
    };
    try {
      await salvarProcuras([nova, ...procuras], "Procura salva! Está na aba Procuras.");
      f.reset();
    } catch (err) { toast(err.message, true); }
  });

  /* =========================================================
     ATENDIMENTO (CRM de WhatsApp)
     ========================================================= */
  const atend = {
    modo: "demo", equipe: [], conversas: [], filtro: "novas", busca: "",
    aberta: null,          // telefone da conversa aberta
    mensagens: [], assinaturaMsgs: "", timer: null, novasVistas: null,
  };
  const ETAPAS = { novo: "Novo", atendimento: "Em atendimento", proposta: "Proposta", vendido: "Vendido", perdido: "Perdido" };
  const CORES = ["#e3a83a", "#4ea1ff", "#3ecf8e", "#c77dff", "#ff7a59", "#9aa5b1"];

  const pessoa = (id) => atend.equipe.find((u) => u.id === id);
  const nomePessoa = (id) => (id === eu?.id ? "Você" : pessoa(id)?.nome || "—");
  const corPessoa = (id) => {
    const i = atend.equipe.findIndex((u) => u.id === id);
    return i < 0 ? CORES[5] : (atend.equipe[i].papel === "gerente" ? CORES[5] : CORES[i % 5]);
  };
  const iniciais = (n) => String(n || "?").replace(/^\+/, "").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
  const telBonito = (t) => {
    const m = String(t).match(/^55(\d{2})(\d{4,5})(\d{4})$/);
    return m ? `(${m[1]}) ${m[2]}-${m[3]}` : `+${t}`;
  };
  function quando(iso) {
    const d = new Date(iso), hoje = new Date();
    const ontem = new Date(); ontem.setDate(hoje.getDate() - 1);
    const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    if (d.toDateString() === hoje.toDateString()) return hora;
    if (d.toDateString() === ontem.toDateString()) return "ontem";
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  }
  function bip() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.setValueAtTime(0.08, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35);
      o.start(); o.stop(ctx.currentTime + 0.35);
    } catch (_) {}
  }

  /* ---------- Carregar lista ---------- */
  async function carregarConversas(silencioso = false) {
    try {
      const d = await api("/api/conversas");
      atend.modo = d.modo;
      atend.equipe = d.equipe;
      atend.conversas = d.conversas;
      // Aviso sonoro quando chega conversa nova sem ninguém atendendo
      const novas = new Set(d.conversas.filter((c) => !c.atendente && c.naoLidas).map((c) => c.tel + c.ultima?.em));
      if (atend.novasVistas && [...novas].some((k) => !atend.novasVistas.has(k))) {
        bip();
        if (silencioso) toast("Nova mensagem de cliente!");
      }
      atend.novasVistas = novas;
      renderAtend();
    } catch (err) {
      if (!silencioso) toast(err.message, true);
    }
  }

  function renderAtend() {
    $("#avisoDemo").hidden = atend.modo !== "demo";
    $("#btnReiniciarDemo").hidden = eu?.papel !== "gerente";

    const novas = atend.conversas.filter((c) => !c.atendente && c.etapa !== "vendido" && c.etapa !== "perdido");
    const minhas = atend.conversas.filter((c) => c.atendente === eu?.id && c.etapa !== "vendido" && c.etapa !== "perdido");
    const minhasNaoLidas = minhas.reduce((s, c) => s + (c.naoLidas || 0), 0);
    $("#cNovas").textContent = novas.length || "";
    $("#cMinhas").textContent = minhasNaoLidas || "";
    $("#nAtend").textContent = (novas.length + minhasNaoLidas) || "";
    document.title = (novas.length + minhasNaoLidas ? `(${novas.length + minhasNaoLidas}) ` : "") + "Painel MT Multimarcas";

    // Resumo da equipe: quantas conversas ativas cada um tem
    $("#equipeResumo").innerHTML = atend.equipe.filter((u) => u.papel === "atendente" || u.id === eu?.id).map((u) => {
      const ativas = atend.conversas.filter((c) => c.atendente === u.id && !["vendido", "perdido"].includes(c.etapa)).length;
      const vendas = atend.conversas.filter((c) => c.atendente === u.id && c.etapa === "vendido").length;
      return `<div class="pessoa${u.id === eu?.id ? " pessoa--eu" : ""}">
        <span class="avatar avatar--p" style="--cor:${corPessoa(u.id)}">${esc(iniciais(u.nome))}</span>
        <div><b>${esc(u.id === eu?.id ? u.nome + " (você)" : u.nome)}</b><small>${ativas} em atendimento · ${vendas} vendas</small></div>
      </div>`;
    }).join("");

    const termo = slug(atend.busca);
    let lista = atend.filtro === "novas" ? novas : atend.filtro === "minhas" ? minhas : atend.conversas;
    if (termo) lista = atend.conversas.filter((c) => slug(`${c.nome} ${c.tel}`).includes(termo));

    $("#listaConv").innerHTML = lista.length ? lista.map((c) => {
      const dono = c.atendente;
      return `
      <li class="conv${c.tel === atend.aberta ? " conv--ativa" : ""}${c.naoLidas ? " conv--naolida" : ""}" data-tel="${esc(c.tel)}" tabindex="0">
        <span class="avatar">${esc(iniciais(c.nome))}</span>
        <div class="conv__meio">
          <div class="conv__linha"><b>${esc(c.nome)}</b><time>${c.ultima ? quando(c.ultima.em) : ""}</time></div>
          <p>${c.ultima?.de === "loja" ? '<i class="fa-solid fa-reply"></i> ' : ""}${esc(c.ultima?.texto || "")}</p>
          <div class="conv__tags">
            <span class="etapa etapa--${c.etapa}">${ETAPAS[c.etapa]}</span>
            ${dono ? `<span class="dono" style="--cor:${corPessoa(dono)}"><i class="fa-solid fa-headset"></i> ${esc(nomePessoa(dono))}</span>` : `<span class="dono dono--livre">Ninguém atendendo</span>`}
          </div>
        </div>
        ${c.naoLidas ? `<span class="bolinha">${c.naoLidas}</span>` : ""}
      </li>`;
    }).join("") : `<li class="convs__vazio">${atend.filtro === "novas" && !termo ? "Nenhuma conversa esperando 🎉" : "Nenhuma conversa aqui."}</li>`;

    if (atend.aberta) renderBarra();
  }

  /* ---------- Conversa aberta ---------- */
  const conversaAberta = () => atend.conversas.find((c) => c.tel === atend.aberta);

  async function abrirConversa(tel) {
    atend.aberta = tel;
    atend.assinaturaMsgs = "";
    $("#atendGrid").classList.add("atend-grid--chat");
    $("#chatVazio").hidden = true;
    $("#chatAberto").hidden = false;
    $("#chatNotas").hidden = true;
    const c = conversaAberta();
    if (c) {
      $("#chatNome").textContent = c.nome;
      $("#chatTel").textContent = telBonito(c.tel);
      $("#chatAvatar").textContent = iniciais(c.nome);
      $("#chatAbrirWhats").href = `https://wa.me/${c.tel}`;
      $("#notas").value = c.notas || "";
    }
    $("#chatMsgs").innerHTML = `<div class="carregando"><i class="fa-solid fa-spinner fa-spin"></i> Carregando conversa...</div>`;
    renderAtend();
    renderRapidas();
    await carregarMensagens(true);
    // Quem está atendendo abriu: zera as não lidas
    if (c && c.naoLidas && (c.atendente === eu.id || !c.atendente)) acao("lida", {}, true);
  }

  function fecharConversa() {
    atend.aberta = null;
    $("#atendGrid").classList.remove("atend-grid--chat");
    $("#chatAberto").hidden = true;
    $("#chatVazio").hidden = false;
    renderAtend();
  }

  async function carregarMensagens(rolar = false) {
    const tel = atend.aberta;
    if (!tel) return;
    try {
      const { conversa, mensagens } = await api(`/api/conversas/${tel}`);
      if (tel !== atend.aberta) return;
      const i = atend.conversas.findIndex((c) => c.tel === tel);
      if (i >= 0) atend.conversas[i] = conversa;
      const assinatura = JSON.stringify(mensagens.map((m) => [m.id, m.status]));
      if (assinatura !== atend.assinaturaMsgs) {
        const box = $("#chatMsgs");
        const noFim = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
        atend.assinaturaMsgs = assinatura;
        atend.mensagens = mensagens;
        renderMensagens();
        if (rolar || noFim) box.scrollTop = box.scrollHeight;
      }
      renderBarra();
    } catch (err) {
      if (rolar) $("#chatMsgs").innerHTML = `<div class="aviso-busca">${esc(err.message)}</div>`;
    }
  }

  function renderMensagens() {
    let dia = "";
    const ICONE = { simulada: "fa-solid fa-check", enviada: "fa-solid fa-check", entregue: "fa-solid fa-check-double", lida: "fa-solid fa-check-double lida", falhou: "fa-solid fa-triangle-exclamation", celular: "fa-solid fa-mobile-screen" };
    $("#chatMsgs").innerHTML = atend.mensagens.map((m) => {
      const d = new Date(m.em).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
      const sep = d !== dia ? `<div class="dia"><span>${esc(d.charAt(0).toUpperCase() + d.slice(1))}</span></div>` : "";
      dia = d;
      const autor = m.de === "loja"
        ? `<span class="msg__autor" style="--cor:${corPessoa(m.atendente)}">${m.status === "celular" ? "Pelo celular" : esc(nomePessoa(m.atendente))}</span>` : "";
      return `${sep}<div class="msg msg--${m.de}">
        ${autor}
        <div class="msg__texto">${esc(m.texto).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')}</div>
        <span class="msg__hora">${new Date(m.em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          ${m.de === "loja" && m.status ? `<i class="${ICONE[m.status] || ""}" title="${esc(m.status)}"></i>` : ""}</span>
      </div>`;
    }).join("") || `<div class="convs__vazio">Sem mensagens ainda.</div>`;
  }

  function renderBarra() {
    const c = conversaAberta();
    if (!c) return;
    const dono = c.atendente;
    const souEu = dono === eu.id;
    const gerente = eu.papel === "gerente";
    const outros = atend.equipe.filter((u) => u.id !== dono);
    const transferir = (souEu || gerente || !dono) && dono ? `
      <select class="sel-mini" id="selTransferir" aria-label="Transferir conversa">
        <option value="">Transferir para...</option>
        ${outros.map((u) => `<option value="${esc(u.id)}">${esc(u.nome)}</option>`).join("")}
      </select>` : "";
    $("#chatBarra").innerHTML = `
      <div class="barra__quem">
        ${dono
          ? `<span class="dono" style="--cor:${corPessoa(dono)}"><i class="fa-solid fa-headset"></i> ${souEu ? "Você está atendendo" : esc(nomePessoa(dono)) + " está atendendo"}</span>`
          : `<span class="dono dono--livre"><i class="fa-solid fa-bell"></i> Ninguém atendendo ainda</span>`}
      </div>
      <div class="barra__acoes">
        ${!dono ? `<button class="btn btn--ouro btn--sm" data-acao-chat="assumir"><i class="fa-solid fa-hand"></i> Assumir</button>` : ""}
        ${transferir}
        ${dono && (souEu || gerente) ? `<button class="btn btn--contorno btn--sm" data-acao-chat="liberar" title="Devolver para Novas">Liberar</button>` : ""}
        <select class="sel-mini sel-etapa etapa--${c.etapa}" id="selEtapa" aria-label="Etapa">
          ${Object.entries(ETAPAS).map(([k, v]) => `<option value="${k}"${k === c.etapa ? " selected" : ""}>${v}</option>`).join("")}
        </select>
      </div>`;

    // Aviso de quem pode responder e da janela de 24h do WhatsApp
    const aviso = $("#chat24h");
    const bloqueado = dono && !souEu && !gerente;
    const vencida = atend.modo === "whatsapp" && c.ultimaEntradaEm && Date.now() - new Date(c.ultimaEntradaEm) > 24 * 3600e3;
    aviso.hidden = !bloqueado && !vencida;
    aviso.innerHTML = bloqueado
      ? `<i class="fa-solid fa-lock"></i> Esta conversa está com <b>${esc(nomePessoa(dono))}</b>. Para responder, peça para transferir para você.`
      : vencida ? `<i class="fa-solid fa-clock"></i> Já passaram 24h da última mensagem do cliente. O WhatsApp só deixa responder quando ele mandar uma nova.` : "";
    $("#txtEnvio").disabled = !!bloqueado;
    $("#btnEnviar").disabled = !!bloqueado;
  }

  async function acao(nome, extra = {}, quieto = false) {
    const tel = atend.aberta;
    try {
      const { conversa } = await api(`/api/conversas/${tel}/acao`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ acao: nome, ...extra }),
      });
      const i = atend.conversas.findIndex((c) => c.tel === tel);
      if (i >= 0) atend.conversas[i] = conversa;
      renderAtend();
      if (!quieto) {
        const msg = { assumir: "Conversa assumida. Agora é com você!", liberar: "Conversa voltou para Novas.", transferir: `Transferida para ${nomePessoa(conversa.atendente)}.`, etapa: `Etapa: ${ETAPAS[conversa.etapa]}.`, notas: "Notas salvas." }[nome];
        if (msg) toast(msg);
      }
    } catch (err) {
      toast(err.message, true);
      carregarConversas(true);
    }
  }

  $("#chatBarra").addEventListener("click", (e) => {
    const b = e.target.closest("[data-acao-chat]");
    if (b) acao(b.dataset.acaoChat);
  });
  $("#chatBarra").addEventListener("change", (e) => {
    if (e.target.id === "selTransferir" && e.target.value) acao("transferir", { para: e.target.value });
    if (e.target.id === "selEtapa") acao("etapa", { etapa: e.target.value });
  });
  $("#chatNotasBtn").addEventListener("click", () => { $("#chatNotas").hidden = !$("#chatNotas").hidden; });
  $("#salvarNotas").addEventListener("click", () => acao("notas", { notas: $("#notas").value }));
  $("#chatVoltar").addEventListener("click", fecharConversa);

  $("#listaConv").addEventListener("click", (e) => {
    const li = e.target.closest(".conv");
    if (li) abrirConversa(li.dataset.tel);
  });
  $("#listaConv").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.classList.contains("conv")) abrirConversa(e.target.dataset.tel);
  });
  $("#filtroConv").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    atend.filtro = b.dataset.f;
    $$("#filtroConv button").forEach((x) => x.classList.toggle("ativo", x === b));
    renderAtend();
  });
  $("#buscaConv").addEventListener("input", (e) => { atend.busca = e.target.value; renderAtend(); });

  /* ---------- Enviar ---------- */
  const txt = $("#txtEnvio");
  const ajustarAltura = () => { txt.style.height = "auto"; txt.style.height = Math.min(txt.scrollHeight, 140) + "px"; };
  txt.addEventListener("input", ajustarAltura);
  txt.addEventListener("keydown", (e) => {
    // Enter envia no computador; Shift+Enter quebra linha
    if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer: fine)").matches) {
      e.preventDefault();
      $("#formEnvio").requestSubmit();
    }
  });

  $("#formEnvio").addEventListener("submit", async (e) => {
    e.preventDefault();
    const texto = txt.value.trim();
    if (!texto || !atend.aberta) return;
    const btn = $("#btnEnviar");
    btn.disabled = true;
    try {
      const { conversa } = await api(`/api/conversas/${atend.aberta}/mensagens`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ texto }),
      });
      txt.value = "";
      ajustarAltura();
      const i = atend.conversas.findIndex((c) => c.tel === conversa.tel);
      if (i >= 0) atend.conversas[i] = conversa;
      await carregarMensagens(true);
      renderAtend();
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
      renderBarra();
    }
  });

  function renderRapidas() {
    const L = typeof LOJA !== "undefined" ? LOJA : {};
    const frases = [
      ["Saudação", `Olá! Aqui é ${eu.papel === "gerente" ? "da" : `o ${eu.nome}, da`} MT Multimarcas 🏍️ Como posso te ajudar?`],
      ["Financiamento", "Para eu fazer a simulação do financiamento, me passa por favor seu nome completo, CPF e data de nascimento?"],
      ["Troca", "Aceitamos sua moto na troca! Me manda fotos dela, ano e quilometragem que eu faço a avaliação."],
      ["Endereço", `Estamos em ${L.endereco || "nossa loja"}. Horário: ${(L.horarios || []).join(" | ")}.`],
      ["Catálogo", `Dá uma olhada no nosso estoque completo: ${location.origin}/`],
    ];
    $("#rapidas").innerHTML = frases.map(([t, f], i) => `<button type="button" data-i="${i}">${esc(t)}</button>`).join("");
    $("#rapidas").onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      txt.value = frases[Number(b.dataset.i)][1];
      ajustarAltura();
      txt.focus();
    };
  }

  /* ---------- Mandar moto do estoque ---------- */
  $("#btnMotoChat").addEventListener("click", () => {
    const disp = estado.motos.filter((m) => m.status !== "vendida");
    $("#listaMotoChat").innerHTML = disp.length ? disp.map((m) => `
      <li class="item item--clique" data-id="${esc(m.id)}" tabindex="0">
        <div class="item__foto">${m.fotos?.[0] ? `<img src="${esc(fotoSrc(m.fotos[0]))}" alt="">` : `<div class="ilustra"><i class="fa-solid fa-motorcycle" style="color:var(--ouro)"></i></div>`}</div>
        <div class="item__info"><h3>${esc(m.marca)} ${esc(m.modelo)}</h3><p><span class="item__preco">${BRL.format(m.preco)}</span> · ${m.ano} · ${m.km ? NUM.format(m.km) + " km" : "0 km"}</p></div>
      </li>`).join("") : `<li class="convs__vazio">Nenhuma moto à venda no estoque.</li>`;
    $("#modalMotoChat").hidden = false;
  });
  $("#listaMotoChat").addEventListener("click", (e) => {
    const li = e.target.closest("[data-id]");
    if (!li) return;
    const m = estado.motos.find((x) => x.id === li.dataset.id);
    if (!m) return;
    txt.value = `🏍️ ${m.marca} ${m.modelo} ${m.ano}\n${m.km ? NUM.format(m.km) + " km" : "0 km"} · ${BRL.format(m.preco)}\nFotos e detalhes: ${location.origin}/#moto=${m.id}`;
    ajustarAltura();
    $("#modalMotoChat").hidden = true;
    txt.focus();
  });
  $("#modalMotoChat").addEventListener("click", (e) => { if (e.target.closest("[data-fechar-moto]")) $("#modalMotoChat").hidden = true; });

  /* ---------- Demonstração ---------- */
  const EXEMPLOS = [
    ["Bruno Almeida", "Olá! Tem alguma Bros 160 até R$ 18 mil?"],
    ["Aline Costa", "Bom dia, vocês financiam pra quem tem nome sujo?"],
    ["Diego Ramos", "Quanto vocês pagam numa Fan 160 2021 com 20 mil km?"],
    ["Larissa Prado", "Oi! A MT-03 azul ainda está disponível? Posso ir ver hoje?"],
  ];
  $("#btnSimular").addEventListener("click", () => {
    const [n, t] = EXEMPLOS[Math.floor(Math.random() * EXEMPLOS.length)];
    const f = $("#formSimular");
    f.nome.value = n;
    f.texto.value = t;
    $("#modalSimular").hidden = false;
  });
  $("#modalSimular").addEventListener("click", (e) => { if (e.target.closest("[data-fechar-sim]")) $("#modalSimular").hidden = true; });
  $("#formSimular").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      // Mesmo nome = mesmo cliente (telefone fixo por nome, para a demonstração)
      const existente = atend.conversas.find((c) => c.nome.toLowerCase() === f.nome.value.trim().toLowerCase());
      await api("/api/conversas/simular", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ nome: f.nome.value, texto: f.texto.value, tel: existente?.tel }),
      });
      $("#modalSimular").hidden = true;
      atend.filtro = existente?.atendente ? "todas" : "novas";
      $$("#filtroConv button").forEach((x) => x.classList.toggle("ativo", x.dataset.f === atend.filtro));
      await carregarConversas(true);
      if (atend.aberta) carregarMensagens();
    } catch (err) { toast(err.message, true); }
  });
  $("#btnReiniciarDemo").addEventListener("click", async () => {
    if (!confirm("Apagar as conversas de teste e criar as originais de novo?")) return;
    try {
      await api("/api/conversas/reiniciar", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
      fecharConversa();
      atend.novasVistas = null;
      await carregarConversas();
      toast("Demonstração reiniciada.");
    } catch (err) { toast(err.message, true); }
  });

  /* ---------- Atualização automática ---------- */
  function iniciarAtendimento() {
    clearInterval(atend.timer);
    carregarConversas();
    atend.timer = setInterval(() => {
      if (document.visibilityState !== "visible" || !token) return;
      carregarConversas(true);
      if (atend.aberta && !$("#abaAtendimento").hidden) carregarMensagens();
    }, 4000);
  }

  /* ---------- Início ---------- */
  (async () => {
    if (!token) return sair();
    try {
      ({ usuario: eu } = await api("/api/login", { method: "GET" })); // confere se a sessão ainda vale
      await carregar();
    } catch (err) {
      if (token) { mostrar("login"); $("#erroLogin").textContent = err.message; }
    }
  })();
})();
