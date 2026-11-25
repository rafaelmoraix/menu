import { BUTTONS, STD_PAD_MAP, bit, randomId, fmtTime } from "./shared.js";

const $ = (id) => document.getElementById(id);
const video = $("video"), stage = $("stage"), overlay = $("overlay");
const joinForm = $("joinForm"), waitBox = $("waitBox");
const statusPill = $("status"), msg = $("msg"), timerEl = $("timer");

// ---------- pré-preenche o código da sala a partir do link (#codigo) ----------
function parseRoom(v) {
  v = (v || "").trim();
  const hash = v.includes("#") ? v.split("#").pop() : v;
  return hash.replace(/[^a-z0-9]/gi, "").toLowerCase();
}
$("room").value = parseRoom(location.hash);
try { $("name").value = localStorage.getItem("pc_name") || ""; } catch {}

function setStatus(text, kind = "") {
  statusPill.textContent = text;
  statusPill.className = "pill " + kind;
}
function showWait(title, text) {
  joinForm.hidden = true; waitBox.hidden = false;
  $("waitTitle").textContent = title; $("waitText").textContent = text;
}
function showForm(text = "") {
  joinForm.hidden = false; waitBox.hidden = true; msg.textContent = text;
  $("joinBtn").disabled = false;
}

// ---------- conexão ----------
let peer = null, conn = null, hostId = null;
let playing = false, endsAt = 0;

joinForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const room = parseRoom($("room").value);
  const name = $("name").value.trim().slice(0, 24);
  const pin = $("pin").value.trim();
  if (room.length < 12) return (msg.textContent = "Código da sala inválido.");
  if (!/^\d{6}$/.test(pin)) return (msg.textContent = "O PIN tem 6 números.");
  try { localStorage.setItem("pc_name", name); } catch {}
  $("joinBtn").disabled = true;
  msg.textContent = "Conectando…";
  video.muted = false; // o clique em "Entrar" libera o áudio depois
  connect(room, name, pin);
});

function connect(room, name, pin) {
  cleanup();
  hostId = "pc-" + room;
  peer = new Peer("pcg-" + randomId(16), { debug: 0 });
  peer.on("open", () => {
    conn = peer.connect(hostId, { reliable: true, serialization: "json" });
    conn.on("open", () => {
      setStatus("conectado", "warn");
      conn.send({ t: "hello", name, pin });
    });
    conn.on("data", onHostMessage);
    conn.on("close", () => endSession("A conexão com a sala caiu."));
    conn.on("error", () => endSession("Erro na conexão com a sala."));
  });
  peer.on("call", (call) => {
    if (call.peer !== hostId) return call.close(); // só aceita vídeo do host
    call.answer();
    call.on("stream", (s) => { video.srcObject = s; video.play().catch(() => {}); });
  });
  peer.on("error", (err) => {
    const t = err.type === "peer-unavailable" ? "Sala não encontrada (ou está fechada)." : "Não deu pra conectar: " + err.type;
    endSession(t);
  });
}

function onHostMessage(m) {
  if (!m || typeof m !== "object") return;
  switch (m.t) {
    case "pin_bad":
      setStatus("PIN errado", "bad");
      showForm(`PIN errado. Tentativas restantes: ${m.left}.`);
      cleanup();
      break;
    case "blocked":
      endSession("Você foi bloqueado nesta sala.");
      break;
    case "waiting":
      setStatus("na fila", "warn");
      showWait("Aguardando aprovação…", m.pos > 1 ? `Você é o ${m.pos}º da fila.` : 'O dono da sala precisa clicar em "Aprovar".');
      break;
    case "denied":
      endSession("O dono da sala recusou a entrada.");
      break;
    case "start":
      playing = true;
      endsAt = performance.now() + m.seconds * 1000;
      overlay.hidden = true; timerEl.hidden = false; $("leaveBtn").hidden = false;
      setStatus("jogando", "ok");
      break;
    case "end":
      endSession(m.reason || "Sessão encerrada.");
      break;
  }
}

function endSession(text) {
  playing = false;
  if (document.pointerLockElement) document.exitPointerLock();
  overlay.hidden = false; timerEl.hidden = true; $("leaveBtn").hidden = true;
  video.srcObject = null;
  setStatus("desconectado", "bad");
  showForm(text);
  cleanup();
}

function cleanup() {
  // tira os listeners antes de fechar, senão o "close" sobrescreve a mensagem na tela
  try { conn && (conn.removeAllListeners(), conn.close()); } catch {}
  try { peer && (peer.removeAllListeners(), peer.destroy()); } catch {}
  conn = null; peer = null;
}

$("leaveBtn").onclick = () => { try { conn?.send({ t: "bye" }); } catch {} setTimeout(() => endSession("Você saiu."), 100); };
$("fsBtn").onclick = () => (document.fullscreenElement ? document.exitFullscreen() : stage.requestFullscreen?.());
$("muteBtn").onclick = () => { video.muted = !video.muted; $("muteBtn").textContent = video.muted ? "🔇 Mudo" : "🔊 Som"; };

// ---------- entrada: teclado + mouse ----------
const KEYMAP = {
  Space: "X", ShiftLeft: "A", ShiftRight: "A", KeyF: "Y", KeyR: "B",
  KeyQ: "RB", Tab: "LB", ControlLeft: "LS", KeyC: "RS",
  KeyV: "VIEW", KeyP: "MENU", Enter: "MENU",
  ArrowUp: "UP", ArrowDown: "DOWN", ArrowLeft: "LEFT", ArrowRight: "RIGHT",
};
const STICK_KEYS = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "KeyJ", "KeyK"]);
const keys = new Set();
let mouseL = false, mouseR = false, mdx = 0, mdy = 0, mrx = 0, mry = 0;
const MOUSE_SENS = 0.045;

addEventListener("keydown", (e) => {
  if (!playing) return;
  if (KEYMAP[e.code] || STICK_KEYS.has(e.code)) { e.preventDefault(); keys.add(e.code); }
});
addEventListener("keyup", (e) => keys.delete(e.code));
addEventListener("blur", () => { keys.clear(); mouseL = mouseR = false; });

stage.addEventListener("click", () => { if (playing && !document.pointerLockElement) stage.requestPointerLock?.(); });
stage.addEventListener("contextmenu", (e) => e.preventDefault());
addEventListener("mousemove", (e) => { if (document.pointerLockElement === stage) { mdx += e.movementX; mdy += e.movementY; } });
addEventListener("mousedown", (e) => {
  if (document.pointerLockElement !== stage) return;
  if (e.button === 0) mouseL = true; if (e.button === 2) mouseR = true;
});
addEventListener("mouseup", (e) => { if (e.button === 0) mouseL = false; if (e.button === 2) mouseR = false; });
document.addEventListener("pointerlockchange", () => { if (!document.pointerLockElement) { mouseL = mouseR = false; } });

// ---------- loop de leitura (controle + teclado) ----------
const DZ = 0.12;
const dz = (v) => (Math.abs(v) < DZ ? 0 : v);
const clamp1 = (v) => Math.max(-1, Math.min(1, v));

const viz = $("viz");
const vizEls = BUTTONS.map((n) => { const s = document.createElement("span"); s.className = "btnviz"; s.textContent = n; viz.append(s); return s; });

// Escolhe o controle certo: o último que teve um botão/analógico mexido.
// (Alguns PCs listam outros aparelhos como "controle": volante, fone, etc.)
let activePad = -1;
function pickPad() {
  const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter((p) => p && p.connected) : [];
  if (!pads.length) { activePad = -1; return null; }
  for (const p of pads) {
    const moved = p.buttons.some((x) => x.pressed) || p.axes.some((a) => Math.abs(a) > 0.5);
    if (moved) activePad = p.index;
  }
  return pads.find((p) => p.index === activePad) || pads.find((p) => p.mapping === "standard") || pads[0];
}

let padShown = "";
function updatePadUI(pad) {
  const label = pad ? pad.id.replace(/\s*\(.*?(Vendor|STANDARD).*?\)\s*/gi, " ").trim().slice(0, 40) || "Controle" : "";
  const key = pad ? pad.index + label + pad.mapping : "none";
  if (key === padShown) return;
  padShown = key;
  $("padPill").textContent = pad ? "🎮 controle ok" : "sem controle";
  $("padPill").className = "pill " + (pad ? "ok" : "warn");
  const box = $("padBox");
  if (!pad) {
    box.className = "notice";
    box.innerHTML = "🎮 <b>Ligue o controle no PC</b> (cabo ou Bluetooth) e <b>aperte qualquer botão</b> com esta página aberta.";
  } else {
    box.className = "notice ok";
    box.textContent = `✅ Controle reconhecido: ${label}` + (pad.mapping === "standard" ? "" : " (use Chrome ou Edge se algum botão ficar trocado)");
  }
}
addEventListener("gamepadconnected", () => { padShown = ""; });
addEventListener("gamepaddisconnected", () => { padShown = ""; activePad = -1; });

// Avisa quando a janela perde o foco: o navegador para de ler o controle.
function updateFocus() {
  $("focusWarn").hidden = !playing || (document.hasFocus() && !document.hidden);
}
addEventListener("focus", updateFocus); addEventListener("blur", updateFocus);
document.addEventListener("visibilitychange", updateFocus);
setInterval(updateFocus, 1000);

let last = "", lastSent = 0;
function frame(now) {
  requestAnimationFrame(frame);
  let b = 0, lx = 0, ly = 0, rx = 0, ry = 0, lt = 0, rt = 0;

  // controle físico (o controle ligado no PC do amigo)
  const pad = pickPad();
  updatePadUI(pad);
  if (pad) {
    pad.buttons.forEach((btn, i) => {
      const name = STD_PAD_MAP[i]; // índice 16 (botão Xbox) não está no mapa → ignorado
      if (name && btn.pressed) b |= bit(name);
    });
    lt = pad.buttons[6]?.value || 0;
    rt = pad.buttons[7]?.value || 0;
    lx = dz(pad.axes[0] || 0); ly = dz(pad.axes[1] || 0);
    rx = dz(pad.axes[2] || 0); ry = dz(pad.axes[3] || 0);
  }

  // teclado
  for (const k of keys) if (KEYMAP[k]) b |= bit(KEYMAP[k]);
  if (keys.has("KeyA")) lx = -1; if (keys.has("KeyD")) lx = 1;
  if (keys.has("KeyW")) ly = -1; if (keys.has("KeyS")) ly = 1;
  if (keys.has("KeyJ") || mouseR) lt = 1;
  if (keys.has("KeyK") || mouseL) rt = 1;

  // mouse → analógico direito (suavizado)
  mrx = mrx * 0.55 + clamp1(mdx * MOUSE_SENS) * 0.45;
  mry = mry * 0.55 + clamp1(mdy * MOUSE_SENS) * 0.45;
  mdx = mdy = 0;
  if (Math.abs(mrx) > 0.02) rx = clamp1(rx + mrx); else mrx = 0;
  if (Math.abs(mry) > 0.02) ry = clamp1(ry + mry); else mry = 0;

  vizEls.forEach((el, i) => el.classList.toggle("on", !!(b & (1 << i))));

  if (playing) {
    const left = (endsAt - now) / 1000;
    timerEl.textContent = fmtTime(left);
    timerEl.classList.toggle("low", left < 30);
  }

  if (!playing || !conn || !conn.open) return;
  const r = (v) => Math.round(v * 1000) / 1000;
  const state = { t: "in", b, lx: r(lx), ly: r(ly), rx: r(rx), ry: r(ry), lt: r(lt), rt: r(rt) };
  const key = JSON.stringify(state);
  // manda quando muda, e reenvia a cada 100ms como "batimento"
  if (key !== last || now - lastSent > 100) {
    conn.send(state);
    last = key; lastSent = now;
  }
}
requestAnimationFrame(frame);
