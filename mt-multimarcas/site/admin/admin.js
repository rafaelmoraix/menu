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
      const { token: t } = await api("/api/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ senha: $("#senha").value }),
      });
      token = t;
      try { localStorage.setItem(CHAVE_TOKEN, t); } catch (_) {}
      await carregar();
    } catch (err) {
      $("#erroLogin").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
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
    render();
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

  /* ---------- Início ---------- */
  (async () => {
    if (!token) return sair();
    try {
      await api("/api/login", { method: "GET" }); // confere se a sessão ainda vale
      await carregar();
    } catch (err) {
      if (token) { mostrar("login"); $("#erroLogin").textContent = err.message; }
    }
  })();
})();
