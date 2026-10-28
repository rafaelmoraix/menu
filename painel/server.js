'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

loadEnv(path.join(__dirname, '.env'));

const API_URL = process.env.API_URL || 'https://baratoebom.com/api/v2';
const API_KEY = process.env.API_KEY || '';
const MOCK = process.env.MOCK === '1' || !API_KEY;
const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || '127.0.0.1';
const APP_PASSWORD = process.env.APP_PASSWORD || '';
const DATA_DIR = path.join(__dirname, 'data');
const HISTORY_FILE = path.join(DATA_DIR, 'history.json');
const PUBLIC_DIR = path.join(__dirname, 'public');
const SERVICES_TTL = 5 * 60 * 1000;
const BATCH = 100;

const mock = MOCK ? require('./mock') : null;

// ---------- .env ----------

function loadEnv(file) {
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/i);
    if (!m || process.env[m[1]] !== undefined) continue;
    process.env[m[1]] = m[2].replace(/^(['"])(.*)\1$/, '$2');
  }
}

// ---------- API upstream ----------

class ApiError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.status = status;
  }
}

async function callApi(action, params = {}) {
  if (mock) return mock.call(action, params);

  const body = new URLSearchParams({ key: API_KEY, action });
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') body.append(k, String(v));
  }

  let res;
  try {
    res = await fetch(API_URL, {
      method: 'POST',
      body,
      headers: { 'User-Agent': 'Mozilla/5.0 (painel-smm)' },
      signal: AbortSignal.timeout(30000),
    });
  } catch (err) {
    throw new ApiError(`Falha ao conectar na API: ${err.message}`);
  }

  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new ApiError(`Resposta inválida da API (HTTP ${res.status})`);
  }
  if (data && !Array.isArray(data) && typeof data.error === 'string') {
    throw new ApiError(data.error, 400);
  }
  return data;
}

let servicesCache = { at: 0, list: null };

async function getServices(force = false) {
  if (!force && servicesCache.list && Date.now() - servicesCache.at < SERVICES_TTL) {
    return servicesCache.list;
  }
  const list = await callApi('services');
  if (!Array.isArray(list)) throw new ApiError('Lista de serviços inválida');
  servicesCache = { at: Date.now(), list };
  return list;
}

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function errorText(value) {
  return value && typeof value === 'object' && value.error ? String(value.error) : null;
}

// ---------- histórico local ----------
// A API não lista pedidos, então guardamos os IDs criados por aqui.

function readHistory() {
  try {
    const data = JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf8'));
    return Array.isArray(data.orders) ? data : { orders: [] };
  } catch {
    return { orders: [] };
  }
}

function writeHistory(history) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const tmp = `${HISTORY_FILE}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(history, null, 2));
  fs.renameSync(tmp, HISTORY_FILE);
}

function findOrder(history, id) {
  return history.orders.find(o => String(o.id) === String(id));
}

// ---------- handlers ----------

async function handleBalance() {
  return callApi('balance');
}

async function handleServices(query) {
  return getServices(query.get('refresh') === '1');
}

async function handleAddOrder(body) {
  const services = await getServices();
  const service = services.find(s => String(s.service) === String(body.service));
  if (!service) throw new ApiError('Serviço não encontrado', 400);

  const link = String(body.link || '').trim();
  if (!link) throw new ApiError('Informe o link', 400);

  const type = String(service.type || 'Default');
  const params = { service: service.service, link };
  let quantity = Number(body.quantity) || 0;

  if (type === 'Custom Comments') {
    const comments = String(body.comments || '')
      .split(/\r?\n/)
      .map(s => s.trim())
      .filter(Boolean);
    if (!comments.length) throw new ApiError('Informe ao menos um comentário', 400);
    quantity = comments.length;
    params.comments = comments.join('\n');
  } else if (type !== 'Package') {
    params.quantity = quantity;
  }

  if (type !== 'Package') {
    const min = Number(service.min);
    const max = Number(service.max);
    if (!Number.isInteger(quantity) || quantity < min || quantity > max) {
      throw new ApiError(`Quantidade deve estar entre ${min} e ${max}`, 400);
    }
  }

  const runs = Number(body.runs) || 0;
  const interval = Number(body.interval) || 0;
  if (runs || interval) {
    if (!Number.isInteger(runs) || runs < 1 || !Number.isInteger(interval) || interval < 1) {
      throw new ApiError('Drip-feed: informe execuções e intervalo (inteiros ≥ 1)', 400);
    }
    params.runs = runs;
    params.interval = interval;
  }

  const result = await callApi('add', params);
  if (!result || !result.order) throw new ApiError('A API não retornou o ID do pedido');

  const total = type === 'Package' ? 1 : quantity * (runs || 1);
  const entry = {
    id: result.order,
    service: service.service,
    serviceName: service.name,
    category: service.category,
    type,
    link,
    quantity: type === 'Package' ? null : quantity,
    runs: runs || null,
    interval: interval || null,
    estimate: type === 'Package' ? Number(service.rate) : (Number(service.rate) * total) / 1000,
    createdAt: new Date().toISOString(),
    refills: [],
    status: null,
  };
  const history = readHistory();
  history.orders.unshift(entry);
  writeHistory(history);
  return entry;
}

async function handleListOrders() {
  const history = readHistory();
  const ids = history.orders.map(o => o.id);

  for (const group of chunk(ids, BATCH)) {
    let result;
    try {
      result = await callApi('status', { orders: group.join(',') });
    } catch (err) {
      // Mantém o último status salvo se a consulta falhar.
      return { orders: history.orders, warning: err.message };
    }
    for (const id of group) {
      const st = result && result[id];
      if (!st) continue;
      const order = findOrder(history, id);
      order.status = errorText(st) ? { error: errorText(st) } : st;
      order.checkedAt = new Date().toISOString();
    }
  }

  const refillIds = history.orders.flatMap(o => o.refills.map(r => r.id));
  for (const group of chunk(refillIds, BATCH)) {
    let result;
    try {
      result = await callApi('refill_status', { refills: group.join(',') });
    } catch {
      break;
    }
    const byId = new Map((Array.isArray(result) ? result : []).map(r => [String(r.refill), r.status]));
    for (const order of history.orders) {
      for (const r of order.refills) {
        if (!byId.has(String(r.id))) continue;
        const st = byId.get(String(r.id));
        r.status = errorText(st) ? `Erro: ${errorText(st)}` : String(st);
      }
    }
  }

  writeHistory(history);
  return { orders: history.orders };
}

function parseIds(value) {
  const ids = (Array.isArray(value) ? value : String(value || '').split(/[\s,;]+/))
    .map(v => String(v).trim())
    .filter(v => /^\d+$/.test(v));
  if (!ids.length) throw new ApiError('Nenhum ID de pedido válido', 400);
  if (ids.length > BATCH) throw new ApiError(`Máximo de ${BATCH} pedidos por vez`, 400);
  return [...new Set(ids)];
}

async function handleRefill(body) {
  const ids = parseIds(body.orders);
  const result = await callApi('refill', { orders: ids.join(',') });
  const rows = Array.isArray(result) ? result : [{ order: ids[0], refill: result && result.refill }];

  const history = readHistory();
  const out = rows.map(row => {
    const err = errorText(row.refill);
    if (!err && row.refill) {
      const order = findOrder(history, row.order);
      if (order) order.refills.push({ id: row.refill, createdAt: new Date().toISOString(), status: 'Pending' });
    }
    return { order: row.order, ok: !err && !!row.refill, refill: err ? null : row.refill, error: err };
  });
  writeHistory(history);
  return out;
}

async function handleCancel(body) {
  const ids = parseIds(body.orders);
  const result = await callApi('cancel', { orders: ids.join(',') });
  return (Array.isArray(result) ? result : []).map(row => {
    const err = errorText(row.cancel);
    return { order: row.order, ok: !err, error: err };
  });
}

async function handleImport(body) {
  const ids = parseIds(body.orders);
  const history = readHistory();
  const added = [];
  for (const id of ids) {
    if (findOrder(history, id)) continue;
    const entry = {
      id: Number(id),
      service: null,
      serviceName: 'Importado',
      category: null,
      type: null,
      link: null,
      quantity: null,
      runs: null,
      interval: null,
      estimate: null,
      createdAt: new Date().toISOString(),
      refills: [],
      status: null,
    };
    history.orders.unshift(entry);
    added.push(id);
  }
  writeHistory(history);
  return { added: added.length };
}

function handleRemove(id) {
  const history = readHistory();
  const before = history.orders.length;
  history.orders = history.orders.filter(o => String(o.id) !== String(id));
  if (history.orders.length === before) throw new ApiError('Pedido não está no histórico', 404);
  writeHistory(history);
  return { removed: id };
}

// ---------- HTTP ----------

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function send(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const parts = [];
    req.on('data', c => {
      size += c.length;
      if (size > 1e6) {
        reject(new ApiError('Corpo da requisição muito grande', 413));
        req.destroy();
      } else parts.push(c);
    });
    req.on('end', () => {
      const raw = Buffer.concat(parts).toString('utf8');
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new ApiError('JSON inválido', 400));
      }
    });
    req.on('error', reject);
  });
}

function authorized(req) {
  if (!APP_PASSWORD) return true;
  const header = req.headers.authorization || '';
  if (!header.startsWith('Basic ')) return false;
  const decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  const pass = decoded.slice(decoded.indexOf(':') + 1);
  const a = crypto.createHash('sha256').update(pass).digest();
  const b = crypto.createHash('sha256').update(APP_PASSWORD).digest();
  return crypto.timingSafeEqual(a, b);
}

function serveStatic(req, res, pathname) {
  const rel = pathname === '/' ? 'index.html' : pathname.slice(1);
  const file = path.normalize(path.join(PUBLIC_DIR, rel));
  if (!file.startsWith(PUBLIC_DIR + path.sep)) {
    res.writeHead(403);
    return res.end();
  }
  fs.readFile(file, (err, buf) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Não encontrado');
    }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(buf);
  });
}

async function route(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const { pathname } = url;
  const method = req.method;

  if (!authorized(req)) {
    res.writeHead(401, { 'WWW-Authenticate': 'Basic realm="Painel"' });
    return res.end('Autenticação necessária');
  }

  if (!pathname.startsWith('/api/')) {
    if (method !== 'GET' && method !== 'HEAD') {
      res.writeHead(405);
      return res.end();
    }
    return serveStatic(req, res, pathname);
  }

  try {
    let data;
    if (method === 'GET' && pathname === '/api/config') data = { mock: MOCK };
    else if (method === 'GET' && pathname === '/api/balance') data = await handleBalance();
    else if (method === 'GET' && pathname === '/api/services') data = await handleServices(url.searchParams);
    else if (method === 'GET' && pathname === '/api/orders') data = await handleListOrders();
    else if (method === 'POST' && pathname === '/api/orders') data = await handleAddOrder(await readBody(req));
    else if (method === 'POST' && pathname === '/api/orders/refill') data = await handleRefill(await readBody(req));
    else if (method === 'POST' && pathname === '/api/orders/cancel') data = await handleCancel(await readBody(req));
    else if (method === 'POST' && pathname === '/api/orders/import') data = await handleImport(await readBody(req));
    else if (method === 'DELETE' && pathname.startsWith('/api/orders/')) data = handleRemove(pathname.split('/').pop());
    else return send(res, 404, { error: 'Rota não encontrada' });
    send(res, 200, data);
  } catch (err) {
    const status = err instanceof ApiError ? err.status : 500;
    if (status === 500) console.error(err);
    send(res, status, { error: err.message || 'Erro interno' });
  }
}

http.createServer(route).listen(PORT, HOST, () => {
  console.log(`Painel rodando em http://${HOST}:${PORT}`);
  if (MOCK) console.log('Modo DEMONSTRAÇÃO (sem API_KEY): dados simulados, nenhum pedido real é feito.');
  if (!APP_PASSWORD && HOST !== '127.0.0.1' && HOST !== 'localhost') {
    console.warn('ATENÇÃO: servidor exposto sem APP_PASSWORD — qualquer um pode gastar seu saldo.');
  }
});
