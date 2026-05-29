let editor, problemData, allProblemsData, testCases = [];

const MODE_MAP = {
  python:'python', javascript:'javascript', java:'text/x-java',
  cpp:'text/x-c++src', c:'text/x-csrc', go:'text/x-go',
  typescript:'text/typescript', csharp:'text/x-csharp', rust:'text/x-rustsrc'
};

const LANG_TEMPLATES = {
  python: `import sys

def solve():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    # TODO: 在此编写解题代码
    # 解析输入 -> 计算结果 -> 输出
    # print(result)

if __name__ == "__main__":
    solve()`,
  javascript: `const readline = require('readline');
const rl = readline.createInterface({input:process.stdin,output:process.stdout});
const lines = [];
rl.on('line', line => lines.push(line.trim()));
rl.on('close', () => {
    // TODO: 在此编写解题代码
    // console.log(result)
});`,
  java: `import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // TODO: 在此编写解题代码
        sc.close();
    }
}`,
  cpp: `#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    // TODO: 在此编写解题代码
    return 0;
}`,
  c: `#include <stdio.h>

int main() {
    // TODO: 在此编写解题代码
    return 0;
}`,
  go: `package main

import "fmt"

func main() {
    // TODO: 在此编写解题代码
    var n int
    fmt.Scan(&n)
}`,
  typescript: `// TypeScript
function solve(): void {
    // TODO: 在此编写解题代码
}
solve();`,
  csharp: `using System;

class Program {
    static void Main() {
        // TODO: 在此编写解题代码
    }
}`,
  rust: `use std::io::{self, BufRead};

fn main() {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        // TODO: 在此编写解题代码
    }
}`
};

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || '';
}

async function init() {
  const path = getQueryParam('path');
  if (!path) {
    document.getElementById('problemTitle').textContent = '错误: 缺少题目路径';
    return;
  }

  const isStatic = !window.location.pathname.includes('/coding') || window.location.pathname.endsWith('.html');

  try {
    if (isStatic) {
      const resp = await fetch('problems.json');
      const pd = await resp.json();
      allProblemsData = { problems: pd.problems };
      problemData = pd.problems.find(p => p.file_path === path);
    } else {
      const resp = await fetch('/api/data');
      allProblemsData = await resp.json();
      problemData = allProblemsData.problems.find(p => p.file_path === path);
    }

    if (problemData) {
      document.getElementById('problemTitle').textContent =
        (problemData.difficulty === '简单' ? '🟢' : problemData.difficulty === '中等' ? '🟡' : '🔴') + ' ' + problemData.title;
    }

    loadProblemContent(path, isStatic);
  } catch (e) {
    document.getElementById('problemContent').innerHTML =
      '<div class="problem-loading" style="color:#f44336">❌ 加载失败: ' + e.message + '</div>';
  }

  initEditor(isStatic);

  document.getElementById('langSelect').addEventListener('change', onLangChange);

  const saved = loadSavedCode(path);
  if (saved) {
    editor.setValue(saved);
  }

  if (isStatic) {
    document.getElementById('runBtn').textContent = '⛔ 静态模式';
    document.getElementById('runBtn').disabled = true;
    document.getElementById('runBtn').title = '本地服务器模式支持运行代码';
    document.getElementById('runStatus').textContent = '静态页面不支持运行代码，请启动本地服务器';
    document.getElementById('langSelect').value = 'python';
  }
}

function initEditor(isStatic) {
  const ta = document.getElementById('codeEditor');
  try {
    if (typeof CodeMirror === 'undefined') throw new Error('CodeMirror not loaded');
    editor = CodeMirror.fromTextArea(ta, {
      mode: 'python',
      theme: 'monokai',
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      lineWrapping: false,
      matchBrackets: true,
      autoCloseBrackets: true,
      extraKeys: {
        'Ctrl-Space': 'autocomplete',
        'Tab': function(cm) {
          cm.replaceSelection('    ', 'end');
        }
      },
      gutters: ['CodeMirror-linenumbers'],
      foldGutter: false,
    });
    editor.on('change', function() { saveCode(); });
    setTimeout(() => editor.refresh(), 100);
  } catch (e) {
    console.warn('CodeMirror init failed, using textarea fallback:', e);
    ta.style.width = '100%';
    ta.style.height = '100%';
    ta.style.background = '#1e1e2e';
    ta.style.color = '#cdd6f4';
    ta.style.fontFamily = '"JetBrainsMono Nerd Font", Consolas, monospace';
    ta.style.fontSize = '19px';
    ta.style.lineHeight = '1.6';
    ta.style.padding = '10px';
    ta.style.border = 'none';
    ta.style.resize = 'none';
    ta.style.outline = 'none';
    ta.style.tabSize = '4';
    ta.value = LANG_TEMPLATES.python;
    ta.addEventListener('input', function() {
      try { localStorage.setItem('coding_code_fallback_' + getQueryParam('path'), ta.value); } catch(e) {}
    });
    editor = { getValue: function() { return ta.value; }, setValue: function(v) { ta.value = v; }, setOption: function() {} };
  }
}

function onLangChange() {
  const lang = this.value;
  const mode = MODE_MAP[lang] || 'python';
  editor.setOption('mode', mode);

  const path = getQueryParam('path');
  const saved = loadSavedCode(path, lang);
  if (saved) {
    editor.setValue(saved);
  } else {
    const template = LANG_TEMPLATES[lang] || LANG_TEMPLATES.python;
    editor.setValue(template);
  }

  updateHintOptions(lang);
}

function updateHintOptions(lang) {
  const hints = {
    python: 'python', javascript: 'javascript', java: 'java',
    cpp: 'cpp', c: 'c', go: 'go',
    typescript: 'javascript', csharp: 'cpp', rust: 'rust'
  };
  const hintLang = hints[lang] || 'python';
  if (CodeMirror.hint && CodeMirror.hint[hintLang]) {
    editor.setOption('hintOptions', { hint: CodeMirror.hint[hintLang] });
  } else if (CodeMirror.hint && CodeMirror.hint.words) {
    editor.setOption('hintOptions', { hint: CodeMirror.hint.words, words: LANG_KEYWORDS[lang] || [] });
  }
  editor.setOption('extraKeys', {
    'Ctrl-Space': 'autocomplete',
    'Tab': function(cm) { cm.replaceSelection('    ', 'end'); }
  });
}

const LANG_KEYWORDS = {
  python: ['False','None','True','and','as','assert','async','await','break','class','continue','def','del','elif','else','except','finally','for','from','global','if','import','in','is','lambda','nonlocal','not','or','pass','raise','return','try','while','with','yield','print','len','range','int','str','list','dict','set','tuple','map','filter','sorted','sum','min','max','abs','input','open','sys','__name__','__main__'],
  javascript: ['async','await','break','case','catch','class','const','continue','debugger','default','delete','do','else','enum','export','extends','false','finally','for','function','if','import','in','instanceof','let','new','null','of','return','static','super','switch','this','throw','true','try','typeof','undefined','var','void','while','with','yield','console','require','module'],
  java: ['abstract','assert','boolean','break','byte','case','catch','char','class','const','continue','default','do','double','else','enum','extends','false','final','finally','float','for','if','implements','import','instanceof','int','interface','long','native','new','null','package','private','protected','public','return','short','static','super','switch','synchronized','this','throw','throws','transient','true','try','void','volatile','while','System','String','ArrayList','HashMap','Scanner'],
  cpp: ['auto','bool','break','case','catch','char','class','const','constexpr','continue','default','delete','do','double','else','enum','explicit','export','extern','false','float','for','friend','goto','if','inline','int','long','mutable','namespace','new','noexcept','nullptr','operator','override','private','protected','public','register','return','short','signed','sizeof','static','struct','switch','template','this','throw','true','try','typedef','typeid','typename','union','unsigned','using','virtual','void','volatile','while','include','iostream','vector','string','cout','cin']
};

function saveCode() {
  const path = getQueryParam('path');
  const lang = document.getElementById('langSelect').value;
  if (!path || !editor) return;
  try {
    const key = 'coding_code_' + encodeURIComponent(path) + '_' + lang;
    const data = { code: editor.getValue(), lang: lang, time: Date.now() };
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) { /* ignore storage errors */ }
}

function loadSavedCode(path, lang) {
  lang = lang || document.getElementById('langSelect').value;
  if (!path) return null;
  try {
    const key = 'coding_code_' + encodeURIComponent(path) + '_' + lang;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (data.lang === lang) return data.code;
  } catch (e) { /* ignore */ }
  return null;
}

async function loadProblemContent(filePath, isStatic) {
  const container = document.getElementById('problemContent');
  try {
    let resp;
    if (isStatic) {
      const pid = problemData ? problemData.id : encodeURIComponent(filePath);
      resp = await fetch('problems/' + pid + '.json');
    } else {
      resp = await fetch('/api/problem-json?path=' + encodeURIComponent(filePath));
    }
    if (!resp.ok) throw new Error('加载失败');
    const parsed = await resp.json();
    if (parsed.error) {
      container.innerHTML = '<div class="problem-loading" style="color:#f44336">❌ ' + parsed.error + '</div>';
      return;
    }
    renderDescription(parsed);
    extractTestCases(parsed);
  } catch (e) {
    container.innerHTML = '<div class="problem-loading" style="color:#f44336">❌ 加载失败: ' + e.message + '</div>';
  }
}

function renderDescription(parsed) {
  const container = document.getElementById('problemContent');
  const sections = parsed.sections || [];
  const typeIcons = { desc: '📋', input: '📥', output: '📤', sample: '📊', note: 'ℹ️' };

  const solutionKeywords = ['题解', '思路', '解题', '解析', '答案', '解法', '参考', '代码', 'approach', 'solution'];

  let html = '';
  for (const s of sections) {
    if (s.type === 'solution') continue;
    const headingLower = s.heading.toLowerCase();
    const isSolution = solutionKeywords.some(kw => headingLower.includes(kw));
    if (isSolution) continue;
    const icon = typeIcons[s.type] || '📄';
    const body = formatBody(s.html);
    html += '<div class="section-card ' + (s.type || 'desc') + '">' +
      '<div class="section-header">' + icon + ' ' + escapeHtml(s.heading) + '</div>' +
      '<div class="section-body">' + body + '</div></div>';
  }

  if (!html) {
    html = '<div class="problem-loading">暂无题目内容</div>';
  }

  container.innerHTML = html;
}

function formatBody(html) {
  const div = document.createElement('div');
  div.innerHTML = html;
  div.querySelectorAll('script, style, link, meta, head').forEach(el => el.remove());
  div.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => el.remove());
  div.querySelectorAll('a').forEach(el => el.replaceWith(el.textContent));
  div.querySelectorAll('span').forEach(el => el.replaceWith(el.textContent));
  div.querySelectorAll('code').forEach(el => el.className = 'inline');
  div.querySelectorAll('p').forEach(el => { if (!el.innerHTML.trim()) el.remove(); });
  div.querySelectorAll('pre').forEach(pre => {
    const codeLines = pre.querySelectorAll('.CodeMirror-line');
    if (codeLines.length > 0) {
      pre.textContent = Array.from(codeLines).map(el => el.textContent).join('\n');
    }
    pre.className = 'plain-code';
  });
  div.querySelectorAll('table').forEach(t => {
    t.style.width = 'auto';
    t.style.fontSize = '13px';
  });
  return div.innerHTML.trim();
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function extractTestCases(parsed) {
  testCases = [];
  const sections = parsed.sections || [];

  for (const s of sections) {
    if (s.type !== 'sample') continue;

    const div = document.createElement('div');
    div.innerHTML = s.html;

    // Remove line-number artifacts (pre-numbering lists from code blocks)
    div.querySelectorAll('ul.pre-numbering, ol.linenums, .line-numbers').forEach(el => el.remove());

    // ---- Method 1: Table format (most common, ~90% of problems) ----
    const tables = div.querySelectorAll('table');
    for (const table of tables) {
      const rows = table.querySelectorAll('tr');
      let input = '', output = '';
      for (const row of rows) {
        const cells = row.querySelectorAll('td, th');
        let label = '';
        let value = '';
        if (cells.length >= 2) {
          label = cells[0].textContent.trim();
          value = cells[1].textContent.trim();
        } else if (cells.length === 1) {
          label = cells[0].textContent.trim();
        }
        if (/输入/.test(label)) input = value;
        else if (/输出/.test(label)) output = value;
      }
      if (input || output) {
        testCases.push({ input, expected: output });
      }
    }

    // ---- Method 2: Paragraph + <pre> format (for non-table samples) ----
    if (tables.length === 0) {
      const children = Array.from(div.children);
      let inputBuf = '', outputBuf = '';

      for (let i = 0; i < children.length; i++) {
        const el = children[i];
        const tag = el.tagName;
        const text = el.textContent.trim();
        const isHeading = tag === 'H1' || tag === 'H2' || tag === 'H3' || tag === 'H4';

        // "说明" terminates the current test case
        if (/说明/.test(text) && (inputBuf || outputBuf)) {
          commitIOPair(inputBuf, outputBuf);
          inputBuf = ''; outputBuf = '';
          continue;
        }

        // "用例2", "示例1" etc. indicate a new example within the same section
        if (isHeading && /用例|示例/.test(text) && (inputBuf || outputBuf)) {
          commitIOPair(inputBuf, outputBuf);
          inputBuf = ''; outputBuf = '';
          continue;
        }

        if (tag === 'P' || tag === 'DIV' || tag === 'SPAN' || isHeading) {
          if (/输入/.test(text)) {
            commitIOPair(inputBuf, outputBuf);
            inputBuf = ''; outputBuf = '';
            for (let j = i + 1; j < children.length; j++) {
              const nxt = children[j];
              if (nxt.tagName === 'PRE') {
                inputBuf = extractPreText(nxt);
                i = j;
                break;
              }
              if (/输入|输出|说明|用例|示例/.test(nxt.textContent)) break;
            }
          } else if (/输出/.test(text) && !/说明/.test(text)) {
            for (let j = i + 1; j < children.length; j++) {
              const nxt = children[j];
              if (nxt.tagName === 'PRE') {
                outputBuf = extractPreText(nxt);
                i = j;
                break;
              }
              if (/输入|输出|说明|用例|示例/.test(nxt.textContent)) break;
            }
          }
        }
      }
      commitIOPair(inputBuf, outputBuf);
    }
  }

  // Deduplicate
  const seen = new Set();
  testCases = testCases.filter(tc => {
    const key = tc.input + '|||' + tc.expected;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  if (testCases.length > 0) {
    document.getElementById('runStatus').textContent = '已提取 ' + testCases.length + ' 个测试示例';
  } else {
    document.getElementById('runStatus').textContent = '⚠️ 未能提取测试用例，题目样本格式可能与解析器不兼容';
  }
}

function commitIOPair(input, output) {
  if (input || output) {
    testCases.push({ input: input || '', expected: output || '' });
  }
}

function extractPreText(preEl) {
  // Remove line-number lists and copy buttons
  preEl.querySelectorAll('ul.pre-numbering, ol.linenums, .line-numbers, .hljs-button, div[class*="hljs"]').forEach(el => el.remove());
  let text = preEl.textContent.trim();
  // Strip leading/trailing blank lines
  text = text.replace(/^\s*\n/, '').replace(/\n\s*$/, '');
  return text;
}



async function runCode() {
  const btn = document.getElementById('runBtn');
  const status = document.getElementById('runStatus');
  const resultPanel = document.getElementById('resultPanel');
  const resultContent = document.getElementById('resultContent');

  if (testCases.length === 0) {
    status.textContent = '⚠️ 未找到测试示例，请检查题目内容';
    return;
  }

  const code = editor.getValue();
  if (!code.trim()) {
    status.textContent = '⚠️ 请先编写代码';
    return;
  }

  btn.disabled = true;
  btn.classList.add('running');
  btn.textContent = '⏳ 运行中...';
  status.textContent = '正在测试 ' + testCases.length + ' 个示例...';
  resultPanel.classList.add('show');
  resultContent.innerHTML = '<div class="result-placeholder">⏳ 运行中...</div>';

  try {
    const resp = await fetch('/api/run-python', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, test_cases: testCases })
    });
    const data = await resp.json();
    displayResults(data.results || []);
  } catch (e) {
    resultContent.innerHTML = '<div class="result-error">❌ 请求失败: ' + e.message + '</div>';
    status.textContent = '❌ 运行失败';
  } finally {
    btn.disabled = false;
    btn.classList.remove('running');
    btn.textContent = '▶ 运行代码';
  }
}

function displayResults(results) {
  const panel = document.getElementById('resultPanel');
  const container = document.getElementById('resultContent');
  panel.classList.add('show');

  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  const allPassed = passed === total;
  const allFailed = passed === 0;

  let statusMsg;
  if (allPassed) {
    statusMsg = '✅ 全部通过 (' + passed + '/' + total + ')';
  } else if (allFailed) {
    statusMsg = '❌ 全部未通过 (0/' + total + ')';
  } else {
    statusMsg = '❌ 通过 ' + passed + '/' + total;
  }

  let html = '<div class="result-summary">';
  if (allPassed) {
    html += '<span class="pass">✅ 全部通过</span>';
  } else if (allFailed) {
    html += '<span class="fail">❌ 全部未通过</span>';
  } else {
    html += '<span class="fail">❌ 部分通过</span>';
  }
  html += ' <span style="color:#aaa">' + passed + '/' + total + ' 通过</span></div>';

  results.forEach((r, i) => {
    const hasStderr = r.stderr && r.stderr.length > 0;
    html += '<div class="test-case' + (hasStderr ? ' tc-has-error' : '') + '">';
    html += '<div class="tc-header">' +
      (r.passed ? '<span class="tc-pass">✅</span>' : '<span class="tc-fail">❌</span>') +
      ' <span>测试用例 ' + (i + 1) + '</span></div>';
    html += '<div class="tc-detail">';
    if (r.input) {
      html += '<div><span class="tc-label">输入:</span><span class="tc-val">' + escapeHtml(r.input) + '</span></div>';
    }
    if (hasStderr) {
      // Show error output prominently as the primary feedback
      html += '<div class="stderr-block"><div class="stderr-title">⛔ 错误输出:</div><pre class="stderr-text">' + escapeHtml(r.stderr) + '</pre></div>';
    } else {
      // Only show output/expected when there's no compilation error
      html += '<div><span class="tc-label">输出:</span><span class="tc-val' + (r.passed ? '' : ' tc-diff') + '">' + escapeHtml(r.output || '(空)') + '</span></div>';
      if (!r.passed && r.expected) {
        html += '<div><span class="tc-label">期望:</span><span class="tc-val">' + escapeHtml(r.expected) + '</span></div>';
      }
    }
    html += '</div></div>';
  });

  container.innerHTML = html;

  document.getElementById('runStatus').textContent = statusMsg;
}

window.addEventListener('load', init);
