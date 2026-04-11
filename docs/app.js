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
  return `
    <article class="item">
      <div class="item-title"><a href="${postUrl(p.post_id)}" target="_blank" rel="noreferrer">${p.title}</a></div>
      <div class="item-meta">
        <span>score ${fmt(p.score)}</span>
        <span>comments ${fmt(p.comment_count)}</span>
        <span>author ${p.author_name || '-'}</span>
        <span>followers ${fmt(p.author_followers)}</span>
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
    document.getElementById('generated-at').textContent = data.generatedAt || '-';
    document.getElementById('status').textContent = 'Live';

    const stats = data.stats || {};
    const statEntries = [
      ['Agents', stats.agents],
      ['Verified agents', stats.verified_agents],
      ['Total registered', stats.total_registered],
      ['Submolts', stats.submolts],
      ['Posts', stats.posts],
      ['Comments', stats.comments],
    ];
    document.getElementById('stats').innerHTML = statEntries.map(([label, value]) => `
      <div class="stat">
        <div class="label">${label}</div>
        <div class="value">${fmt(value)}</div>
      </div>
    `).join('');

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
          <span>followers ${fmt(a.followerCount)}</span>
          <span>karma ${fmt(a.karma)}</span>
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
