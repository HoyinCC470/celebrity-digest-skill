# Celebrity Digest

张凌赫每日微博动态摘要 — 一句话安装，沙箱里也能跑的明星日报 Skill。

## 安装

```bash
npx skills add HoyinCC470/celebrity-digest-skill -g --all
```

## 依赖

**只有 Python 3。** Jina Reader 使用标准库 `urllib`，零额外 pip 包。不需要 mcporter、不需要 weibo MCP、不需要 Cookie。

## 运行

```bash
python3 scripts/fetch_feeds.py
```

默认抓取昨天数据。指定日期：

```bash
python3 scripts/fetch_feeds.py --date "2026-06-09"
```

脚本输出 JSON，由 Agent 做去噪、聚类、摘要，最终生成极致紧凑的 Markdown 日报。

## 触发词

张凌赫日报、明星日报、追星 digest、celebrity digest、行程日报

## 结构

```
celebrity-digest/
├── SKILL.md
├── scripts/
│   └── fetch_feeds.py          # Jina Reader 抓取，默认方式
└── references/
    ├── styles.md               # 排版规范
    ├── whitelist-zlh.json      # 张凌赫白名单
    └── weibo-fetch.md          # API 文档
```
