# 微博数据抓取

celebrity-digest 的数据采集层。支持两种方式：

## 方式一：Jina Reader（默认，推荐）

通过 Jina Reader 代理访问微博移动端 API，**无需登录、无需 Cookie、无需 mcporter**。

```
URL: https://r.jina.ai/https://m.weibo.cn/api/container/getIndex?type=uid&value={UID}&containerid={CONTAINER_ID}
```

- Container ID 规则：`107603{UID}`（微博 tab）
- 自动生成访客 Cookie，不受 432 限制
- 3 秒间隔防限流
- 偶尔 503 属正常，重试即可

### 字段映射（Jina Reader 返回结构）

Jina Reader 将微博 API JSON 包装在 Markdown Content 中，脚本自动提取。返回结构与原始 API 一致：

```json
{
  "id": "5307989066257928",
  "text": "...HTML + 表情短代码...",
  "mblog_text": "...纯文本备选字段...",
  "created_at": "Tue Jun 09 20:04:34 +0800 2026",
  "created_at_timestamp": 1749463474,
  "attitudes_count": 514,
  "reposts_count": 24,
  "comments_count": 34,
  "like_count": 514,
  "pics": [{"url": "...", "pid": "..."}],
  "user": {"id": 6458278005, "screen_name": "张凌赫全球粉丝后援会"}
}
```

**字段差异处理**：
- `like_count` 和 `attitudes_count` 都可能出现，脚本统一取 `attitudes_count`，fallback 到 `like_count`
- `mblog_text` 是 `text` 的纯文本备选，脚本优先用清洗后的 `text`
- `created_at_timestamp` 在 `created_at` 解析失败时作为 fallback

## 方式二：mcporter weibo MCP（备选）

通过 mcporter 调用 `mcp-server-weibo`，**需要 mcporter 和 weibo MCP 已注册**。

```bash
mcporter call 'weibo.get_feeds(uid: UID, limit: 10)'
mcporter call 'weibo.search_users(keyword: "名称", limit: 10)'
mcporter call 'weibo.search_content(keyword: "关键词", limit: 15)'
```

**注意**：mcporter 方式依赖 `mcp-server-weibo` 包，该包不发送 Cookie，微博 API 对无 Cookie 请求返回 432（空数据）。如果需要使用 mcporter 方式，必须配置微博 Cookie。

## 互动量计算

```python
engagement = attitudes_count + reposts_count + 0.5 * comments_count
```

选代表帖时按 `engagement` 降序排，**不**看时间。

## 死号判定

使用 Jina Reader 方式：

```
curl -s "https://r.jina.ai/https://m.weibo.cn/api/container/getIndex?type=uid&value={UID}" | python3 -c "import sys,json; ..."
# 返回数据中有 userInfo → 存活；为空或 503 → 可能限流或死号
```

白名单每隔 1-2 周巡检一次，剔除死号。