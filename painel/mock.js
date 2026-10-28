'use strict';

// API simulada para testar o painel sem chave e sem gastar saldo.
// Imita as respostas documentadas em https://baratoebom.com/api/v2.

const services = [
  { service: 1, name: 'Instagram Seguidores [Brasileiros]', type: 'Default', category: 'Instagram Seguidores', rate: '0.90', min: '50', max: '10000', refill: true, cancel: true },
  { service: 2, name: 'Instagram Seguidores [Mundiais] [Sem reposição]', type: 'Default', category: 'Instagram Seguidores', rate: '0.35', min: '100', max: '50000', refill: false, cancel: false },
  { service: 3, name: 'Instagram Curtidas [Rápidas]', type: 'Default', category: 'Instagram Curtidas', rate: '0.12', min: '20', max: '20000', refill: true, cancel: true },
  { service: 4, name: 'Instagram Comentários Personalizados', type: 'Custom Comments', category: 'Instagram Comentários', rate: '8', min: '5', max: '1500', refill: false, cancel: true },
  { service: 5, name: 'Instagram Visualizações Reels', type: 'Default', category: 'Instagram Visualizações', rate: '0.02', min: '100', max: '1000000', refill: false, cancel: false },
  { service: 6, name: 'TikTok Seguidores', type: 'Default', category: 'TikTok', rate: '1.80', min: '100', max: '20000', refill: true, cancel: true },
  { service: 7, name: 'TikTok Curtidas', type: 'Default', category: 'TikTok', rate: '0.25', min: '50', max: '50000', refill: false, cancel: true },
  { service: 8, name: 'TikTok Visualizações', type: 'Default', category: 'TikTok', rate: '0.01', min: '500', max: '10000000', refill: false, cancel: false },
  { service: 9, name: 'YouTube Inscritos [Reposição 30 dias]', type: 'Default', category: 'YouTube', rate: '12.50', min: '50', max: '5000', refill: true, cancel: true },
  { service: 10, name: 'YouTube Visualizações [Retenção alta]', type: 'Default', category: 'YouTube', rate: '1.20', min: '1000', max: '500000', refill: true, cancel: false },
  { service: 11, name: 'Kwai Seguidores', type: 'Default', category: 'Kwai', rate: '2.00', min: '100', max: '10000', refill: false, cancel: true },
  { service: 12, name: 'Pacote Instagram Iniciante', type: 'Package', category: 'Pacotes', rate: '5.00', min: '1', max: '1', refill: false, cancel: false },
];

let balance = 100.84292;
let nextOrder = 23501;
let nextRefill = 1;
const orders = new Map();
const refills = new Map();

function fail(error) {
  return { error };
}

function orderStatus(o) {
  if (o.canceled) return { charge: '0', start_count: String(o.start), status: 'Canceled', remains: String(o.quantity), currency: 'USD' };
  const age = (Date.now() - o.at) / 1000;
  let status = 'Pending';
  let remains = o.quantity;
  if (age > 15) {
    status = 'In progress';
    remains = Math.max(0, Math.round(o.quantity * (1 - (age - 15) / 60)));
  }
  if (age > 75) {
    status = o.partial ? 'Partial' : 'Completed';
    remains = o.partial ? Math.round(o.quantity * 0.1) : 0;
  }
  return {
    charge: o.charge.toFixed(5),
    start_count: String(o.start),
    status,
    remains: String(remains),
    currency: 'USD',
  };
}

function ids(value) {
  return String(value || '').split(',').map(s => s.trim()).filter(Boolean);
}

async function call(action, p) {
  await new Promise(r => setTimeout(r, 150));

  switch (action) {
    case 'balance':
      return { balance: balance.toFixed(5), currency: 'USD' };

    case 'services':
      return services;

    case 'add': {
      const s = services.find(x => String(x.service) === String(p.service));
      if (!s) return fail('Incorrect service ID');
      const qty = s.type === 'Package' ? 1 : s.type === 'Custom Comments' ? ids(p.comments?.replace(/\n/g, ',')).length : Number(p.quantity);
      const total = qty * (Number(p.runs) || 1);
      const charge = s.type === 'Package' ? Number(s.rate) : (Number(s.rate) * total) / 1000;
      if (charge > balance) return fail('Not enough funds on balance');
      balance -= charge;
      const id = nextOrder++;
      orders.set(String(id), {
        at: Date.now(),
        quantity: total,
        charge,
        start: Math.floor(Math.random() * 5000),
        partial: Math.random() < 0.15,
        canceled: false,
        service: s,
      });
      return { order: id };
    }

    case 'status': {
      if (p.order) {
        const o = orders.get(String(p.order));
        return o ? orderStatus(o) : fail('Incorrect order ID');
      }
      const out = {};
      for (const id of ids(p.orders)) {
        const o = orders.get(id);
        out[id] = o ? orderStatus(o) : { error: 'Incorrect order ID' };
      }
      return out;
    }

    case 'refill': {
      const one = id => {
        const o = orders.get(id);
        if (!o) return { error: 'Incorrect order ID' };
        if (!o.service.refill) return { error: 'Refill is disabled for this service' };
        const st = orderStatus(o).status;
        if (st !== 'Completed' && st !== 'Partial') return { error: 'Order is not completed yet' };
        const rid = nextRefill++;
        refills.set(String(rid), Date.now());
        return rid;
      };
      if (p.order) {
        const r = one(String(p.order));
        return typeof r === 'number' ? { refill: String(r) } : r;
      }
      return ids(p.orders).map(id => ({ order: Number(id), refill: one(id) }));
    }

    case 'refill_status': {
      const one = id => {
        const at = refills.get(id);
        if (!at) return { error: 'Refill not found' };
        const age = (Date.now() - at) / 1000;
        return age < 20 ? 'Pending' : age < 60 ? 'In progress' : 'Completed';
      };
      if (p.refill) {
        const st = one(String(p.refill));
        return typeof st === 'string' ? { status: st } : st;
      }
      return ids(p.refills).map(id => ({ refill: Number(id), status: one(id) }));
    }

    case 'cancel':
      return ids(p.orders).map(id => {
        const o = orders.get(id);
        if (!o) return { order: Number(id), cancel: { error: 'Incorrect order ID' } };
        if (!o.service.cancel) return { order: Number(id), cancel: { error: 'Cancel is disabled for this service' } };
        const st = orderStatus(o).status;
        if (st === 'Completed' || st === 'Partial' || st === 'Canceled') {
          return { order: Number(id), cancel: { error: 'Order cannot be canceled' } };
        }
        o.canceled = true;
        balance += o.charge;
        return { order: Number(id), cancel: 1 };
      });

    default:
      return fail('Incorrect request');
  }
}

module.exports = { call };
