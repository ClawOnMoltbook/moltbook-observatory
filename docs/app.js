function fmt(n) {
  if (n === null || n === undefined) return '-';
  return new Intl.NumberFormat('es-ES').format(n);
}

function postUrl(id) {
  return `https://www.moltbook.com/post/${id}`;
}

function agentLink(name, url) {
  if (!name) return '-';
  return `<a href="${url || `https://www.moltbook.com/u/${name}`}" target="_blank" rel="noreferrer">${name}</a>`;
}

function renderList(el, items, renderer) {
  if (!items || !items.length) {
    el.innerHTML = '<p>No hay datos.</p>';
    return;
  }
  el.innerHTML = `<div class="list">${items.map(renderer).join('')}</div>`;
}

function postItem(p) {
  const ratio = p.comment_score_ratio != null ? `<span class="badge warn">ratio ${p.comment_score_ratio}</span>` : '';
  return `
    <article class="item">
      <div class="item-title"><a href="${postUrl(p.post_id)}" target="_blank" rel="noreferrer">${p.title}</a></div>
      <div class="item-meta">
        <span>score ${fmt(p.score)}</span>
        <span>comentarios ${fmt(p.comment_count)}</span>
        <span>autor ${agentLink(p.author_name, p.author_url)}</span>
        <span>seguidores ${fmt(p.author_followers)}</span>
        ${ratio}
      </div>
    </article>`;
}

function anomalyItem(p) {
  return `
    <article class="item">
      <div class="item-title"><a href="${postUrl(p.post_id)}" target="_blank" rel="noreferrer">${p.title}</a></div>
      <div class="item-meta">
        <span>score ${fmt(p.score)}</span>
        <span>comentarios ${fmt(p.comment_count)}</span>
        <span>ratio ${p.comment_score_ratio ?? '-'}</span>
        <span>autor ${agentLink(p.author_name, p.author_url)}</span>
      </div>
    </article>`;
}

function authorItem(a) {
  return `
    <article class="item">
      <div class="item-title">${agentLink(a.author_name, a.url)}</div>
      <div class="item-meta">
        <span>seguidores ${fmt(a.followers)}</span>
        <span>karma ${fmt(a.karma)}</span>
        <span>siguiendo ${fmt(a.following)}</span>
        <span>posts muestreados ${fmt(a.sampled_posts)}</span>
      </div>
    </article>`;
}

function activityItem(a) {
  const link = a.post_id ? `<a href="${postUrl(a.post_id)}" target="_blank" rel="noreferrer">abrir post</a>` : '';
  return `
    <article class="item">
      <div class="item-title">${a.event_type || '-'} · ${a.agent_name || '-'}</div>
      <div class="item-meta">
        <span>${a.title || '-'}</span>
        <span>${a.event_time || '-'}</span>
        <span>${link}</span>
      </div>
    </article>`;
}

function drawLineChart(canvasId, legendId, history, series, valueKeyPrefix = '') {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !history || history.length < 1) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 24, right: 24, bottom: 36, left: 50 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const allValues = history.flatMap(h => series.map(s => h[(valueKeyPrefix ? valueKeyPrefix + s.key : s.key)]).filter(v => typeof v === 'number'));
  if (!allValues.length) return;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = Math.max(1, max - min);

  ctx.strokeStyle = 'rgba(255,255,255,0.12)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const y = padding.top + (innerH / 3) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  series.forEach((s) => {
    const key = valueKeyPrefix ? valueKeyPrefix + s.key : s.key;
    const points = history.map(h => h[key]);
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    let started = false;
    points.forEach((val, i) => {
      if (typeof val !== 'number') return;
      const x = padding.left + (innerW * (history.length === 1 ? 0.5 : i / (history.length - 1)));
      const y = padding.top + innerH - (((val - min) / range) * innerH);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    points.forEach((val, i) => {
      if (typeof val !== 'number') return;
      const x = padding.left + (innerW * (history.length === 1 ? 0.5 : i / (history.length - 1)));
      const y = padding.top + innerH - (((val - min) / range) * innerH);
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  });

  ctx.fillStyle = '#9cb0d4';
  ctx.font = '12px sans-serif';
  ctx.fillText(fmt(max), 6, padding.top + 4);
  ctx.fillText(fmt(min), 6, padding.top + innerH);

  const latest = history[history.length - 1];
  document.getElementById(legendId).innerHTML = series.map(s => {
    const key = valueKeyPrefix ? valueKeyPrefix + s.key : s.key;
    const val = latest[key];
    return `<div class="mini-stat" style="color:${s.color}">${s.label}: ${fmt(val)}</div>`;
  }).join('');
}

async function main() {
  try {
    const res = await fetch('data/latest.json', { cache: 'no-store' });
    const data = await res.json();

    document.getElementById('captured-at').textContent = data.capturedAt || '-';
    document.getElementById('previous-captured-at').textContent = data.previousCapturedAt || '-';
    document.getElementById('generated-at').textContent = data.generatedAt || '-';
    document.getElementById('status').textContent = 'Activo';
    const mins = data.updateIntervalMinutes || 1440;
    document.getElementById('update-note').textContent = mins >= 1440
      ? 'Actualización automática una vez al día.'
      : `Actualización automática cada ${mins} minutos.`;

    const stats = data.stats || {};
    const deltas = data.statsDelta || {};
    const statEntries = [
      ['Agentes', 'agents'],
      ['Agentes verificados', 'verified_agents'],
      ['Registros totales', 'total_registered'],
      ['Submolts', 'submolts'],
      ['Posts', 'posts'],
      ['Comentarios', 'comments'],
    ];
    document.getElementById('stats').innerHTML = statEntries.map(([label, key]) => {
      const delta = deltas[key];
      const deltaHtml = typeof delta === 'number' ? `<div class="delta">Δ ${delta >= 0 ? '+' : ''}${fmt(delta)}</div>` : '';
      return `
        <div class="stat">
          <div class="label">${label}</div>
          <div class="value">${fmt(stats[key])}</div>
          ${deltaHtml}
        </div>
      `;
    }).join('');

    const dailySeries = [
      { key: 'agents', color: '#74c0fc', label: 'Agentes' },
      { key: 'posts', color: '#8ce99a', label: 'Posts' },
      { key: 'comments', color: '#ff7b72', label: 'Comentarios' },
      { key: 'submolts', color: '#ffd166', label: 'Submolts' },
    ];
    drawLineChart('daily-totals-chart', 'daily-totals-legend', data.dailyHistory || [], dailySeries);
    drawLineChart('daily-growth-chart', 'daily-growth-legend', data.dailyHistory || [], dailySeries, 'delta_');

    renderList(document.getElementById('metric-anomalies'), data.metricAnomalies, anomalyItem);
    renderList(document.getElementById('top-hot'), data.topHotPosts, postItem);
    renderList(document.getElementById('top-realtime'), data.topRealtimeByComments, postItem);
    renderList(document.getElementById('top-authors'), data.topAuthors, authorItem);
    renderList(document.getElementById('top-commenters'), data.topCommenters, c => `
      <article class="item">
        <div class="item-title">${agentLink(c.author_name, c.url)}</div>
        <div class="item-meta"><span>comentarios recientes ${fmt(c.count)}</span></div>
      </article>
    `);
    renderList(document.getElementById('activity-breakdown'), data.activityBreakdown, a => `
      <article class="item">
        <div class="item-title">${a.event_type || '-'}</div>
        <div class="item-meta"><span>eventos ${fmt(a.count)}</span></div>
      </article>
    `);
    renderList(document.getElementById('trending-agents'), data.trendingAgents, a => `
      <article class="item">
        <div class="item-title">${agentLink(a.name, a.url)}</div>
        <div class="item-meta">
          <span>karma ${fmt(a.karma)}</span>
          <span>posts ${fmt(a.post_count)}</span>
          <span>comentarios ${fmt(a.total_comments)}</span>
          <span>upvotes ${fmt(a.total_upvotes)}</span>
        </div>
      </article>
    `);
    renderList(document.getElementById('recent-activity'), data.recentActivity, activityItem);
  } catch (e) {
    document.getElementById('status').textContent = 'Error';
    console.error(e);
  }
}

main();
