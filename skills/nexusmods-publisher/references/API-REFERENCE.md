# Nexus Mods API 与发布 Action 参考

本文件记录经官方文档、Action 元数据/源码及示例仓库交叉核验的接口边界。Nexus Mods API 和 Action 会演进；执行实际发布前重新核对链接指向的最新版本。

## 权威来源

1. [Nexus Mods API Documentation](https://api-docs.nexusmods.com/) — 当前 v3 API 文档入口。
2. [Nexus Mods OpenAPI schema](https://github.com/Nexus-Mods/Vortex/blob/master/packages/nexus-api-v3/schema/openapi.yaml) — API 服务器、认证方案、路径、请求/响应 schema 和 upcoming changes。
3. [Nexus-Mods/upload-action](https://github.com/Nexus-Mods/upload-action) — 官方 Action 的 action.yml、README 和 TypeScript 实现。
4. [GitHub Marketplace: Upload to Nexus Mods](https://github.com/marketplace/actions/upload-to-nexus-mods) — Action 发布版本与公开输入/输出。
5. [Nexus-Mods/API-Example](https://github.com/Nexus-Mods/API-Example) — release / workflow_dispatch 自动发布示例。
6. [Agent Skills spec](https://agentskills.io/specification) 与 [Anthropic skills examples](https://github.com/anthropics/skills) — 技能目录及 SKILL.md 元数据结构。

## v3 认证与服务器

- Production base URL：**https://api.nexusmods.com/v3**
- OpenAPI 定义 ApiKeyAuth：HTTP header **apikey**。官方 upload-action 使用该 header。
- OpenAPI 还定义 Bearer JWT / service JWT 认证；不要仅凭存在该方案，就假定所有端点、普通 API key 和服务 token 可以互换。按目标 endpoint 的 security 声明选凭据。
- API key 只能放在 GitHub Secret、受控 CI secret store 或本机安全凭据管理器中。不要硬编码进源码、workflow、仓库变量或日志。

## Action 目前实现的上传生命周期

读取当前官方 action.yml 和 src/index.ts 后，上传的阶段顺序如下：

1. 读取 api_key、file_id、filename、version 等 inputs，确认 ZIP 文件存在。
2. 对 **POST /uploads/multipart** 发起 JSON 请求，当前实现发送文件 basename 和 size_bytes（十进制字符串）。
3. 使用返回的 part_presigned_urls 分片 PUT 文件数据。当前实现默认最多 6 个并发分片，并记录各分片响应的 ETag。
4. 向 complete_presigned_url 发送 CompleteMultipartUpload XML，包含 part number 与 ETag。
5. 调用 **POST /uploads/{upload_id}/finalise** 关闭上传会话。
6. 调用 **GET /uploads/{upload_id}** 轮询 upload state，直到 state 为 **available**。源码默认轮询间隔 2 秒、按 1.5 倍递增、最大 30 秒，最多 60 次。
7. 调用 **POST /mod-files/{file_id}/versions** 创建文件版本，并输出 version_id。
8. 若提供 changelog 和 mod_id，再调用 **POST /mods/{mod_id}/changelogs** 添加 changelog。

Action 当前 action.yml 声明 Node 24 runtime。README 中的开发环境最低 Node 版本说明不应覆盖实际 Action runtime 声明；按所用版本的 action.yml 核对。

### 重要 API 语义

- **/uploads/multipart** 创建的是上传会话，并非 mod 文件版本。
- finalise 成功后仍需轮询，直到状态为 **available**；不能把会话创建或分片完成直接视为版本已发布。
- **/mod-files/{id}/versions** 的 id 是既有 mod file ID。
- **/mods/{id}/changelogs** 的 id 是 mod ID。当前 OpenAPI 将该操作描述为 additive：重复调用会追加文字，不会替换旧 changelog。
- 创建全新 file entry 使用 **POST /mod-files**；上传文件后需要单独执行此端点。创建全新 mod 页面不是 upload-action 的功能。
- 预签名 PUT/complete URL 属于临时授权 URL。其请求不应再带 API key；严格按照签名所要求的方法、header 和 body 发送。

## 当前 Action Inputs / Output

| 名称 | 必填 | 说明 |
|---|---:|---|
| api_key | 是 | Nexus Mods API key |
| file_id | 是 | 目标既有 mod file ID |
| filename | 是 | runner 上待上传的 ZIP 路径 |
| version | 是 | 文件版本 |
| display_name | 否 | 展示名；默认 basename |
| description | 否 | 文件版本描述 |
| category | 否 | 文件分类；默认 main |
| archive_existing_version | 否 | 归档现有版本；默认 false |
| primary_mod_manager_download | 否 | 是否为 mod manager 默认下载 |
| allow_mod_manager_download | 否 | 是否允许 mod manager 下载 |
| show_requirements_pop_up | 否 | 是否显示 requirements 弹窗 |
| update_mod_version | 否 | 是否同步 mod 版本 |
| mod_id | 否 | 写 changelog 时必填 |
| changelog | 否 | changelog 内容；有值时要求 mod_id |

Action output：**version_id**，即创建的文件版本 ID。

参数最终以所 pin 的 Action 版本的 action.yml 为准。Marketplace 或 README 的输入表若与 action.yml 不一致，停下来检查发布 tag 与源码版本，不要猜测。

## 单段上传和 multipart 的分界

官方 OpenAPI 当前说明：

- 文件小于 100 MiB 可使用单段 **POST /uploads**；超过 100 MiB 必须使用 **POST /uploads/multipart**。
- 单段接口返回 presigned_url；PUT 上传时必须提供与创建请求 filename 匹配的 **Content-Disposition: attachment; filename="<filename>"**。
- 2026-12-01 起，单段创建上传请求的 md5 字段变为必填。请求值为 32 位十六进制摘要；上传 PUT 的 Content-MD5 header 为同一摘要的 Base64 表示。
- multipart 创建请求走独立 schema；不要把单段的 md5 约束套到 multipart 请求。
- 当前官方 Action 的 src/index.ts 使用 multipart API，不论构建 ZIP 的实际大小都走 multipart。

对自定义 API client，摘要需对最终 ZIP 计算，不要用源码目录摘要代替 ZIP 摘要。单段预签名 URL 签名约束要求的 header 必须准确匹配。

## 官方 schema 公告的近期变更

当前 OpenAPI 文档列出：

| 生效日期 | 变更 | 应对 |
|---|---|---|
| 2026-11-23 | 创建 mod file 和创建新文件版本的 description 长度最多 255 字符 | 现在就限制为不超过 255 字符 |
| 2026-12-01 | 单段 POST /uploads 请求的 md5 变为必填 | 单段客户端提前实现并在 PUT 发送匹配的 Content-MD5 |

日期根据 2026-11-17 检查的官方 schema；每次发布都应重新核对 OpenAPI 的 Upcoming Changes 区段。

## API-Example 样例与生产化差异

[Nexus-Mods/API-Example](https://github.com/Nexus-Mods/API-Example) 展示了：

- release published 和 workflow_dispatch 两种触发入口；
- checkout 使用完整 Git 历史以构建 changelog；
- 从源码/发布目录构建 ZIP；
- 从 secrets 读取 NEXUSMODS_API_KEY，从 variables 读取 NEXUSMODS_FILE_ID / NEXUSMODS_MOD_ID；
- 使用 upload-action 发布并写 changelog。

样例是展示流程，不是安全基线。它采用 **Nexus-Mods/upload-action@main** 和较旧 checkout 版本；生产 workflow 应将 Action 固定到已审查的完整 commit SHA，并按当前 Actions 运行器要求升级 checkout。为发布配置 Environment approval、workflow concurrency 和最小权限。

## 失败与重跑策略

| 阶段 | 核验 |
|---|---|
| 创建 upload session | API key、权限、文件名/大小字段、HTTP 400/403/422 |
| 上传 parts | presigned URL 有效期、分片大小、ETag、网络/超时 |
| complete multipart | 所有分片齐全、PartNumber 排序、ETag 未带多余双引号 |
| finalise / poll | 会话是否已 finalise；GET 状态是否 available |
| create file version | file_id 是否正确、版本值和分类、字段长度 |
| changelog | mod_id 是否正确、请求权限、已有内容是否已追加 |

失败后先检查已完成步骤。特别是 version 已创建但 changelog 请求失败时，只修复 changelog；不要重新执行整条 Action，避免重复创建版本。若 changelog 请求已成功但 workflow 结果未知，先检查现有条目，避免重复追加。

## 参考实现位置

- Action 元数据：action.yml
- 上传与 API 客户端：src/index.ts
- API endpoint 类型：src/api-types.ts
- OpenAPI generated types：src/openapi.schema.ts
- 示例 workflow：API-Example/.github/workflows/upload-mod.yaml
