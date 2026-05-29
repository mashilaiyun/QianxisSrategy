let data = null;
let currentCategory = null;
let currentVol = null;
let debounceTimer = null;
let pageSize = 50;
let currentPage = 0;
function debounceFilter(){clearTimeout(debounceTimer);debounceTimer=setTimeout(()=>{currentPage=0;filterProblems()},200)}

async function loadData(){
  try{
    const resp = await fetch('/api/data');
    data = await resp.json();
    render();
  }catch(e){
    document.getElementById('headerSub').textContent = '加载失败: ' + e.message;
  }
}

function render(){
  renderFavorites();
  renderHistory();
  document.getElementById('headerSub').textContent = `共 ${data.problems.length} 道题目，${data.categories.length} 个分类`;
  const easy = data.problems.filter(p=>p.difficulty==='简单').length;
  const med = data.problems.filter(p=>p.difficulty==='中等').length;
  const hard = data.problems.filter(p=>p.difficulty==='困难').length;
  document.getElementById('statsBar').innerHTML = `
    <div class="stat-card"><div class="num">${data.problems.length}</div><div class="label">总题目</div></div>
    <div class="stat-card"><div class="num" style="color:#4caf50">${easy}</div><div class="label">🟢 简单</div></div>
    <div class="stat-card"><div class="num" style="color:#ff9800">${med}</div><div class="label">🟡 中等</div></div>
    <div class="stat-card"><div class="num" style="color:#f44336">${hard}</div><div class="label">🔴 困难</div></div>
    <div class="stat-card"><div class="num">${data.categories.length}</div><div class="label">分类数</div></div>
    <div class="stat-card" style="cursor:pointer" onclick="randomProblem()"><div class="num" style="font-size:22px">🎲</div><div class="label">刷一题</div></div>`;

  const vols = [...new Set(data.problems.map(p=>p.volume))];
  document.getElementById('volFilter').innerHTML = '<button class="vol-btn active" onclick="setVol(\'all\')">全部</button>' +
    vols.map(v => `<button class="vol-btn" onclick="setVol('${v.replace(/'/g,"\\'")}')">${v}</button>`).join('');

  const langs = new Set();
  data.problems.forEach(p => (p.languages||'').split('&').forEach(l => {const t=l.trim();if(t)langs.add(t)}));
  document.getElementById('langFilter').innerHTML = '<option value="all">全部语言</option>' +
    [...langs].sort().map(l => `<option value="${l}">${l}</option>`).join('');

  renderCategories();
  renderStudyPlan();
  renderTemplates();
  filterProblems();
}

function renderCategories(activeCat){
  const phases = {};
  data.categories.forEach(c => {
    const ph = c.phase || 'P5-综合';
    if(!phases[ph]) phases[ph] = [];
    phases[ph].push(c);
  });
  const phaseOrder = ['P1-基础','P2-核心','P3-进阶','P4-高阶','P5-综合'];
  const phaseNames = {'P1-基础':'1️⃣ 基础','P2-核心':'2️⃣ 核心','P3-进阶':'3️⃣ 进阶','P4-高阶':'4️⃣ 高阶','P5-综合':'5️⃣ 综合'};
  let html = `<div class="category-item${currentCategory===null?' active':''}" onclick="setCategory(null)"><span>📋 全部题目</span><span class="count">${data.problems.length}</span></div>`;
  phaseOrder.forEach(ph => {
    if(!phases[ph]) return;
    html += `<div class="phase-section"><div class="phase-header phase-${ph.replace(':','').replace('-','')}">${phaseNames[ph]||ph} <span>${phases[ph].reduce((a,c)=>a+c.count,0)}题</span></div>`;
    phases[ph].forEach(c => {
      const isActive = activeCat === c.name || currentCategory === c.name;
      html += `<div class="category-item${isActive?' active':''}" onclick="setCategory('${c.name.replace(/'/g,"\\'")}')" style="padding-left:24px"><span>${c.name}</span><span class="count">${c.count}</span></div>`;
    });
    html += '</div>';
  });
  document.getElementById('categoryList').innerHTML = html;
}

function setCategory(name){
  currentCategory = name;
  document.getElementById('currentCategory').textContent = name ? `当前: ${name}` : '';
  renderCategories(name);
  filterProblems();
}

function setVol(vol){
  currentVol = vol === 'all' ? null : vol;
  document.querySelectorAll('.vol-btn').forEach(b => b.classList.toggle('active', b.textContent===vol || (vol==='all'&&b.textContent==='全部')));
  filterProblems();
}

function filterProblems(){
  if(!data) return;
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  const score = document.getElementById('scoreFilter').value;
  const diff = document.getElementById('diffFilter').value;
  const lang = document.getElementById('langFilter').value;
  const phase = document.getElementById('phaseFilter').value;

  let filtered = data.problems.filter(p => {
    if(currentCategory && !(p.categories||[]).includes(currentCategory)) return false;
    if(currentVol && p.volume !== currentVol) return false;
    if(score !== 'all' && p.score !== parseInt(score)) return false;
    if(diff !== 'all' && p.difficulty !== diff) return false;
    if(lang !== 'all' && !(p.languages||'').includes(lang)) return false;
    if(phase !== 'all' && !(p.phase||'').startsWith(phase)) return false;
    if(q && !p.title.toLowerCase().includes(q) && !(p.volume||'').toLowerCase().includes(q) && !(p.languages||'').toLowerCase().includes(q)) return false;
    return true;
  });

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  if (currentPage >= totalPages) currentPage = totalPages - 1;
  const start = currentPage * pageSize;
  const end = Math.min(start + pageSize, filtered.length);
  const pageItems = filtered.slice(start, end);

  document.getElementById('resultCount').textContent = totalPages > 1
    ? `共 ${filtered.length} 道 (第 ${currentPage+1}/${totalPages} 页)`
    : `共 ${filtered.length} 道`;

  if(pageItems.length === 0){
    document.getElementById('problemList').innerHTML = '<div class="empty">未找到匹配的题目</div>';
    return;
  }

  let listHtml = pageItems.map(p => {
    const diffClass = {简单:'tag-easy',中等:'tag-medium',困难:'tag-hard'}[p.difficulty]||'';
    const diffEmoji = {简单:'🟢',中等:'🟡',困难:'🔴'}[p.difficulty]||'⚪';
    const volEsc = (p.volume||'').replace(/'/g,"\\'");
    const categories = (p.categories||[]).map(c => `<span class="tag" style="background:#e3f2fd;color:#1565c0;cursor:pointer" onclick="event.stopPropagation();setCategory('${c.replace(/'/g,"\\'")}')">${c}</span>`).join(' ');
    const path = encodeURIComponent(p.file_path);
    return `<div class="problem-item" onclick="showDetail('${path}')">
      <div class="problem-info">
        <div class="problem-title">${diffEmoji} ${p.title}</div>
        <div class="problem-meta">
          <span style="cursor:pointer" onclick="event.stopPropagation();setVol('${volEsc}')">${p.volume}</span>
          <span class="${diffClass}">${p.difficulty} ${p.score}分</span>
          <span style="cursor:pointer" onclick="event.stopPropagation();filterByLang('${(p.languages||'').replace(/'/g,"\\'")}')">${p.languages||''}</span>
          <span class="tag-phase">${p.phase||''}</span>
        </div>
        <div style="margin-top:3px">${categories}</div>
      </div>
    </div>`;
  }).join('');

  if (totalPages > 1) {
    let navHtml = '<div class="pagination">';
    navHtml += `<button class="page-btn" onclick="goPage(0)"${currentPage===0?' disabled':''}>◀◀</button>`;
    navHtml += `<button class="page-btn" onclick="goPage(${currentPage-1})"${currentPage===0?' disabled':''}>◀</button>`;
    const startP = Math.max(0, currentPage - 2);
    const endP = Math.min(totalPages, startP + 5);
    for (let p = startP; p < endP; p++) {
      navHtml += `<button class="page-btn${p===currentPage?' active':''}" onclick="goPage(${p})">${p+1}</button>`;
    }
    navHtml += `<button class="page-btn" onclick="goPage(${currentPage+1})"${currentPage>=totalPages-1?' disabled':''}>▶</button>`;
    navHtml += `<button class="page-btn" onclick="goPage(${totalPages-1})"${currentPage>=totalPages-1?' disabled':''}>▶▶</button>`;
    navHtml += '</div>';
    listHtml += navHtml;
  }

  document.getElementById('problemList').innerHTML = listHtml;
}

function goPage(page){
  currentPage = Math.max(0, page);
  filterProblems();
}

function filterByLang(langStr){
  const sel = document.getElementById('langFilter');
  if(!sel) return;
  const first = langStr.split('&')[0].trim();
  if(first && [...sel.options].some(o => o.value === first)){
    sel.value = first;
    currentPage = 0;
    filterProblems();
  }
}

function closeModal(){document.getElementById('modalOverlay').classList.remove('show');}
document.getElementById('modalOverlay').onclick = function(e){if(e.target===this)closeModal();};
document.addEventListener('keydown', function(e){
  if(e.key === 'Escape') closeModal();
  if(e.ctrlKey && e.key >= '1' && e.key <= '4'){
    const tabs = ['browse','exam','plan','templates'];
    switchTab(tabs[parseInt(e.key)-1]);
  }
});

function showDetail(encodedPath){
  const path = decodeURIComponent(encodedPath);
  const p = data.problems.find(x => x.file_path === path);
  if(!p) return;
  const isFav = isFavorite(encodedPath);
  document.getElementById('modalTitle').textContent = `${p.difficulty === '简单'?'🟢':p.difficulty==='中等'?'🟡':'🔴'} ${p.title}`;
  document.getElementById('modalFooter').innerHTML = `
    <button class="fav-btn${isFav?' active':''}" id="favBtn" onclick="toggleFavorite('${encodedPath}')">${isFav?'⭐':'☆'}</button>
    <span class="meta-tag">${p.volume}</span>
    <span class="meta-tag" style="background:${p.score===200?'#fce4ec':'#e8f5e9'};color:${p.score===200?'#c62828':'#2e7d32'}">${p.score}分</span>
    <span class="meta-tag" style="background:${p.difficulty==='简单'?'#e8f5e9':p.difficulty==='中等'?'#fff3e0':'#fce4ec'};color:${p.difficulty==='简单'?'#2e7d32':p.difficulty==='中等'?'#e65100':'#c62828'}">${p.difficulty}</span>
    ${(p.categories||[]).map(c => `<span class="meta-tag">${c}</span>`).join('')}
    <span style="flex:1"></span>`;
  document.getElementById('modalOverlay').classList.add('show');
  loadProblemContent(path);
  addHistory(encodedPath, p.title);
}

function randomProblem(){
  if(!data || !data.problems.length) return;
  const p = data.problems[Math.floor(Math.random() * data.problems.length)];
  showDetail(encodeURIComponent(p.file_path));
}

async function loadProblemContent(filePath){
  const container = document.getElementById('problemContent');
  container.innerHTML = '<div style="text-align:center;padding:40px;color:#999">📖 加载题目内容...</div>';
  try{
    const resp = await fetch('/api/problem-json?path=' + encodeURIComponent(filePath));
    if(!resp.ok) throw new Error('加载失败');
    const parsed = await resp.json();
    if(parsed.error){
      container.innerHTML = `<div style="text-align:center;padding:40px;color:#f44336">❌ ${parsed.error}</div>`;
      return;
    }
    renderProblemContent(parsed);
  }catch(e){
    container.innerHTML = `<div style="text-align:center;padding:40px;color:#f44336">❌ 加载失败: ${e.message}</div>`;
  }
}



function renderProblemContent(parsed){
  const container = document.getElementById('problemContent');
  if(!parsed || typeof parsed !== 'object'){
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336">❌ 无效的响应数据</div>';
    return;
  }
  const sections = parsed.sections || [];
  const codeBlocks = parsed.code_blocks || {};
  if(!sections.length && !Object.keys(codeBlocks).length){
    container.innerHTML = '<div style="text-align:center;padding:40px;color:#999">暂无内容</div>';
    return;
  }

  const typeIcons = {desc:'📋',input:'📥',output:'📤',sample:'📊',solution:'💡',note:'ℹ️'};
  let html = '';

  sections.forEach(s => {
    const icon = typeIcons[s.type]||'📄';
    let bodyHtml = formatSectionBody(s.html, s.type);
    html += `<div class="section-card ${s.type||'desc'}">
      <div class="section-header">${icon} ${s.heading}</div>
      <div class="section-body">${bodyHtml}</div>
    </div>`;
  });

  const langs = Object.keys(codeBlocks).filter(l => codeBlocks[l].length > 0);
  if(langs.length > 0){
    html += `<div class="section-card solution">
      <div class="section-header">💡 解题代码</div>
      <div class="section-body" style="padding:0">`;
    html += `<div class="lang-tabs" id="langTabs">`;
    langs.forEach((l,i) => {
      html += `<button class="lang-tab${i===0?' active':''}" onclick="switchLang('${l}',this)">${l}</button>`;
    });
    html += `</div>`;
    html += `<div class="code-container">`;
    langs.forEach((l,i) => {
      const code = codeBlocks[l].join('\n\n');
      const hlCode = highlightCode(code, l);
      const display = i === 0 ? 'block' : 'none';
      html += `<pre class="code-display" id="code-${l.replace(/[^a-zA-Z0-9]/g,'_')}" style="display:${display}"><code>${hlCode}</code></pre>`;
    });
    html += `<button class="copy-btn" onclick="copyCurrentCode(this)">📋 复制代码</button></div></div></div>`;
  }

  container.innerHTML = html;
}

function switchLang(lang, btn){
  document.querySelectorAll('.lang-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.code-container .code-display').forEach(pre => pre.style.display = 'none');
  const id = 'code-' + lang.replace(/[^a-zA-Z0-9]/g,'_');
  const el = document.getElementById(id);
  if(el) el.style.display = 'block';
}

function formatSectionBody(html, type){
  const div = document.createElement('div');
  div.innerHTML = html;
  div.querySelectorAll('script, style, link, meta, head').forEach(el => el.remove());
  div.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => el.remove());
  div.querySelectorAll('a').forEach(el => el.replaceWith(el.textContent));
  div.querySelectorAll('span').forEach(el => el.replaceWith(el.textContent));
  div.querySelectorAll('code').forEach(el => el.className = 'inline');
  div.querySelectorAll('p').forEach(el => {
    if(!el.innerHTML.trim()) el.remove();
  });
  div.querySelectorAll('pre').forEach(pre => {
    const codeLines = pre.querySelectorAll('.CodeMirror-line');
    if(codeLines.length > 0){
      const lines = Array.from(codeLines).map(el => el.textContent).join('\n');
      pre.textContent = lines;
    }
    pre.className = 'plain-code';
  });
  div.querySelectorAll('table').forEach(t => {
    t.style.width = 'auto';
    t.style.fontSize = '13px';
  });
  let result = div.innerHTML.trim();
  return result || '<p>' + div.textContent.trim().substring(0,200) + '...</p>';
}

function escapeHtml(text){
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

let examTimer = null;
let examSeconds = 0;

async function generateExam(){
  document.getElementById('examResult').style.display = 'none';
  document.getElementById('examProblems').style.display = 'block';
  document.getElementById('examCards').innerHTML = '<div style="text-align:center;padding:40px;color:#999">生成中...</div>';
  try{
    const resp = await fetch('/api/exam');
    const data = await resp.json();
    renderExam(data);
    startExamTimer();
  }catch(e){
    document.getElementById('examCards').innerHTML = `<div style="text-align:center;padding:40px;color:#f44336">生成失败: ${e.message}</div>`;
  }
}

function renderExam(data){
  const diffEmoji = {简单:'🟢',中等:'🟡',困难:'🔴'};
  const diffClass = {简单:'tag-easy',中等:'tag-medium',困难:'tag-hard'};
  const html = data.problems.map((p,i) => {
    const labels = {0:'200分题（困难）',1:'100分题（简单）',2:'100分题（中等）'};
    const colors = {0:'#fce4ec',1:'#e8f5e9',2:'#fff3e0'};
    const path = encodeURIComponent(p.file_path);
    const eid = `examContent${i}`;
    return `<div style="background:white;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;border-top:3px solid ${colors[i]}">
      <div style="padding:10px 14px;background:#fafafa;font-size:12px;font-weight:600;color:#666;display:flex;justify-content:space-between">
        <span>第 ${i+1} 题</span>
        <span style="background:${colors[i]};padding:0 8px;border-radius:4px">${labels[i]}</span>
      </div>
      <div style="padding:14px">
        <div style="font-size:15px;font-weight:500;color:#1a0dab;margin-bottom:6px">${diffEmoji[p.difficulty]||''} ${p.title}</div>
        <div style="font-size:12px;color:#999;margin-bottom:8px">
          <span>${p.volume}</span>
          <span class="${diffClass[p.difficulty]||''}" style="padding:1px 6px;border-radius:3px;margin-left:6px">${p.score}分 · ${p.difficulty}</span>
        </div>
        <div style="margin-bottom:8px">${(p.categories||[]).map(c => `<span class="tag" style="background:#e3f2fd;color:#1565c0;font-size:11px;padding:1px 6px;border-radius:3px;margin-right:4px">${c}</span>`).join('')}</div>
        <span class="exam-toggle" id="examToggle${i}" onclick="toggleExamContent('${path}',${i})">📖 展开题解</span>
        <a href="javascript:showDetail('${path}')" style="font-size:12px;color:#1a73e8;text-decoration:none;padding:4px 10px;border:1px solid #1a73e8;border-radius:4px;display:inline-block;margin-left:6px">📄 新窗口</a>
        <div class="exam-inline" id="${eid}"></div>
      </div>
    </div>`;
  }).join('');
  document.getElementById('examCards').innerHTML = html;
}

async function toggleExamContent(encodedPath, idx){
  const container = document.getElementById(`examContent${idx}`);
  const toggle = document.getElementById(`examToggle${idx}`);
  if (!container || !toggle) return;
  if (container.classList.contains('show')) {
    container.classList.remove('show');
    container.innerHTML = '';
    toggle.textContent = '📖 展开题解';
    toggle.classList.remove('active');
    return;
  }
  if (!container.innerHTML) {
    toggle.textContent = '⏳ 加载中...';
    try {
      const resp = await fetch('/api/problem-json?path=' + encodeURIComponent(decodeURIComponent(encodedPath)));
      const parsed = await resp.json();
      if (parsed.error) { container.innerHTML = `<div style="color:#f44336">${parsed.error}</div>`; return; }
      container.innerHTML = renderExamInlineContent(parsed);
    } catch(e) { container.innerHTML = `<div style="color:#f44336">加载失败</div>`; return; }
  }
  container.classList.add('show');
  toggle.textContent = '📕 收起题解';
  toggle.classList.add('active');
}

function renderExamInlineContent(parsed){
  const sections = parsed.sections || [];
  const codeBlocks = parsed.code_blocks || {};
  const typeIcons = {desc:'📋',input:'📥',output:'📤',sample:'📊',solution:'💡',note:'ℹ️'};
  let html = '';
  sections.forEach(s => {
    const icon = typeIcons[s.type]||'📄';
    const body = (s.html||'').replace(/<script[\s\S]*?<\/script>/gi,'').replace(/<style[\s\S]*?<\/style>/gi,'');
    html += `<div class="section-card ${s.type||'desc'}" style="margin-bottom:6px">
      <div class="section-header">${icon} ${s.heading}</div>
      <div class="section-body">${body}</div>
    </div>`;
  });
  const langs = Object.keys(codeBlocks).filter(l => codeBlocks[l].length > 0);
  if (langs.length > 0) {
    html += `<div class="lang-tabs" style="font-size:11px">`;
    langs.forEach((l,i) => {
      html += `<span class="lang-tab${i===0?' active':''}" onclick="this.parentNode.querySelectorAll('.lang-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');this.closest('.exam-inline').querySelectorAll('.exam-code').forEach(p=>p.style.display='none');this.closest('.exam-inline').querySelector('#examCode-${l.replace(/[^a-zA-Z0-9]/g,'_')}').style.display='block'">${l}</span>`;
    });
    html += `</div>`;
    langs.forEach((l,i) => {
      const code = codeBlocks[l].join('\n\n');
      const hlCode = highlightCode(code, l);
      html += `<pre class="code-display exam-code" id="examCode-${l.replace(/[^a-zA-Z0-9]/g,'_')}" style="display:${i===0?'block':'none'};background:#1e1e2e;color:#cdd6f4;padding:10px 14px;font-family:'JetBrainsMono Nerd Font',Consolas,monospace;font-size:17px;line-height:1.5;overflow-x:auto;margin:0;white-space:pre;tab-size:4"><code>${hlCode}</code></pre>`;
      html += `<button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('examCode-${l.replace(/[^a-zA-Z0-9]/g,'_')}').textContent).then(()=>{this.textContent='✅ 已复制';this.classList.add('copied');setTimeout(()=>{this.textContent='📋 复制';this.classList.remove('copied')},2000)}).catch(()=>{this.textContent='❌ 失败'})">📋 复制</button>`;
    });
  }
  return html || '<div style="color:#999">暂无内容</div>';
}

function startExamTimer(){
  if(examTimer) clearInterval(examTimer);
  examSeconds = 0;
  document.getElementById('examTimer').style.display = 'block';
  examTimer = setInterval(() => {
    examSeconds++;
    const m = String(Math.floor(examSeconds/60)).padStart(2,'0');
    const s = String(examSeconds%60).padStart(2,'0');
    document.getElementById('examTimer').textContent = `⏱️ ${m}:${s}`;
  }, 1000);
}

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelector(`.tab[onclick*="'${name}'"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

function renderStudyPlan(){
  if(!data) return;
  const phases = {};
  data.problems.forEach(p => {
    (p.categories||[]).forEach(c => {
      if(!phases[c]) phases[c] = {easy:0,medium:0,hard:0,total:0};
      phases[c][p.difficulty] = (phases[c][p.difficulty]||0) + 1;
      phases[c].total++;
    });
  });

  const catPhase = {};
  data.categories.forEach(c => catPhase[c.name] = c.phase || 'P5-综合');

  const phaseOrder = ['P1-基础','P2-核心','P3-进阶','P4-高阶','P5-综合'];
  const phaseNames = {'P1-基础':'1️⃣ 基础阶段 — 数据结构与基础算法','P2-核心':'2️⃣ 核心阶段 — 算法思维培养','P3-进阶':'3️⃣ 进阶阶段 — 复杂算法训练','P4-高阶':'4️⃣ 高阶阶段 — 综合应用','P5-综合':'5️⃣ 综合阶段 — 查漏补缺'};
  const phaseTips = {'P1-基础':'先掌握数组/字符串/哈希表/排序等基础数据结构，练习模拟题建立编程手感',
    'P2-核心':'重点训练双指针/滑动窗口/二分查找/栈队列等核心算法模式',
    'P3-进阶':'攻克树/回溯/贪心/区间问题，培养递归思维和最优子结构意识',
    'P4-高阶':'主攻动态规划和图论，这是面试重点也是难点',
    'P5-综合':'刷历年真题，查漏补缺，限时训练'};

  let html = '<div style="margin-bottom:16px;padding:12px 16px;background:#e3f2fd;border-radius:8px;font-size:13px">🔑 <b>推荐刷题顺序</b>：按 P1 → P5 循序渐进的顺序刷题。建议每天 3-5 题，先看模板再做题，做完总结。</div>';
  phaseOrder.forEach(ph => {
    const cats = data.categories.filter(c => (c.phase||'P5-综合') === ph).sort((a,b)=>b.count-a.count);
    if(cats.length === 0) return;
    const total = cats.reduce((a,c)=>a+c.count,0);
    html += `<div class="plan-phase"><div class="p-header phase-${ph.replace(':','').replace('-','')}">${phaseNames[ph]||ph}<span>${total}题</span></div><div class="p-body"><div style="font-size:12px;color:#666;margin-bottom:8px">💡 ${phaseTips[ph]||''}</div>`;
    cats.forEach(c => {
      const d = phases[c.name]||{easy:0,medium:0,hard:0};
      const diffs = [];
      if(d.easy>0) diffs.push(`<span class="diff-dot diff-easy"></span>${d.easy}`);
      if(d.medium>0) diffs.push(`<span class="diff-dot diff-medium"></span>${d.medium}`);
      if(d.hard>0) diffs.push(`<span class="diff-dot diff-hard"></span>${d.hard}`);
      html += `<div class="plan-cat"><span><b>${c.name}</b> (${c.count}题)</span><span class="cat-diffs">${diffs.join(' ')}</span></div>`;
    });
    html += '</div></div>';
  });
  document.getElementById('studyPlan').innerHTML = html;
}

function renderTemplates(){
  if(!data) return;
  const html = '<div style="margin-bottom:16px;padding:12px 16px;background:#e3f2fd;border-radius:8px;font-size:13px">📝 各题型通用解题模板，建议先看模板理解核心思路，再刷对应类型题目</div>' +
    '<div class="template-section">' +
    data.templates.map(t => {
      const body = t.template ? t.template.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>').replace(/```/g,'') : '(暂无)';
      // Format body nicely
      let formatted = '';
      const lines = t.template.split('\n');
      let inCode = false;
      lines.forEach(line => {
        if(line.trimStart().startsWith('```')) { inCode = !inCode; return; }
        if(inCode) formatted += `<pre><code>${line.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</code></pre>`;
        else if(line.trim()) formatted += `<div>${line.replace(/\*\*(.*?)\*\*/g,'<b>$1</b>')}</div>`;
      });
      return `<div class="template-card">
        <div class="t-header"><span>${t.name}</span><span class="tag tag-phase">${t.phase||''}</span></div>
        <div class="t-body">${formatted || '(暂无模板)'}</div>
      </div>`;
    }).join('') + '</div>';
  document.getElementById('templateList').innerHTML = html;
}

// ===== Syntax Highlighting =====
function codeLangToHighlight(lang) {
  const m = {'c++':'cpp','c':'c','c#':'csharp','java':'java','python':'python','javascript':'javascript','js':'javascript','go':'go','golang':'go','typescript':'typescript','ts':'typescript','JAVA':'java','C++':'cpp','Go':'go','C':'c','C#':'csharp','Java':'java','Python':'python','JavaScript':'javascript'};
  return m[lang]||'';
}
function highlightCode(code, lang){
  const hl = codeLangToHighlight(lang);
  const kwSets = {
    'javascript':'async|await|break|case|catch|class|const|continue|debugger|default|delete|do|else|enum|export|extends|false|finally|for|function|if|import|in|instanceof|let|new|null|of|return|static|super|switch|this|throw|true|try|typeof|undefined|var|void|while|with|yield',
    'typescript':'abstract|any|as|async|await|boolean|break|case|catch|class|const|continue|debugger|declare|default|delete|do|else|enum|export|extends|false|finally|for|function|if|implements|import|in|instanceof|interface|let|module|namespace|never|new|null|number|of|private|protected|public|readonly|return|static|string|super|switch|this|throw|true|try|type|typeof|undefined|unknown|var|void|while|with|yield',
    'java':'abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|extends|false|final|finally|float|for|goto|if|implements|import|instanceof|int|interface|long|native|new|null|package|private|protected|public|return|short|static|strictfp|super|switch|synchronized|this|throw|throws|transient|true|try|void|volatile|while|var',
    'cpp':'auto|bool|break|case|catch|char|class|const|constexpr|continue|default|delete|do|double|else|enum|explicit|export|extern|false|float|for|friend|goto|if|inline|int|long|mutable|namespace|new|noexcept|nullptr|operator|override|private|protected|public|register|return|short|signed|sizeof|static|static_assert|struct|switch|template|this|throw|true|try|typedef|typeid|typename|union|unsigned|using|virtual|void|volatile|while',
    'c':'auto|break|case|char|const|continue|default|do|double|else|enum|extern|false|float|for|goto|if|inline|int|long|register|return|short|signed|sizeof|static|struct|switch|true|typedef|union|unsigned|void|volatile|while',
    'csharp':'abstract|as|async|await|base|bool|break|byte|case|catch|char|checked|class|const|continue|decimal|default|delegate|do|double|else|enum|event|explicit|extern|false|finally|fixed|float|for|foreach|goto|if|implicit|in|init|int|interface|internal|is|lock|long|namespace|new|null|object|operator|out|override|params|private|protected|public|readonly|record|ref|return|sbyte|sealed|short|sizeof|stackalloc|static|string|struct|switch|this|throw|true|try|typeof|uint|ulong|unchecked|unsafe|ushort|using|var|virtual|void|volatile|while',
    'python':'False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield',
    'go':'break|case|chan|const|continue|default|defer|else|fallthrough|for|func|go|goto|if|import|interface|map|package|range|return|select|struct|switch|type|var|true|false|nil'
  };
  const kw = kwSets[hl]||'';
  const kwRe = kw ? new RegExp('\\b('+kw+')\\b','g') : null;
  let s = escapeHtml(code);
  const isPy = hl==='python';
  const isCLike = ['cpp','c','csharp','java','javascript','typescript','go'].includes(hl);

  const cmts = [];
  let cmtIdx = 0;
  if (isCLike) s = s.replace(/\/\*[\s\S]*?\*\//g, m => { const p = `\x00C${cmtIdx}\x00`; cmts.push(m); cmtIdx++; return p; });
  if (isPy) s = s.replace(/(?:'''[\s\S]*?'''|"""[\s\S]*?""")/g, m => { const p = `\x00C${cmtIdx}\x00`; cmts.push(m); cmtIdx++; return p; });

  const lines = s.split('\n');
  let result = lines.map(line => {
    if(isPy) line = line.replace(/(#.*)$/g,'<span class="cmt">$1</span>');
    else if(isCLike) line = line.replace(/(\/\/.*)$/g,'<span class="cmt">$1</span>');
    const _html = [];
    line = line.replace(/<[^>]*>/g, m => { const p = `\x00T${_html.length}\x00`; _html.push(m); return p; });
    if(kwRe) line = line.replace(kwRe,'<span class="kw">$1</span>');
    line = line.replace(/\b(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b/g,'<span class="num">$1</span>');
    _html.forEach((t, i) => { line = line.replace(`\x00T${i}\x00`, t); });
    return `<span class="line">${line}</span>`;
  }).join('\n');

  for (let i = 0; i < cmts.length; i++) {
    result = result.replace(`\x00C${i}\x00`, `<span class="cmt">${cmts[i]}</span>`);
  }
  return result;
}

// ===== Copy Button =====
function copyCurrentCode(btn){
  const visible = document.querySelector('.code-container > .code-display:not([style*="none"]), .code-container > .code-display:first-child');
  if(!visible) return;
  const text = visible.textContent;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✅ 已复制'; btn.classList.add('copied');
    setTimeout(()=>{btn.textContent = '📋 复制代码'; btn.classList.remove('copied');},2000);
  }).catch(()=>{btn.textContent = '❌ 复制失败';});
}

// ===== Favorites =====
function getFavorites(){ try{return JSON.parse(localStorage.getItem('kb_favorites')||'[]')}catch(e){return[]} }
function saveFavorites(f){ localStorage.setItem('kb_favorites',JSON.stringify(f)) }
function toggleFavorite(encodedPath){
  const cp = decodeURIComponent(encodedPath);
  let favs = getFavorites();
  const idx = favs.indexOf(cp);
  if(idx>=0) favs.splice(idx,1); else favs.push(cp);
  saveFavorites(favs);
  renderFavorites();
  const btn = document.getElementById('favBtn');
  if(btn) btn.classList.toggle('active', idx<0);
}
function isFavorite(encodedPath){ return getFavorites().includes(decodeURIComponent(encodedPath)) }
function getFavoriteProblems(){ const f=getFavorites(); return data?data.problems.filter(p=>f.includes(p.file_path)):[] }
function renderFavorites(){
  const sec = document.getElementById('favSection'), list = document.getElementById('favList');
  const probs = getFavoriteProblems();
  if(!probs.length){sec.style.display='none';return}
  sec.style.display='block';
  list.innerHTML = probs.map(p => {
    const ep = encodeURIComponent(p.file_path);
    return `<div class="fav-item" onclick="showDetail('${ep}')"><span class="fav-star">⭐</span><span class="fav-title">${escapeHtml(p.title)}</span></div>`;
  }).join('');
}

// ===== History =====
function getHistory(){ try{return JSON.parse(localStorage.getItem('kb_history')||'[]')}catch(e){return[]} }
function saveHistory(h){ localStorage.setItem('kb_history',JSON.stringify(h)) }
function addHistory(encodedPath, title){
  const cp = decodeURIComponent(encodedPath);
  let h = getHistory().filter(x => x.path!==cp);
  h.unshift({path:cp,title:title,time:Date.now()});
  if(h.length>20) h=h.slice(0,20);
  saveHistory(h); renderHistory();
}
function renderHistory(){
  const panel = document.getElementById('historyPanel'), list = document.getElementById('historyList');
  const h = getHistory();
  if(!h.length){panel.style.display='none';return}
  panel.style.display='block';
  list.innerHTML = h.map(x => {
    const ep = encodeURIComponent(x.path);
    const t = x.title || x.path.split('/').pop().replace('.html','');
    let ds = '刚刚'; const d=Date.now()-x.time;
    if(d>=60000){const m=Math.floor(d/60000);ds=m>=60?Math.floor(m/60)+'小时前':m+'分钟前'}
    return `<div class="history-item" onclick="showDetail('${ep}')"><span class="h-title">${escapeHtml(t)}</span><span class="h-time">${ds}</span></div>`;
  }).join('');
}

loadData();
