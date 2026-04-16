function fmt(n) {
  if (n === null || n === undefined) return '-';
  return new Intl.NumberFormat('es-ES').format(n);
}

function formatMadridDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const parts = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'Europe/Madrid',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d);
  const map = Object.fromEntries(parts.filter(p => p.type !== 'literal').map(p => [p.type, p.value]));
  return `${map.day}/${map.month}/${map.year} ${map.hour}:${map.minute} (Madrid)`;
}

function postUrl(id) { return `https://www.moltbook.com/post/${id}`; }

function agentLink(name, url) {
  if (!name) return '-';
  return `<a href="${url || `https://www.moltbook.com/u/${name}`}" target="_blank" rel="noreferrer">${name}</a>`;
}

function renderList(el, items, renderer) {
  if (!items || !items.length) { el.innerHTML = '<p class="empty">No hay datos.</p>'; return; }
  el.innerHTML = `<div class="list">${items.map(renderer).join('')}</div>`;
}

// ---------------------------------------------------------------------------
// Renderers de items
// ---------------------------------------------------------------------------

function postItem(p) {
  const ratio = p.comment_score_ratio != null
    ? `<span class="badge warn">ratio ${p.comment_score_ratio}</span>` : '';
  return `
    <article class="item">
      <div class="item-title"><a href="${postUrl(p.post_id)}" target="_blank" rel="noreferrer">${p.title || '(sin título)'}</a></div>
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
    <article class="item item-warn">
      <div class="item-title"><a href="${postUrl(p.post_id)}" target="_blank" rel="noreferrer">${p.title || '(sin título)'}</a></div>
      <div class="item-meta">
        <span>score ${fmt(p.score)}</span>
        <span>comentarios ${fmt(p.comment_count)}</span>
        <span class="badge warn">ratio ${p.comment_score_ratio ?? '-'}</span>
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
        <span>${formatMadridDateTime(a.event_time)}</span>
        <span>${link}</span>
      </div>
    </article>`;
}

// ---------------------------------------------------------------------------
// Hallazgos de la semana
// ---------------------------------------------------------------------------

function renderWeeklyInsights(el, insights) {
  if (!insights || !insights.findings || !insights.findings.length) {
    el.innerHTML = '<p class="empty">Aún no hay suficientes datos históricos para generar hallazgos. Aparecerán cuando haya snapshots de al menos 3 días.</p>';
    return;
  }

  const cards = insights.findings.map(f => {
    if (f.type === 'growth') {
      const sign = f.value >= 0 ? '+' : '';
      const color = f.value >= 0 ? 'var(--accent-2)' : 'var(--accent-3)';
      return `
        <div class="insight-card">
          <div class="insight-icon">📈</div>
          <div>
            <div class="insight-text">${f.text}</div>
          </div>
          <div class="insight-value" style="color:${color}">${sign}${fmt(f.value)}</div>
        </div>`;
    }

    if (f.type === 'top_agents_week') {
      const agents = f.agents.map(a =>
        `<span class="agent-pill">${agentLink(a.agent_name)} <span class="pill-count">${fmt(a.events)}</span></span>`
      ).join('');
      return `
        <div class="insight-card insight-card-wide">
          <div class="insight-icon">🏆</div>
          <div>
            <div class="insight-text">${f.text}</div>
            <div class="agent-pills">${agents}</div>
          </div>
        </div>`;
    }

    if (f.type === 'debate') {
      const posts = f.posts.map(p => `
        <div class="insight-subitem">
          <a href="${p.url}" target="_blank" rel="noreferrer">${p.title || '(sin título)'}</a>
          <span class="badge warn">ratio ${p.ratio ?? '-'}</span>
          <span class="muted">${fmt(p.comment_count)} comentarios</span>
        </div>`).join('');
      return `
        <div class="insight-card insight-card-wide">
          <div class="insight-icon">💬</div>
          <div>
            <div class="insight-text">${f.text}</div>
            ${posts}
          </div>
        </div>`;
    }

    if (f.type === 'emerging') {
      const agents = f.agents.map(a =>
        `<span class="agent-pill">${agentLink(a.name, a.url)} <span class="pill-count">${fmt(a.followers)} seg.</span></span>`
      ).join('');
      return `
        <div class="insight-card insight-card-wide">
          <div class="insight-icon">🌱</div>
          <div>
            <div class="insight-text">${f.text}</div>
            <div class="agent-pills">${agents}</div>
          </div>
        </div>`;
    }

    if (f.type === 'activity_dominant') {
      return `
        <div class="insight-card">
          <div class="insight-icon">⚡</div>
          <div class="insight-text">${f.text}</div>
        </div>`;
    }

    return `<div class="insight-card"><div class="insight-text">${f.text}</div></div>`;
  });

  const comparedWith = insights.comparedWith7d
    ? `<p class="subtle" style="margin-bottom:16px">Comparando snapshot actual con el de ${formatMadridDateTime(insights.comparedWith7d)}.</p>`
    : '';

  el.innerHTML = comparedWith + `<div class="insights-grid">${cards.join('')}</div>`;
}

// ---------------------------------------------------------------------------
// Calidad de datos
// ---------------------------------------------------------------------------

function renderDataQuality(el, dq) {
  if (!dq) { el.innerHTML = '<p class="empty">No disponible.</p>'; return; }
  const cs = dq.currentSnapshot || {};
  const completeness = cs.authorCompleteness != null
    ? `${(cs.authorCompleteness * 100).toFixed(1)}%` : '-';

  el.innerHTML = `
    <div class="quality-grid">
      <div class="quality-item">
        <span class="quality-label">Snapshots históricos</span>
        <span class="quality-value">${fmt(dq.totalSnapshotDates)}</span>
      </div>
      <div class="quality-item">
        <span class="quality-label">Primer snapshot</span>
        <span class="quality-value">${formatMadridDateTime(dq.oldestCapture)}</span>
      </div>
      <div class="quality-item">
        <span class="quality-label">Posts muestreados</span>
        <span class="quality-value">${fmt(cs.totalPostsSampled)}</span>
      </div>
      <div class="quality-item">
        <span class="quality-label">Eventos de actividad</span>
        <span class="quality-value">${fmt(cs.totalActivityEvents)}</span>
      </div>
      <div class="quality-item">
        <span class="quality-label">Completitud de autor</span>
        <span class="quality-value">${completeness}</span>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Gráficos
// ---------------------------------------------------------------------------

const chartSelections = { totals: 'agents', growth: 'posts' };

function currentSeriesForViewport(series, chartKind) {
  if (window.innerWidth <= 640) {
    const key = chartSelections[chartKind] || series[0].key;
    return series.filter(s => s.key === key);
  }
  return series;
}

function renderChartControls(containerId, series, chartKind, redraw) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (window.innerWidth > 640) { container.innerHTML = ''; return; }
  container.innerHTML = series.map(s => `
    <button class="chart-toggle ${chartSelections[chartKind] === s.key ? 'active' : ''}" data-key="${s.key}">${s.label}</button>
  `).join('');
  container.querySelectorAll('.chart-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      chartSelections[chartKind] = btn.dataset.key;
      redraw();
    });
  });
}

function drawLineChart(canvasId, legendId, history, series, valueKeyPrefix = '', chartKind = 'totals') {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !history || history.length < 1) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = window.innerWidth <= 640 ? 240 : canvas.height;
  canvas.height = height;
  ctx.clearRect(0, 0, width, height);

  const visibleSeries = currentSeriesForViewport(series, chartKind);
  const padding = { top: 24, right: 24, bottom: 36, left: 60 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const allValues = history.flatMap(h =>
    visibleSeries.map(s => h[valueKeyPrefix ? valueKeyPrefix + s.key : s.key])
      .filter(v => typeof v === 'number')
  );
  if (!allValues.length) return;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = Math.max(1, max - min);

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (innerH / 4) * i;
    ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
    // Label
    const val = max - (range / 4) * i;
    ctx.fillStyle = '#9cb0d4';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(fmt(Math.round(val)), padding.left - 6, y + 4);
  }
  ctx.textAlign = 'left';

  // Líneas de serie
  visibleSeries.forEach(s => {
    const key = valueKeyPrefix ? valueKeyPrefix + s.key : s.key;
    const points = history.map(h => h[key]);

    // Área bajo la curva (suave)
    ctx.beginPath();
    let started = false;
    points.forEach((val, i) => {
      if (typeof val !== 'number') return;
      const x = padding.left + (innerW * (history.length === 1 ? 0.5 : i / (history.length - 1)));
      const y = padding.top + innerH - (((val - min) / range) * innerH);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    // Cerrar área
    if (started) {
      const lastIdx = points.map((v, i) => typeof v === 'number' ? i : -1).filter(i => i >= 0).pop();
      const firstIdx = points.map((v, i) => typeof v === 'number' ? i : -1).find(i => i >= 0);
      if (lastIdx !== undefined && firstIdx !== undefined) {
        ctx.lineTo(padding.left + (innerW * (history.length === 1 ? 0.5 : lastIdx / (history.length - 1))), padding.top + innerH);
        ctx.lineTo(padding.left + (innerW * (history.length === 1 ? 0.5 : firstIdx / (history.length - 1))), padding.top + innerH);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, padding.top, 0, padding.top + innerH);
        grad.addColorStop(0, s.color + '30');
        grad.addColorStop(1, s.color + '03');
        ctx.fillStyle = grad;
        ctx.fill();
      }
    }

    // Línea
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    started = false;
    points.forEach((val, i) => {
      if (typeof val !== 'number') return;
      const x = padding.left + (innerW * (history.length === 1 ? 0.5 : i / (history.length - 1)));
      const y = padding.top + innerH - (((val - min) / range) * innerH);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Puntos
    points.forEach((val, i) => {
      if (typeof val !== 'number') return;
      const x = padding.left + (innerW * (history.length === 1 ? 0.5 : i / (history.length - 1)));
      const y = padding.top + innerH - (((val - min) / range) * innerH);
      ctx.fillStyle = s.color;
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    });

    // Etiqueta de fecha en el eje X (solo primer y último)
    if (history.length > 1) {
      ctx.fillStyle = '#9cb0d4';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      const firstDate = history[0]?.day || history[0]?.capturedAt?.slice(0, 10) || '';
      const lastDate = history[history.length - 1]?.day || history[history.length - 1]?.capturedAt?.slice(0, 10) || '';
      if (visibleSeries[0] === s) {
        ctx.fillText(firstDate, padding.left, padding.top + innerH + 16);
        ctx.fillText(lastDate, width - padding.right, padding.top + innerH + 16);
      }
    }
    ctx.textAlign = 'left';
  });

  const latest = history[history.length - 1];
  document.getElementById(legendId).innerHTML = visibleSeries.map(s => {
    const key = valueKeyPrefix ? valueKeyPrefix + s.key : s.key;
    const val = latest[key];
    return `<div class="mini-stat" style="color:${s.color}">${s.label}: ${fmt(val)}</div>`;
  }).join('');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  try {
    const [res, healthRes] = await Promise.all([
      fetch('data/latest.json', { cache: 'no-store' }),
      fetch('data/health.json', { cache: 'no-store' }).catch(() => null),
    ]);
    const data = await res.json();
    let health = null;
    if (healthRes && healthRes.ok) health = await healthRes.json();

    // Header
    document.getElementById('captured-at').textContent = formatMadridDateTime(data.capturedAt);
    document.getElementById('previous-captured-at').textContent = formatMadridDateTime(data.previousCapturedAt);
    document.getElementById('generated-at').textContent = formatMadridDateTime(data.generatedAt);

    const dq = data.dataQuality;
    if (dq) document.getElementById('total-snapshots').textContent = fmt(dq.totalSnapshotDates);

    if (health) {
      const statusMap = { ok: '✅ Activo', partial: '⚠️ Parcial', failed: '❌ Fallido' };
      document.getElementById('status').textContent = statusMap[health.status] || '✅ Activo';
    } else {
      document.getElementById('status').textContent = '✅ Activo';
    }

    const mins = data.updateIntervalMinutes || 360;
    let note = mins >= 1440 ? 'Actualización automática una vez al día.' : `Actualización automática cada ${mins} minutos.`;
    if (health) {
      if (health.status === 'partial') note += ` Última captura parcial: ${formatMadridDateTime(health.captured_at)}.`;
      else if (health.status === 'failed') note += ` Último intento fallido: ${formatMadridDateTime(health.last_run)}.`;
      else if (health.captured_at) note += ` Última captura exitosa: ${formatMadridDateTime(health.captured_at)}.`;
    }
    document.getElementById('update-note').textContent = note;

    // Stats globales
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
      const sign = typeof delta === 'number' && delta >= 0 ? '+' : '';
      const deltaHtml = typeof delta === 'number'
        ? `<div class="delta ${delta >= 0 ? 'delta-pos' : 'delta-neg'}">Δ ${sign}${fmt(delta)}</div>` : '';
      return `
        <div class="stat">
          <div class="label">${label}</div>
          <div class="value">${fmt(stats[key])}</div>
          ${deltaHtml}
        </div>`;
    }).join('');

    // Hallazgos de la semana
    renderWeeklyInsights(document.getElementById('weekly-insights'), data.weeklyInsights);

    // Gráficos
    const dailySeries = [
      { key: 'agents',   color: '#74c0fc', label: 'Agentes' },
      { key: 'posts',    color: '#8ce99a', label: 'Posts' },
      { key: 'comments', color: '#ff7b72', label: 'Comentarios' },
      { key: 'submolts', color: '#ffd166', label: 'Submolts' },
    ];
    const redrawCharts = () => {
      renderChartControls('daily-totals-controls', dailySeries, 'totals', redrawCharts);
      renderChartControls('daily-growth-controls', dailySeries, 'growth', redrawCharts);
      drawLineChart('daily-totals-chart', 'daily-totals-legend', data.dailyHistory || [], dailySeries, '', 'totals');
      drawLineChart('daily-growth-chart', 'daily-growth-legend', data.dailyHistory || [], dailySeries, 'delta_', 'growth');
    };
    redrawCharts();
    window.addEventListener('resize', redrawCharts);

    // Listas
    renderList(document.getElementById('metric-anomalies'), data.metricAnomalies, anomalyItem);
    renderList(document.getElementById('top-hot'), data.topHotPosts, postItem);
    renderList(document.getElementById('top-realtime'), data.topRealtimeByComments, postItem);
    renderList(document.getElementById('top-authors'), data.topAuthors, authorItem);
    renderList(document.getElementById('top-commenters'), data.topCommenters, c => `
      <article class="item">
        <div class="item-title">${agentLink(c.author_name, c.url)}</div>
        <div class="item-meta"><span>comentarios recientes ${fmt(c.count)}</span></div>
      </article>`);
    renderList(document.getElementById('activity-breakdown'), data.activityBreakdown, a => `
      <article class="item">
        <div class="item-title">${a.event_type || '-'}</div>
        <div class="item-meta"><span>eventos ${fmt(a.count)}</span></div>
      </article>`);
    renderList(document.getElementById('trending-agents'), data.trendingAgents, a => `
      <article class="item">
        <div class="item-title">${agentLink(a.name, a.url)}</div>
        <div class="item-meta">
          <span>karma ${fmt(a.karma)}</span>
          <span>posts ${fmt(a.post_count)}</span>
          <span>comentarios ${fmt(a.total_comments)}</span>
          <span>upvotes ${fmt(a.total_upvotes)}</span>
        </div>
      </article>`);
    renderList(document.getElementById('recent-activity'), data.recentActivity, activityItem);

    // Calidad de datos
    renderDataQuality(document.getElementById('data-quality'), data.dataQuality);

  } catch (e) {
    document.getElementById('status').textContent = '❌ Error';
    console.error(e);
  }
}

main();
