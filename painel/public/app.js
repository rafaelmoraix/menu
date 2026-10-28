'use strict';

const $ = sel => document.querySelector(sel);

const state = {
  services: [],
  serviceById: new Map(),
  orders: [],
  balance: null,
  currency: 'USD',
  selected: new Set(),
};

const STATUS = {
  'Pending': ['Pendente', 'badge'],
  'In progress': ['Em andamento', 'badge-info'],
  'Processing': ['Processando', 'badge-info'],
  'Completed': ['Concluído', 'badge-ok'],
  'Partial': ['Parcial', 'badge-warn'],
  'Canceled': ['Cancelado', 'badge-err'],
};
const FINAL = new Set(['Completed', 'Partial', 'Canceled']);
const REFILLABLE = new Set(['Completed', 'Partial']);

// ---------- utilidades ----------

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Erro HTTP ${res.status}`);
  return data;
}

function money(value, digits) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  const max = digits ?? (Math.abs(n) < 1 && n !== 0 ? 4 : 2);
  try {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency', currency: state.currency, minimumFractionDigits: 2, maximumFractionDigits: max,
    }).format(n);
  } catch {
    return `${n.toFixed(max)} ${state.currency}`;
  }
}

function int(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString('pt-BR') : '—';
}

function date(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function toast(message, isError = false) {
  const t = el('div', { class: `toast${isError ? ' err' : ''}` }, message);
  $('#toasts').append(t);
  setTimeout(() => t.remove(), isError ? 6000 : 3500);
}

function statusBadge(status) {
  if (!status) return el('span', { class: 'badge' }, '—');
  if (status.error) return el('span', { class: 'badge badge-err', title: status.error }, 'Erro');
  const [label, cls] = STATUS[status.status] || [status.status, 'badge'];
  return el('span', { class: `badge ${cls}` }, label);
}

function safeHref(link) {
  try {
    const u = new URL(link);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}

// ---------- abas ----------

function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.panel').forEach(p => (p.hidden = p.id !== `tab-${name}`));
  if (name === 'pedidos') loadOrders();
}

document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => showTab(t.dataset.tab)));

// ---------- saldo ----------

async function loadBalance() {
  try {
    const b = await api('/api/balance');
    state.balance = Number(b.balance);
    state.currency = b.currency || 'USD';
    $('#balance-value').textContent = money(b.balance, 2);
  } catch (err) {
    $('#balance-value').textContent = 'erro';
    toast(`Saldo: ${err.message}`, true);
  }
  updateCost();
}

$('#balance').addEventListener('click', loadBalance);

// ---------- serviços ----------

function categories() {
  return [...new Set(state.services.map(s => s.category || 'Sem categoria'))];
}

function fillCategorySelect(select, allLabel) {
  const current = select.value;
  select.replaceChildren(el('option', { value: '' }, allLabel), ...categories().map(c => el('option', { value: c }, c)));
  select.value = categories().includes(current) ? current : '';
}

async function loadServices(force = false) {
  try {
    state.services = await api(`/api/services${force ? '?refresh=1' : ''}`);
  } catch (err) {
    toast(`Serviços: ${err.message}`, true);
    return;
  }
  state.serviceById = new Map(state.services.map(s => [String(s.service), s]));
  fillCategorySelect($('#svc-category'), 'Todas as categorias');
  fillCategorySelect($('#svc-filter-cat'), 'Todas as categorias');
  renderServiceSelect();
  renderServicesTable();
}

function matches(s, term) {
  if (!term) return true;
  term = term.toLowerCase();
  return String(s.service) === term
    || String(s.name).toLowerCase().includes(term)
    || String(s.category || '').toLowerCase().includes(term);
}

function renderServicesTable() {
  const term = $('#svc-filter').value.trim();
  const cat = $('#svc-filter-cat').value;
  const list = state.services.filter(s => matches(s, term) && (!cat || (s.category || 'Sem categoria') === cat));
  const rows = [];
  let lastCat = null;
  for (const s of list) {
    const c = s.category || 'Sem categoria';
    if (c !== lastCat) {
      rows.push(el('tr', { class: 'cat-row' }, el('td', { colspan: 8 }, c)));
      lastCat = c;
    }
    rows.push(el('tr', {},
      el('td', { 'data-label': 'ID', class: 'num' }, s.service),
      el('td', { 'data-label': 'Serviço' }, s.name, s.type && s.type !== 'Default' ? el('span', { class: 'sub' }, s.type) : null),
      el('td', { 'data-label': 'Preço / 1000', class: 'num' }, money(s.rate)),
      el('td', { 'data-label': 'Mín.', class: 'num' }, int(s.min)),
      el('td', { 'data-label': 'Máx.', class: 'num' }, int(s.max)),
      el('td', { 'data-label': 'Refill' }, yesNo(s.refill)),
      el('td', { 'data-label': 'Cancelar' }, yesNo(s.cancel)),
      el('td', {}, el('div', { class: 'actions' },
        el('button', { class: 'btn btn-sm btn-primary', onclick: () => pickService(s.service) }, 'Pedir'))),
    ));
  }
  $('#services-table tbody').replaceChildren(...rows);
  $('#services-empty').hidden = list.length > 0;
}

function yesNo(v) {
  return v ? el('span', { class: 'badge badge-ok' }, 'Sim') : el('span', { class: 'badge' }, 'Não');
}

$('#svc-filter').addEventListener('input', renderServicesTable);
$('#svc-filter-cat').addEventListener('change', renderServicesTable);
$('#refresh-services').addEventListener('click', () => loadServices(true));

// ---------- novo pedido ----------

const form = $('#order-form');

function currentService() {
  return state.serviceById.get(String($('#svc-select').value));
}

function renderServiceSelect() {
  const term = $('#svc-search').value.trim();
  const cat = $('#svc-category').value;
  const select = $('#svc-select');
  const current = select.value;
  const list = state.services.filter(s => matches(s, term) && (!cat || (s.category || 'Sem categoria') === cat));

  const groups = new Map();
  for (const s of list) {
    const c = s.category || 'Sem categoria';
    if (!groups.has(c)) groups.set(c, []);
    groups.get(c).push(s);
  }
  const options = [];
  for (const [c, items] of groups) {
    options.push(el('optgroup', { label: c },
      items.map(s => el('option', { value: s.service }, `${s.service} — ${s.name} — ${money(s.rate)}/1000`))));
  }
  select.replaceChildren(...(options.length ? options : [el('option', { value: '' }, 'Nenhum serviço encontrado')]));
  if (list.some(s => String(s.service) === current)) select.value = current;
  onServiceChange();
}

function onServiceChange() {
  const s = currentService();
  const info = $('#svc-info');
  if (!s) {
    info.hidden = true;
    updateCost();
    return;
  }
  const type = s.type || 'Default';
  info.hidden = false;
  info.replaceChildren(
    el('div', {}, el('span', {}, 'Preço / 1000'), el('strong', {}, money(s.rate))),
    el('div', {}, el('span', {}, 'Mínimo'), el('strong', {}, int(s.min))),
    el('div', {}, el('span', {}, 'Máximo'), el('strong', {}, int(s.max))),
    el('div', {}, el('span', {}, 'Refill'), yesNo(s.refill)),
    el('div', {}, el('span', {}, 'Cancelamento'), yesNo(s.cancel)),
    el('div', {}, el('span', {}, 'Tipo'), el('strong', {}, type)),
  );

  const qty = form.elements.quantity;
  const isComments = type === 'Custom Comments';
  const isPackage = type === 'Package';
  $('#qty-field').hidden = isComments || isPackage;
  $('#comments-field').hidden = !isComments;
  $('#drip').hidden = isPackage;
  qty.required = !isComments && !isPackage;
  qty.min = s.min;
  qty.max = s.max;
  $('#qty-hint').textContent = `Entre ${int(s.min)} e ${int(s.max)}`;
  updateCost();
}

function orderQuantity(s) {
  const type = s.type || 'Default';
  if (type === 'Package') return 1;
  if (type === 'Custom Comments') {
    return form.elements.comments.value.split('\n').filter(l => l.trim()).length;
  }
  return Number(form.elements.quantity.value) || 0;
}

function updateCost() {
  const s = currentService();
  const warn = $('#cost-warn');
  warn.hidden = true;
  if (!s) {
    $('#cost').textContent = '—';
    return;
  }
  const type = s.type || 'Default';
  const qty = orderQuantity(s);
  const runs = $('#drip').open && type !== 'Package' ? Number(form.elements.runs.value) || 1 : 1;
  const cost = type === 'Package' ? Number(s.rate) : (Number(s.rate) * qty * runs) / 1000;
  $('#cost').textContent = qty ? money(cost) : '—';

  if (type === 'Custom Comments') {
    $('#comments-hint').textContent = `${qty} comentário(s) — entre ${int(s.min)} e ${int(s.max)}`;
  }

  const problems = [];
  if (type !== 'Package' && qty && (qty < Number(s.min) || qty > Number(s.max))) {
    problems.push(`Quantidade fora do limite (${int(s.min)}–${int(s.max)}).`);
  }
  if (state.balance !== null && qty && cost > state.balance) {
    problems.push(`Saldo insuficiente (${money(state.balance, 2)}).`);
  }
  if (problems.length) {
    warn.textContent = problems.join(' ');
    warn.hidden = false;
  }
}

function pickService(id) {
  $('#svc-search').value = '';
  $('#svc-category').value = '';
  renderServiceSelect();
  $('#svc-select').value = String(id);
  onServiceChange();
  showTab('novo');
  form.elements.link.focus();
}

$('#svc-search').addEventListener('input', renderServiceSelect);
$('#svc-category').addEventListener('change', renderServiceSelect);
$('#svc-select').addEventListener('change', onServiceChange);
form.addEventListener('input', updateCost);
$('#drip').addEventListener('toggle', updateCost);

form.addEventListener('submit', async e => {
  e.preventDefault();
  const s = currentService();
  if (!s) return toast('Escolha um serviço', true);

  const body = { service: s.service, link: form.elements.link.value.trim() };
  if (s.type === 'Custom Comments') body.comments = form.elements.comments.value;
  else if (s.type !== 'Package') body.quantity = Number(form.elements.quantity.value);
  if ($('#drip').open && (form.elements.runs.value || form.elements.interval.value)) {
    body.runs = Number(form.elements.runs.value);
    body.interval = Number(form.elements.interval.value);
  }

  const btn = $('#submit-btn');
  btn.disabled = true;
  btn.textContent = 'Enviando…';
  try {
    const order = await api('/api/orders', { method: 'POST', body });
    toast(`Pedido #${order.id} criado!`);
    form.elements.link.value = '';
    form.elements.quantity.value = '';
    form.elements.comments.value = '';
    updateCost();
    loadBalance();
    showTab('pedidos');
  } catch (err) {
    toast(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Fazer pedido';
  }
});

// ---------- pedidos ----------

function canRefill(o) {
  const s = state.serviceById.get(String(o.service));
  return (!s || s.refill) && o.status && REFILLABLE.has(o.status.status);
}

function canCancel(o) {
  const s = state.serviceById.get(String(o.service));
  return (!s || s.cancel) && o.status && !o.status.error && !FINAL.has(o.status.status);
}

async function loadOrders() {
  $('#refresh-orders').disabled = true;
  try {
    const data = await api('/api/orders');
    state.orders = data.orders;
    if (data.warning) toast(`Status não atualizado: ${data.warning}`, true);
  } catch (err) {
    toast(err.message, true);
  } finally {
    $('#refresh-orders').disabled = false;
  }
  const ids = new Set(state.orders.map(o => String(o.id)));
  for (const id of state.selected) if (!ids.has(id)) state.selected.delete(id);
  renderOrders();
}

function renderOrders() {
  const filter = $('#status-filter').value;
  const list = state.orders.filter(o => !filter || (o.status && o.status.status === filter));

  const rows = list.map(o => {
    const id = String(o.id);
    const st = o.status || {};
    const href = o.link && safeHref(o.link);
    const lastRefill = o.refills && o.refills.length ? o.refills[o.refills.length - 1] : null;
    const qty = o.quantity ? (o.runs ? `${int(o.quantity)} × ${o.runs}` : int(o.quantity)) : '—';

    return el('tr', {},
      el('td', { class: 'check' }, el('input', {
        type: 'checkbox',
        checked: state.selected.has(id),
        'aria-label': `Selecionar pedido ${id}`,
        onchange: e => { e.target.checked ? state.selected.add(id) : state.selected.delete(id); updateBulk(); },
      })),
      el('td', { 'data-label': 'ID', class: 'num' }, `#${id}`),
      el('td', { 'data-label': 'Serviço' }, o.serviceName || '—',
        lastRefill ? el('span', { class: 'sub' }, `Refill #${lastRefill.id}: ${lastRefill.status || '—'}`) : null),
      el('td', { 'data-label': 'Link', class: 'link' },
        href ? el('a', { href, target: '_blank', rel: 'noopener noreferrer', title: o.link }, o.link) : (o.link || '—')),
      el('td', { 'data-label': 'Qtd.', class: 'num' }, qty),
      el('td', { 'data-label': 'Status' }, statusBadge(o.status)),
      el('td', { 'data-label': 'Início', class: 'num' }, st.start_count !== undefined ? int(st.start_count) : '—'),
      el('td', { 'data-label': 'Restante', class: 'num' }, st.remains !== undefined ? int(st.remains) : '—'),
      el('td', { 'data-label': 'Custo', class: 'num' }, st.charge !== undefined ? money(st.charge) : (o.estimate != null ? `~${money(o.estimate)}` : '—')),
      el('td', { 'data-label': 'Data', class: 'num' }, date(o.createdAt)),
      el('td', {}, el('div', { class: 'actions' },
        canRefill(o) ? el('button', { class: 'btn btn-sm', onclick: () => refill([id]) }, 'Refill') : null,
        canCancel(o) ? el('button', { class: 'btn btn-sm btn-danger', onclick: () => cancel([id]) }, 'Cancelar') : null,
        el('button', { class: 'btn btn-sm', title: 'Remover da lista (não cancela o pedido)', onclick: () => removeOrder(id) }, '✕'),
      )),
    );
  });

  $('#orders-table tbody').replaceChildren(...rows);
  $('#orders-empty').hidden = list.length > 0;
  $('#orders-empty').textContent = state.orders.length ? 'Nenhum pedido com esse status.' : 'Nenhum pedido ainda.';
  $('#check-all').checked = list.length > 0 && list.every(o => state.selected.has(String(o.id)));
  updateBulk();
}

function updateBulk() {
  const n = state.selected.size;
  $('#bulk-bar').hidden = n === 0;
  $('#bulk-count').textContent = `${n} selecionado(s)`;
}

function reportResults(results, verb) {
  const ok = results.filter(r => r.ok);
  const bad = results.filter(r => !r.ok);
  if (ok.length) toast(`${verb}: ${ok.map(r => `#${r.order}`).join(', ')}`);
  for (const r of bad) toast(`#${r.order}: ${r.error || 'falhou'}`, true);
}

async function refill(ids) {
  try {
    reportResults(await api('/api/orders/refill', { method: 'POST', body: { orders: ids } }), 'Refill solicitado');
  } catch (err) {
    toast(err.message, true);
  }
  loadOrders();
}

async function cancel(ids) {
  if (!confirm(`Cancelar ${ids.length === 1 ? `o pedido #${ids[0]}` : `${ids.length} pedidos`}?`)) return;
  try {
    reportResults(await api('/api/orders/cancel', { method: 'POST', body: { orders: ids } }), 'Cancelamento solicitado');
  } catch (err) {
    toast(err.message, true);
  }
  loadOrders();
  loadBalance();
}

async function removeOrder(id) {
  if (!confirm(`Remover o pedido #${id} da lista? Ele não será cancelado.`)) return;
  try {
    await api(`/api/orders/${encodeURIComponent(id)}`, { method: 'DELETE' });
    state.orders = state.orders.filter(o => String(o.id) !== id);
    state.selected.delete(id);
    renderOrders();
  } catch (err) {
    toast(err.message, true);
  }
}

$('#status-filter').addEventListener('change', renderOrders);
$('#refresh-orders').addEventListener('click', loadOrders);
$('#check-all').addEventListener('change', e => {
  const filter = $('#status-filter').value;
  for (const o of state.orders) {
    if (filter && !(o.status && o.status.status === filter)) continue;
    e.target.checked ? state.selected.add(String(o.id)) : state.selected.delete(String(o.id));
  }
  renderOrders();
});
$('#bulk-refill').addEventListener('click', () => refill([...state.selected].slice(0, 100)));
$('#bulk-cancel').addEventListener('click', () => cancel([...state.selected].slice(0, 100)));

$('#import-btn').addEventListener('click', () => {
  $('#import-ids').value = '';
  $('#import-dialog').showModal();
});
$('#import-dialog').addEventListener('close', async () => {
  if ($('#import-dialog').returnValue !== 'ok') return;
  const ids = $('#import-ids').value;
  if (!ids.trim()) return;
  try {
    const r = await api('/api/orders/import', { method: 'POST', body: { orders: ids } });
    toast(`${r.added} pedido(s) importado(s)`);
    loadOrders();
  } catch (err) {
    toast(err.message, true);
  }
});

// Atualiza status sozinho enquanto a aba de pedidos estiver aberta.
setInterval(() => {
  if (!$('#tab-pedidos').hidden && !document.hidden) loadOrders();
}, 60000);

// ---------- início ----------

(async function init() {
  api('/api/config').then(c => { $('#mock-badge').hidden = !c.mock; }).catch(() => {});
  await loadBalance();
  await loadServices();
})();
