#!/usr/bin/env python3
"""
华为 OD 刷题知识库构建工具
扫描所有题目文件，提取元数据，自动分类，构建 SQLite 知识库
"""

import os
import re
import sqlite3
from pathlib import Path

SCAN_DIRS = [
    "华为od/ABCD卷",
    "华为od/ABCD卷/老A卷包含C++的解析",
    "华为od/2025年A卷",
    "华为od/2024-2025 E卷",
    "华为od/2025B卷",
    "华为od/2025C卷",
    "华为od/双机位A卷",
    "华为od/双机位B卷",
    "华为od/双机位C卷",
    "2025C卷",
    "2025年A卷",
    "双机位A卷",
    "双机位B卷",
    "双机位C卷",
    "双机位C卷(1)",
]

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DB_PATH = BASE_DIR / "知识库" / "problems.db"

FILENAME_RE = re.compile(
    r'^\((?P<volume>[^,]+),(?P<score>\d+)分\)\s*-\s*(?P<title>[^（(]+)[（(](?P<languages>[^）)]+)[）)]\)?(?:\(1\))?\.(html|md)$'
)

# ─── 刷题阶段 ───
STUDY_PHASES = {
    "P1-基础": ["数组 / 矩阵", "数组 / 子数组", "数组 / 模拟", "字符串", "字符串 / 子串",
                "哈希表", "排序", "排序 / 查找", "数学 / 数论", "数学 / 位运算", "模拟 / 实现"],
    "P2-核心": ["双指针", "滑动窗口", "二分查找", "栈 / 队列", "前缀和 / 差分"],
    "P3-进阶": ["树 / Tree", "回溯 / 递归", "贪心 / Greedy", "区间问题"],
    "P4-高阶": ["动态规划 / DP", "图论", "图论 / BFS", "并查集 / Union-Find",
                "堆 / Heap", "最短路径", "最小生成树", "拓扑排序"],
    "P5-综合": ["记忆化搜索", "未分类 / Other"],
}

PHASE_ORDER = {"P1-基础": 1, "P2-核心": 2, "P3-进阶": 3, "P4-高阶": 4, "P5-综合": 5}

# ─── 难度计算 ───
# (category_pattern, 100分 -> difficulty, 200分 -> difficulty)
DIFFICULTY_RULES = [
    # 基础题型：100分=简单，200分=中等
    (["数组", "字符串", "哈希表", "排序", "数学", "模拟"], "简单", "中等"),
    # 核心题型：100分=简单/中等，200分=中等/困难
    (["双指针", "滑动窗口", "二分查找", "栈 / 队列", "前缀和"], "简单", "中等"),
    # 进阶题型
    (["树 / Tree", "回溯", "贪心", "区间", "并查集", "双指针"], "中等", "困难"),
    # 高阶题型
    (["动态规划", "图论", "堆 / Heap", "最短路径", "最小生成树", "拓扑", "记忆化"], "中等", "困难"),
]


def calc_difficulty(categories, score):
    """计算难度等级"""
    base = "简单" if score == 100 else "中等"

    for patterns, easy, hard in DIFFICULTY_RULES:
        for cat in categories:
            for pat in patterns:
                if pat in cat:
                    return easy if score == 100 else hard

    return base


def calc_study_phase(categories):
    """计算刷题阶段"""
    for phase_name, cat_list in STUDY_PHASES.items():
        for cl in cat_list:
            for c in categories:
                if c == cl:
                    return phase_name
    return "P5-综合"


# ─── 解题模板 ───
TEMPLATES = {
    "数组 / 矩阵": """
### 数组 / 矩阵 解题模板
**核心思路**：遍历、双循环、模拟指针移动
```
def solve(arr):
    n = len(arr)
    for i in range(n):
        # 处理当前元素
        pass
    return result
```
**常见题型**：螺旋矩阵、数组去重、矩阵扩散
**关键技巧**：注意边界条件、善用下标映射
""",
    "字符串": """
### 字符串 解题模板
**核心思路**：遍历字符、字符串哈希、双端比较
```
def solve(s):
    # 常用操作
    arr = list(s)
    # 遍历
    for i, c in enumerate(s):
        pass
    return ''.join(arr)
```
**常见题型**：反转字符串、括号匹配、通配符匹配
**关键技巧**：Python字符串不可变→转list、善用切片
""",
    "哈希表": """
### 哈希表 解题模板
**核心思路**：空间换时间，O(1)查找
```
def solve(nums):
    seen = {}
    for i, val in enumerate(nums):
        complement = target - val
        if complement in seen:
            return [seen[complement], i]
        seen[val] = i
```
**常见题型**：两数之和、字符统计、去重
**关键技巧**：活用defaultdict/Counter
""",
    "排序": """
### 排序 解题模板
**核心思路**：自定义排序规则
```
def solve(arr):
    # 自定义排序
    arr.sort(key=lambda x: (x[0], -x[1]))
    return arr
```
**常见题型**：区间合并、第K大、自定义排序
**关键技巧**：灵活使用key和cmp_to_key
""",
    "双指针": """
### 双指针 解题模板
**核心思路**：相向/同向/快慢指针
```
def solve(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        # 根据条件移动指针
        if condition:
            left += 1
        else:
            right -= 1
```
**常见题型**：两数之和、三数之和、盛水容器
**关键技巧**：有序数组优先考虑双指针
""",
    "滑动窗口": """
### 滑动窗口 解题模板
**核心思路**：维护窗口[left, right)，记录窗口状态
```
def solve(s):
    n = len(s)
    left = 0
    window = {}
    for right in range(n):
        # 加入right
        window[s[right]] = window.get(s[right], 0) + 1
        # 收缩left
        while need_shrink(window):
            window[s[left]] -= 1
            left += 1
        # 更新结果
        ans = max(ans, right - left + 1)
    return ans
```
**常见题型**：最长无重复子串、最小覆盖子串
**关键技巧**：窗口内状态用Counter/哈希表维护
""",
    "二分查找": """
### 二分查找 解题模板
**核心思路**：有序序列中查找边界
```
def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1  # 或 left (插入位置)
```
**常见题型**：查找边界值、旋转数组搜索
**关键技巧**：注意边界条件<= vs <，和mid取整方向
""",
    "栈 / 队列": """
### 栈 / 队列 解题模板
**核心思路**：单调栈维护最近最大/最小值
```
def solve(nums):
    stack = []
    result = [-1] * len(nums)
    for i in range(len(nums)):
        while stack and nums[stack[-1]] < nums[i]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)
    return result
```
**常见题型**：括号匹配、单调栈、表达式求值
**关键技巧**：栈中存下标而不是值，方便计算距离
""",
    "树 / Tree": """
### 树 / Tree 解题模板
**核心思路**：递归遍历（前/中/后序）或层序BFS
```
# 递归遍历
def traverse(root):
    if not root:
        return
    # 前序: print(root.val)
    traverse(root.left)
    # 中序: print(root.val)
    traverse(root.right)
    # 后序: print(root.val)
```
```
# 层序BFS
from collections import deque
def bfs(root):
    q = deque([root])
    while q:
        node = q.popleft()
        if node.left: q.append(node.left)
        if node.right: q.append(node.right)
```
**常见题型**：遍历、最近公共祖先、BST验证
**关键技巧**：递归时明确子问题、层序BFS模板
""",
    "回溯 / 递归": """
### 回溯 / 递归 解题模板
**核心思路**：做选择→递归→撤销选择
```
def backtrack(path, choices):
    if 满足条件:
        result.append(path[:])
        return
    for choice in choices:
        # 做选择
        path.append(choice)
        # 递归
        backtrack(path, 新choices)
        # 撤销选择
        path.pop()
```
**常见题型**：全排列、组合、子集、N皇后
**关键技巧**：剪枝优化（排序去重、合法性检查）
""",
    "贪心 / Greedy": """
### 贪心 / Greedy 解题模板
**核心思路**：每步选当前最优，需证明局部最优=全局最优
```
def solve(nums):
    # 排序是关键步骤
    nums.sort()
    result = 0
    for i in range(len(nums)):
        # 每步取最优
        pass
    return result
```
**常见题型**：区间调度、活动选择、任务规划
**关键技巧**：排序是贪心最常见预处理手段
""",
    "动态规划 / DP": """
### 动态规划 / DP 解题模板
**核心思路**：状态定义→状态转移→初始化→遍历顺序
```
def solve(nums):
    n = len(nums)
    # 1. 定义dp数组
    dp = [0] * n
    # 2. 初始化
    dp[0] = nums[0]
    # 3. 状态转移
    for i in range(1, n):
        dp[i] = max(dp[i-1] + nums[i], nums[i])
    # 4. 返回结果
    return max(dp)
```
**常见类型**：
- 线性DP: 最大子数组和、LIS
- 二维DP: 编辑距离、LCS
- 背包DP: 0-1背包、完全背包
- 区间DP: 回文分割
**关键技巧**：先想状态定义→再想转移方程→再想遍历顺序
""",
    "图论": """
### 图论 解题模板
**核心思路**：DFS/BFS遍历，邻接表/邻接矩阵
```
# BFS模板（最短路/层序遍历）
from collections import deque
def bfs(graph, start):
    visited = {start}
    q = deque([start])
    while q:
        node = q.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                q.append(neighbor)
```
```
# DFS模板（遍历/连通性）
def dfs(graph, node, visited):
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)
```
**常见题型**：岛屿数量、拓扑排序、图的遍历
**关键技巧**：BFS求最短路径，DFS求连通分量
""",
    "并查集 / Union-Find": """
### 并查集 解题模板
**核心思路**：查找+合并，路径压缩+按秩合并
```
class UnionFind:
    def __init__(self, n):
        self.fa = list(range(n))
        self.rank = [1] * n
        self.count = n

    def find(self, x):
        if self.fa[x] != x:
            self.fa[x] = self.find(self.fa[x])
        return self.fa[x]

    def union(self, x, y):
        xr, yr = self.find(x), self.find(y)
        if xr == yr: return
        if self.rank[xr] < self.rank[yr]:
            xr, yr = yr, xr
        self.fa[yr] = xr
        self.rank[xr] += self.rank[yr]
        self.count -= 1
```
**常见题型**：连通分量、朋友圈、发广播
**关键技巧**：路径压缩是性能关键
""",
    "堆 / Heap": """
### 堆 / Heap 解题模板
**核心思路**：大顶堆/小顶堆维护TopK
```
import heapq
# Python默认小顶堆
heap = []
heapq.heappush(heap, val)
val = heapq.heappop(heap)

# 大顶堆：存负数
heapq.heappush(heap, -val)
max_val = -heapq.heappop(heap)
```
**常见题型**：TopK、数据流中位数、合并K个有序链表
**关键技巧**：求第K大用最小堆，求第K小用最大堆
""",
    "前缀和 / 差分": """
### 前缀和 / 差分 解题模板
**核心思路**：预处理前缀和数组，O(1)求区间和
```
# 前缀和
pre = [0]
for x in nums:
    pre.append(pre[-1] + x)
# 区间[i, j]和 = pre[j+1] - pre[i]

# 差分（区间增减操作）
diff = [0] * (n + 1)
diff[l] += val
diff[r+1] -= val
# 还原
for i in range(1, n):
    diff[i] += diff[i-1]
```
**常见题型**：子数组和、区间增减、二维前缀和
**关键技巧**：前缀和数组长度多1，避免边界判断
""",
    "区间问题": """
### 区间问题 解题模板
**核心思路**：排序后合并/交集
```
def merge(intervals):
    intervals.sort(key=lambda x: x[0])
    result = [intervals[0]]
    for s, e in intervals[1:]:
        if s <= result[-1][1]:
            result[-1][1] = max(result[-1][1], e)
        else:
            result.append([s, e])
    return result
```
**常见题型**：合并区间、区间交集、会议室
**关键技巧**：按起点排序是关键第一步
""",
    "最短路径": """
### 最短路径 解题模板
```
# Dijkstra（单源无负权）
import heapq
def dijkstra(graph, start):
    dist = {node: float('inf') for node in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist[node]: continue
        for neighbor, w in graph[node]:
            nd = d + w
            if nd < dist[neighbor]:
                dist[neighbor] = nd
                heapq.heappush(pq, (nd, neighbor))
    return dist
```
**常见题型**：单源最短路径、网络延迟
**关键技巧**：Dijkstra+BFS模板化，注意visited优化
""",
    "拓扑排序": """
### 拓扑排序 解题模板
**核心思路**：入度表+BFS/DFS
```
from collections import deque
def topological_sort(n, edges):
    graph = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v in edges:
        graph[u].append(v)
        indeg[v] += 1
    q = deque([i for i in range(n) if indeg[i] == 0])
    result = []
    while q:
        u = q.popleft()
        result.append(u)
        for v in graph[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return result if len(result) == n else []
```
**常见题型**：课程表、编译依赖、任务调度
**关键技巧**：入度为0入队，有环则返回空
""",
    "数学 / 数论": """
### 数学 / 数论 解题模板
**常见技巧**：
- 素数判断: 试除法到sqrt(n)
- gcd/lcm: math.gcd
- 快速幂: pow(x, n, mod)
- 质因数分解: 试除法
- 找规律: 模拟小数据推公式
**关键技巧**：大数据量时找数学公式而非模拟
""",
    "数学 / 位运算": """
### 位运算 解题模板
**常用操作**：
- 判断奇偶: n & 1
- 取第k位: (n >> k) & 1
- 移除最低1: n & (n-1)
- 获取最低1: n & -n
- 异或性质: a ^ a = 0, a ^ 0 = a
**常见题型**：二进制计数、异或找唯一数
**关键技巧**：熟记常用位运算公式
""",
    "模拟 / 实现": """
### 模拟 / 实现 解题模板
**核心思路**：忠实模拟题目描述的过程
```
def solve(data):
    # 1. 解析输入
    # 2. 准备数据结构
    # 3. 按规则模拟每一步
    # 4. 输出结果
    pass
```
**关键技巧**：
- 先理清所有规则再写代码
- 复杂逻辑拆成多个小函数
- 注意边界条件和特殊用例
""",
    "滑动窗口": """
### 滑动窗口 解题模板
**核心思路**：维护窗口[left, right)，记录窗口状态
```
def solve(s):
    n = len(s)
    left = 0
    window = {}
    for right in range(n):
        window[s[right]] = window.get(s[right], 0) + 1
        while need_shrink(window):
            window[s[left]] -= 1
            left += 1
        ans = max(ans, right - left + 1)
    return ans
```
**常见题型**：最长无重复子串、最小覆盖子串
**关键技巧**：窗口内状态用Counter/哈希表维护
""",
    "未分类 / Other": """
### 其他题型
**建议**：
1. 仔细阅读题目描述，识别核心数据结构
2. 尝试暴力解→分析瓶颈→优化
3. 考虑所有常见算法：DP/贪心/图/二分
4. 看看题解中提到的算法关键词
**万能调试法**：先小规模模拟，再写代码
""",
}


TITLE_CATEGORY_MAP = [
    (r"并查集|连通分量|朋友圈|发广播|快递主站点|快递业务站|开心消消乐|计算快递", "并查集 / Union-Find"),
    (r"图|BFS|DFS|广度优先|深度优先|拓扑排序|拓扑|最短路径|Dijkstra", "图论"),
    (r"网络|路由|通信误码|信号|荒岛求生|周末爬山|战场索敌|可以组成网络", "图论"),
    (r"迷宫|探险|机器人移动|机器人活动|服务器", "图论"),
    (r"电脑病毒感染|网络延迟|报文回路|环路", "图论"),
    (r"二叉树|树|BST|二叉搜索|完全二叉树|三叉搜索树", "树 / Tree"),
    (r"中序遍历|前序遍历|后序遍历|层序遍历|叶子|节点|祖先|LCA", "树 / Tree"),
    (r"动态规划|DP|背包|LIS|LCS|股票|收益|买卖", "动态规划 / DP"),
    (r"分积木|分苹果|分披萨|几何平均值|取出球|打家劫舍", "动态规划 / DP"),
    (r"爬楼梯|跳跃游戏|跳到终点|不同路径|最小路径和", "动态规划 / DP"),
    (r"编辑距离|回文子串|最长回文|最大子数组和|最大和", "动态规划 / DP"),
    (r"任务调度|调度|任务规划|高效的任务规划", "动态规划 / DP"),
    (r"贪心|Greedy|贪心商人|贪心歌手|区间连接器|最多的宝石", "贪心 / Greedy"),
    (r"活动选择|加油站", "贪心 / Greedy"),
    (r"字符串|加密|解密|摘要|通配符|字符串分割|字符串排序", "字符串"),
    (r"完美走位|字符统计|单词反转|句子反转|括号匹配|括号生成", "字符串"),
    (r"正则|KMP|字典序|重排|替换|反转", "字符串"),
    (r"螺旋数字矩阵|矩阵最大值|矩阵扩散|数值同化|最大矩阵和", "数组 / 矩阵"),
    (r"数组去重|数组拼接|数据分类|数据整理", "数组 / 矩阵"),
    (r"栈|队列|最大括号深度|空栈压数|符号运算|打印机", "栈 / 队列"),
    (r"支持优先级的队列", "栈 / 队列"),
    (r"堆|TopK|第K|最大堆|最小堆|优先队列|数据流", "堆 / Heap"),
    (r"两数之和|三数之和|四数之和|最接近的三数之和", "哈希表"),
    (r"双指针|快慢指针|左右指针|三数|盛水", "双指针"),
    (r"滑动窗口|最长无重复|连续子串|连续子数组", "滑动窗口"),
    (r"二分查找|二分法|折半", "二分查找"),
    (r"回溯|全排列|组合|子集|N皇后|八皇后|棋盘|电路板", "回溯 / 递归"),
    (r"素数|质数|回文数|因数|整除|约数|自然数", "数学 / 数论"),
    (r"位运算|异或|XOR|进制|二进制", "数学 / 位运算"),
    (r"模拟|斗地主|顺子|跳房子|转盘寿司|篮球游戏|五子棋", "模拟 / 实现"),
    (r"猜数字|比赛|冠亚季军|排名|分班", "模拟 / 实现"),
    (r"排序|第K大|中位数", "排序"),
    (r"前缀和|差分|区间和|子数组和", "前缀和 / 差分"),
    (r"记忆化|备忘录", "记忆化搜索"),
    (r"最小生成树|Kruskal|Prim", "最小生成树"),
    (r"最短路径|Dijkstra|SPFA|Floyd|Bellman", "最短路径"),
    (r"拓扑|依赖|课程表|编译", "拓扑排序"),
    (r"子串|子串|最长.*子串|回文子串", "字符串 / 子串"),
    (r"子数组|子数组和|最大子数组", "数组 / 子数组"),
    (r"滑动窗口|窗口", "滑动窗口"),
    (r"不含101|位运算|异或|或电路|二进制|进制转换", "数学 / 位运算"),
    (r"比大小|比较|排序|排列|第[kK]个|第[kK]大", "排序 / 查找"),
    (r"游戏|比赛|猜数字|斗地主|骰子|扑克|棋子|围棋", "模拟 / 实现"),
    (r"编码|解码|压缩|解压缩|加密|解密", "字符串"),
    (r"区间交叠|区间交集|区间合并|连接器|区间", "区间问题"),
    (r"过河|农夫|羊狼|过河", "图论 / BFS"),
    (r"购物|优惠|商城|最优|资源分配|方案", "动态规划 / DP"),
    (r"快检|核酸检测|检测", "并查集 / Union-Find"),
    (r"手机|App|防沉迷|系统|软件", "模拟 / 实现"),
    (r"停车场|车辆|车位|交通", "模拟 / 实现"),
    (r"身高|排队|调整座位|座位", "数组 / 模拟"),
    (r"算术|计算|数学|数论|数字游戏|自然数", "数学 / 数论"),
    (r"单词接龙|单词搜索|单词倒序|英文输入", "字符串"),
    (r"日志|打卡|记录|统计|流量|数据", "模拟 / 实现"),
    (r"分配|调度|人员|分组|团队|队伍", "贪心 / Greedy"),
    (r"转盘|寿司|打印机|编辑|编辑器|输入法", "模拟 / 实现"),
    (r"N皇后|八皇后|棋盘|格子", "回溯 / 递归"),
    (r"跳跃|跳格子|爬楼梯|登山|攀登", "动态规划 / DP"),
    (r"最大利润|股票|收益|买卖", "动态规划 / DP"),
    (r"数位|digit|不含", "数学 / 数论"),
    (r"报数|约瑟夫|循环|数到", "模拟 / 实现"),
    (r"括号|表达式|计算|运算", "栈 / 队列"),
    (r"缓存|LFU|LRU|内存|文件系统", "堆 / Heap"),
]

SOLUTION_SECTION_RULES = [
    (r"并查集|UnionFindSet|union.find|连通分量", "并查集 / Union-Find"),
    (r"DFS|深度优先搜索|BFS|广度优先搜索|拓扑排序", "图论"),
    (r"Dijkstra|最短路径|SPFA|Floyd|Bellman-Ford", "最短路径"),
    (r"最小生成树|Kruskal|Prim算法", "最小生成树"),
    (r"动态规划|状态转移方程|dp数组|dp\s*\[|背包问题|LIS|LCS", "动态规划 / DP"),
    (r"贪心策略|贪心算法|贪心思想|每次都选择|局部最优", "贪心 / Greedy"),
    (r"滑动窗口|维护一个窗口|窗口收缩|窗口扩张|最小覆盖子串", "滑动窗口"),
    (r"双指针|左右指针|快慢指针|相向|对撞指针", "双指针"),
    (r"二分查找|二分法|二分搜索|binary search|折半查找", "二分查找"),
    (r"回溯算法|回溯法|递归回溯|剪枝|深度优先搜索.+回溯|全排列|组合", "回溯 / 递归"),
    (r"单调栈|单调递减栈|单调递增栈|单调队列|下一个更大|下一个更小", "栈 / 队列"),
    (r"优先级队列|优先队列|堆排序|最大堆|最小堆|TopK|topk|大根堆|小根堆", "堆 / Heap"),
    (r"前缀和|差分数组|差分法", "前缀和 / 差分"),
    (r"记忆化搜索|备忘录|memoization", "记忆化搜索"),
    (r"位运算|异或运算|按位与|按位或|左移|右移|XOR|二进制", "数学 / 位运算"),
    (r"哈希表|HashMap|HashSet|哈希集合|哈希映射|统计.*字符.*次数", "哈希表"),
    (r"二叉树|BST|二叉搜索树|中序遍历|前序遍历|后序遍历|层序遍历|树", "树 / Tree"),
    (r"字符串匹配|KMP|字典树|Trie|字符串处理|子串", "字符串"),
    (r"排序算法|快速排序|归并排序|计数排序|桶排序|中位数", "排序"),
    (r"模拟过程|模拟题|直接模拟", "模拟 / 实现"),
    (r"矩阵|二维数组|螺旋遍历", "数组 / 矩阵"),
    (r"区间合并|区间覆盖|区间调度|区间交叠|贪心.+区间", "区间问题"),
    (r"约瑟夫环|循环链表|报数", "模拟 / 实现"),
    (r"缓存淘汰|LRU|LFU|最近最少使用", "堆 / Heap"),
    (r"(?i)greedy|贪心选择|贪心性质|贪心策略", "贪心 / Greedy"),
    (r"统计.*字符|字符.*统计|字母.*统计", "哈希表"),
    (r"最大公约数|最小公倍数|gcd|lcm|因数分解|质因数|素数筛", "数学 / 数论"),
    (r"中位数定理|找规律", "数学 / 数论"),
    (r"转二进制|十六进制|进制", "数学 / 位运算"),
    (r"双循环|双重for|双重循环", "模拟 / 实现"),
    (r"二分图|染色|欧拉", "图论"),
    (r"数位DP|数位", "动态规划 / DP"),
    (r"自定义排序|排序规则|Comparator", "排序"),
]


def parse_filename(filename):
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    return {
        "volume": m.group("volume"),
        "score": int(m.group("score")),
        "title": m.group("title").strip(),
        "languages": [lang.strip() for lang in m.group("languages").replace("（", "(").replace("）", ")").split("&")],
    }


def extract_solution_section(html_content):
    if not html_content:
        return ""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'&#x[0-9a-f]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    patterns = [
        r'题目解析\s*(.*?)(?=算法源码|JavaScript算法|Java算法|Python算法|C\+\+|Go算法|JS算法)',
        r'题解\s*(.*?)(?=算法源码|JavaScript算法|Java算法|Python算法|C\+\+|Go算法|JS算法)',
        r'解题思路\s*(.*?)(?=算法源码|JavaScript算法|Java算法|Python算法|C\+\+|Go算法|JS算法)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            section = m.group(1).strip()
            if len(section) > 20:
                return section
    return text


def extract_categories_from_title(title):
    categories = set()
    for pattern, category in TITLE_CATEGORY_MAP:
        if re.search(pattern, title):
            categories.add(category)
    return categories


def extract_categories_from_solution(solution_text):
    if not solution_text:
        return set()
    categories = set()
    for pattern, category in SOLUTION_SECTION_RULES:
        if re.search(pattern, solution_text, re.IGNORECASE):
            categories.add(category)
    return categories


def categorize_problem(meta, html_content):
    categories = set()
    title_cats = extract_categories_from_title(meta["title"])
    categories.update(title_cats)
    solution_text = extract_solution_section(html_content)
    solution_cats = extract_categories_from_solution(solution_text)
    categories.update(solution_cats)
    title = meta["title"]
    if "图" in title and "图论" not in categories:
        categories.add("图论")
    return sorted(categories) if categories else ["未分类 / Other"]


def extract_volume_order(volume):
    order = {"A卷": 1, "双机位A卷": 2, "B卷": 3, "双机位B卷": 4,
             "C卷": 5, "双机位C卷": 6, "CD卷": 7, "D卷": 8, "E卷": 9}
    for k, v in order.items():
        if k in volume:
            return v
    return 99


def scan_problems():
    problems = []
    seen_titles = set()

    for rel_dir in SCAN_DIRS:
        scan_path = BASE_DIR / rel_dir
        if not scan_path.exists():
            continue
        html_files = list(scan_path.glob("*.html")) + list(scan_path.glob("*.md"))
        for fpath in sorted(html_files):
            if fpath.suffix not in (".html", ".md"):
                continue
            meta = parse_filename(fpath.name)
            if not meta:
                continue
            dedup_key = (meta["title"], meta["score"])
            if dedup_key in seen_titles:
                continue
            seen_titles.add(dedup_key)
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            categories = categorize_problem(meta, content)
            volume_order = extract_volume_order(meta["volume"])
            difficulty = calc_difficulty(categories, meta["score"])
            phase = calc_study_phase(categories)
            problems.append({
                "title": meta["title"],
                "volume": meta["volume"],
                "score": meta["score"],
                "difficulty": difficulty,
                "phase": phase,
                "languages": " & ".join(meta["languages"]),
                "file_path": str(fpath.relative_to(BASE_DIR)),
                "categories": categories,
                "volume_order": volume_order,
            })
    return problems


def build_database(problems):
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA encoding='UTF-8'")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            volume TEXT,
            volume_order INTEGER DEFAULT 99,
            score INTEGER,
            difficulty TEXT DEFAULT '简单',
            phase TEXT DEFAULT 'P1-基础',
            languages TEXT,
            file_path TEXT,
            UNIQUE(title, score)
        )
    """)

    c.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            phase TEXT DEFAULT 'P5-综合',
            template TEXT
        )
    """)

    c.execute("""
        CREATE TABLE problem_categories (
            problem_id INTEGER,
            category_id INTEGER,
            FOREIGN KEY (problem_id) REFERENCES problems(id),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            PRIMARY KEY (problem_id, category_id)
        )
    """)

    all_cats = set()
    for p in problems:
        all_cats.update(p["categories"])
    all_cats = sorted(all_cats)

    for i, cat in enumerate(all_cats):
        phase = calc_study_phase([cat])
        template = TEMPLATES.get(cat, "")
        c.execute("INSERT OR IGNORE INTO categories (name, sort_order, phase, template) VALUES (?, ?, ?, ?)",
                  (cat, i, phase, template))

    c.execute("SELECT id, name FROM categories")
    cat_map = {row[1]: row[0] for row in c.fetchall()}

    for p in problems:
        c.execute("""
            INSERT OR REPLACE INTO problems (title, volume, volume_order, score, difficulty, phase, languages, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["title"], p["volume"], p["volume_order"], p["score"],
              p["difficulty"], p["phase"], p["languages"], p["file_path"]))

        c.execute("SELECT id FROM problems WHERE title=? AND score=?", (p["title"], p["score"]))
        problem_id = c.fetchone()[0]

        for cat in p["categories"]:
            c.execute("""
                INSERT OR REPLACE INTO problem_categories (problem_id, category_id)
                VALUES (?, ?)
            """, (problem_id, cat_map[cat]))

    conn.commit()
    conn.close()
    return len(problems)


def print_study_plan(problems):
    """打印刷题路线"""
    print(f"\n{'=' * 60}")
    print(f"  📚 推荐刷题路线")
    print(f"{'=' * 60}\n")

    phases_data = {}
    for p in problems:
        phase = p["phase"]
        if phase not in phases_data:
            phases_data[phase] = {"count": 0, "categories": {}}
        phases_data[phase]["count"] += 1
        for cat in p["categories"]:
            phases_data[phase]["categories"][cat] = phases_data[phase]["categories"].get(cat, 0) + 1

    sorted_phases = sorted(phases_data.items(), key=lambda x: PHASE_ORDER.get(x[0], 99))

    for phase_name, info in sorted_phases:
        emoji = {"P1-基础": "1️⃣", "P2-核心": "2️⃣", "P3-进阶": "3️⃣",
                 "P4-高阶": "4️⃣", "P5-综合": "5️⃣"}.get(phase_name, "📌")
        print(f"  {emoji} {phase_name}（{info['count']} 题）")
        print(f"    涉及题型：")
        sorted_cats = sorted(info["categories"].items(), key=lambda x: -x[1])
        for cat, cnt in sorted_cats:
            diff_counts = {"简单": 0, "中等": 0, "困难": 0}
            for p in problems:
                if p["phase"] == phase_name and cat in p["categories"]:
                    diff_counts[p["difficulty"]] = diff_counts.get(p["difficulty"], 0) + 1
            parts = []
            if diff_counts.get("简单"): parts.append(f"简单{diff_counts['简单']}")
            if diff_counts.get("中等"): parts.append(f"中等{diff_counts['中等']}")
            if diff_counts.get("困难"): parts.append(f"困难{diff_counts['困难']}")
            print(f"      · {cat:25s} {cnt:3d} 题 [{', '.join(parts)}]")
        print()

    print(f"  💡 查看解题模板: python query_kb.py -t '<分类名>'")
    print(f"  或启动 Web 界面后点击「解题模板」标签\n")


def main():
    print("=" * 60)
    print("  华为 OD 刷题知识库构建工具")
    print("=" * 60)

    print("\n[1/3] 扫描题目文件...")
    problems = scan_problems()
    print(f"\n  共发现 {len(problems)} 道不重复的题目\n")

    print("[2/3] 构建 SQLite 知识库...")
    count = build_database(problems)
    print(f"  知识库已保存到: {DB_PATH}")
    print(f"  共入库 {count} 道题目\n")

    print("[3/3] 分类统计")
    stats = {}
    for p in problems:
        for cat in p["categories"]:
            stats[cat] = stats.get(cat, 0) + 1
    sorted_stats = sorted(stats.items(), key=lambda x: -x[1])
    cat_count = len(sorted_stats)
    print(f"  共 {cat_count} 个分类：\n")
    for cat, cnt in sorted_stats:
        print(f"    {cat}: {cnt} 题")
    print()

    # 难度分布
    diff_stats = {"简单": 0, "中等": 0, "困难": 0}
    for p in problems:
        diff_stats[p["difficulty"]] = diff_stats.get(p["difficulty"], 0) + 1
    print(f"  难度分布：")
    for d in ["简单", "中等", "困难"]:
        print(f"    {d}: {diff_stats.get(d, 0)} 题")
    print()

    # 刷题路线
    print_study_plan(problems)

    print(f"\n{'=' * 60}")
    print(f"  知识库构建完成！共 {count} 题，{cat_count} 个分类")
    print(f"  使用 query_kb.py 查询知识库")
    print(f"  使用 web_kb.py 启动可视化界面")
    print(f"{'=' * 60}")

    return problems


if __name__ == "__main__":
    main()
