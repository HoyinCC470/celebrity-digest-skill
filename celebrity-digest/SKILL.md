---
name: celebrity-digest
description: >
  张凌赫每日微博动态摘要生成器。基于白名单账号的微博动态，去噪过滤、主题聚类、挑选代表帖 + 极简摘要 + 互动数据，输出极致紧凑型 Markdown 日报到当前对话。
  触发词：张凌赫日报、明星日报、追星 digest、偶像动态、白名单追踪、celebrity digest、艺人日报、fan-account digest、行程日报。
  当用户说"今天张凌赫有什么动态"、"给我看一下追星日报"、"运行 celebrity-digest"时使用。
metadata:
  category: productivity
---

# Celebrity Digest — 张凌赫每日微博动态摘要

将白名单内粉圈账号的当日微博动态进行去噪、聚类、代表帖筛选与高保真摘要，输出极致紧凑的 Markdown 日报到当前对话。

## 运行

直接执行抓取脚本：

```bash
python3 scripts/fetch_feeds.py
```

不传 `--date` 时默认取昨天数据。指定日期：

```bash
python3 scripts/fetch_feeds.py --date "YYYY-MM-DD"
```

只抓某一组：

```bash
python3 scripts/fetch_feeds.py --column "官方组"
```

脚本会逐账号调用微博 API，账号间间隔 10s 防限流，10 个账号大约需 100 秒。

**脚本返回 JSON 数组后，Agent 直接进入分析流程（Step 2）。**

---

## 出错处理

运行脚本后如果报错，按下面的表定位问题：

| 报错信息 | 原因 | 处理 |
|---------|------|------|
| `python3: command not found` | Python 3 未安装 | macOS: `brew install python3`，Linux: `sudo apt install python3` |
| `mcporter not found` 前缀 | mcporter 未安装或不在 PATH | `npm install -g mcporter`，装完确认 `which mcporter` 有输出 |
| `Error: Whitelist file not found` | 脚本找不到白名单 JSON | 确认 `references/whitelist-zlh.json` 存在，或用 `--whitelist` 指定绝对路径 |
| `weibo.get_feeds` 返回 error | weibo MCP 未注册或限流 |     先跑 `mcporter list \| grep weibo` 确认 weibo 已注册。如果没有，需要手动配置 weibo MCP server（参考 `references/weibo-fetch.md`）。如果已注册但仍报错，可能被限流，等几分钟后重试 |
| `TimeoutExpired` | 单个账号请求超时 | 网络问题，重试即可 |
| 返回 `[]` 空数组 | 目标日期无发帖或被限流 | 告知用户，换一个日期重试 |
| `Invalid JSON response` | 微博 API 返回了非 JSON 内容 | 可能被限流，等几分钟后重试 |

**原则：能装就装，装不上就把完整错误信息给用户，说清楚什么装不了、为什么、用户需要做什么。不要猜，不要假设依赖不在。**

---

## Agent 侧分析（Step 2）

Agent 读取脚本输出的 JSON 数据，在自身认知中执行：

1. **去噪过滤**：排除正文少于 5 字且无图无话题的超短水帖或打卡。
2. **主题聚类**：依据 `#话题#` 或文本语义相似度（如："开始推理吧"、"适乐肤"、"高考加油"），将同一事件的帖子聚类为一个"合并主题"。
3. **计算热度与筛选代表帖**：`Engagement = attitudes_count + reposts_count + 0.5 × comments_count`，挑每个合并主题中 engagement 最高的帖子。
4. **清理内容噪音**：
   - 过滤代表帖正文中的所有 `#话题名称#` 标签
   - 去除皇冠 Emoji `👑`

## 输出排版（Step 3）

Agent 按照**极致紧凑风格（终版极简）**输出到当前对话：

- **🎯 今日动态总结**：仅保留大事件的主题标题列表，不含冒号和后置描述。某组无新帖则标注 `* [组名] 当日无新动态`。
- **📢 动态详情（极致紧凑版）**：每个主题项统一结构：
  - `### [序号]. [Emoji] [主题名]`（不带合并数量）
  - `* ` 一句话极简总结（28-35 字。不带"总结："前缀，完全去除"工作室"、"视频组"、"后援会"等角色前缀。措辞热情激动的饭圈风格，用"超绝"、"高甜"、"排面"、"高燃"等情绪词，直接描述动态核心事实）
  - `* 🔗 [微博正文](链接)`
  - `* 🔁 [转发] / 💬 [评论] / ❤️ [点赞]`（互动数据独立成行，不加括号）

详细排版规范见 `references/styles.md`。

---

## 已知避坑

1. **`raw_text` 永远为空**：脚本已将 HTML 标签清洗，使用 `text` 清洗后的纯文本。
2. **Weibo 互动字段**：真实字段在根节点 `attitudes_count`（点赞）、`reposts_count`（转发）、`comments_count`（评论），不在嵌套的 `counts` 字典内。脚本已修正。
3. **微博限流**：脚本已内置 10s 间隔，如仍被限流，返回空数据属正常，稍后重试。

更多细节见 `references/weibo-fetch.md`。