import { BUTTONS, NEUTRAL, sanitizeInput, randomId, randomPin, fmtTime } from "./shared.js";

const $ = (id) => document.getElementById(id);
const DEFAULT_SITE = "https://passa-o-controle.netlify.app/play.html";
const MAX_PIN_TRIES = 3;        // por pessoa
const MAX_GLOBAL_FAILS = 10;    // somando todo mundo → PIN é trocado
const MAX_QUEUE = 8;
const HELLO_TIMEOUT_MS = 10000;
const MAX_MSGS_PER_SEC = 240;   // acima disso a pessoa é derrubada

// ---------- log ----------
function log(text) {
  const line = document.createElement("div");
  line.textContent = `${new Date().toLocaleTimeString()}  ${text}`;
  $("log").prepend(line);
}

// ---------- agente local (controle virtual) ----------
let agent = null;
function connectAgent() {
  if (location.hostname !== "127.0.0.1" && location.hostname !== "localhost") {
    $("agentPill").textContent = "abra esta página pelo agente (127.0.0.1)";
    return;
  }
  agent = new WebSocket(`ws://${location.host}/ws`);
  agent.onopen = () => { $("agentPill").textContent = "agente: ok"; $("agentPill").className = "pill ok"; };
  agent.onmessage = (e) => {
    try { const m = JSON.parse(e.data); if (m.t === "info") log(`Agente: ${m.text}`); } catch {}
  };
  agent.onclose = () => {
    $("agentPill").textContent = "agente: offline"; $("agentPill").className = "pill bad";
    setTimeout(connectAgent, 1500);
  };
}
function toAgent(obj) {
  if (agent && agent.readyState === WebSocket.OPEN) agent.send(JSON.stringify(obj));
}
connectAgent();

// ---------- configuração ----------
try { $("siteUrl").value = localStorage.getItem("pc_site") || DEFAULT_SITE; } catch { $("siteUrl").value = DEFAULT_SITE; }
$("siteUrl").addEventListener("change", () => { try { localStorage.setItem("pc_site", $("siteUrl").value.trim()); } catch {} updateShare(); });

// ---------- estado da sala ----------
let peer = null, stream = null, roomCode = null, pin = null;
let globalFails = 0;
const guests = new Map();   // peerId -> { conn, name, status, msgCount, msgWindow }
const tries = new Map();    // peerId -> tentativas erradas
const blocked = new Set();
let current = null;         // { id, call, endsAt }

function updateShare() {
  if (!roomCode) return;
  const base = $("siteUrl").value.trim() || DEFAULT_SITE;
  $("shareLink").textContent = `${base.split("#")[0]}#${roomCode}`;
}
function newPin() {
  pin = randomPin(); globalFails = 0; tries.clear();
  $("pin").textContent = pin;
}

$("openBtn").onclick = async () => {
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: { ideal: 60, max: 60 }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: true,
    });
  } catch {
    return log("Captura de tela cancelada.");
  }
  const vt = stream.getVideoTracks()[0];
  if (vt) vt.contentHint = "motion";
  vt?.addEventListener("ended", () => closeRoom("Captura de tela encerrada."));
  $("preview").srcObject = stream;
  $("previewOverlay").hidden = true;

  roomCode = randomId(20);
  newPin();
  peer = new Peer("pc-" + roomCode, { debug: 0 });
  peer.on("open", () => {
    $("roomPill").textContent = "sala aberta"; $("roomPill").className = "pill ok";
    $("shareBox").hidden = false; updateShare();
    $("openBtn").disabled = true; $("closeBtn").disabled = false;
    log("Sala aberta.");
  });
  peer.on("connection", onGuestConnection);
  peer.on("call", (c) => c.close()); // ninguém liga pra gente
  peer.on("error", (err) => log("Erro de rede: " + err.type));
  peer.on("disconnected", () => { try { peer.reconnect(); } catch {} });
};

$("closeBtn").onclick = () => closeRoom("Sala fechada pelo dono.");
$("panicBtn").onclick = () => closeRoom("Pânico! Tudo desligado.");
$("newPinBtn").onclick = () => { newPin(); log("PIN trocado."); };
$("copyBtn").onclick = () => navigator.clipboard?.writeText($("shareLink").textContent).then(() => log("Link copiado."));
$("kickBtn").onclick = () => current && endPlayer(current.id, "O dono encerrou sua vez.");
$("addTime").onclick = () => {
  if (!current) return;
  current.endsAt += 120000;
  const g = guests.get(current.id);
  g?.conn.send({ t: "start", seconds: (current.endsAt - performance.now()) / 1000 });
};

function closeRoom(reason) {
  toAgent(NEUTRAL);
  for (const [id] of guests) dropGuest(id, reason);
  try { peer?.destroy(); } catch {}
  stream?.getTracks().forEach((t) => t.stop());
  peer = null; stream = null; roomCode = null; current = null;
  $("preview").srcObject = null; $("previewOverlay").hidden = false;
  $("shareBox").hidden = true; $("timer").hidden = true;
  $("roomPill").textContent = "sala fechada"; $("roomPill").className = "pill";
  $("openBtn").disabled = false; $("closeBtn").disabled = true;
  renderCurrent(); renderQueue();
  log(reason);
}

// ---------- convidados ----------
function onGuestConnection(conn) {
  const id = conn.peer;
  if (blocked.has(id) || guests.size >= MAX_QUEUE + 1) {
    conn.on("open", () => { conn.send({ t: blocked.has(id) ? "blocked" : "end", reason: "Sala cheia." }); setTimeout(() => conn.close(), 200); });
    return;
  }
  const g = { conn, name: "?", status: "new", msgCount: 0, msgWindow: performance.now() };
  guests.set(id, g);
  const helloTimer = setTimeout(() => { if (g.status === "new") dropGuest(id); }, HELLO_TIMEOUT_MS);

  conn.on("data", (m) => {
    // limite de mensagens por segundo
    const now = performance.now();
    if (now - g.msgWindow > 1000) { g.msgWindow = now; g.msgCount = 0; }
    if (++g.msgCount > MAX_MSGS_PER_SEC) { log(`${g.name}: mensagens demais, derrubado.`); return dropGuest(id, "Conexão derrubada."); }
    if (!m || typeof m !== "object") return;

    if (g.status === "new" && m.t === "hello") {
      clearTimeout(helloTimer);
      const name = String(m.name || "").replace(/[\u0000-\u001f]/g, "").trim().slice(0, 24) || "Sem nome";
      if (String(m.pin) !== pin) {
        const n = (tries.get(id) || 0) + 1; tries.set(id, n);
        globalFails++;
        log(`PIN errado de "${name}" (${n}/${MAX_PIN_TRIES}).`);
        if (n >= MAX_PIN_TRIES) { blocked.add(id); conn.send({ t: "blocked" }); }
        else conn.send({ t: "pin_bad", left: MAX_PIN_TRIES - n });
        if (globalFails >= MAX_GLOBAL_FAILS) { newPin(); log("Muitos PINs errados: PIN trocado automaticamente."); }
        setTimeout(() => dropGuest(id), 300);
        return;
      }
      g.name = name; g.status = "waiting";
      log(`"${name}" entrou na fila.`);
      renderQueue();
      return;
    }

    if (m.t === "bye") return dropGuest(id);

    // input só vale de quem está jogando agora
    if (m.t === "in" && current && current.id === id) {
      const clean = sanitizeInput(m);
      if (clean) { toAgent(clean); showViz(clean.b); }
    }
  });
  conn.on("close", () => dropGuest(id));
  conn.on("error", () => dropGuest(id));
}

function dropGuest(id, reason) {
  const g = guests.get(id);
  if (!g) return;
  if (current && current.id === id) {
    toAgent(NEUTRAL); showViz(0);
    try { current.call?.close(); } catch {}
    current = null; renderCurrent();
  }
  if (reason) { try { g.conn.send({ t: "end", reason }); } catch {} }
  guests.delete(id);
  setTimeout(() => { try { g.conn.close(); } catch {} }, 200);
  renderQueue();
}

function approve(id) {
  const g = guests.get(id);
  if (!g || g.status !== "waiting" || !stream) return;
  if (current) endPlayer(current.id, "Sua vez acabou.");
  g.status = "playing";
  const seconds = Math.max(1, Math.min(30, Number($("minutes").value) || 5)) * 60;
  const call = peer.call(id, stream);
  tuneBitrate(call);
  current = { id, call, endsAt: performance.now() + seconds * 1000 };
  g.conn.send({ t: "start", seconds });
  log(`"${g.name}" começou a jogar (${seconds / 60} min).`);
  renderCurrent(); renderQueue();
}

function endPlayer(id, reason) {
  const g = guests.get(id);
  log(`Vez de "${g?.name}" acabou.`);
  dropGuest(id, reason);
}

function tuneBitrate(call) {
  let tries = 0;
  const t = setInterval(() => {
    const pc = call.peerConnection;
    if (++tries > 40) return clearInterval(t);
    if (!pc) return;
    const sender = pc.getSenders().find((s) => s.track && s.track.kind === "video");
    if (!sender) return;
    clearInterval(t);
    const p = sender.getParameters();
    if (!p.encodings || !p.encodings.length) p.encodings = [{}];
    p.encodings[0].maxBitrate = 8_000_000;
    p.degradationPreference = "maintain-framerate";
    sender.setParameters(p).catch(() => {});
  }, 250);
}

// ---------- timer ----------
setInterval(() => {
  if (!current) return;
  const left = (current.endsAt - performance.now()) / 1000;
  $("timer").hidden = false;
  $("timer").textContent = fmtTime(left);
  $("timer").classList.toggle("low", left < 30);
  if (left <= 0) endPlayer(current.id, "O tempo acabou! Valeu por jogar.");
}, 250);

// ---------- UI ----------
function renderQueue() {
  const q = $("queue");
  q.replaceChildren();
  const waiting = [...guests].filter(([, g]) => g.status === "waiting");
  if (!waiting.length) { q.innerHTML = '<span class="muted">Vazia.</span>'; return; }
  waiting.forEach(([id, g], i) => {
    try { g.conn.send({ t: "waiting", pos: i + 1 }); } catch {}
    const row = document.createElement("div"); row.className = "item";
    const name = document.createElement("b"); name.textContent = g.name;
    const btns = document.createElement("div"); btns.className = "row";
    const ok = document.createElement("button"); ok.className = "btn small"; ok.textContent = "Aprovar"; ok.onclick = () => approve(id);
    const no = document.createElement("button"); no.className = "btn ghost small"; no.textContent = "Recusar";
    no.onclick = () => { try { g.conn.send({ t: "denied" }); } catch {} dropGuest(id); };
    const ban = document.createElement("button"); ban.className = "btn ghost small"; ban.textContent = "Bloquear";
    ban.onclick = () => { blocked.add(id); try { g.conn.send({ t: "blocked" }); } catch {} dropGuest(id); };
    btns.append(ok, no, ban); row.append(name, btns); q.append(row);
  });
}

function renderCurrent() {
  const el = $("current");
  const g = current && guests.get(current.id);
  el.textContent = g ? `🎮 ${g.name} está jogando.` : "Ninguém jogando.";
  $("kickBtn").disabled = !g; $("addTime").disabled = !g;
  if (!g) $("timer").hidden = true;
}

const vizEls = BUTTONS.map((n) => { const s = document.createElement("span"); s.className = "btnviz"; s.textContent = n; $("viz").append(s); return s; });
function showViz(b) { vizEls.forEach((el, i) => el.classList.toggle("on", !!(b & (1 << i)))); }

addEventListener("beforeunload", () => toAgent(NEUTRAL));
