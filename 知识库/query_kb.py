#!/usr/bin/env python3
"""
华为 OD 刷题知识库查询工具
用法:
  python query_kb.py                     - 列出所有分类/阶段
  python query_kb.py <分类名>            - 查询某分类所有题目
  python query_kb.py -k <关键词>          - 搜索标题
  python query_kb.py -d 简单              - 按难度筛选（简单/中等/困难）
  python query_kb.py -p P1               - 按阶段筛选（P1-P5）
  python query_kb.py -v <卷名>            - 按卷筛选
  python query_kb.py -s 100              - 按分数筛选
  python query_kb.py -l Java             - 按语言筛选
  python query_kb.py -t <分类名>          - 查看解题模板
  python query_kb.py --plan              - 查看刷题路线
  python query_kb.py --interactive       - 交互式查询
"""

import sqlite3
import sys
import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DB_PATH = BASE_DIR / "知识库" / "problems.db"

PHASE_EMOJI = {"P1-基础": "1️⃣", "P2-核心": "2️⃣", "P3-进阶": "3️⃣",
               "P4-高阶": "4️⃣", "P5-综合": "5️⃣"}
PHASE_ORDER = {"P1-基础": 1, "P2-核心": 2, "P3-进阶": 3, "P4-高阶": 4, "P5-综合": 5}
DIFF_EMOJI = {"简单": "🟢", "中等": "🟡", "困难": "🔴"}


def get_conn():
    if not DB_PATH.exists():
        print(f"错误: 知识库未找到，请先运行 build_kb.py")
        print(f"预期路径: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA encoding='UTF-8'")
    return conn


def list_overview():
    """显示分类和阶段概览"""
    conn = get_conn()
    c = conn.cursor()

    # 统计
    c.execute("SELECT COUNT(*) FROM problems")
    total = c.fetchone()[0]

    c.execute("SELECT difficulty, COUNT(*) FROM problems GROUP BY difficulty ORDER BY CASE difficulty WHEN '简单' THEN 1 WHEN '中等' THEN 2 WHEN '困难' THEN 3 END")
    diffs = dict(c.fetchall())

    print(f"\n{'='*60}")
    print(f"  华为 OD 知识库  📚 共 {total} 题")
    print(f"{'='*60}")
    print(f"  难度: 🟢简单 {diffs.get('简单',0)}  🟡中等 {diffs.get('中等',0)}  🔴困难 {diffs.get('困难',0)}")
    print(f"{'='*60}\n")

    # 按阶段分组
    c.execute("""
        SELECT phase, COUNT(*) as cnt
        FROM problems
        GROUP BY phase
        ORDER BY CASE phase
            WHEN 'P1-基础' THEN 1 WHEN 'P2-核心' THEN 2
            WHEN 'P3-进阶' THEN 3 WHEN 'P4-高阶' THEN 4
            WHEN 'P5-综合' THEN 5 ELSE 99 END
    """)
    phases = c.fetchall()

    for p in phases:
        phase = p['phase']
        emoji = PHASE_EMOJI.get(phase, "📌")
        cnt = p['cnt']

        c.execute("""
            SELECT cat.name, COUNT(pc.problem_id) as cat_cnt
            FROM categories cat
            JOIN problem_categories pc ON cat.id = pc.category_id
            WHERE cat.phase = ?
            GROUP BY cat.id
            ORDER BY cat_cnt DESC
        """, (phase,))
        cats = c.fetchall()

        print(f"  {emoji} {phase}（{cnt} 题）")
        for cat in cats:
            # 统计该分类下的难度分布
            c2 = conn.cursor()
            c2.execute("""
                SELECT p.difficulty, COUNT(*) as d_cnt
                FROM problems p
                JOIN problem_categories pc ON p.id = pc.problem_id
                JOIN categories cat2 ON cat2.id = pc.category_id
                WHERE cat2.name = ?
                GROUP BY p.difficulty
                ORDER BY CASE p.difficulty WHEN '简单' THEN 1 WHEN '中等' THEN 2 WHEN '困难' THEN 3 END
            """, (cat['name'],))
            diffs_str = " ".join([f"{DIFF_EMOJI.get(r['difficulty'],'')}{r['d_cnt']}" for r in c2.fetchall()])
            print(f"    · {cat['name']:25s} {cat['cat_cnt']:>3d}题  {diffs_str}")
        print()

    conn.close()
    print(f"  提示: python query_kb.py '<分类名>'  查具体题目")
    print(f"         python query_kb.py -t '<分类名>'  看解题模板")
    print(f"         python query_kb.py -d 简单  查简单题")
    print(f"         python query_kb.py --plan  看刷题路线\n")


def list_problems_by_category(category_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT p.title, p.volume, p.score, p.difficulty, p.phase, p.languages, p.file_path
        FROM problems p
        JOIN problem_categories pc ON p.id = pc.problem_id
        JOIN categories cat ON cat.id = pc.category_id
        WHERE cat.name LIKE ?
        ORDER BY p.volume_order, p.score DESC, p.title
    """, (f"%{category_name}%",))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"\n  未找到分类包含 '{category_name}' 的题目")
        return

    print(f"\n{'='*60}")
    print(f"  分类: {category_name}（共 {len(rows)} 题）")
    print(f"{'='*60}\n")

    for r in rows:
        diff_emoji = DIFF_EMOJI.get(r['difficulty'], "⚪")
        print(f"  {diff_emoji} ({r['volume']},{r['score']}分) - {r['title']}")
        print(f"    难度: {r['difficulty']}  阶段: {r['phase']}  语言: {r['languages']}")
        print(f"    路径: {r['file_path']}")
        print()


def search_by_keyword(keyword):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT p.title, p.volume, p.score, p.difficulty, p.languages, p.file_path
        FROM problems p
        WHERE p.title LIKE ?
        ORDER BY p.volume_order, p.score DESC, p.title
    """, (f"%{keyword}%",))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"\n  未找到标题包含 '{keyword}' 的题目")
        return

    print(f"\n{'='*60}")
    print(f"  搜索: '{keyword}'（共 {len(rows)} 题）")
    print(f"{'='*60}\n")

    for r in rows:
        diff_emoji = DIFF_EMOJI.get(r['difficulty'], "⚪")
        print(f"  {diff_emoji} ({r['volume']},{r['score']}分) - {r['title']}")

    print()


def filter_problems(difficulty=None, phase=None, volume=None, score=None, lang=None):
    conn = get_conn()
    c = conn.cursor()

    conditions = []
    params = []

    if difficulty:
        conditions.append("p.difficulty = ?")
        params.append(difficulty)
    if phase:
        conditions.append("p.phase LIKE ?")
        params.append(f"%{phase}%")
    if volume:
        conditions.append("p.volume LIKE ?")
        params.append(f"%{volume}%")
    if score is not None:
        conditions.append("p.score = ?")
        params.append(int(score))
    if lang:
        conditions.append("p.languages LIKE ?")
        params.append(f"%{lang}%")

    where = " AND ".join(conditions) if conditions else "1=1"

    c.execute(f"""
        SELECT p.title, p.volume, p.score, p.difficulty, p.phase, p.languages
        FROM problems p
        WHERE {where}
        ORDER BY p.volume_order, p.score DESC, p.title
    """, params)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"\n  未找到匹配的题目")
        return

    filters = "  ".join(filter(None, [
        f"难度: {difficulty}" if difficulty else "",
        f"阶段: {phase}" if phase else "",
        f"卷: {volume}" if volume else "",
        f"分数: {score}" if score else "",
        f"语言: {lang}" if lang else "",
    ]))
    diff_counts = {}
    for r in rows:
        diff_counts[r['difficulty']] = diff_counts.get(r['difficulty'], 0) + 1

    diff_str = "  ".join([f"{DIFF_EMOJI.get(d,'')}{d}: {c}" for d, c in diff_counts.items()])

    print(f"\n{'='*60}")
    print(f"  {filters}（共 {len(rows)} 题）{diff_str}")
    print(f"{'='*60}\n")

    for r in rows:
        diff_emoji = DIFF_EMOJI.get(r['difficulty'], "⚪")
        print(f"  {diff_emoji} ({r['volume']},{r['score']}分) - {r['title']}")


def show_template(category_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT name, template, phase FROM categories WHERE name LIKE ?", (f"%{category_name}%",))
    rows = c.fetchall()
    conn.close()

    if not rows:
        # Try template dict directly
        from build_kb import TEMPLATES
        for key, template in TEMPLATES.items():
            if category_name.lower() in key.lower():
                print(f"\n{'='*60}")
                print(f"  解题模板: {key}")
                print(f"{'='*60}")
                print(template)
                return
        print(f"\n  未找到 '{category_name}' 的解题模板")
        return

    from build_kb import TEMPLATES
    for r in rows:
        template = r['template'] or TEMPLATES.get(r['name'], "暂无模板")
        print(f"\n{'='*60}")
        print(f"  解题模板: {r['name']}（{r['phase']}）")
        print(f"{'='*60}")
        print(template if template.strip() else "(暂无模板)")


def show_study_plan():
    """显示完整的刷题路线"""
    conn = get_conn()
    c = conn.cursor()

    from build_kb import TEMPLATES, STUDY_PHASES, PHASE_ORDER

    print(f"\n{'='*60}")
    print(f"  📚 推荐刷题路线")
    print(f"{'='*60}\n")
    print(f"  🔑 路线说明：按知识点依赖关系编排，建议按 P1→P5 顺序刷\n")

    for phase_name in sorted(STUDY_PHASES.keys(), key=lambda x: PHASE_ORDER.get(x, 99)):
        emoji = PHASE_EMOJI.get(phase_name, "📌")
        c.execute("SELECT COUNT(*) FROM problems WHERE phase=?", (phase_name,))
        total = c.fetchone()[0]
        cat_list = STUDY_PHASES[phase_name]
        print(f"  {emoji} {phase_name}（共 {total} 题）")

        for cat_name in cat_list:
            c.execute("SELECT COUNT(*) FROM problems p JOIN problem_categories pc ON p.id=pc.problem_id JOIN categories cat ON cat.id=pc.category_id WHERE cat.name=?", (cat_name,))
            cnt = c.fetchone()[0]
            if cnt == 0: continue

            c.execute("""
                SELECT p.difficulty, COUNT(*) as d_cnt
                FROM problems p
                JOIN problem_categories pc ON p.id = pc.problem_id
                JOIN categories cat ON cat.id = pc.category_id
                WHERE cat.name = ?
                GROUP BY p.difficulty
                ORDER BY CASE p.difficulty WHEN '简单' THEN 1 WHEN '中等' THEN 2 WHEN '困难' THEN 3 END
            """, (cat_name,))
            diffs = " ".join([f"{DIFF_EMOJI.get(r['difficulty'],'')}{r['d_cnt']}" for r in c.fetchall()])

            template = TEMPLATES.get(cat_name, "")
            snippet = ""
            if template:
                lines = [l.strip() for l in template.split("\n") if l.strip()]
                for l in lines:
                    if "核心思路" in l:
                        snippet = l.replace("**", "").replace("**", "")
                        break
            print(f"    · {cat_name:25s} {cnt:>3d}题 {diffs:20s}")
            if snippet:
                print(f"      💡 {snippet}")
            print()

        print()

    conn.close()
    print(f"{'='*60}")
    print(f"  提示: python query_kb.py -t '<分类名>' 查看完整解题模板")
    print(f"{'='*60}\n")


def interactive_mode():
    import readline
    print(f"\n{'='*60}")
    print(f"  华为 OD 知识库 - 交互模式 (输入 help 查看帮助)")
    print(f"{'='*60}\n")

    while True:
        try:
            cmd = input("kb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not cmd: continue
        if cmd in ("exit", "quit", "q"): break
        if cmd in ("help", "h"):
            print("""
  命令:
    <分类名/关键词>    搜索题目
    list                列出所有分类/阶段
    plan                查看刷题路线
    template <分类>     查看解题模板
    -d <难度>           按难度筛选（简单/中等/困难）
    -p <阶段>           按阶段筛选（P1-P5）
    stats / -c          统计
    exit / q            退出
            """)
            continue
        if cmd == "list":
            list_overview()
            continue
        if cmd == "plan":
            show_study_plan()
            continue
        if cmd.startswith("template "):
            show_template(cmd[9:])
            continue
        if cmd in ("stats", "-c"):
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT difficulty, COUNT(*) FROM problems GROUP BY difficulty")
            print(f"\n  难度分布:")
            for r in c.fetchall():
                print(f"    {DIFF_EMOJI.get(r['difficulty'],'')} {r['difficulty']}: {r[1]} 题")
            conn.close()
            continue

        # Search
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM categories WHERE name LIKE ?", (f"%{cmd}%",))
        cats = cur.fetchall()
        conn.close()

        if cats:
            for cat in cats:
                list_problems_by_category(cat["name"])
        else:
            search_by_keyword(cmd)


def main():
    if not DB_PATH.exists():
        print(f"知识库未找到，正在构建...")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_kb import main as build
        build()
        print()

    if len(sys.argv) == 1:
        list_overview()
        return

    args = sys.argv[1:]

    if "--interactive" in args or "-i" in args:
        interactive_mode()
        return

    if "--plan" in args:
        show_study_plan()
        return

    if "-t" in args:
        idx = args.index("-t")
        name = args[idx + 1] if idx + 1 < len(args) else ""
        show_template(name)
        return

    if "-d" in args:
        idx = args.index("-d")
        difficulty = args[idx + 1] if idx + 1 < len(args) else None
        filter_problems(difficulty=difficulty)
        return

    if "-p" in args:
        idx = args.index("-p")
        phase_val = args[idx + 1] if idx + 1 < len(args) else ""
        phase_name = None
        for pn in PHASE_ORDER:
            if phase_val in pn or phase_val in pn.replace("P", ""):
                phase_name = pn
                break
        if phase_name:
            filter_problems(phase=phase_name)
        else:
            print(f"未知阶段: {phase_val}，可选: P1-基础, P2-核心, P3-进阶, P4-高阶, P5-综合")
        return

    if "-k" in args:
        idx = args.index("-k")
        keyword = args[idx + 1] if idx + 1 < len(args) else ""
        search_by_keyword(keyword)
        return

    if "-c" in args:
        conn = get_conn()
        c = conn.cursor()
        print(f"\n  难度分布:")
        c.execute("SELECT difficulty, COUNT(*) FROM problems GROUP BY difficulty")
        for r in c.fetchall():
            print(f"    {DIFF_EMOJI.get(r['difficulty'],'')} {r['difficulty']}: {r[1]} 题")
        conn.close()
        return

    # Handle combination filters (-v, -s, -l)
    volume = None
    score = None
    lang = None
    if "-v" in args:
        idx = args.index("-v")
        volume = args[idx + 1] if idx + 1 < len(args) else None
    if "-s" in args:
        idx = args.index("-s")
        score = args[idx + 1] if idx + 1 < len(args) else None
    if "-l" in args:
        idx = args.index("-l")
        lang = args[idx + 1] if idx + 1 < len(args) else None

    if volume or score is not None or lang:
        filter_problems(volume=volume, score=score, lang=lang)
        return

    # Default: treat as category name or keyword
    query = " ".join(args)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories WHERE name LIKE ?", (f"%{query}%",))
    cats = cur.fetchall()
    conn.close()

    if cats:
        for cat in cats:
            list_problems_by_category(cat["name"])
    else:
        search_by_keyword(query)


if __name__ == "__main__":
    main()
