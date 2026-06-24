const API = '/api';
let _pnlChart = null;

async function loadStats() {
  const r = await fetch(API + '/stats?period=2026-06');
  const d = await r.json();
  document.getElementById('statsRow').innerHTML =
    `<div class="stat"><div class="num">${d.win_rate}%</div><div class="lbl">胜率</div></div>` +
    `<div class="stat"><div class="num">${d.completed_trades}</div><div class="lbl">已完结</div></div>` +
    `<div class="stat"><div class="num">${d.profit_loss.toFixed(0)}</div><div class="lbl">总盈亏</div></div>` +
    `<div class="stat"><div class="num">${d.max_consecutive_loss}</div><div class="lbl">最大连亏</div></div>`;
  return d;
}

async function loadTrades() {
  const r = await fetch(API + '/trades?limit=30');
  const d = await r.json();
  const tbody = document.getElementById('tradeList');
  tbody.innerHTML = d.trades.map(t =>
    `<tr>
      <td>${t.trade_time}</td>
      <td>${t.code}</td>
      <td>${t.name}</td>
      <td><span class="tag tag-${t.direction}">${t.direction === 'buy' ? '买' : '卖'}</span></td>
      <td>${t.price}</td>
      <td class="${t.profit_loss > 0 ? 'tag-buy' : t.profit_loss < 0 ? 'tag-sell' : ''}">${t.direction === 'sell' ? t.profit_pct.toFixed(2) + '%' : '-'}</td>
      <td>${t.strategy}</td>
    </tr>`
  ).join('');

  const sells = d.trades.filter(t => t.direction === 'sell').reverse();
  let cum = 0;
  const labels = sells.map(t => t.trade_time ? t.trade_time.slice(5, 10) : '');
  const data = sells.map(t => { cum += t.profit_loss; return cum.toFixed(2); });

  if (_pnlChart) _pnlChart.destroy();
  const ctx = document.getElementById('pnlChart').getContext('2d');
  _pnlChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{ label: '累计盈亏', data, borderColor: '#38bdf8', tension: 0.3 }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#94a3b8' } } },
      scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } }
    }
  });
}

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
    loadTrades();
    loadStats();
  } else {
    alert('录入失败');
  }
};

loadStats();
loadTrades();
