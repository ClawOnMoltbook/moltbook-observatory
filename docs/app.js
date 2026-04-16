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
// Navegación por pestañas — marca la activa según sección visible
// ---------------------------------------------------------------------------

function initTabNav() {
  const sections = [
    'section-stats', 'section-insights', 'section-anomalies',
    'section-posts', 'section-agents', 'section-activity', 'section-meta',
  ];
  const links = document.querySelectorAll('.tab-link');

  function setActive(id) {
    links.forEach(l => {
      l.classList.toggle('active', l.getAttribute('href') === '#' + id);
    });
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) setActive(entry.target.id);
    });
  }, { rootMargin: '-20% 0px -70% 0px' });

  sections.forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });

  // Activar la primera al cargar
  setActive('section-stats');
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

    // Stats globales (se omite 'agents' porque siempre coincide con 'verified_agents')
    const stats = data.stats || {};
    const deltas = data.statsDelta || {};
    const statEntries = [
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

    // Navegación
    initTabNav();

  } catch (e) {
    document.getElementById('status').textContent = '❌ Error';
    console.error(e);
  }
}

main();
