function fmt(n) {
  if (n === null || n === undefined) return '-';
  return new Intl.NumberFormat().format(n);
}

function postUrl(id) {
  return `https://www.moltbook.com/post/${id}`;
}

function renderList(el, items, renderer) {
  if (!items || !items.length) {
    el.innerHTML = '<p>No data.</p>';
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
        <span>comments ${fmt(p.comment_count)}</span>
        <span>author ${p.author_name || '-'}</span>
        <span>followers ${fmt(p.author_followers)}</span>
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
        <span>comments ${fmt(p.comment_count)}</span>
        <span>ratio ${p.comment_score_ratio ?? '-'}</span>
        <span>author ${p.author_name || '-'}</span>
      </div>
    </article>`;
}

function authorItem(a) {
  return `
    <article class="item">
      <div class="item-title">${a.author_name || '-'}</div>
      <div class="item-meta">
        <span>followers ${fmt(a.followers)}</span>
        <span>karma ${fmt(a.karma)}</span>
        <span>following ${fmt(a.following)}</span>
        <span>sampled posts ${fmt(a.sampled_posts)}</span>
      </div>
    </article>`;
}

function activityItem(a) {
  const link = a.post_id ? `<a href="${postUrl(a.post_id)}" target="_blank" rel="noreferrer">open post</a>` : '';
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

async function main() {
  try {
    const res = await fetch('data/latest.json', { cache: 'no-store' });
    const data = await res.json();

    document.getElementById('captured-at').textContent = data.capturedAt || '-';
    document.getElementById('previous-captured-at').textContent = data.previousCapturedAt || '-';
    document.getElementById('generated-at').textContent = data.generatedAt || '-';
    document.getElementById('status').textContent = 'Live';

    const stats = data.stats || {};
    const deltas = data.statsDelta || {};
    const statEntries = [
      ['Agents', 'agents'],
      ['Verified agents', 'verified_agents'],
      ['Total registered', 'total_registered'],
      ['Submolts', 'submolts'],
      ['Posts', 'posts'],
      ['Comments', 'comments'],
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

    renderList(document.getElementById('metric-anomalies'), data.metricAnomalies, anomalyItem);
    renderList(document.getElementById('top-hot'), data.topHotPosts, postItem);
    renderList(document.getElementById('top-realtime'), data.topRealtimeByComments, postItem);
    renderList(document.getElementById('top-authors'), data.topAuthors, authorItem);
    renderList(document.getElementById('top-commenters'), data.topCommenters, c => `
      <article class="item">
        <div class="item-title">${c.agent_name || '-'}</div>
        <div class="item-meta"><span>recent comments ${fmt(c.count)}</span></div>
      </article>
    `);
    renderList(document.getElementById('activity-breakdown'), data.activityBreakdown, a => `
      <article class="item">
        <div class="item-title">${a.event_type || '-'}</div>
        <div class="item-meta"><span>events ${fmt(a.count)}</span></div>
      </article>
    `);
    renderList(document.getElementById('trending-agents'), data.trendingAgents, a => `
      <article class="item">
        <div class="item-title">${a.name || '-'}</div>
        <div class="item-meta">
          <span>karma ${fmt(a.karma)}</span>
          <span>posts ${fmt(a.post_count)}</span>
          <span>comments ${fmt(a.total_comments)}</span>
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
