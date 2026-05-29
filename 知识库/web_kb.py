#!/usr/bin/env python3
"""
华为 OD 刷题知识库 Web 服务器
启动后访问 http://localhost:8899
"""

import html
import json
import sqlite3
import sys
import os
import urllib.parse
import subprocess
import tempfile
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DB_PATH = BASE_DIR / "知识库" / "problems.db"
PORT = 8899
STATIC_DIR = Path(__file__).parent / "static"
_cache = {}

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write((STATIC_DIR / "index.html").read_bytes())
            return

        if path == "/coding":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write((STATIC_DIR / "coding.html").read_bytes())
            return

        if path.startswith("/static/"):
            rel = path[8:]
            full = (STATIC_DIR / rel).resolve()
            try:
                full.relative_to(STATIC_DIR.resolve())
            except ValueError:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            if full.exists() and full.is_file():
                ext = full.suffix.lower()
                ct = {"css": "text/css; charset=utf-8", "js": "application/javascript; charset=utf-8", "html": "text/html; charset=utf-8", "json": "application/json", "png": "image/png", "svg": "image/svg+xml"}.get(ext.lstrip("."), "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(full.read_bytes())
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        if path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

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
            self.wfile.write(json.dumps({
                "problems": problems,
                "categories": categories,
                "templates": templates,
                "base_path": str(BASE_DIR),
            }, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/exam":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # 1 道 200分困难题
            c.execute("""
                SELECT p.* FROM problems p
                WHERE p.score = 200 AND p.difficulty = '困难'
                ORDER BY RANDOM() LIMIT 1
            """)
            hard200 = c.fetchone()

            # 2 道 100分题：1道简单 + 1道中等
            c.execute("""
                SELECT p.* FROM problems p
                WHERE p.score = 100 AND p.difficulty = '简单'
                ORDER BY RANDOM() LIMIT 1
            """)
            easy100 = c.fetchone()

            c.execute("""
                SELECT p.* FROM problems p
                WHERE p.score = 100 AND p.difficulty = '中等'
                ORDER BY RANDOM() LIMIT 1
            """)
            med100 = c.fetchone()

            selected = [hard200, easy100, med100]
            problems = []
            for row in selected:
                if row is None:
                    continue
                pid = row["id"]
                c2 = conn.cursor()
                c2.execute("""
                    SELECT cat.name FROM categories cat
                    JOIN problem_categories pc ON cat.id = pc.category_id
                    WHERE pc.problem_id = ?
                """, (pid,))
                cats = [r[0] for r in c2.fetchall()]
                problems.append({
                    "title": row["title"],
                    "volume": row["volume"],
                    "score": row["score"],
                    "difficulty": row["difficulty"],
                    "languages": row["languages"],
                    "file_path": row["file_path"],
                    "categories": cats,
                })

            conn.close()
            self.wfile.write(json.dumps({"problems": problems}, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/problem-raw":
            query = urllib.parse.parse_qs(parsed.query)
            file_path = query.get('path', [''])[0]
            if not file_path:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing path param")
                return
            full_path = (BASE_DIR / file_path).resolve()
            try:
                full_path.relative_to(BASE_DIR.resolve())
            except ValueError:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            if full_path.exists() and full_path.is_file():
                content = full_path.read_text('utf-8', errors='replace')
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")
            return

        if path == "/api/problem-json":
            query = urllib.parse.parse_qs(parsed.query)
            file_path = query.get('path', [''])[0]
            if not file_path:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing path param")
                return
            full_path = (BASE_DIR / file_path).resolve()
            try:
                full_path.relative_to(BASE_DIR.resolve())
            except ValueError:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            if not (full_path.exists() and full_path.is_file()):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
                return

            cache_key = f"problem-json:{file_path}"
            if cache_key in _cache:
                result = _cache[cache_key]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                return

            import re
            raw_html = full_path.read_text('utf-8', errors='replace')

            def extract_div_content(html, div_id):
                m = re.search(rf'<div[^>]*id=[\'"]{div_id}[\'"][^>]*>', html)
                if not m:
                    return None
                body_end = html.rfind('</body>')
                depth = 1
                pos = m.end()
                while depth > 0 and pos < len(html) and (body_end == -1 or pos < body_end):
                    n_open = html.find('<div', pos)
                    n_close = html.find('</div>', pos)
                    if n_close == -1:
                        break
                    elif n_open != -1 and n_open < n_close and (body_end == -1 or n_open < body_end):
                        depth += 1
                        pos = n_open + 5
                    else:
                        depth -= 1
                        if depth == 0:
                            return html[m.end():n_close]
                        pos = n_close + 6
                return html[m.end():]

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
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "write div not found"}, ensure_ascii=False).encode("utf-8"))
                return

            code_blocks = {}
            solution_langs = ['java','python','c++','c#','c','javascript','js','go','golang','rust','ruby','php','swift','kotlin','typescript','ts','scala','dart','perl','r','matlab','bash','shell','sql','lua']
            lang_map = {'java':'Java','python':'Python','c++':'C++','c#':'C#','javascript':'JavaScript','js':'JavaScript','go':'Go','c':'C','typescript':'TypeScript'}

            def extract_code_from_pre(block_inner):
                clines = re.findall(r'<pre\s+class="\s*CodeMirror-line[^"]*"[^>]*>(.*?)</pre>', block_inner, re.DOTALL)
                if clines:
                    return '\n'.join(re.sub(r'<[^>]+>', '', cl).rstrip('\n\r') for cl in clines)
                return re.sub(r'<[^>]+>', '', block_inner)

            def clean_code_text(text):
                text = text.strip()
                for ent in [('&lt;','<'),('&gt;','>'),('&amp;','&'),('&nbsp;',' '),('&quot;','"'),('&#39;',"'")]:
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
                    parts.append(html_text[i:i+pre_start.start()])
                    tag_text = html_text[i+pre_start.start():i+pre_start.end()]
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
                    block_inner = html_text[i+pre_start.end():pos-6] if depth == 0 else html_text[i+pre_start.end():]
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

            if is_typora:
                typora_orig = main_html
                def is_solution(lang, tag):
                    ll = lang.lower()
                    return (ll not in ('none', '', 'text', 'plain') and (any(sl in ll for sl in solution_langs) or ll == 'code' or (lang and lang[0].isupper())))
                main_html = has_depth_aware_replace(
                    main_html,
                    r'<pre\s[^>]*class="[^"]*md-fences[^"]*"[^>]*>',
                    r'lang',
                    is_solution
                )
                if not code_blocks and re.search(r'<h2[^>]*>', typora_orig):
                    has_h2_lang = any(
                        re.sub(r'<[^>]+>', '', hm.group(1)).strip().lower()
                        in {'java','python','c++','c','javascript','js','go','c#','typescript','ts','ruby','rust','php','swift','kotlin','scala','dart','perl','r','matlab','bash','shell','sql','lua','golang'}
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
                                next_h2 = h2_matches[idx+1] if idx+1 < len(h2_matches) else None
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
                                    block_inner = between[pre_m.end():pos-6] if depth == 0 else between[pre_m.end():]
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
                # Scan ALL heading levels for language-named headings
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
                                block_inner = between[pre_m.end():pos-6] if depth == 0 else between[pre_m.end():]
                                ct = html.unescape(re.sub(r'<[^>]+>', '', block_inner).strip())
                                if ct:
                                    if curr_lang not in code_blocks:
                                        code_blocks[curr_lang] = []
                                    code_blocks[curr_lang].append(ct)
                                    remove_ranges.append((h_m.start(), h_m.end()))
                                    # Also mark the pre block and content between heading and next heading
                                    # We'll handle removal differently - just mark heading + code for removal
                                    remove_ranges.append((h_m.end() + pre_m.start(), h_m.end() + pos - 6 + 6))
                # Remove extracted code blocks and their headings from main_html
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
                end = heading_matches[i+1].start() if i+1 < len(heading_matches) else len(main_html)
                section_html = main_html[start:end].strip()
                text_content = re.sub(r'<[^>]+>', '', section_html)
                text_content = text_content.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').strip()
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
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        if path.startswith("/file/"):
            encoded = path[6:]
            rel_path = urllib.parse.unquote(encoded)
            full_path = (BASE_DIR / rel_path).resolve()
            try:
                full_path.relative_to(BASE_DIR.resolve())
            except ValueError:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            if full_path.exists() and full_path.is_file():
                self.send_response(200)
                ct = "text/html; charset=utf-8" if full_path.suffix == ".html" else "text/markdown; charset=utf-8" if full_path.suffix == ".md" else "application/octet-stream"
                self.send_header("Content-Type", ct)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")
            return

        # Fallback: serve static files from STATIC_DIR
        rel = path.lstrip('/')
        full = (STATIC_DIR / rel).resolve()
        try:
            full.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        if full.exists() and full.is_file():
            ext = full.suffix.lower()
            ct = {"css": "text/css; charset=utf-8", "js": "application/javascript; charset=utf-8",
                  "html": "text/html; charset=utf-8", "json": "application/json",
                  "png": "image/png", "svg": "image/svg+xml"}.get(ext.lstrip("."), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(full.read_bytes())
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run-python":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = json.loads(self.rfile.read(content_length))
            code = post_data.get('code', '')
            test_cases = post_data.get('test_cases', [])

            results = []
            for tc in test_cases:
                input_str = tc.get('input', '')
                expected = tc.get('expected', '')
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                        f.write(code)
                        tmp_path = f.name
                    proc = subprocess.run(
                        [sys.executable, tmp_path],
                        input=input_str,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    output = proc.stdout.strip()
                    stderr = proc.stderr.strip()
                    # Non-zero return code = compilation/runtime error -> test fails
                    has_error = proc.returncode != 0
                    if has_error:
                        passed = False
                    else:
                        passed = output.rstrip() == expected.rstrip()
                    results.append({
                        'input': input_str,
                        'expected': expected,
                        'output': output,
                        'stderr': stderr,
                        'passed': passed,
                    })
                except subprocess.TimeoutExpired:
                    results.append({
                        'input': input_str, 'expected': expected,
                        'output': '', 'stderr': '⏱️ 执行超时（10秒）', 'passed': False,
                    })
                except MemoryError:
                    results.append({
                        'input': input_str, 'expected': expected,
                        'output': '', 'stderr': '💥 内存不足，代码可能进入了死循环或消耗了过多内存', 'passed': False,
                    })
                except OSError as e:
                    results.append({
                        'input': input_str, 'expected': expected,
                        'output': '', 'stderr': f'⚠️ 系统错误: {e}\n请确保 Python 环境正常', 'passed': False,
                    })
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    results.append({
                        'input': input_str, 'expected': expected,
                        'output': '', 'stderr': f'❌ 服务端异常:\n{tb}', 'passed': False,
                    })
                finally:
                    if tmp_path is not None and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps({"results": results}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")


def main():
    if not DB_PATH.exists():
        print(f"知识库未找到: {DB_PATH}")
        print("请先运行 build_kb.py 构建知识库")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  华为 OD 刷题知识库")
    print(f"  请访问: http://localhost:{PORT}")
    print(f"  (按 Ctrl+C 停止)")
    print(f"{'='*60}\n")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()


if __name__ == "__main__":
    main()
