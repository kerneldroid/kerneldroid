import fs from 'node:fs';

const TOKEN = process.env.GITHUB_TOKEN || '';
const USER = process.env.TARGET_USER || 'kerneldroid';
const EXPLICIT_ORGS = ["sysv86","sysrv64"];

const CONFIG = {
  speed: 76,
  direction: 'left',
  sort: 'stars',
  limit: 0,
  cardWidth: 410,
  pauseOnHover: true
};

const HEADERS = {
  'User-Agent': 'Profile-Showcase-Bot',
  'Accept': 'application/vnd.github+json',
  ...(TOKEN ? { 'Authorization': `Bearer ${TOKEN}` } : {})
};

function escapeXml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function getM3TonalTokens(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
    hash |= 0;
  }
  const H = Math.abs(hash) % 360;
  return {
    surface: `oklch(0.17 0.015 ${H})`,
    surfaceHigh: `oklch(0.22 0.02 ${H})`,
    outline: `oklch(0.28 0.025 ${H} / 0.7)`,
    onSurface: `oklch(0.94 0.01 ${H})`,
    onSurfaceVariant: `oklch(0.74 0.02 ${H})`,
    primaryContainer: `oklch(0.28 0.06 ${H})`,
    onPrimaryContainer: `oklch(0.88 0.08 ${H})`,
    primary: `oklch(0.82 0.12 ${H})`
  };
}

async function fetchAll(url) {
  let list = [];
  let page = 1;
  while (page <= 5) {
    const sep = url.includes('?') ? '&' : '?';
    const res = await fetch(`${url}${sep}per_page=100&page=${page}`, { headers: HEADERS });
    if (!res.ok) {
      if (res.status !== 404) console.warn(`GitHub API ${res.status} for ${url}`);
      break;
    }
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) break;
    list = list.concat(data);
    if (data.length < 100) break;
    page++;
  }
  return list;
}

async function run() {
  let repos = [];
  if (USER) {
    repos = await fetchAll(`https://api.github.com/users/${USER}/repos?type=owner&sort=updated`);
  }

  let orgList = [...EXPLICIT_ORGS];
  if (!orgList.length && USER) {
    const autoOrgs = await fetchAll(`https://api.github.com/users/${USER}/orgs`);
    orgList = autoOrgs.map(o => o.login);
  }

  for (const org of orgList) {
    const orgRepos = await fetchAll(`https://api.github.com/orgs/${org}/repos?type=public`);
    repos = repos.concat(orgRepos);
  }

  const seen = new Set();
  repos = repos.filter(r => {
    if (!r || !r.full_name || r.private || seen.has(r.full_name)) return false;
    seen.add(r.full_name);
    return true;
  });

  if (CONFIG.sort === 'stars') {
    repos.sort((a, b) => (b.stargazers_count || 0) - (a.stargazers_count || 0));
  } else if (CONFIG.sort === 'name') {
    repos.sort((a, b) => (a.full_name || a.name).localeCompare(b.full_name || b.name));
  } else {
    repos.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
  }

  if (CONFIG.limit > 0) {
    repos = repos.slice(0, CONFIG.limit);
  }

  if (!repos.length) {
    console.log('No repos found to render.');
    return;
  }

  const cardW = CONFIG.cardWidth;
  const cardH = 84;
  const gap = 16;
  const oneSetWidth = repos.length * (cardW + gap);
  const totalH = cardH + 10;
  const duration = (oneSetWidth / CONFIG.speed).toFixed(2);

  let cardsHtml = '';
  [...repos, ...repos].forEach(d => {
    const t = getM3TonalTokens(d.full_name);
    const title = escapeXml(d.full_name || d.name);
    const desc = escapeXml(d.description || 'No description provided.');
    const lang = escapeXml(d.language || '');
    const stars = Number(d.stargazers_count || 0);

    cardsHtml += `
      <div style="width:${cardW}px;min-width:${cardW}px;height:${cardH}px;background:${t.surface};border:1px solid ${t.outline};border-radius:20px;padding:12px 16px;display:flex;align-items:center;gap:14px;box-sizing:border-box;font-family:'Google Sans Code',monospace;">
        <div style="width:44px;height:44px;border-radius:12px;background:${t.primaryContainer};color:${t.onPrimaryContainer};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
          <svg style="width:20px;height:20px;fill:currentColor;" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        </div>
        <div style="display:flex;flex-direction:column;justify-content:center;gap:3px;min-width:0;flex-grow:1;">
          <div style="font-size:13px;font-weight:700;color:${t.onSurface};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${title}</div>
          <div style="font-size:11px;color:${t.onSurfaceVariant};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.2;">${desc}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
          <span style="background:${t.primaryContainer};color:${t.onPrimaryContainer};border-radius:8px;padding:3px 8px;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px;">
            <svg style="width:12px;height:12px;fill:currentColor;" viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
            ${stars}
          </span>
          ${lang ? `<span style="font-size:11px;font-weight:500;color:${t.onSurfaceVariant};">${lang}</span>` : ''}
        </div>
      </div>`;
  });

  const animKeyframes = CONFIG.direction === 'right'
    ? `@keyframes scroll { 0% { transform:translate3d(-${oneSetWidth}px, 0, 0); } 100% { transform:translate3d(0, 0, 0); } }`
    : `@keyframes scroll { 0% { transform:translate3d(0, 0, 0); } 100% { transform:translate3d(-${oneSetWidth}px, 0, 0); } }`;

  const pauseCss = CONFIG.pauseOnHover ? '.track:hover { animation-play-state: paused; }' : '';

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="${totalH}" viewBox="0 0 1000 ${totalH}" fill="none">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans+Code:wght@400;600;700&amp;display=swap');
        .track-wrapper { width:100%; overflow:hidden; background:transparent; display:flex; }
        .track { display:flex; gap:${gap}px; width:max-content; will-change:transform; animation:scroll ${duration}s linear infinite; }
        ${pauseCss}
        ${animKeyframes}
      </style>
      <div class="track-wrapper">
        <div class="track">
          ${cardsHtml}
        </div>
      </div>
    </div>
  </foreignObject>
</svg>`;

  fs.writeFileSync('showcase.svg', svg);

  let readme = fs.existsSync('README.md') ? fs.readFileSync('README.md', 'utf8') : '# Profile\n\n<!-- SHOWCASE_START -->\n<!-- SHOWCASE_END -->';
  const tagStart = '<!-- SHOWCASE_START -->';
  const tagEnd = '<!-- SHOWCASE_END -->';
  const showcaseBlock = `${tagStart}\n<p align="center">\n  <img src="showcase.svg" alt="Repositories Showcase" width="100%" />\n</p>\n${tagEnd}`;

  if (readme.includes(tagStart) && readme.includes(tagEnd)) {
    const regex = new RegExp(`${tagStart}[\\s\\S]*?${tagEnd}`, 'g');
    readme = readme.replace(regex, showcaseBlock);
  } else {
    readme += `\n\n${showcaseBlock}`;
  }
  fs.writeFileSync('README.md', readme);
}

run();
