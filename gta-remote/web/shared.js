// Coisas usadas tanto pelo host quanto pelo jogador.
// O botão Xbox (guide / botão do meio) NÃO existe nesta lista de propósito:
// ele nunca é enviado, nunca é aceito e o agente não sabe apertá-lo.
export const BUTTONS = [
  "A", "B", "X", "Y",
  "LB", "RB",
  "VIEW", "MENU",
  "LS", "RS",
  "UP", "DOWN", "LEFT", "RIGHT",
];
export const BUTTON_MASK_ALL = (1 << BUTTONS.length) - 1;

// Índices do Gamepad API "standard mapping" -> nome do botão.
// 6 e 7 são os gatilhos (analógicos, tratados à parte). 16 é o botão Xbox: ignorado.
export const STD_PAD_MAP = {
  0: "A", 1: "B", 2: "X", 3: "Y",
  4: "LB", 5: "RB",
  8: "VIEW", 9: "MENU",
  10: "LS", 11: "RS",
  12: "UP", 13: "DOWN", 14: "LEFT", 15: "RIGHT",
};

export const bit = (name) => 1 << BUTTONS.indexOf(name);

const clamp = (v, lo, hi) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.min(hi, Math.max(lo, n));
};

// Valida e limpa qualquer pacote de input que chegue da rede.
// Retorna null se o pacote for lixo.
export function sanitizeInput(msg) {
  if (!msg || typeof msg !== "object" || msg.t !== "in") return null;
  const b = Number(msg.b);
  if (!Number.isInteger(b) || b < 0) return null;
  return {
    t: "in",
    b: b & BUTTON_MASK_ALL, // corta qualquer bit fora da lista permitida
    lx: clamp(msg.lx, -1, 1),
    ly: clamp(msg.ly, -1, 1),
    rx: clamp(msg.rx, -1, 1),
    ry: clamp(msg.ry, -1, 1),
    lt: clamp(msg.lt, 0, 1),
    rt: clamp(msg.rt, 0, 1),
  };
}

export const NEUTRAL = { t: "in", b: 0, lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0 };

export function randomId(len = 20) {
  const abc = "abcdefghijkmnpqrstuvwxyz23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(len));
  return Array.from(bytes, (x) => abc[x % abc.length]).join("");
}

export function randomPin() {
  const n = crypto.getRandomValues(new Uint32Array(1))[0] % 1000000;
  return String(n).padStart(6, "0");
}

export function fmtTime(sec) {
  sec = Math.max(0, Math.round(sec));
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}
