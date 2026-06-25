const API = '/api';
let _pnlChart = null;

/* ── Clock in topbar ───────────────────── */
function tickClock() {
  const now = new Date();
  document.getElementById('metaTime').textContent =
    now.toLocaleDateString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit' }) + ' ' +
    now.toLocaleTimeString('zh-CN', { hour12:false });
}
tickClock();
setInterval(tickClock, 30_000);

/* ── Stats ─────────────────────────────── */
async function loadStats() {
  const r = await fetch(API + '/stats?period=2026-06');
  const d = await r.json();
  const pnl = d.profit_loss || 0;
  document.getElementById('statsRow').innerHTML =
    `<div class="qs"><div class="val">${d.win_rate}%</div><div class="lbl">胜率</div></div>` +
    `<div class="qs"><div class="val">${d.completed_trades}</div><div class="lbl">已完结</div></div>` +
    `<div class="qs"><div class="val" style="color:${pnl>=0?'var(--up)':'var(--down)'}">${pnl>=0?'+':''}${pnl.toFixed(0)}</div><div class="lbl">总盈亏</div></div>` +
    `<div class="qs"><div class="val">${d.max_consecutive_loss}</div><div class="lbl">最大连亏</div></div>`;
  return d;
}

/* ── Trades + Chart ────────────────────── */
async function loadTrades() {
  const r = await fetch(API + '/trades?limit=30');
  const d = await r.json();

  // Table
  const tbody = document.getElementById('tradeList');
  tbody.innerHTML = d.trades.map(t =>
    `<tr>
      <td>${t.trade_time ? t.trade_time.slice(5,16) : ''}</td>
      <td>${t.code}</td>
      <td>${t.name || ''}</td>
      <td><span class="tag tag-${t.direction}">${t.direction==='buy'?'买':'卖'}</span></td>
      <td>${t.price}</td>
      <td class="${t.profit_loss>0?'pnl-up':t.profit_loss<0?'pnl-down':''}">${t.direction==='sell'&&t.profit_pct!=null?t.profit_pct.toFixed(2)+'%':'-'}</td>
      <td>${t.strategy||''}</td>
    </tr>`
  ).join('');

  // PnL curve
  const sells = d.trades.filter(t => t.direction === 'sell').reverse();
  let cum = 0;
  const labels = sells.map(t => t.trade_time ? t.trade_time.slice(5,10) : '');
  const data  = sells.map(t => { cum += t.profit_loss; return cum; });

  // Hero number
  const finalPnl = data.length ? data[data.length-1] : 0;
  const hero = document.getElementById('heroPnl');
  hero.textContent = (finalPnl>=0?'+':'') + finalPnl.toFixed(0);
  hero.className = 'cum-pnl ' + (finalPnl >= 0 ? 'up' : 'down');

  // Chart
  if (_pnlChart) _pnlChart.destroy();
  const ctx = document.getElementById('pnlChart').getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 260);
  grad.addColorStop(0, finalPnl >= 0 ? 'rgba(239,68,68,0.25)' : 'rgba(34,197,94,0.25)');
  grad.addColorStop(1, 'rgba(240,180,41,0.02)');

  _pnlChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: finalPnl >= 0 ? '#ef4444' : '#22c55e',
        backgroundColor: grad,
        borderWidth: 1.5,
        pointRadius: 2,
        pointHoverRadius: 5,
        pointBackgroundColor: finalPnl >= 0 ? '#ef4444' : '#22c55e',
        tension: 0.25,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: '#5a6474', font: { size: 10, family: 'monospace' } },
          grid: { color: 'rgba(30,39,51,0.5)' }
        },
        y: {
          ticks: {
            color: '#5a6474',
            font: { size: 10, family: 'monospace' },
            callback: v => (v>=0?'+':'') + v
          },
          grid: { color: 'rgba(30,39,51,0.5)' }
        }
      }
    }
  });
}

/* ── Positions ──────────────────────────── */
async function loadPositions() {
  try {
    const r = await fetch(API + '/positions');
    const d = await r.json();
    const bar = document.getElementById('positionsBar');
    if (!d.positions || !d.positions.length) {
      bar.innerHTML = '';
      return;
    }
    bar.innerHTML = d.positions.map(p =>
      `<div class="pos-tag"><span class="code">${p.code}</span> ${p.name||''} &nbsp;成本${p.avg_cost} &nbsp;现价${p.current_price||'—'}</div>`
    ).join('');
  } catch (_) { /* positions endpoint may not exist yet */ }
}

/* ── Form submit ───────────────────────── */
document.getElementById('tradeForm').onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  body.price = parseFloat(body.price);
  const r = await fetch(API + '/trades', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (r.ok) {
    e.target.reset();
    await Promise.all([loadTrades(), loadStats(), loadPositions()]);
  } else {
    alert('录入失败');
  }
};

/* ── Init ──────────────────────────────── */
loadStats();
loadTrades();
loadPositions();
