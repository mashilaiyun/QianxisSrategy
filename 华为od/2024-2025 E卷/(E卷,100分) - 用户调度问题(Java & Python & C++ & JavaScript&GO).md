# 题目描述

在通信系统中，一个常见的问题是对用户进行不同策略的调度，会得到不同的系统消耗和性能。假设当前有n个待串行调度用户，每个用户可以使用A/B/C三种不同的调度策略，不同的策略会消耗不同的系统资源。请你根据如下规则进行用户调度，并返回总的消耗资源数。

规则：

1. 相邻的用户不能使用相同的调度策略，例如，第1个用户使用了A策略，则第2个用户只能使用B或者C策略。
2. 对单个用户而言，不同的调度策略对系统资源的消耗可以归一化后抽象为数值。例如，某用户分别使用A/B/C策略的系统消耗分别为15/8/17。
3. 每个用户依次选择当前所能选择的对系统资源消耗最少的策略（局部最优），如果有多个满足要求的策略，选最后一个。

# 输入描述

第一行表示用户个数n

接下来每一行表示一个用户分别使用三个策略的系统消耗resA resB resC

# 输出描述

最优策略组合下的总的系统资源消耗数

# 用例1

## 输入

```none
3
15 8 17
12 20 9
11 7 5
```

## 输出

```none
24
```

## 说明

> 1号用户使用B策略，2号用户使用C策略，3号用户使用B策略。系统资源消耗: 8 + 9 + 7 = 24。

# 题解



## c++

```c++
#include<iostream>
#include<vector>
#include<string>
#include <utility> 
#include <sstream>
#include<algorithm>
#include<climits>
using namespace std;

//获取当前选择的下标
int getMinElemPos(vector<int> ans, int excluePos) {
    int value = INT_MAX;
    int pos = -1;
    for (int i = 0; i < 3; i++) {
        if (i == excluePos) {
            continue;
        }
        // <= 是优先选择后面的
        if (ans[i] <= value) {
            value = ans[i];
            pos = i;
        }
    }
    return pos;
}

int main() {
    int n;
    cin >> n;
    vector<vector<int>> ans(n, vector<int>(3));
    for (int i = 0; i < n; i++) {
        cin >> ans[i][0] >> ans[i][1]>> ans[i][2];
    }
    int sum = 0;
    int last = -1;
    for (int i = 0; i < n; i++) {
        last = getMinElemPos(ans[i], last);
        sum += ans[i][last];
    }
    cout << sum;
}
```

## JAVA

```JAVA
import java.util.Scanner;

public class Main {
  public static void main(String[] args) {
    Scanner sc = new Scanner(System.in);

    int n = sc.nextInt();

    int[][] res = new int[n][3];
    for (int i = 0; i < n; i++) {
      res[i][0] = sc.nextInt();
      res[i][1] = sc.nextInt();
      res[i][2] = sc.nextInt();
    }

    System.out.println(getResult(n, res));
  }

  public static int getResult(int n, int[][] res) {
    int last = -1;
    int sum = 0;

    for (int i = 0; i < n; i++) {
      last = getMinEleIdx(res[i], last);
      sum += res[i][last];
    }

    return sum;
  }

  public static int getMinEleIdx(int[] arr, int excludeIdx) {
    int minEleVal = Integer.MAX_VALUE;
    int minEleIdx = -1;

    for (int i = 0; i < arr.length; i++) {
      if (i == excludeIdx) continue;

      if (arr[i] <= minEleVal) {
        minEleVal = arr[i];
        minEleIdx = i;
      }
    }

    return minEleIdx;
  }
}
```

## Python

```python
import sys

# 输入获取
n = int(input())
res = [list(map(int, input().split())) for _ in range(n)]


def getMinEleIdx(arr, excludeIdx):
    minEleVal = sys.maxsize
    minEleIdx = -1

    for i in range(len(arr)):
        if i == excludeIdx:
            continue

        if arr[i] <= minEleVal:
            minEleVal = arr[i]
            minEleIdx = i

    return minEleIdx


# 算法入口
def getResult():
    last = -1
    total = 0

    for i in range(n):
        last = getMinEleIdx(res[i], last)
        total += res[i][last]

    return total


# 算法调用
print(getResult())
```

## JavaScript

```js
/* JavaScript Node ACM模式 控制台输入获取 */
const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const lines = [];
let n;
rl.on("line", (line) => {
  lines.push(line);

  if (lines.length === 1) {
    n = parseInt(lines[0]);
  }

  if (n != undefined && lines.length === n + 1) {
    lines.shift();
    const res = lines.map((line) => line.split(" ").map(Number));

    console.log(getResult(n, res));

    lines.length = 0;
  }
});

function getResult(n, res) {
  let last = -1;
  let sum = 0;

  for (let i = 0; i < n; i++) {
    last = getMinEleIdx(res[i], last);
    sum += res[i][last];
  }

  return sum;
}

function getMinEleIdx(arr, excludeIdx) {
  let minEleVal = Infinity;
  let minEleIdx = -1;

  for (let i = 0; i < arr.length; i++) {
    if (i == excludeIdx) continue;

    if (arr[i] <= minEleVal) {
      minEleVal = arr[i];
      minEleIdx = i;
    }
  }

  return minEleIdx;
}
```

## Go

```go
package main

import (
	"fmt"
	"math"
)

func getMinElemPos(ans []int, excludePos int) int {
	value := math.MaxInt32
	pos := -1
	for i := 0; i < 3; i++ {
		if i == excludePos {
			continue
		}
		// 优先选择后面的
		if ans[i] <= value {
			value = ans[i]
			pos = i
		}
	}
	return pos
}

func main() {
	var n int
	fmt.Scan(&n)

	ans := make([][]int, n)
	for i := 0; i < n; i++ {
		ans[i] = make([]int, 3)
		fmt.Scan(&ans[i][0], &ans[i][1], &ans[i][2])
	}

	sum := 0
	last := -1
	for i := 0; i < n; i++ {
		last = getMinElemPos(ans[i], last)
		sum += ans[i][last]
	}

	fmt.Println(sum)
}



```

