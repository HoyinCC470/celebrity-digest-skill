# 微博 MCP 抓取细节

celebrity-digest 的数据采集层。

## 工具

```bash
mcporter call 'weibo.get_feeds(uid: UID, limit: 10)'
mcporter call 'weibo.search_users(keyword: "名称")'
mcporter call 'weibo.search_content(keyword: "关键词", limit: 15)'
mcporter call 'weibo.get_comments(feed_id: FEED_ID)'
```

无需 Cookie 登录。

## 字段映射（get_feeds 返回结构）

```json
{
  "id": "5306179907486538",
  "text": "...HTML + 表情短代码...",
  "raw_text": "",
  "created_at": "Thu Jun 04 20:15:00 +0800 2026",
  "pics": [{"url": "https://wx1.sinaimg.cn/...", "pid": "..."}],
  "videos": [],
  "counts": {
    "likes": 12,
    "reposts": 7,
    "comments": 10
  },
  "user": {"id": 7503034355, "screen_name": "张凌赫核桃种植园"}
}
```

**重要**：`raw_text` 永远为空，使用 `text` 字段（经脚本 HTML 清洗后的纯文本）。

真实互动字段在根节点：`attitudes_count`（点赞）、`reposts_count`（转发）、`comments_count`（评论），不在 `counts` 内。

**Source URL 拼接**：`https://weibo.com/{user.id}/{id}`

## 限流策略

| 模式 | 触发条件 | 应对 |
|------|---------|------|
| `limit=15` × 10 账号 / 分钟 | 撞上限速 | 改 `limit=10` + `sleep 10s` |
| 单条 `get_feeds` 返回空 | 账号被限流/已死 | `sleep 15` 重试一次，仍空视为死号 |

## 死号判定

`search_users` 不可靠，判定流程必须用 `get_feeds`：

```bash
result=$(mcporter call "weibo.get_feeds(uid: $uid, limit: 1)" 2>/dev/null)
# mblog 数 > 0 → 存活；返回空/error → 从白名单剔除
```