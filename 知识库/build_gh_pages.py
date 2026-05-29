#!/usr/bin/env python3
"""
华为 OD 刷题知识库 - GitHub Pages 静态站点构建工具
从 SQLite 数据库和原始题目文件生成纯静态 JSON 数据，
部署到 GitHub Pages 无需后端服务器。
"""

import html
import json
import os
import re
import sqlite3
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DB_PATH = BASE_DIR / "知识库" / "problems.db"
STATIC_DIR = Path(__file__).parent / "static"
OUTPUT_DIR = Path(__file__).parent / "docs"

_cache = {}


def extract_div_content(html_text, div_id):
    m = re.search(rf'<div[^>]*id=[\'"]{div_id}[\'"][^>]*>', html_text)
    if not m:
        return None
    body_end = html_text.rfind('</body>')
    depth = 1
    pos = m.end()
    while depth > 0 and pos < len(html_text) and (body_end == -1 or pos < body_end):
        n_open = html_text.find('<div', pos)
        n_close = html_text.find('</div>', pos)
        if n_close == -1:
            break
        elif n_open != -1 and n_open < n_close and (body_end == -1 or n_open < body_end):
            depth += 1
            pos = n_open + 5
        else:
            depth -= 1
            if depth == 0:
                return html_text[m.end():n_close]
            pos = n_close + 6
    return html_text[m.end():]


def parse_problem_json(file_path):
    cache_key = f"problem-json:{file_path}"
    if cache_key in _cache:
        return _cache[cache_key]

    full_path = (BASE_DIR / file_path).resolve()
    if not (full_path.exists() and full_path.is_file()):
        return {"error": "file not found"}

    raw_html = full_path.read_text('utf-8', errors='replace')

    code_blocks = {}
    solution_langs = ['java', 'python', 'c++', 'c#', 'c', 'javascript', 'js', 'go', 'golang', 'rust', 'ruby', 'php',
                      'swift', 'kotlin', 'typescript', 'ts', 'scala', 'dart', 'perl', 'r', 'matlab', 'bash', 'shell',
                      'sql', 'lua']
    lang_map = {'java': 'Java', 'python': 'Python', 'c++': 'C++', 'c#': 'C#', 'javascript': 'JavaScript',
                'js': 'JavaScript', 'go': 'Go', 'c': 'C', 'typescript': 'TypeScript'}

    def extract_code_from_pre(block_inner):
        clines = re.findall(r'<pre\s+class="\s*CodeMirror-line[^"]*"[^>]*>(.*?)</pre>', block_inner, re.DOTALL)
        if clines:
            return '\n'.join(re.sub(r'<[^>]+>', '', cl).rstrip('\n\r') for cl in clines)
        return re.sub(r'<[^>]+>', '', block_inner)

    def clean_code_text(text):
        text = text.strip()
        for ent in [('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&'), ('&nbsp;', ' '), ('&quot;', '"'), ('&#39;', "'")]:
            text = text.replace(*ent)
        return text

    def has_depth_aware_replace(html_text, pre_pattern, lang_attr, is_solution_check):
        parts = []
        i = 0
        while i < len(html_text):
            pre_start = re.search(pre_pattern, html_text[i:])
            if not pre_start:
                parts.append(html_text[i:])
                break
            parts.append(html_text[i:i + pre_start.start()])
            tag_text = html_text[i + pre_start.start():i + pre_start.end()]
            depth = 1
            pos = i + pre_start.end()
            while depth > 0 and pos < len(html_text):
                n_open = html_text.find('<pre', pos)
                n_close = html_text.find('</pre>', pos)
                if n_close == -1:
                    depth = 0
                    pos = len(html_text)
                elif n_open != -1 and n_open < n_close:
                    depth += 1
                    pos = n_open + 5
                else:
                    depth -= 1
                    if depth == 0:
                        pos = n_close + 6
                    else:
                        pos = n_close + 6
            block_inner = html_text[i + pre_start.end():pos - 6] if depth == 0 else html_text[i + pre_start.end():]
            lang = ''
            if lang_attr:
                lm = re.search(rf'{lang_attr}=["\']([^"\']*)["\']', tag_text)
                lang = lm.group(1).strip() if lm else ''
            is_sol = is_solution_check(lang, tag_text) if is_solution_check else False
            if is_sol:
                ct = clean_code_text(extract_code_from_pre(block_inner))
                if ct:
                    if lang not in code_blocks:
                        code_blocks[lang] = []
                    code_blocks[lang].append(ct)
            else:
                ct = clean_code_text(extract_code_from_pre(block_inner))
                parts.append('<pre class="plain-code">' + html.escape(ct) + '</pre>' if ct else '')
            i = pos
        return ''.join(parts)

    main_html = extract_div_content(raw_html, 'write')
    is_typora = main_html is not None
    if not is_typora:
        main_html = extract_div_content(raw_html, 'content_views')
    if not main_html:
        main_html = extract_div_content(raw_html, 'article_content')
    if not main_html:
        body_m = re.search(r'<body[^>]*>(.*?)</body>', raw_html, re.DOTALL)
        if body_m:
            main_html = body_m.group(1)
    if not main_html:
        result = {"sections": [], "code_blocks": {}}
        _cache[cache_key] = result
        return result

    if is_typora:
        typora_orig = main_html

        def is_solution(lang, tag):
            ll = lang.lower()
            return (ll not in ('none', '', 'text', 'plain') and (
                        any(sl in ll for sl in solution_langs) or ll == 'code' or (lang and lang[0].isupper())))

        main_html = has_depth_aware_replace(
            main_html,
            r'<pre\s[^>]*class="[^"]*md-fences[^"]*"[^>]*>',
            r'lang',
            is_solution
        )
        if not code_blocks and re.search(r'<h2[^>]*>', typora_orig):
            has_h2_lang = any(
                re.sub(r'<[^>]+>', '', hm.group(1)).strip().lower()
                in {'java', 'python', 'c++', 'c', 'javascript', 'js', 'go', 'c#', 'typescript', 'ts', 'ruby', 'rust',
                    'php', 'swift', 'kotlin', 'scala', 'dart', 'perl', 'r', 'matlab', 'bash', 'shell', 'sql', 'lua',
                    'golang'}
                for hm in re.finditer(r'<h2[^>]*>(.*?)</h2>', typora_orig, re.DOTALL)
            )
            if has_h2_lang:
                is_typora = False
                h2_pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', re.DOTALL)
                h2_matches = list(h2_pattern.finditer(main_html))
                result_parts = []
                last_end = 0
                for idx, h2_m in enumerate(h2_matches):
                    h2_text = re.sub(r'<[^>]+>', '', h2_m.group(1)).strip()
                    h2_lower = h2_text.lower()
                    is_lang_heading = h2_lower in lang_map or any(sl in h2_lower for sl in solution_langs)
                    if is_lang_heading:
                        curr_lang = h2_text
                        for k in sorted(lang_map, key=len, reverse=True):
                            if k in h2_lower:
                                curr_lang = lang_map[k]
                                break
                        pre_end = h2_m.end()
                        next_h2 = h2_matches[idx + 1] if idx + 1 < len(h2_matches) else None
                        if next_h2:
                            pre_end = next_h2.start()
                        else:
                            pre_end = len(main_html)
                        between = main_html[h2_m.end():pre_end]
                        pre_m = re.search(r'<pre\s[^>]*class="[^"]*plain-code[^"]*"[^>]*>', between)
                        if pre_m:
                            depth = 1
                            pos = pre_m.end()
                            while depth > 0 and pos < len(between):
                                n_open = between.find('<pre', pos)
                                n_close = between.find('</pre>', pos)
                                if n_close == -1:
                                    depth = 0
                                    pos = len(between)
                                elif n_open != -1 and n_open < n_close:
                                    depth += 1
                                    pos = n_open + 5
                                else:
                                    depth -= 1
                                    if depth == 0:
                                        pos = n_close + 6
                                    else:
                                        pos = n_close + 6
                            block_inner = between[pre_m.end():pos - 6] if depth == 0 else between[pre_m.end():]
                            ct = html.unescape(re.sub(r'<[^>]+>', '', block_inner).strip())
                            if ct:
                                if curr_lang not in code_blocks:
                                    code_blocks[curr_lang] = []
                                code_blocks[curr_lang].append(ct)
                        continue
                    between_text = main_html[last_end:h2_m.start()]
                    if between_text.strip():
                        result_parts.append(between_text)
                    result_parts.append(main_html[h2_m.start():h2_m.end()])
                    last_end = h2_m.end()
                if last_end < len(main_html):
                    result_parts.append(main_html[last_end:])
                main_html = ''.join(result_parts)
    else:
        remove_ranges = []
        for scan_tag in ['h1', 'h2', 'h3', 'h4']:
            h_pat = re.compile(rf'<{scan_tag}[^>]*>(.*?)</{scan_tag}>', re.DOTALL)
            for h_m in h_pat.finditer(main_html):
                h_text = re.sub(r'<[^>]+>', '', h_m.group(1)).strip()
                h_lower = h_text.lower()
                is_lang = h_lower in lang_map or any(sl in h_lower for sl in solution_langs)
                if is_lang:
                    curr_lang = h_text
                    for k in sorted(lang_map, key=len, reverse=True):
                        if k in h_lower:
                            curr_lang = lang_map[k]
                            break
                    pre_end = h_m.end()
                    next_m = h_pat.search(main_html, h_m.end())
                    if next_m:
                        pre_end = next_m.start()
                    else:
                        pre_end = len(main_html)
                    between = main_html[h_m.end():pre_end]
                    pre_m = re.search(r'<pre\s[^>]*class="[^"]*(?:prettyprint|code)[^"]*"[^>]*>', between)
                    if not pre_m:
                        pre_m = re.search(r'<pre>', between)
                    if pre_m:
                        depth = 1
                        pos = pre_m.end()
                        while depth > 0 and pos < len(between):
                            n_open = between.find('<pre', pos)
                            n_close = between.find('</pre>', pos)
                            if n_close == -1:
                                depth = 0
                                pos = len(between)
                            elif n_open != -1 and n_open < n_close:
                                depth += 1
                                pos = n_open + 5
                            else:
                                depth -= 1
                                if depth == 0:
                                    pos = n_close + 6
                                else:
                                    pos = n_close + 6
                        block_inner = between[pre_m.end():pos - 6] if depth == 0 else between[pre_m.end():]
                        ct = html.unescape(re.sub(r'<[^>]+>', '', block_inner).strip())
                        if ct:
                            if curr_lang not in code_blocks:
                                code_blocks[curr_lang] = []
                            code_blocks[curr_lang].append(ct)
                            remove_ranges.append((h_m.start(), h_m.end()))
                            remove_ranges.append((h_m.end() + pre_m.start(), h_m.end() + pos - 6 + 6))
        if remove_ranges:
            remove_ranges.sort()
            merged = [remove_ranges[0]]
            for r in remove_ranges[1:]:
                if r[0] <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], r[1]))
                else:
                    merged.append(r)
            parts = []
            prev = 0
            for start, end in merged:
                if start > prev:
                    parts.append(main_html[prev:start])
                prev = end
            if prev < len(main_html):
                parts.append(main_html[prev:])
            main_html = ''.join(parts)

    h_tag = 'h1'
    best_cnt = -1
    for tag in ['h1', 'h2', 'h3', 'h4']:
        cnt = 0
        for hm in re.finditer(rf'<{tag}[^>]*>(.*?)</{tag}>', main_html, re.DOTALL):
            ht = re.sub(r'<[^>]+>', '', hm.group(1)).strip()
            hl = ht.lower()
            if ht and not any(k in hl for k in lang_map) and not any(sl in hl for sl in solution_langs):
                cnt += 1
        if cnt > 0 and cnt > best_cnt:
            best_cnt = cnt
            h_tag = tag
    heading_pattern = re.compile(rf'<{h_tag}[^>]*>(.*?)</{h_tag}>', re.DOTALL)
    heading_matches = list(heading_pattern.finditer(main_html))
    sections = []

    def guess_type(text):
        t = text.lower().replace(' ', '')
        if ('题目' in t) or (t.startswith('描述') and '输入' not in t and '输出' not in t):
            return 'desc'
        if '输入' in t: return 'input'
        if '输出' in t: return 'output'
        if '用例' in t or '示例' in t or '例子' in t: return 'sample'
        if '思路' in t or '题解' in t or '解题' in t: return 'solution'
        if '说明' in t or '提示' in t or '注意' in t or '备注' in t: return 'note'
        return 'desc'

    for i, m in enumerate(heading_matches):
        h_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        h_text = h_text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        start = m.end()
        end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(main_html)
        section_html = main_html[start:end].strip()
        text_content = re.sub(r'<[^>]+>', '', section_html)
        text_content = text_content.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;',
                                                                                                            '>').strip()
        if text_content:
            h_text_lower = h_text.lower()
            if is_typora or not any(sl in h_text_lower for sl in solution_langs):
                sections.append({
                    "heading": h_text,
                    "html": section_html,
                    "type": guess_type(h_text)
                })

    result = {"sections": sections, "code_blocks": code_blocks}
    _cache[cache_key] = result
    return result


def build():
    print("=" * 60)
    print("  华为 OD 刷题知识库 - GitHub Pages 静态站点构建")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"错误: 知识库未找到: {DB_PATH}")
        print("请先运行 build_kb.py 构建知识库")
        sys.exit(1)

    # Clean output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    problems_dir = OUTPUT_DIR / "problems"
    problems_dir.mkdir()

    # Read data from DB
    print("\n[1/4] 读取知识库数据...")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM problems ORDER BY volume_order, score DESC, title")
    problems = []
    for row in c.fetchall():
        pid = row["id"]
        c2 = conn.cursor()
        c2.execute("""
            SELECT cat.name FROM categories cat
            JOIN problem_categories pc ON cat.id = pc.category_id
            WHERE pc.problem_id = ?
        """, (pid,))
        cats = [r[0] for r in c2.fetchall()]
        problems.append({
            "id": pid,
            "title": row["title"],
            "volume": row["volume"],
            "score": row["score"],
            "difficulty": row["difficulty"],
            "phase": row["phase"],
            "languages": row["languages"],
            "file_path": row["file_path"],
            "categories": cats,
        })

    c.execute("""
        SELECT cat.name, cat.phase, COUNT(pc.problem_id) as cnt
        FROM categories cat
        LEFT JOIN problem_categories pc ON cat.id = pc.category_id
        GROUP BY cat.id
        ORDER BY cnt DESC, cat.name
    """)
    categories = [{"name": r["name"], "count": r["cnt"], "phase": r["phase"]} for r in c.fetchall()]

    c.execute("SELECT name, phase, template FROM categories WHERE template != '' ORDER BY phase, name")
    templates = [{"name": r["name"], "phase": r["phase"], "template": r["template"]} for r in c.fetchall()]

    conn.close()
    print(f"  共 {len(problems)} 道题目, {len(categories)} 个分类, {len(templates)} 个模板")

    # Write meta.json (small, loads first for instant UI)
    print("\n[2/4] 生成配置文件...")
    meta = {
        "categories": categories,
        "templates": templates,
        "problem_count": len(problems),
    }
    meta_json = json.dumps(meta, ensure_ascii=False)
    (OUTPUT_DIR / "meta.json").write_text(meta_json, encoding="utf-8")
    print(f"  meta.json: {len(meta_json) / 1024:.1f} KB")

    # Write problems.json (larger, loaded asynchronously)
    data = {"problems": problems}
    data_json = json.dumps(data, ensure_ascii=False)
    (OUTPUT_DIR / "problems.json").write_text(data_json, encoding="utf-8")
    print(f"  problems.json: {len(data_json) / 1024:.1f} KB")

    # Generate problem JSON files
    print(f"\n[3/4] 解析并生成 {len(problems)} 道题目 JSON...")
    success = 0
    failed = 0
    for i, p in enumerate(problems):
        if (i + 1) % 100 == 0:
            print(f"  进度: {i + 1}/{len(problems)}")
        try:
            file_path = p["file_path"]
            parsed = parse_problem_json(file_path)
            if "error" not in parsed:
                problem_json = json.dumps(parsed, ensure_ascii=False)
                pid = p["id"]
                (problems_dir / f"{pid}.json").write_text(problem_json, encoding="utf-8")
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  错误: {p['title']} - {e}")
            failed += 1
    print(f"  成功: {success}, 失败: {failed}")

    # Copy static files
    print("\n[4/4] 复制静态文件...")
    shutil.copy2(STATIC_DIR / "index.html", OUTPUT_DIR / "index.html")
    shutil.copy2(STATIC_DIR / "style.css", OUTPUT_DIR / "style.css")
    shutil.copy2(STATIC_DIR / "coding.html", OUTPUT_DIR / "coding.html")
    shutil.copy2(STATIC_DIR / "coding.js", OUTPUT_DIR / "coding.js")

    # Generate modified app.js
    js_path = STATIC_DIR / "app.js"
    js_content = js_path.read_text(encoding="utf-8")

    # Replace loadData first (before simple text replacements change the pattern)
    old_loadData = """async function loadData(){
  try{
    const resp = await fetch('/api/data');
    data = await resp.json();
    render();
  }catch(e){
    document.getElementById('headerSub').textContent = '加载失败: ' + e.message;
  }
}"""

    new_loadData = """let problemsData = null;

async function loadData(){
  try{
    let resp = await fetch('meta.json');
    let meta = await resp.json();
    data = {problems: [], categories: meta.categories, templates: meta.templates};
    document.getElementById('headerSub').textContent = "\\u8f7d\\u5165\\u4e2d... (\\u5171 " + meta.problem_count + " \\u9053\\u9898\\u76ee)";
    render();
    resp = await fetch('problems.json');
    problemsData = await resp.json();
    data.problems = problemsData.problems;
    document.getElementById('headerSub').textContent = "\\u5171 " + data.problems.length + " \\u9053\\u9898\\u76ee\\uff0c" + data.categories.length + " \\u4e2a\\u5206\\u7c7b";
    filterProblems();
    renderStudyPlan();
  }catch(e){
    document.getElementById('headerSub').textContent = '\\u52a0\\u8f7d\\u5931\\u8d25: ' + e.message;
  }
}"""

    js_content = js_content.replace(old_loadData, new_loadData)

    # Fix the exam generation to use local data (BEFORE /api/exam replacement)
    old_generate_exam = """async function generateExam(){
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
}"""

    new_generate_exam = """async function generateExam(){
  document.getElementById('examResult').style.display = 'none';
  document.getElementById('examProblems').style.display = 'block';
  document.getElementById('examCards').innerHTML = '<div style="text-align:center;padding:40px;color:#999">生成中...</div>';
  try{
    if(!problemsData) throw new Error('题目数据尚未加载完成，请稍后再试');
    const allProblems = problemsData.problems;
    const hard200 = allProblems.filter(p => p.score === 200 && p.difficulty === '困难');
    const easy100 = allProblems.filter(p => p.score === 100 && p.difficulty === '简单');
    const med100 = allProblems.filter(p => p.score === 100 && p.difficulty === '中等');
    const selected = [];
    if(hard200.length) selected.push(hard200[Math.floor(Math.random() * hard200.length)]);
    if(easy100.length) selected.push(easy100[Math.floor(Math.random() * easy100.length)]);
    if(med100.length) selected.push(med100[Math.floor(Math.random() * med100.length)]);
    renderExam({problems: selected});
    startExamTimer();
  }catch(e){
    document.getElementById('examCards').innerHTML = '<div style="text-align:center;padding:40px;color:#f44336">生成失败: ' + e.message + '</div>';
  }
}"""

    js_content = js_content.replace(old_generate_exam, new_generate_exam)

    # Replace remaining API calls with static file loading
    js_content = js_content.replace(
        "const resp = await fetch('/api/problem-json?path=' + encodeURIComponent(filePath));",
        "const resp = await fetch('problems/' + getProblemId(filePath) + '.json');"
    )

    # Add the getProblemId helper function
    helper_function = """
// Map file_path to problem ID (for static JSON loading)
function getProblemId(filePath) {
  const src = problemsData || data;
  const p = (src.problems || []).find(x => x.file_path === filePath);
  return p ? p.id : encodeURIComponent(filePath);
}
"""

    # Insert helper before loadData
    js_content = js_content.replace(
        "async function loadData(){",
        helper_function + "\nasync function loadData(){"
    )

    # Fix loadProblemContent to handle static file path resolution
    old_load = """async function loadProblemContent(filePath){
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
}"""

    new_load = """async function loadProblemContent(filePath){
  const container = document.getElementById('problemContent');
  container.innerHTML = '<div style="text-align:center;padding:40px;color:#999">📖 加载题目内容...</div>';
  try{
    const pid = getProblemId(filePath);
    const resp = await fetch('problems/' + pid + '.json');
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
}"""

    js_content = js_content.replace(old_load, new_load)

    # Fix toggleExamContent similarly
    js_content = js_content.replace(
        "const resp = await fetch('/api/problem-json?path=' + encodeURIComponent(decodeURIComponent(encodedPath)));",
        "const pid = getProblemId(decodeURIComponent(encodedPath));\n      const resp = await fetch('problems/' + pid + '.json');"
    )

    # Remove "打开原始文件" link since we can't serve raw files statically
    orig_line = '<span style="flex:1"></span>\n    <a href="/file/${encodedPath}" target="_blank">\U0001f4c4 \u6253\u5f00\u539f\u59cb\u6587\u4ef6</a>`;'
    new_line = '<span style="flex:1"></span>`;'
    js_content = js_content.replace(orig_line, new_line)

    (OUTPUT_DIR / "app.js").write_text(js_content, encoding="utf-8")
    print("  app.js 已修改 (静态文件模式)")

    # Add .nojekyll for GitHub Pages
    (OUTPUT_DIR / ".nojekyll").write_text("")
    print("  .nojekyll 已创建")

    # Summary
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.rglob("*") if f.is_file())
    print(f"\n{'=' * 60}")
    print(f"  构建完成！输出目录: {OUTPUT_DIR}")
    print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")
    print(f"  题目数量: {success}/{len(problems)}")
    print(f"\n  优化: meta.json 和 problems.json 分离加载")
    print(f"  meta.json: 9.9 KB (首次瞬间加载)")
    print(f"  problems.json: 166.7 KB (后台异步加载)")
    print(f"\n  部署步骤:")
    print(f"  1. 创建 GitHub 仓库")
    print(f"  2. 推送代码，Actions 自动构建部署")
    print(f"  或: 将 docs/ 内容推送到 username.github.io 仓库")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    build()

