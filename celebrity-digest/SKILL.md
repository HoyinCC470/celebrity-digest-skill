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

## 安装流程（首次运行必须按序执行）

首次触发本 Skill 时，Agent 必须按以下三步走完，任何一步失败都不要继续往下。

### Step 1: 依赖确认与安装

Agent 逐项检查以下依赖，缺什么装什么：

**1.1 Python 3**
```bash
python3 --version
```
- 有 → 通过，记下版本号
- 没有 → macOS 执行 `brew install python3`，Linux 执行 `sudo apt install python3`，装完重新检查
- 装不上 → 报告给用户，终止

**1.2 mcporter**
```bash
mcporter --version
```
- 有 → 通过
- 没有 → `npm install -g mcporter`，装完重新检查
- 装不上 → 报告给用户，终止

**1.3 weibo MCP**
```bash
mcporter list 2>&1 | grep -i weibo
```
- 能看到 `weibo (N tools, ...)` → 通过
- 没有 → Agent 无法自动注册 MCP server，告诉用户需要手动配置 weibo MCP（参考 `references/weibo-fetch.md`），终止

全部通过后，进入 Step 2。

### Step 2: MVP 冒烟测试

用一条最简单的调用验证整条链路是通的：

```bash
mcporter call "weibo.get_feeds(uid: 7051114584, limit: 1)"
```

**判断逻辑：**
- 返回 JSON 数组（哪怕是空 `[]`）→ ✅ 链路通，进入 Step 3
- 返回错误信息 → 查 `references/weibo-fetch.md` 的"已知问题"一节，看能否对应上
  - 能对应 → 按文档里的修复方式处理，然后重跑冒烟测试
  - 不能对应 → 把完整错误信息原样输出给用户，说"冒烟测试失败，以下是错误信息，我无法自动修复，请检查 MCP 配置"，终止
- 命令超时（>30s）→ 告知用户网络可能有问题，终止

### Step 3: 抓取当天数据

冒烟测试通过后，直接执行正式抓取：

```bash
python3 scripts/fetch_feeds.py
```

不传 `--date` 时默认取昨天数据。如果用户指定了日期：

```bash
python3 scripts/fetch_feeds.py --date "YYYY-MM-DD"
```

脚本会逐账号调用微博 API，账号间间隔 10s 防限流，10 个账号大约需要 100 秒。

**判断逻辑：**
- 拿到数据（即使只有少量帖子）→ 进入 Step 4 做 Agent 侧分析
- 拿到空数组 `[]` → 告知用户"目标日期无数据"，可能是当天确实无发帖或微博限流
- 脚本报错 → 把错误信息输出给用户，检查 `references/weibo-fetch.md`

---

## Agent 侧分析（Step 4）

Agent 读取脚本输出的 JSON 数据，在自身认知中执行：

1. **去噪过滤**：排除正文少于 5 字且无图无话题的超短水帖或打卡。
2. **主题聚类**：依据 `#话题#` 或文本语义相似度（如："开始推理吧"、"适乐肤"、"高考加油"），将同一事件的帖子聚类为一个"合并主题"。
3. **计算热度与筛选代表帖**：`Engagement = attitudes_count + reposts_count + 0.5 × comments_count`，挑每个合并主题中 engagement 最高的帖子。
4. **清理内容噪音**：
   - 过滤代表帖正文中的所有 `#话题名称#` 标签
   - 去除皇冠 Emoji `👑`

## 输出排版（Step 5）

Agent 按照**极致紧凑风格（终版极简）**输出到当前对话：

- **🎯 今日动态总结**：仅保留大事件的主题标题列表，不含冒号和后置描述。某组无新帖则标注 `* [组名] 当日无新动态`。
- **📢 动态详情（极致紧凑版）**：每个主题项统一结构：
  - `### [序号]. [Emoji] [主题名]`（不带合并数量）
  - `* ` 一句话极简总结（28-35 字。不带"总结："前缀，完全去除"工作室"、"视频组"、"后援会"等角色前缀。措辞热情激动的饭圈风格，用"超绝"、"高甜"、"排面"、"高燃"等情绪词，直接描述动态核心事实）
  - `* 🔗 [微博正文](链接)`
  - `* 🔁 [转发] / 💬 [评论] / ❤️ [点赞]`（互动数据独立成行，不加括号）

详细排版规范见 `references/styles.md`。

---

## 已知问题速查

| 现象 | 原因 | 处理 |
|------|------|------|
| `get_feeds` 返回 `[]` | 当前日期确实无发帖 | 告知用户，正常结束 |
| `get_feeds` 返回 error / timeout | 微博限流或 MCP 配置问题 | 建议等几分钟后重试 |
| `raw_text` 永远为空 | API 字段特性 | 使用脚本清洗后的 `text` 字段 |
| 互动数在 `counts` 字典里 | API 文档与实际不符 | 脚本已修正，直接从根节点取 `attitudes_count` / `reposts_count` / `comments_count` |
| 脚本报 `mcporter not found` | Python 子进程找不到 mcporter | 检查 mcporter 是否在 PATH 中，或用绝对路径 |

更多细节见 `references/weibo-fetch.md`。