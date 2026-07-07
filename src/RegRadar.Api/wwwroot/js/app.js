const state = {
  events: [], documents: [], clients: [], notifications: [], sources: [],
  impacts: {},
  loaded: false,
  changesFilter: { search: '', impact: '', regulator: '', tag: '', status: '', deadline: '', industry: '', notified: '' },
  changesSort: 'impact_desc',
  filtersVisible: true,
  clientsSearch: '',
  notificationsSearch: '',
  chatMode: 'lawyer',
  chatDocId: '',
  chatDocSearch: '',
  chatHistory: [],
  chatLoading: false,
  composeResult: {},
};

const IMPACT_LABEL = { Low: 'Низкий', Medium: 'Средний', High: 'Высокий' };
const IMPACT_LABEL_NEUTER = { Low: 'Низкое', Medium: 'Среднее', High: 'Высокое' };
const IMPACT_BADGE = { Low: 'badge-info', Medium: 'badge-warning', High: 'badge-danger' };
const IMPACT_DOT = { Low: 'var(--info-text)', Medium: 'var(--warning-text)', High: 'var(--danger-text)' };

const STATUS_LABEL = { New: 'Новое', Updated: 'Обновлено', Aborted: 'Приостановлено', Rejected: 'Отклонено', InForce: 'Действует' };
const STATUS_BADGE = { New: 'badge-info', Updated: 'badge-warning', Aborted: 'badge-warning', Rejected: 'badge-danger', InForce: 'badge-positive' };

const NOTIF_STATUS_LABEL = { Pending: 'В очереди', Sent: 'Отправлено', Failed: 'Ошибка', Mocked: 'Тест (mock)' };
const NOTIF_STATUS_BADGE = { Pending: 'badge-warning', Sent: 'badge-positive', Failed: 'badge-danger', Mocked: 'badge-info' };

const SIZE_LABEL = { Micro: 'Микро', Small: 'Малый', Medium: 'Средний', Large: 'Крупный' };
const CASH_LABEL = { Low: 'Низкий', Medium: 'Средний', High: 'Высокий' };
const SOURCE_TYPE_LABEL = { BankOfRussia: 'Банк России', RegulationGov: 'regulation.gov.ru', PravoGov: 'pravo.gov.ru', UserUpload: 'Загрузка пользователем', Seed: 'Демо-данные' };

const MONTHS = ['ЯНВ', 'ФЕВ', 'МАР', 'АПР', 'МАЙ', 'ИЮН', 'ИЮЛ', 'АВГ', 'СЕН', 'ОКТ', 'НОЯ', 'ДЕК'];

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function jsArg(s) {
  return String(s ?? '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r?\n/g, ' ');
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU');
}

function fmtDateTime(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function dateParts(d) {
  const dt = new Date(d + 'T00:00:00');
  return { day: String(dt.getDate()).padStart(2, '0'), month: MONTHS[dt.getMonth()] };
}

function daysUntil(d) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const target = new Date(d + 'T00:00:00');
  return Math.round((target - today) / 86400000);
}

function initials(name) {
  const cleaned = String(name ?? '').replace(/[«»"]/g, '').replace(/^(ООО|ИП|АО|ЗАО|ПАО)\s+/i, '');
  const words = cleaned.split(/\s+/).filter(Boolean);
  return ((words[0]?.[0] ?? '') + (words[1]?.[0] ?? '')).toUpperCase() || '—';
}

function icon(name, size = 16) {
  return `<img class="icon" src="assets/icons/${name}.svg" width="${size}" height="${size}" alt="">`;
}

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  document.getElementById('toast-stack').appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { }
  return { ok: res.ok, status: res.status, data };
}

async function loadAll() {
  const [ev, docs, clients, notifs, sources] = await Promise.all([
    api('/api/RegulatoryEvents'), api('/api/Documents'),
    api('/api/ClientProfiles'), api('/api/Notifications'), api('/api/Sources'),
  ]);
  state.events = ev.data ?? [];
  state.documents = docs.data ?? [];
  state.clients = clients.data ?? [];
  state.notifications = notifs.data ?? [];
  state.sources = sources.data ?? [];
  const impactResults = await Promise.all(
    state.events.map(e => api(`/api/RegulatoryEvents/${e.id}/impacts`))
  );
  state.impacts = {};
  state.events.forEach((e, i) => state.impacts[e.id] = impactResults[i].data ?? []);
  state.loaded = true;
}

function docFor(event) {
  return state.documents.find(d => d.id === event.documentId);
}

function clientFor(id) {
  return state.clients.find(c => c.id === id);
}

function eventMetaLine(event) {
  const doc = docFor(event);
  const bits = [];
  if (doc?.regulator) bits.push(esc(doc.regulator));
  if (doc?.title) bits.push(esc(doc.title));
  bits.push(event.effectiveDate ? `вступает ${fmtDate(event.effectiveDate)}` : fmtDate(event.createdAt));
  return bits.join(' · ');
}

/* ---------- shell chrome ---------- */

function fieldBox(id, placeholder, value) {
  return `<div class="field-box">${icon('icon-search')}<input id="${id}" placeholder="${esc(placeholder)}" value="${esc(value ?? '')}"></div>`;
}

function btnOutline(label, onclick, iconName) {
  return `<button class="btn btn-outline" onclick="${onclick}">${iconName ? icon(iconName) : ''}${esc(label)}</button>`;
}

function btnPrimary(label, onclick, iconName) {
  return `<button class="btn btn-primary" onclick="${onclick}">${iconName ? icon(iconName) : ''}${esc(label)}</button>`;
}

function btnTopbar(label, onclick, iconName, kind = 'outline') {
  return `<button class="btn btn-${kind} topbar-btn" onclick="${onclick}">${iconName ? icon(iconName) : ''}${esc(label)}</button>`;
}

function renderTopbar(title, subtitle, actionsHtml) {
  document.getElementById('topbar').innerHTML = `
    <div class="page-heading"><h1>${esc(title)}</h1><p>${subtitle}</p></div>
    <div class="topbar-actions">${actionsHtml}</div>`;
}

function genericActions(searchId, placeholder) {
  return fieldBox(searchId, placeholder, '') +
    btnOutline('Обновить источники', 'runIngestion()', 'icon-refresh') +
    btnPrimary('Загрузить документ', 'triggerUpload()', 'icon-upload');
}

function bindGlobalSearch(searchId) {
  document.getElementById(searchId)?.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    state.changesFilter.search = e.target.value;
    location.hash = '#/changes';
    route();
  });
}

function setActiveNav(route) {
  document.querySelectorAll('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.route === route);
  });
}

/* ---------- router ---------- */

function currentRoute() {
  const hash = (location.hash || '#/overview').slice(2);
  return hash.split('/').filter(Boolean);
}

function route() {
  if (!state.loaded) return;
  const [top, ...rest] = currentRoute();
  const routeName = top || 'overview';
  setActiveNav(routeName);
  const page = document.getElementById('page');
  document.body.dataset.route = routeName;
  document.body.dataset.view = rest[0] ? `${routeName}-detail` : `${routeName}-list`;
  page.className = `page page-${routeName}`;
  switch (top) {
    case 'changes':
      if (rest[0]) { renderChangeDetail(rest[0]); } else { renderChangesList(); }
      break;
    case 'chat':
      if (rest[0]) state.chatDocId = rest[0];
      renderChat();
      break;
    case 'clients':
      if (rest[0]) { renderClientProfile(rest[0]); } else { renderClientsList(); }
      break;
    case 'notifications':
      if (rest[0] === 'compose') document.body.dataset.view = 'notifications-compose';
      if (rest[0] === 'compose') { renderComposeNotification(rest[1], rest[2]); } else { renderNotificationsList(); }
      break;
    case 'sources': renderSources(); break;
    case 'settings': renderSettings(); break;
    default: renderOverview();
  }
}

window.addEventListener('hashchange', route);

/* ---------- Overview ---------- */

function renderOverview() {
  renderTopbar('Регуляторная повестка', 'Риски, клиенты и уведомления · обновлено при последней загрузке', genericActions('q-overview', 'Поиск изменений и клиентов…'));

  const DAY = 86400000;
  const now = Date.now();
  const newEvents = state.events.filter(e => e.status === 'New');
  const newLast7 = state.events.filter(e => now - new Date(e.createdAt).getTime() <= 7 * DAY);
  const highEvents = state.events.filter(e => e.impactLevel === 'High');
  const highLast7 = highEvents.filter(e => now - new Date(e.createdAt).getTime() <= 7 * DAY);
  const allImpacts = state.events.flatMap(e => state.impacts[e.id] ?? []);
  const distinctClients = new Set(allImpacts.map(i => i.clientProfileId));
  const upcoming = state.events.filter(e => e.effectiveDate && daysUntil(e.effectiveDate) >= 0)
    .sort((a, b) => daysUntil(a.effectiveDate) - daysUntil(b.effectiveDate));
  const upcoming30 = upcoming.filter(e => daysUntil(e.effectiveDate) <= 30);
  const upcoming7 = upcoming30.filter(e => daysUntil(e.effectiveDate) <= 7);

  const kpis = `
    <div class="kpi-row">
      <div class="card kpi-card">
        <div class="kpi-top"><span class="kpi-label">Новые изменения</span><span class="kpi-tick"></span></div>
        <span class="kpi-value">${newEvents.length}</span>
        <div class="kpi-foot"><span class="kpi-delta">+${newLast7.length}</span><span class="kpi-foot-note">за 7 дней</span></div>
      </div>
      <div class="card kpi-card dark">
        <div class="kpi-top"><span class="kpi-label">Высокий риск</span><span class="kpi-tick"></span></div>
        <span class="kpi-value">${highEvents.length}</span>
        <div class="kpi-foot"><span class="kpi-delta danger">+${highLast7.length}</span><span class="kpi-foot-note">требуют решения</span></div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-top"><span class="kpi-label">Затронутые клиенты</span><span class="kpi-tick"></span></div>
        <span class="kpi-value">${distinctClients.size}</span>
        <div class="kpi-foot"><span class="kpi-delta">${allImpacts.length}</span><span class="kpi-foot-note">совпадений всего</span></div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-top"><span class="kpi-label">Ближайшие дедлайны</span><span class="kpi-tick"></span></div>
        <span class="kpi-value">${upcoming30.length}</span>
        <div class="kpi-foot"><span class="kpi-delta">${upcoming7.length} срочных</span><span class="kpi-foot-note">до 30 дней</span></div>
      </div>
    </div>`;

  const weight = { High: 3, Medium: 2, Low: 1 };
  const topEvents = [...state.events]
    .sort((a, b) => weight[b.impactLevel] - weight[a.impactLevel] || new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, 3);

  const criticalRows = topEvents.map(e => `
    <div class="event-row" onclick="location.hash='#/changes/${e.id}'">
      <div class="event-content">
        <span class="event-title">${esc(e.title)}</span>
        <span class="event-meta">${eventMetaLine(e)}</span>
      </div>
      <div class="event-impact-clients">
        <span class="badge ${IMPACT_BADGE[e.impactLevel]}">${IMPACT_LABEL[e.impactLevel]}</span>
        <span class="muted-count">${(state.impacts[e.id] ?? []).length} клиентов</span>
      </div>
    </div>`).join('');

  const criticalCard = `
    <div class="card card-pad">
      <div class="card-header">
        <div><div class="card-title">Критические изменения</div><div class="card-subtitle">Новые события с максимальным влиянием</div></div>
      </div>
      <div class="event-list">${criticalRows || '<div class="empty-state">Событий пока нет — обновите источники</div>'}</div>
      <div class="list-footer">
        <span>Показано ${topEvents.length} из ${state.events.length} изменений</span>
        <a href="#/changes">Открыть список →</a>
      </div>
    </div>`;

  const riskCounts = { High: 0, Medium: 0, Low: 0 };
  state.events.forEach(e => riskCounts[e.impactLevel]++);
  const total = state.events.length || 1;
  const highDeg = riskCounts.High / total * 360;
  const medDeg = highDeg + riskCounts.Medium / total * 360;
  const donutStyle = `background: conic-gradient(var(--danger-text) 0deg ${highDeg}deg, var(--warning-text) ${highDeg}deg ${medDeg}deg, var(--info-text) ${medDeg}deg 360deg);`;

  const regulatorCounts = {};
  state.events.forEach(e => {
    const reg = docFor(e)?.regulator || 'Другие';
    regulatorCounts[reg] = (regulatorCounts[reg] ?? 0) + 1;
  });
  const regEntries = Object.entries(regulatorCounts).sort((a, b) => b[1] - a[1]);
  const topRegs = regEntries.slice(0, 2);
  const otherRegCount = regEntries.slice(2).reduce((s, [, n]) => s + n, 0);

  const riskCard = `
    <div class="card card-pad">
      <div class="card-header"><div class="card-title">Обзор рисков</div></div>
      <div class="donut-wrap">
        <div class="donut" style="${donutStyle}">
          <div class="donut-hole"><span class="donut-value">${state.events.length}</span><span class="donut-caption">изменений</span></div>
        </div>
        <div class="legend">
          <div class="legend-item"><span class="legend-label"><span class="legend-dot" style="background:var(--danger-text)"></span>Высокий</span><span class="legend-value">${riskCounts.High}</span></div>
          <div class="legend-item"><span class="legend-label"><span class="legend-dot" style="background:var(--warning-text)"></span>Средний</span><span class="legend-value">${riskCounts.Medium}</span></div>
          <div class="legend-item"><span class="legend-label"><span class="legend-dot" style="background:var(--info-text)"></span>Низкий</span><span class="legend-value">${riskCounts.Low}</span></div>
        </div>
      </div>
      <hr class="divider">
      <div class="source-tally">
        ${topRegs.map(([name, n]) => `<div class="col"><span>${esc(name)}</span><span>${n}</span></div>`).join('')}
        ${otherRegCount ? `<div class="col"><span>Другие</span><span>${otherRegCount}</span></div>` : ''}
      </div>
    </div>`;

  const deadlineRows = upcoming30.slice(0, 3).map(e => {
    const dp = dateParts(e.effectiveDate);
    const d = daysUntil(e.effectiveDate);
    const cls = d <= 3 ? 'badge-danger' : d <= 14 ? 'badge-warning' : 'badge-info';
    return `<div class="deadline-row">
      <div class="deadline-main">
        <div class="deadline-date"><span class="day">${dp.day}</span><span class="month">${dp.month}</span></div>
        <div class="deadline-info"><div class="name">${esc(e.title.slice(0, 40))}${e.title.length > 40 ? '…' : ''}</div><div class="regulator">${esc(docFor(e)?.regulator ?? '—')}</div></div>
      </div>
      <span class="badge ${cls}">${d === 0 ? 'сегодня' : d + ' ' + pluralDays(d)}</span>
    </div>`;
  }).join('');

  const deadlinesCard = `
    <div class="card card-pad-sm deadlines-card">
      <div class="card-header"><div><div class="card-title">Ближайшие дедлайны</div><div class="card-subtitle">Сроки исполнения требований</div></div></div>
      <div class="deadline-list">${deadlineRows || '<div class="deadline-empty"><span class="badge badge-positive">Нет срочных сроков</span><strong>Дедлайнов не найдено</strong><small>Новые сроки появятся здесь после обработки документов</small></div>'}</div>
      <span class="card-subtitle">${upcoming30.length} дедлайнов · ${upcoming7.length} требуют внимания</span>
    </div>`;

  const recentNotifs = state.notifications.slice(0, 5);
  const notifRows = recentNotifs.map(n => {
    const ev = state.events.find(e => e.id === n.regulatoryEventId);
    const cl = clientFor(n.clientProfileId);
    return `<tr>
      <td><div class="client-cell"><div class="client-avatar">${initials(cl?.companyName)}</div><div><div class="client-name">${esc(cl?.companyName ?? '—')}</div><div class="client-sub">${esc(cl?.industry ?? '')}</div></div></div></td>
      <td><span class="badge ${NOTIF_STATUS_BADGE[n.status]}">${NOTIF_STATUS_LABEL[n.status]}</span></td>
      <td>${esc(ev ? ev.title.slice(0, 24) + (ev.title.length > 24 ? '…' : '') : '—')}</td>
      <td>${esc(n.channel)}</td>
    </tr>`;
  }).join('');

  const notifCard = `
    <div class="card card-pad-sm recent-notifs-card">
      <div class="card-header"><div><div class="card-title">Последние уведомления</div><div class="card-subtitle">Готовые и отправленные сообщения</div></div>
        <a href="#/notifications" class="btn btn-outline small">Все уведомления</a></div>
      <div class="table-card">
        <table class="data-table">
          <thead><tr><th>Клиент</th><th>Статус</th><th>Изменение</th><th>Канал</th></tr></thead>
          <tbody>${notifRows || '<tr><td colspan="4" class="empty-state overview-notifs-empty">Уведомлений ещё нет</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;

  document.getElementById('page').innerHTML = kpis +
    `<div class="analytics-row">${criticalCard}${riskCard}</div>` +
    `<div class="lower-row">${deadlinesCard}${notifCard}</div>`;

  bindGlobalSearch('q-overview');
}

function pluralDays(n) {
  const abs = Math.abs(n);
  const mod10 = abs % 10, mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return 'день';
  if ([2, 3, 4].includes(mod10) && ![12, 13, 14].includes(mod100)) return 'дня';
  return 'дней';
}

/* ---------- Changes list ---------- */

function toggleFilters() {
  state.filtersVisible = !state.filtersVisible;
  route();
}

function applyChangesFilters(events) {
  const f = state.changesFilter;
  return events.filter(e => {
    if (f.search) {
      const q = f.search.toLowerCase();
      const doc = docFor(e);
      if (!(e.title.toLowerCase().includes(q) || e.summary.toLowerCase().includes(q) || (doc?.regulator ?? '').toLowerCase().includes(q))) return false;
    }
    if (f.impact && e.impactLevel !== f.impact) return false;
    if (f.status && e.status !== f.status) return false;
    if (f.regulator && (docFor(e)?.regulator ?? '') !== f.regulator) return false;
    if (f.tag && !e.tags.includes(f.tag)) return false;
    if (f.deadline) {
      if (!e.effectiveDate) return false;
      const d = daysUntil(e.effectiveDate);
      if (d < 0 || d > Number(f.deadline)) return false;
    }
    if (f.industry) {
      const industries = new Set((state.impacts[e.id] ?? []).map(i => clientFor(i.clientProfileId)?.industry).filter(Boolean));
      if (!industries.has(f.industry)) return false;
    }
    if (f.notified) {
      const has = state.notifications.some(n => n.regulatoryEventId === e.id);
      if (f.notified === 'yes' && !has) return false;
      if (f.notified === 'no' && has) return false;
    }
    return true;
  });
}

function updateChangesFilter(key, value) {
  state.changesFilter[key] = value;
  route();
}

function updateChangesSort(value) {
  state.changesSort = value || 'impact_desc';
  route();
}

function compareChanges(a, b) {
  const weight = { High: 3, Medium: 2, Low: 1 };
  const impact = (weight[b.impactLevel] ?? 0) - (weight[a.impactLevel] ?? 0);
  const createdDesc = new Date(b.createdAt) - new Date(a.createdAt);
  switch (state.changesSort) {
    case 'date_desc':
      return createdDesc;
    case 'date_asc':
      return new Date(a.createdAt) - new Date(b.createdAt);
    case 'deadline_asc': {
      const da = a.effectiveDate ? daysUntil(a.effectiveDate) : Number.POSITIVE_INFINITY;
      const db = b.effectiveDate ? daysUntil(b.effectiveDate) : Number.POSITIVE_INFINITY;
      return da - db || impact || createdDesc;
    }
    case 'clients_desc':
      return (state.impacts[b.id] ?? []).length - (state.impacts[a.id] ?? []).length || impact || createdDesc;
    case 'title_asc':
      return a.title.localeCompare(b.title, 'ru') || impact || createdDesc;
    case 'impact_desc':
    default:
      return impact || createdDesc;
  }
}

function renderChangesList() {
  renderTopbar('Регуляторные изменения', 'Рабочий список событий, рисков и статусов обработки',
    fieldBox('q-changes', 'Поиск по названию или источнику…', state.changesFilter.search) +
    btnOutline('Фильтры', 'toggleFilters()') +
    btnPrimary('Загрузить документ', 'triggerUpload()', 'icon-upload'));

  document.getElementById('q-changes')?.addEventListener('input', e => updateChangesFilter('search', e.target.value));

  const regulators = [...new Set(state.documents.map(d => d.regulator).filter(Boolean))];
  const tags = [...new Set(state.events.flatMap(e => e.tags))];
  const industries = [...new Set(state.clients.map(c => c.industry).filter(Boolean))];

  const select = (key, label, options) => `
    <div class="filter-select">
      <select onchange="updateChangesFilter('${key}', this.value)">
        <option value="">${esc(label)}</option>
        ${options.map(([v, l]) => `<option value="${esc(v)}" ${state.changesFilter[key] === v ? 'selected' : ''}>${esc(l)}</option>`).join('')}
      </select>
    </div>`;

  const filterBar = state.filtersVisible ? `
    <div class="card filter-bar">
      ${select('impact', 'Влияние', Object.entries(IMPACT_LABEL))}
      ${select('regulator', 'Регулятор', regulators.map(r => [r, r]))}
      ${select('tag', 'Тема', tags.map(t => [t, t]))}
      ${select('status', 'Статус', Object.entries(STATUS_LABEL))}
      ${select('deadline', 'Дата', [['7', 'до 7 дней'], ['30', 'до 30 дней'], ['90', 'до 90 дней']])}
      ${select('industry', 'Отрасли', industries.map(i => [i, i]))}
      ${select('notified', 'Уведомления', [['yes', 'есть уведомление'], ['no', 'нет уведомления']])}
    </div>` : '';

  const filtered = applyChangesFilters(state.events)
    .sort(compareChanges);

  const rows = filtered.map(e => {
    const impacts = state.impacts[e.id] ?? [];
    return `<div class="change-row" onclick="location.hash='#/changes/${e.id}'">
      <div class="change-main">
        <span class="change-title">${esc(e.title)}</span>
        <span class="change-meta">${eventMetaLine(e)}</span>
        <span class="change-tags">${e.tags.map(esc).join('  ·  ')}</span>
      </div>
      <div class="change-side">
        <span class="badge ${IMPACT_BADGE[e.impactLevel]}">${impactBadgeLabel(e)}</span>
        <span class="muted-count">${impacts.length} ${impacts.length === 1 ? 'клиент' : 'клиентов'}</span>
        ${eventProcessBadge(e)}
      </div>
    </div>`;
  }).join('');

  const listCard = `
    <div class="card card-pad">
      <div class="list-summary">
        <span class="count">${filtered.length} изменений</span>
        <div class="sort-control">
          <span>Сортировка</span>
          <div class="filter-select sort-select">
            <select onchange="updateChangesSort(this.value)" aria-label="Сортировка изменений">
              ${[
                ['impact_desc', 'по влиянию ↓'],
                ['date_desc', 'сначала новые'],
                ['date_asc', 'сначала старые'],
                ['deadline_asc', 'по дедлайну'],
                ['clients_desc', 'по клиентам ↓'],
                ['title_asc', 'по названию'],
              ].map(([v, l]) => `<option value="${v}" ${state.changesSort === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>
          </div>
        </div>
      </div>
      <div class="event-list">${rows || '<div class="empty-state">Нет изменений по заданным фильтрам</div>'}</div>
    </div>`;

  document.getElementById('page').innerHTML = `<div class="changes-body">${filterBar}${listCard}</div>`;
}

function impactBadgeLabel(e) {
  const score = e.impactScore;
  let label = IMPACT_LABEL[e.impactLevel] ?? e.impactLevel ?? 'Оценка';
  if (e.impactLevel === 'High' && score != null && score >= 85) label = 'Критический';
  return label + (score != null ? ' · ' + score : '');
}

function impactSummaryLabel(e) {
  const score = e.impactScore;
  let label = IMPACT_LABEL_NEUTER[e.impactLevel] ?? IMPACT_LABEL[e.impactLevel] ?? e.impactLevel ?? 'Оценка';
  if (e.impactLevel === 'High' && score != null && score >= 85) label = 'Критическое';
  return `${label} влияние${score != null ? ' · ' + score : ''}`;
}

function eventProcessBadge(e) {
  const hasNotification = state.notifications.some(n => n.regulatoryEventId === e.id);
  if (hasNotification) return '<span class="badge badge-positive">Есть уведомления</span>';
  if (e.reviewRequired) return '<span class="badge badge-warning">На проверке</span>';
  if (e.impactScore == null && !e.impactExplanation) return '<span class="badge badge-info">Обработка</span>';
  if (e.status === 'New') return '<span class="badge badge-info">Готово к разбору</span>';
  return '<span class="badge badge-positive">Обработано</span>';
}

/* ---------- Change detail ---------- */

function levelVars(level) {
  const key = level === 'High' ? 'danger' : level === 'Medium' ? 'warning' : 'info';
  return { bg: `var(--${key}-bg)`, text: `var(--${key}-text)` };
}

function bulletHtml(items) {
  return items.map(i => `<li>• ${esc(i)}</li>`).join('');
}

function renderChangeDetail(id) {
  const e = state.events.find(x => x.id === id);
  if (!e) { document.getElementById('page').innerHTML = '<div class="empty-state">Изменение не найдено</div>'; return; }
  const doc = docFor(e);
  const ai = e.aiDetails ?? {};
  const impacts = state.impacts[e.id] ?? [];
  const drafts = ai.notificationDrafts ?? [];
  const relevances = ai.clientRelevances ?? [];
  const colors = levelVars(e.impactLevel);
  const firstClientId = impacts[0]?.clientProfileId;

  renderTopbar('Карточка изменения', `${doc?.regulator ?? '—'} · ${esc(doc?.title ?? '')} · ${fmtDate(doc?.publicationDate)}`,
    btnTopbar('Спросить ИИ', `location.hash='#/chat/${e.documentId}'`, 'icon-search') +
    btnTopbar('Создать уведомление', firstClientId ? `location.hash='#/notifications/compose/${e.id}/${firstClientId}'` : "toast('Сначала нужен затронутый клиент')", 'icon-refresh') +
    btnTopbar('Отправить в Bitrix', "toast('Отправка в Bitrix доступна из уведомления')", 'icon-upload', 'primary'));

  const readinessBadge = e.reviewRequired
    ? '<span class="badge badge-warning">Требует проверки</span>'
    : drafts.length
      ? '<span class="badge badge-positive">Готово к уведомлению</span>'
      : `<span class="badge ${STATUS_BADGE[e.status]}">${STATUS_LABEL[e.status]}</span>`;

  const summary = `
    <div class="card summary-card">
      <div class="summary-top">
        <span class="badge ${IMPACT_BADGE[e.impactLevel]}">${impactSummaryLabel(e)}</span>
        ${readinessBadge}
      </div>
      <div class="summary-title">${esc(e.title)}</div>
      <div class="summary-desc">${esc(e.summary)}</div>
      <div class="summary-meta">
        <span>●&nbsp; ${impacts.length} затронутых клиентов</span>
        <span>${e.tags.map(esc).join(' · ')}</span>
        ${e.effectiveDate ? `<span>вступает ${fmtDate(e.effectiveDate)}</span>` : ''}
        ${doc?.originalUrl ? `<span class="muted"><a href="${esc(doc.originalUrl)}" target="_blank" rel="noopener">Оригинал документа ↗</a></span>` : ''}
      </div>
    </div>`;

  const reasons = (e.impactExplanation ?? '').split(';').map(s => s.trim()).filter(Boolean);
  const impactExplanation = `
    <div class="card section-card">
      <div class="section-title">Почему это важно</div>
      <div class="score-block">
        <div class="score-badge" style="background:${colors.bg}">
          <span class="score-num" style="color:${colors.text}">${e.impactScore != null ? e.impactScore : IMPACT_LABEL[e.impactLevel]}</span>
          ${e.impactScore != null ? `<span class="score-of" style="color:${colors.text}">из 100</span>` : ''}
          <span class="score-label" style="color:${colors.text}">${IMPACT_LABEL[e.impactLevel]} уровень</span>
        </div>
        <div class="score-text">
          ${reasons.length
            ? `<ul class="bullet-list">${bulletHtml(reasons)}</ul>`
            : '<span class="muted">Оценка влияния ещё не рассчитана.</span>'}
          ${e.urgency ? `<span class="muted">Срочность: ${esc(e.urgency)}${ai.confidence != null ? ` · уверенность ${Math.round(ai.confidence * 100)}%` : ''}</span>` : ''}
        </div>
      </div>
    </div>`;

  const consequences = ai.possibleConsequences ?? [];
  const processes = ai.affectedProcesses ?? [];
  const consequencesCard = (consequences.length || processes.length) ? `
    <div class="card section-card">
      <div class="section-title">Последствия и затронутые процессы</div>
      <div class="two-col-notes">
        <div class="note-block">
          <span class="note-title">Возможные последствия</span>
          <span class="note-body">${consequences.map(c => '• ' + esc(c)).join('\n') || 'Нет данных о санкциях в источнике'}</span>
        </div>
        <div class="note-block">
          <span class="note-title">Процессы банка</span>
          <span class="note-body">${processes.map(p => '• ' + esc(p)).join('\n') || 'Затронутые процессы не определены'}</span>
        </div>
      </div>
    </div>` : '';

  const evidence = (ai.evidence ?? []).length
    ? ai.evidence.map((f, i) => `
      <div class="source-frag">
        <span class="frag-tag">[${i + 1}] ${esc(f.evidenceRole || f.sourceType || 'фрагмент')}</span>
        <span class="frag-quote">«${esc(f.text)}»</span>
      </div>`).join('')
    : (ai.sourceFragments ?? []).map((t, i) => `
      <div class="source-frag">
        <span class="frag-tag">[${i + 1}] фрагмент источника</span>
        <span class="frag-quote">«${esc(t)}»</span>
      </div>`).join('');

  const fragmentsCard = evidence ? `
    <div class="card section-card">
      <div class="section-title">Фрагменты источника</div>
      <div class="card-subtitle">Цитаты привязаны к оригинальному документу</div>
      ${evidence}
    </div>` : '';

  const relevanceFor = clientId =>
    relevances.find(r => r.clientId === clientId || r.clientId === String(clientId));

  const clientRows = impacts.slice(0, 4).map(i => {
    const rel = relevanceFor(i.clientProfileId);
    const client = clientFor(i.clientProfileId);
    return `
    <div class="mini-row" onclick="location.hash='#/clients/${i.clientProfileId}'">
      <div><div class="mini-label">${esc(i.companyName)}</div><div class="mini-value">${esc(client?.industry ?? rel?.explanationForBank ?? i.explanation ?? '')}</div></div>
      <div class="mini-actions">
        <span class="badge ${IMPACT_BADGE[i.impactLevel]}">${rel ? rel.relevanceScore + '% релевантность' : IMPACT_LABEL[i.impactLevel]}</span>
      </div>
    </div>`;
  }).join('');

  const segmentRows = [...new Set(impacts.map(i => clientFor(i.clientProfileId)?.industry).filter(Boolean))]
    .slice(0, 4)
    .map(industry => {
      const count = impacts.filter(i => clientFor(i.clientProfileId)?.industry === industry).length;
      return `<div class="segment-row"><span>${esc(industry)} · ${count}</span></div>`;
    }).join('');

  const affectedSegments = `
    <div class="card section-card side-card">
      <div class="section-title">Затронутые сегменты</div>
      <div class="card-subtitle">Релевантность рассчитана по профилям бизнеса</div>
      <div class="mini-list">${segmentRows || '<div class="empty-state compact">Сегменты не определены</div>'}</div>
    </div>`;

  const affectedClients = `
    <div class="card section-card side-card">
      <div class="card-header"><div class="section-title">Затронутые клиенты</div>
        <button class="btn btn-outline small" onclick="recalcImpacts('${e.id}', this)">Пересчитать</button></div>
      <div class="mini-list">${clientRows || '<div class="empty-state">Влияние на клиентов не выявлено</div>'}</div>
    </div>`;

  const meta = ai.metadata;
  const statusLines = [
    '● Документ обработан',
    e.impactScore != null || e.impactExplanation ? '● Влияние рассчитано и объяснено' : '● Влияние не рассчитано',
    drafts.length ? `● Черновиков уведомлений: ${drafts.length}` : '● Уведомление можно создать вручную',
  ];
  const sourceCard = doc ? `
    <div class="card section-card side-card">
      <div class="section-title">Оригинальный источник</div>
      <div class="source-box">
        <span class="source-name">${esc(doc.regulator ?? 'Документ')}</span>
        <span class="source-doc">${esc(doc.title)}${doc.documentType ? ' · ' + esc(doc.documentType) : ''}</span>
        <span class="source-date">Опубликовано ${fmtDate(doc.publicationDate)}</span>
        ${doc.originalUrl ? `<a class="source-link" href="${esc(doc.originalUrl)}" target="_blank" rel="noopener">Открыть документ ↗</a>` : ''}
      </div>
      <div class="status-lines">${statusLines.map(s => `<span>${esc(s)}</span>`).join('')}</div>
      ${meta ? `<div class="meta-footer">
        <span>Анализ: ${esc(meta.selectedModel ?? '—')} (${esc(meta.runtime ?? '—')})</span>
        ${meta.fallbackUsed ? `<span>fallback: ${esc(meta.fallbackReason ?? 'да')}</span>` : ''}
        ${meta.latencyMs != null ? `<span>${meta.latencyMs} мс</span>` : ''}
        ${(meta.warnings ?? []).length ? `<span>⚠ ${meta.warnings.map(esc).join('; ')}</span>` : ''}
      </div>` : ''}
    </div>` : '';

  document.getElementById('page').innerHTML = `
    <span class="back-link" onclick="location.hash='#/changes'">← к списку изменений</span>
    <div class="detail-body">
      ${summary}
      <div class="detail-columns">
        <div class="detail-main-col">${impactExplanation}${consequencesCard}${fragmentsCard}</div>
        <div class="detail-side-col">${affectedSegments}${affectedClients}${sourceCard}</div>
      </div>
    </div>`;
}

async function recalcImpacts(eventId, btn) {
  btn.disabled = true;
  const res = await api(`/api/RegulatoryEvents/${eventId}/impacts/recalculate`, { method: 'POST' });
  btn.disabled = false;
  if (res.ok) {
    state.impacts[eventId] = res.data;
    toast(`Влияние пересчитано: затронуто ${res.data.length}`, 'ok');
    route();
  } else {
    toast('Ошибка пересчёта: ' + (res.data?.error ?? res.status), 'err');
  }
}

/* ---------- Clients list (custom, not a distinct Figma screen) ---------- */

function renderClientsList() {
  renderTopbar('Клиенты', 'Профили компаний и их риск-профиль',
    fieldBox('q-clients', 'Поиск по названию или отрасли…', state.clientsSearch) +
    btnOutline('Обновить источники', 'runIngestion()', 'icon-refresh'));

  document.getElementById('q-clients')?.addEventListener('input', e => { state.clientsSearch = e.target.value; route(); });

  const q = state.clientsSearch.toLowerCase();
  const clients = state.clients.filter(c =>
    !q || c.companyName.toLowerCase().includes(q) || (c.industry ?? '').toLowerCase().includes(q));

  const rows = clients.map(c => {
    const impactCount = state.events.reduce((n, e) => n + (state.impacts[e.id] ?? []).filter(i => i.clientProfileId === c.id).length, 0);
    return `<tr onclick="location.hash='#/clients/${c.id}'" style="cursor:pointer">
      <td><div class="client-cell"><div class="client-avatar">${initials(c.companyName)}</div><div><div class="client-name">${esc(c.companyName)}</div><div class="client-sub">${esc(c.industry ?? '—')}</div></div></div></td>
      <td>${esc(c.bankSegment ?? '—')}</td>
      <td>${esc(SIZE_LABEL[c.size])}</td>
      <td><span class="badge ${IMPACT_BADGE[c.riskProfile]}">${IMPACT_LABEL[c.riskProfile]}</span></td>
      <td class="num">${impactCount}</td>
    </tr>`;
  }).join('');

  document.getElementById('page').innerHTML = `
    <div class="card card-pad">
      <div class="list-summary"><span class="count">${clients.length} клиентов</span></div>
      <div class="table-card">
        <table class="data-table">
          <thead><tr><th>Клиент</th><th>Сегмент</th><th>Размер</th><th>Риск-профиль</th><th class="num">Изменений</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5" class="empty-state">Клиенты не найдены</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;
}

/* ---------- Client profile ---------- */

function renderClientProfile(id) {
  const c = clientFor(id);
  if (!c) { document.getElementById('page').innerHTML = '<div class="empty-state">Клиент не найден</div>'; return; }

  renderTopbar(c.companyName, `${esc(c.industry ?? '—')} · ${SIZE_LABEL[c.size]} бизнес · ОКВЭД ${esc(c.okved ?? '—')}`,
    fieldBox('q-client', 'Поиск по названию или источнику…', '') +
    btnOutline('Обновить источники', 'runIngestion()', 'icon-refresh') +
    btnOutline('Открыть в Bitrix', `toast('Интеграция с Bitrix настраивается в «Настройках»')`));
  bindGlobalSearch('q-client');

  const related = state.events
    .map(e => ({
      e,
      imp: (state.impacts[e.id] ?? []).find(i => i.clientProfileId === id),
      rel: (e.aiDetails?.clientRelevances ?? []).find(r => r.clientId === id || r.clientId === String(id)),
    }))
    .filter(x => x.imp || x.rel)
    .sort((a, b) => new Date(b.e.createdAt) - new Date(a.e.createdAt));

  const flagChips = [
    c.hasForeignTrade && 'ВЭД',
    c.usesOnlinePayments && 'Онлайн-платежи',
    c.handlesPersonalData && 'Персональные данные',
    c.cashOperationsLevel === 'High' && 'Высокий оборот наличных',
  ].filter(Boolean);

  const summary = `
    <div class="card summary-card">
      <div class="summary-top">
        <div class="summary-title" style="font-size:21px">${esc(c.companyName)}</div>
        <span class="badge ${IMPACT_BADGE[c.riskProfile]}">Риск-профиль · ${IMPACT_LABEL[c.riskProfile]}</span>
      </div>
      <div class="summary-meta">
        <span>${esc(c.industry ?? '—')}</span>
        <span class="muted">ОКВЭД ${esc(c.okved ?? '—')}</span>
        <span class="muted">Сегмент: ${esc(c.bankSegment ?? '—')}</span>
      </div>
      <div class="industry-chips">${flagChips.map(f => `<span class="industry-chip">${esc(f)}</span>`).join('') || '<span class="muted">Особых признаков не выявлено</span>'}</div>
    </div>`;

  const topRelated = related[0];
  const whyBlock = topRelated ? `
    <div class="card section-card">
      <div class="section-title">Почему клиент затронут</div>
      <div class="why-box">
        <div class="why-title">Ближайшее по влиянию изменение — «${esc(topRelated.e.title)}»</div>
        <div class="why-body">${esc(topRelated.rel?.explanationForBank ?? topRelated.imp?.explanation ?? 'Объяснение ещё не рассчитано.')}</div>
        ${topRelated.rel?.matchedFactors?.length ? `<div class="why-signals">Сигналы: ${topRelated.rel.matchedFactors.map(esc).join(' · ')}</div>` : ''}
      </div>
    </div>` : '';

  const relatedRows = related.slice(0, 5).map(({ e, imp, rel }) => `
    <div class="mini-row" style="cursor:pointer" onclick="location.hash='#/changes/${e.id}'">
      <div><div class="mini-label">${esc(e.title.slice(0, 60))}${e.title.length > 60 ? '…' : ''}</div><div class="mini-value">${fmtDate(e.createdAt)}</div></div>
      <span class="badge ${IMPACT_BADGE[imp?.impactLevel ?? e.impactLevel]}">${rel ? rel.relevanceScore + '% релевантность' : IMPACT_LABEL[imp?.impactLevel ?? e.impactLevel]}</span>
    </div>`).join('');

  const relatedCard = `
    <div class="card section-card">
      <div class="section-title">Релевантные изменения</div>
      <div class="mini-list">${relatedRows || '<div class="empty-state">Релевантных изменений не найдено</div>'}</div>
    </div>`;

  const clientNotifs = state.notifications.filter(n => n.clientProfileId === id).slice(0, 5);
  const notifRows = clientNotifs.map(n => {
    const ev = state.events.find(e => e.id === n.regulatoryEventId);
    return `<div class="mini-row">
      <div><div class="mini-label">${esc(ev?.title.slice(0, 50) ?? '—')}</div><div class="mini-value">${fmtDate(n.createdAt)}</div></div>
      <span class="badge ${NOTIF_STATUS_BADGE[n.status]}">${NOTIF_STATUS_LABEL[n.status]}</span>
    </div>`;
  }).join('');

  const notifHistory = `
    <div class="card section-card">
      <div class="section-title">История уведомлений</div>
      <div class="mini-list">${notifRows || '<div class="empty-state">Уведомлений клиенту ещё не отправляли</div>'}</div>
    </div>`;

  const attrs = [
    ['Отрасль', c.industry ?? '—'],
    ['Размер бизнеса', SIZE_LABEL[c.size]],
    ['Оборот наличных', CASH_LABEL[c.cashOperationsLevel]],
    ['Внешнеэкономическая деятельность', c.hasForeignTrade ? 'да' : 'нет'],
    ['Онлайн-платежи', c.usesOnlinePayments ? 'да' : 'нет'],
    ['Обработка персональных данных', c.handlesPersonalData ? 'да' : 'нет'],
  ];
  const attrsCard = `
    <div class="card section-card">
      <div class="section-title">Бизнес-признаки</div>
      ${attrs.map(([l, v]) => `<div class="attr-row"><span class="attr-label">${esc(l)}</span><span class="attr-value">${esc(v)}</span></div>`).join('')}
    </div>`;

  document.getElementById('page').innerHTML = `
    <span class="back-link" onclick="location.hash='#/clients'">← к списку клиентов</span>
    <div class="detail-body">
      ${summary}
      <div class="detail-columns">
        <div class="detail-main-col">${whyBlock}${relatedCard}${notifHistory}</div>
        <div class="detail-side-col">${attrsCard}</div>
      </div>
    </div>`;
}

/* ---------- RAG chat ---------- */

function setChatMode(mode) {
  state.chatMode = mode;
  route();
}

function setChatDoc(docId) {
  if (state.chatDocId === docId) return;
  state.chatDocId = docId;
  state.chatHistory = [];
  route();
}

function updateChatDocSearch(value) {
  state.chatDocSearch = value;
  const list = document.getElementById('doc-picker-list');
  if (list) list.innerHTML = docPickerItems();
}

function chatAudience() {
  return state.chatMode === 'plain' ? 'client' : 'bank_employee';
}

function analyzedChatDocs() {
  return state.documents
    .filter(d => state.events.some(e => e.documentId === d.id))
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
}

function docPickerItems() {
  const q = state.chatDocSearch.trim().toLowerCase();
  const docs = analyzedChatDocs().filter(d =>
    !q || d.title.toLowerCase().includes(q) || (d.regulator ?? '').toLowerCase().includes(q));

  if (!docs.length)
    return '<div class="empty-state" style="padding:24px 12px">Документы не найдены</div>';

  return docs.map(d => {
    const ev = state.events.find(e => e.documentId === d.id);
    const meta = [d.regulator, ev?.impactScore != null ? 'скор ' + ev.impactScore : null]
      .filter(Boolean).join(' · ') || fmtDate(d.createdAt);
    return `<div class="doc-item ${d.id === state.chatDocId ? 'active' : ''}" onclick="setChatDoc('${d.id}')">
      <span class="di-title">${esc(d.title)}</span>
      <span class="di-meta">${esc(meta)}</span>
    </div>`;
  }).join('');
}

function renderChatMessage(m) {
  if (m.role === 'question') return `<div class="chat-question">${esc(m.text)}</div>`;
  const a = m.answer;
  const citations = (a.sources ?? []).map((s, i) => `<span class="aa-citation">[${i + 1}] фрагмент документа</span>`).join('');
  return `
    <div class="ai-answer ${a.noData ? 'no-data' : ''}">
      <div class="aa-head"><span class="aa-title">Ответ RegRadar</span>
        <span class="badge ${a.noData ? 'badge-danger' : 'badge-info'}">${a.noData ? 'Недостаточно данных' : (a.audience === 'client' ? 'Простым языком' : 'Для юриста банка')}</span>
      </div>
      <div class="aa-point" style="white-space:pre-line">${esc(a.answer)}</div>
      ${citations ? `<div class="aa-citations">${citations}</div>` : ''}
      ${a.safetyNotice ? `<div class="aa-note">${esc(a.safetyNotice)}</div>` : ''}
    </div>`;
}

function fillChatQuestion(question) {
  const input = document.getElementById('chat-input');
  if (!input || input.disabled) return;
  input.value = question;
  input.focus();
}

function renderChat() {
  renderTopbar('RAG-чат', 'Ответы по документам и профилям клиентов — только с источниками',
    btnTopbar('Для юриста банка', "setChatMode('lawyer')", 'icon-search') +
    btnTopbar('Простым языком', "setChatMode('plain')", 'icon-refresh') +
    btnTopbar('Создать уведомление', "location.hash='#/notifications'", 'icon-upload', 'primary'));

  document.querySelectorAll('.topbar-actions .btn-outline').forEach((b, i) => {
    if ((i === 0 && state.chatMode === 'lawyer') || (i === 1 && state.chatMode === 'plain')) b.classList.add('mode-active');
  });

  const analyzedDocs = analyzedChatDocs();
  if ((!state.chatDocId || !analyzedDocs.some(d => d.id === state.chatDocId)) && analyzedDocs[0])
    state.chatDocId = analyzedDocs[0].id;
  const currentDoc = state.documents.find(d => d.id === state.chatDocId);

  const lastAnswer = [...state.chatHistory].reverse().find(m => m.role === 'answer')?.answer;
  const sources = lastAnswer?.sources ?? [];

  const suggestions = [
    'Почему этот документ важен для клиентов?',
    'Какие процессы банка нужно проверить?',
    'Какие фрагменты подтверждают вывод?',
  ];
  const thread = state.chatHistory.map(renderChatMessage).join('') || `
    <div class="chat-empty-card">
      <div class="aa-head">
        <span class="aa-title">Ответ RegRadar</span>
        <span class="badge badge-info">Ожидает вопрос</span>
      </div>
      <div class="aa-point">
        Выберите один из рабочих вопросов или задайте свой. Ответ будет построен только по фрагментам выбранного документа и вернётся со ссылками на источники.
      </div>
      <div class="suggestion-row">
        ${suggestions.map(q => `<button class="suggestion-chip" onclick="fillChatQuestion('${jsArg(q)}')">${esc(q)}</button>`).join('')}
      </div>
      <div class="aa-note">${currentDoc ? `Контекст: ${esc(currentDoc.title ?? 'документ')}` : 'Нет обработанного документа для контекста.'}</div>
    </div>`;

  const sourceCards = sources.length
    ? sources.map((s, i) => `
      <div class="rag-source">
        <div class="rs-top"><span class="rs-name">${esc(currentDoc?.title ?? 'Источник ' + (i + 1))}</span><span class="rs-score">${Math.round((s.score ?? 0) * 100)}%</span></div>
        <span class="rs-sub">Фрагмент ${i + 1} · официальный документ</span>
        <span class="rs-link">Открыть источник ↗</span>
      </div>`).join('')
    : `<div class="rag-source">
        <div class="rs-top"><span class="rs-name">${esc(currentDoc?.title ?? 'Документ не выбран')}</span><span class="rs-score">—</span></div>
        <span class="rs-sub">${currentDoc ? esc(currentDoc.regulator ?? 'официальный документ') : 'Выберите документ'}</span>
        <span class="rs-link">Источники появятся после ответа</span>
      </div>`;

  const sourcesRows = sources.length
    ? sources.map((s, i) => `
      <div class="rag-frag">
        <span class="rf-tag">[${i + 1}] ${esc(currentDoc?.title.slice(0, 40) ?? 'документ')} · релевантность ${Math.round((s.score ?? 0) * 100) / 100}</span>
        <span class="rf-quote">«${esc(s.text.slice(0, 220))}${s.text.length > 220 ? '…' : ''}»</span>
      </div>`).join('')
    : '<div class="empty-state" style="padding:16px">Источники появятся после первого ответа</div>';

  document.getElementById('page').innerHTML = `
    <div class="rag-body">
      <div class="card chat-panel">
        <div class="chat-context-bar">
          <div><div class="ctx-title">Контекст ответа</div><div class="ctx-sub">${currentDoc ? esc((currentDoc.title ?? '').slice(0, 64)) : 'Документ не выбран'}</div></div>
          <span class="badge ${sources.length ? 'badge-positive' : 'badge-info'}">${sources.length ? sources.length + ' источн.' : 'нет ответа'}</span>
        </div>
        <div class="chat-thread">${thread}${state.chatLoading ? '<div class="chat-loading">RegRadar анализирует фрагменты…</div>' : ''}</div>
        <div class="chat-input-bar">
          <input id="chat-input" placeholder="Задайте вопрос по изменению, клиенту или источнику…" ${state.chatLoading || !currentDoc ? 'disabled' : ''}>
          <button class="chat-send-btn" onclick="sendChatQuestion()" ${state.chatLoading || !currentDoc ? 'disabled' : ''}>Отправить</button>
        </div>
      </div>
      <div class="detail-side-col">
        <div class="card section-card">
          <div class="section-title">Источники ответа</div>
          <div class="card-subtitle">Цитаты можно открыть в контексте документа</div>
          ${sourceCards}
        </div>
        <div class="card section-card">
          <div class="section-title">Фрагменты документа</div>
          ${sourcesRows}
        </div>
        <div class="card section-card">
          <div class="section-title">Состояния ответа</div>
          <div class="state-row"><span class="badge badge-positive">Ответ со ссылками</span><span class="sr-note">Использованы подтверждённые источники</span></div>
          <div class="state-row"><span class="badge badge-warning">Нет подтверждения источником</span><span class="sr-note">Покажем предупреждение и не сделаем вывод</span></div>
          <div class="state-row"><span class="badge badge-danger">Недостаточно данных</span><span class="sr-note">ИИ сообщит, каких данных не хватает для ответа</span></div>
          ${lastAnswer ? `<div class="meta-footer"><span>Провайдер: ${esc(lastAnswer.provider ?? '—')} (${esc(lastAnswer.runtime ?? '—')})</span></div>` : ''}
        </div>
      </div>
    </div>`;

  const input = document.getElementById('chat-input');
  input?.addEventListener('keydown', e => { if (e.key === 'Enter') sendChatQuestion(); });
  input?.focus();
}

async function sendChatQuestion() {
  const input = document.getElementById('chat-input');
  const question = input?.value.trim();
  if (!question || state.chatLoading) return;

  state.chatHistory.push({ role: 'question', text: question });
  state.chatLoading = true;
  renderChat();

  const res = await api('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, documentId: state.chatDocId || null, audience: chatAudience() }),
  });

  state.chatLoading = false;
  if (res.ok) {
    state.chatHistory.push({ role: 'answer', answer: res.data });
  } else {
    state.chatHistory.push({
      role: 'answer',
      answer: { answer: res.data?.error ?? 'Не удалось получить ответ от AI-сервиса.', audience: chatAudience(), noData: true, sources: [], safetyNotice: null },
    });
  }
  renderChat();
}

/* ---------- Notifications journal ---------- */

function renderNotificationsList() {
  renderTopbar('Уведомления', 'История отправленных и запланированных сообщений',
    fieldBox('q-notifs', 'Поиск по клиенту или изменению…', state.notificationsSearch));

  document.getElementById('q-notifs')?.addEventListener('input', e => { state.notificationsSearch = e.target.value; route(); });

  const q = state.notificationsSearch.toLowerCase();
  const rows = state.notifications
    .map(n => ({ n, ev: state.events.find(e => e.id === n.regulatoryEventId), cl: clientFor(n.clientProfileId) }))
    .filter(({ ev, cl }) => !q || (ev?.title ?? '').toLowerCase().includes(q) || (cl?.companyName ?? '').toLowerCase().includes(q))
    .map(({ n, ev, cl }) => `<tr>
      <td>${fmtDateTime(n.createdAt)}</td>
      <td>${esc(ev?.title.slice(0, 50) ?? n.regulatoryEventId)}</td>
      <td>${esc(cl?.companyName ?? '—')}</td>
      <td>${esc(n.channel)}</td>
      <td><span class="badge ${NOTIF_STATUS_BADGE[n.status]}">${NOTIF_STATUS_LABEL[n.status]}</span></td>
    </tr>`).join('');

  const empty = !rows ? `
    <div class="designed-empty">
      <span class="badge badge-info">Журнал пуст</span>
      <h2>Уведомлений ещё не отправлялось</h2>
      <p>После создания уведомлений клиентам они появятся здесь вместе со статусом отправки, каналом и ссылкой на изменение.</p>
    </div>` : '';

  document.getElementById('page').innerHTML = `
    <div class="card card-pad">
      ${rows ? `
      <div class="table-card">
        <table class="data-table">
          <thead><tr><th>Дата</th><th>Изменение</th><th>Клиент</th><th>Канал</th><th>Статус</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>` : empty}
    </div>`;
}

/* ---------- Notification composer ---------- */

function renderComposeNotification(eventId, clientId) {
  const e = state.events.find(x => x.id === eventId);
  const c = clientFor(clientId);
  if (!e || !c) { document.getElementById('page').innerHTML = '<div class="empty-state">Изменение или клиент не найдены</div>'; return; }

  renderTopbar('Уведомление клиенту', `${esc(c.companyName)} · изменение № ${esc(docFor(e)?.documentNumber ?? e.id.slice(0, 8))}`,
    btnTopbar('Сохранить черновик', "toast('Черновик сохранён локально', 'ok')", 'icon-search') +
    btnTopbar('Предпросмотр', "document.querySelector('.json-preview')?.scrollIntoView({behavior:'smooth'})", 'icon-refresh') +
    btnTopbar('Отправить в Bitrix', `sendNotification('${eventId}','${clientId}', this)`, 'icon-upload', 'primary'));

  const imp = (state.impacts[eventId] ?? []).find(i => i.clientProfileId === clientId);
  const key = eventId + '|' + clientId;
  const result = state.composeResult[key];

  const ai = e.aiDetails ?? {};
  const draft = (ai.notificationDrafts ?? []).find(d => d.clientId === clientId || d.clientId === String(clientId));
  const rel = (ai.clientRelevances ?? []).find(r => r.clientId === clientId || r.clientId === String(clientId));

  const draftCards = draft ? `
      <div class="card section-card">
        <div class="section-title">Краткое сообщение</div>
        <div class="card-subtitle">Черновик подготовлен ИИ · приоритет: ${esc(draft.priority ?? '—')}</div>
        <div class="fg-input" style="display:flex;align-items:center;height:auto;padding:10px 12px">${esc(draft.shortMessage)}</div>
      </div>
      <div class="card section-card">
        <div class="section-title">Полное сообщение</div>
        <div class="fg-input" style="height:auto;padding:12px 14px;white-space:pre-line;line-height:1.6">${esc(draft.fullMessage)}</div>
        ${draft.clientFriendlyExplanation ? `<div class="why-box"><div class="why-title">Объяснение для клиента</div><div class="why-body">${esc(draft.clientFriendlyExplanation)}</div></div>` : ''}
      </div>` : `
      <div class="card section-card">
        <div class="section-title">Текст уведомления</div>
        <span class="muted" style="font-size:10px">ИИ-черновика для этого клиента нет — текст уведомления сформируется автоматически на сервере при отправке.</span>
      </div>`;

  const editor = `
    <div class="notif-editor">
      <div class="card recipient-card">
        <div class="field-row">
          <div class="field-group recipient-client">
            <span class="fg-label">Клиент</span>
            <div class="fg-input">${esc(c.companyName)}</div>
          </div>
          <div class="field-group recipient-subject">
            <span class="fg-label">Тема</span>
            <div class="fg-input">${esc(draft?.title ?? e.title)}</div>
          </div>
        </div>
      </div>
      ${draftCards}
      <div class="card section-card disclaimer-card">
        <div class="section-title">Предупреждение</div>
        <div class="disclaimer-box">${esc(draft?.disclaimer ?? 'Сообщение носит информационный характер и не является юридической консультацией. Применимость требований зависит от конкретных операций компании.')}</div>
      </div>
      <div class="card section-card">
        <div class="section-title">Влияние и источник</div>
        <div class="impact-source-row">
          <span class="badge ${IMPACT_BADGE[e.impactLevel]}">${impactBadgeLabel(e)}</span>
          <span class="badge badge-info">${esc(docFor(e)?.regulator ?? 'Источник')}${docFor(e)?.documentNumber ? ' · ' + esc(docFor(e).documentNumber) : ''}</span>
          ${imp ? `<span class="badge badge-info">${esc(rel?.explanationForBank ?? imp.explanation ?? 'без пояснения')}</span>` : ''}
        </div>
        ${docFor(e)?.originalUrl ? `<a href="${esc(docFor(e).originalUrl)}" target="_blank" rel="noopener">Оригинал документа ↗</a>` : ''}
        <span class="muted" style="font-size:10px">Сгенерировано RegRadar · проверено по фрагментам источника</span>
      </div>
      ${result
        ? btnOutline('Уже отправлено — обновить статус', `sendNotification('${eventId}','${clientId}', this)`)
        : btnPrimary('Отправить уведомление', `sendNotification('${eventId}','${clientId}', this)`)}
    </div>`;

  const delivery = `
    <div class="detail-side-col">
      <div class="card section-card">
        <div class="section-title">Отправка</div>
        ${result ? `<span class="badge ${NOTIF_STATUS_BADGE[result.status]}">${NOTIF_STATUS_LABEL[result.status]}</span>` : `<span class="badge badge-warning">Не отправлено</span>`}
        <div class="attr-row"><span class="attr-label">Канал</span><span class="attr-value">${esc(result?.channel ?? '—')}</span></div>
        <div class="attr-row"><span class="attr-label">Получатель</span><span class="attr-value">${esc(c.contactEmail ?? '—')}</span></div>
        <div class="attr-row"><span class="attr-label">Ответственный</span><span class="attr-value">Елена Орлова</span></div>
        <div class="attr-row"><span class="attr-label">Отправлено</span><span class="attr-value">${fmtDateTime(result?.sentAt)}</span></div>
        ${result?.errorMessage ? `<div class="attr-row"><span class="attr-label">Ошибка</span><span class="attr-value">${esc(result.errorMessage)}</span></div>` : ''}
      </div>
      <div class="card section-card">
        <div class="card-header"><div class="section-title">Данные для Bitrix</div><span class="card-subtitle">JSON</span></div>
        <pre class="json-preview">${result?.payload ? esc(JSON.stringify(JSON.parse(result.payload), null, 2)) : 'Появится после отправки'}</pre>
        <span class="card-subtitle">Данные будут записаны в карточку клиента и историю коммуникаций.</span>
      </div>
      <div class="card section-card">
        <div class="section-title">Состояния отправки</div>
        <div class="state-row"><span class="badge badge-info">Готово к отправке</span><span class="sr-note">Данные проверены</span></div>
        <div class="state-row"><span class="badge badge-positive">Отправлено в Bitrix</span><span class="sr-note">ID активности появится после отправки</span></div>
        <div class="state-row"><span class="badge badge-danger">Ошибка интеграции</span><span class="sr-note">Повторите отправку или сохраните черновик</span></div>
      </div>
    </div>`;

  document.getElementById('page').innerHTML = `
    <span class="back-link" onclick="location.hash='#/changes/${eventId}'">← к изменению</span>
    <div class="notif-body">${editor}${delivery}</div>`;
}

async function sendNotification(eventId, clientId, btn) {
  btn.disabled = true;
  const res = await api('/api/Notifications/send', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ regulatoryEventId: eventId, clientProfileId: clientId }),
  });
  btn.disabled = false;
  if (res.ok) {
    state.composeResult[eventId + '|' + clientId] = res.data;
    state.notifications.unshift(res.data);
    toast(`Уведомление: ${NOTIF_STATUS_LABEL[res.data.status]} (канал ${res.data.channel})`, 'ok');
    renderComposeNotification(eventId, clientId);
  } else {
    toast('Ошибка отправки: ' + (res.data?.error ?? res.status), 'err');
  }
}

/* ---------- Sources ---------- */

function renderSources() {
  renderTopbar('Источники', 'Настроенные источники данных и их статус', btnPrimary('Обновить источники', 'runIngestion()', 'icon-refresh'));

  const rows = state.sources.map(s => `<tr>
    <td>${esc(s.name)}</td>
    <td>${esc(SOURCE_TYPE_LABEL[s.type] ?? s.type)}</td>
    <td>${s.baseUrl ? `<a href="${esc(s.baseUrl)}" target="_blank" rel="noopener">${esc(s.baseUrl)}</a>` : '—'}</td>
    <td><span class="badge ${s.isActive ? 'badge-positive' : 'badge-warning'}">${s.isActive ? 'Активен' : 'Отключён'}</span></td>
  </tr>`).join('');

  document.getElementById('page').innerHTML = `
    <div class="card card-pad">
      <div class="table-card">
        <table class="data-table">
          <thead><tr><th>Название</th><th>Тип</th><th>URL</th><th>Статус</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" class="empty-state">Источники не настроены</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;
}

/* ---------- Settings (placeholder) ---------- */

function renderSettings() {
  renderTopbar('Настройки', 'Учётная запись, интеграции и уведомления', '');
  document.getElementById('page').innerHTML = `
    <div class="card placeholder-card">
      <span class="badge badge-info">Скоро</span>
      <h2>Раздел в разработке</h2>
      <p>Здесь появятся настройки интеграции с Bitrix24, управление пользователями и каналами уведомлений.</p>
      <div class="settings-preview">
        <span>Интеграция с Bitrix24</span>
        <span>Управление пользователями</span>
        <span>Каналы уведомлений</span>
      </div>
    </div>`;
}

/* ---------- global actions ---------- */

async function runIngestion() {
  toast('Обновляем источники…');
  const res = await api('/api/Ingestion/run', { method: 'POST' });
  if (res.ok) {
    const summary = res.data.map(r => `${r.source}: ${r.added != null ? r.added + ' новых' : 'ошибка — ' + r.error}`).join(', ');
    toast('Готово: ' + summary, 'ok');
    await loadAll();
    route();
  } else {
    toast('Ошибка ingestion', 'err');
  }
}

function triggerUpload() {
  document.getElementById('file-input').click();
}

document.getElementById('file-input').onchange = async function () {
  const file = this.files[0];
  if (!file) return;
  this.value = '';
  const form = new FormData();
  form.append('file', file);
  const res = await api('/api/Documents/upload', { method: 'POST', body: form });
  if (res.status === 201) toast('Документ загружен и обработан', 'ok');
  else if (res.status === 409) toast('Такой документ уже есть (дедупликация по хэшу)', 'err');
  else toast('Ошибка: ' + (res.data?.error ?? res.status), 'err');
  await loadAll();
  route();
};

(async function init() {
  await loadAll();
  route();
})();
