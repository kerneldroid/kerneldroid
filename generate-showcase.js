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
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 16 16" style="width:20px;height:20px;fill:currentColor;"><path d="M6.766 11.328c-2.063-.25-3.516-1.734-3.516-3.656 0-.781.281-1.625.75-2.188-.203-.515-.172-1.609.063-2.062.625-.078 1.468.25 1.968.703.594-.187 1.219-.281 1.985-.281.765 0 1.39.094 1.953.265.484-.437 1.344-.765 1.969-.687.218.422.25 1.515.046 2.047.5.593.766 1.39.766 2.203 0 1.922-1.453 3.375-3.547 3.64.531.344.89 1.094.89 1.954v1.625c0 .468.391.734.86.547C13.781 14.359 16 11.53 16 8.03 16 3.61 12.406 0 7.984 0 3.563 0 0 3.61 0 8.031a7.88 7.88 0 0 0 5.172 7.422c.422.156.828-.125.828-.547v-1.25c-.219.094-.5.156-.75.156-1.031 0-1.64-.562-2.078-1.609-.172-.422-.36-.672-.719-.719-.187-.015-.25-.093-.25-.187 0-.188.313-.328.625-.328.453 0 .844.281 1.25.86.313.452.64.655 1.031.655s.641-.14 1-.5c.266-.265.47-.5.657-.656"/></svg>
        </div>
        <div style="display:flex;flex-direction:column;justify-content:center;gap:3px;min-width:0;flex-grow:1;">
          <div style="font-size:13px;font-weight:700;color:${t.onSurface};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${title}</div>
          <div style="font-size:11px;color:${t.onSurfaceVariant};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.2;">${desc}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
          <span style="background:${t.primaryContainer};color:${t.onPrimaryContainer};border-radius:8px;padding:3px 8px;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px;"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/></svg>
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
