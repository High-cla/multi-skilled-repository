---
name: nexusmods-publisher
description: 使用 Nexus Mods v3 API 与 Nexus-Mods/upload-action，将已打包的游戏模组 ZIP 发布为现有 mod file 的新版本，并配置 GitHub Actions 自动发布、版本号、changelog、密钥和失败诊断。用户提到 Nexus Mods 上传、NexusMods 发布、upload-action、file_id、mod_id、模组 CI/CD 或自动发布时使用。
compatibility: Requires GitHub Actions and a Nexus Mods API key with permission to upload files.
---

# Nexus Mods 模组发布 — nexusmods-publisher

为已经存在 Nexus Mods mod 页面及 file entry 的模组建立可审查、可重复的发布流程。优先采用官方 Nexus-Mods/upload-action；只有需要自定义上传协议、创建首个 file entry 或排查 Action 不覆盖的能力时，才直接实现 v3 API。

## 1. 先判断发布类型与 ID

- **已有 mod file 的新版本**：使用 Nexus-Mods/upload-action，提供既有 file ID。
- **同一 mod 页面下的全新 file entry**：Action 不负责创建；使用 v3 API 上传会话，finalise 后调用 POST /mod-files。
- **全新的 mod 页面**：先在 Nexus Mods 网站完成页面创建和授权；不要把 upload-action 当成页面创建工具。
- **file_id** 是目标 mod file ID，Action 必填；不是 mod ID，也不是上传会话 ID。
- **mod_id** 是所属 mod ID；只有设置 changelog 时才必填。
- **upload_id** 是 API 上传会话 ID；**version_id** 是 Action 输出的已创建文件版本 ID。

核实用户确实希望发布。打包、workflow 编写、dry-run 和测试不等于授权上传。没有明确发布指令时，不要触发会实际上传文件的 workflow。版本字符串必须与用户指定的版本/tag/release 一致，不要擅自生成版本号或把 commit SHA 当成 mod 版本。

## 2. 检查并构建发布 ZIP

先识别项目真实构建命令和产物目录，避免把整个仓库打包。发布前检查：

- ZIP 根目录符合游戏 Mod Manager/安装器预期，没有意外多包一层仓库目录。
- 包含必要的插件 DLL、manifest、依赖说明、配置模板和许可证/第三方声明。
- 不包含 API key、访问令牌、签名私钥、用户目录、游戏本体、开发依赖、缓存、.env、调试日志或未获授权的第三方资产。
- 文件名稳定明确；显示名称、版本、描述和 changelog 与压缩包内容一致。
- 列出 ZIP 文件清单、验证 ZIP 可读取，并在适用时运行项目测试。

示例（按项目修改源目录，不要假设 publish/ 是真实目录）：

~~~bash
mkdir -p dist
zip -r dist/my-mod.zip ./publish/
unzip -l dist/my-mod.zip
sha256sum dist/my-mod.zip
~~~

Windows 可用 PowerShell Compress-Archive，并用 Expand-Archive 或 7-Zip 验证。记录最终 ZIP 的 SHA-256 以便追溯。

## 3. 配置密钥与目标 ID

- 在 Nexus Mods 网站创建/管理 mod 页面并至少上传一次文件，才能从 Files 页面 Advanced 信息或 Manage Files 编辑界面取得 file ID。
- 将 API key 保存为 GitHub Actions Repository/Environment/Organization Secret，例如 NEXUSMODS_API_KEY。绝不能放在 Variables、明文 YAML、仓库文件、命令参数、日志或 artifact 中。
- 将非敏感 ID 放到 Variables，例如 NEXUSMODS_FILE_ID 和 NEXUSMODS_MOD_ID；也可按最小权限和环境隔离要求使用受控输入。
- 生产发布建议使用 GitHub Environment approval、受保护 release/tag 或受限 workflow_dispatch；不要让任意分支 push 自动发布。
- workflow permissions 只授予必要权限。普通打包通常只需 contents: read；不要授予 contents: write，除非确实需要创建 GitHub Release/tag。

API key 属于用户凭据。只把它传给官方 Action 的 api_key 输入；不要打印环境变量、把密钥写进临时文件或启用会泄露密钥的 debug 输出。

## 4. 使用官方 GitHub Action

参考 [Nexus-Mods/API-Example](https://github.com/Nexus-Mods/API-Example)：release published 或手动 workflow_dispatch 触发；checkout 完整 Git 历史；由 Git log 生成 changelog；打 ZIP；调用官方 Action。

生产配置应固定到审查过的 Action release 或完整 commit SHA，不要无审查地使用 @main。Marketplace 展示版本、Action 输入、Node runtime 和源码可能变化，发布前核对所 pin 版本的 action.yml 与源码。

~~~yaml
name: Publish mod to Nexus Mods

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      version:
        description: Mod file version
        required: true
        type: string

permissions:
  contents: read

jobs:
  publish:
    environment: nexus-mods-production
    runs-on: ubuntu-latest
    steps:
      - name: Checkout full history
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Build and package mod
        run: |
          set -euo pipefail
          # Replace with the real build and staging commands.
          mkdir -p dist
          zip -r dist/my-mod.zip ./publish/
          unzip -t dist/my-mod.zip

      - name: Generate changelog
        id: changelog
        shell: bash
        run: |
          {
            echo "changelog<<EOF"
            git log -n 10 --no-merges --pretty=format:'- %s'
            echo
            echo "EOF"
          } >> "$GITHUB_OUTPUT"

      - name: Upload new file version
        id: upload
        uses: Nexus-Mods/upload-action@<reviewed-commit-sha>
        with:
          api_key: ${{ secrets.NEXUSMODS_API_KEY }}
          file_id: ${{ vars.NEXUSMODS_FILE_ID }}
          mod_id: ${{ vars.NEXUSMODS_MOD_ID }}
          filename: dist/my-mod.zip
          display_name: My Mod
          description: Release notes for this version
          version: ${{ github.event.release.tag_name || inputs.version }}
          changelog: ${{ steps.changelog.outputs.changelog }}
          update_mod_version: true
~~~

此 YAML 是结构模板，不是无需修改即可发布的成品：替换 build/staging 目录、Nexus Mods ID、描述和 Action SHA；检查 release tag 是否符合版本规则。若不写 changelog，不需要传 mod_id。

当前 Action 输入（以所 pin 版本的 action.yml 为准）：

| 输入 | 用途 / 默认 |
|---|---|
| api_key | 必填，Nexus Mods API key |
| file_id | 必填，追加版本的既有 file ID |
| filename | 必填，待上传 ZIP 路径 |
| version | 必填，文件版本字符串 |
| display_name | 可选，默认取 filename |
| description | 可选，版本描述 |
| category | 可选，默认 main |
| archive_existing_version | 可选，默认 false |
| primary_mod_manager_download | 可选，是否设为 mod manager 默认下载 |
| allow_mod_manager_download | 可选，是否允许 mod manager 下载 |
| show_requirements_pop_up | 可选，是否显示 requirements 弹窗 |
| update_mod_version | 可选，是否同步 mod 页面版本，默认 false |
| mod_id + changelog | 设置 changelog 时必须同时提供 |

Action 输出 version_id。将其作为发布结果记录；不要把 workflow job 成功、上传完成和 Nexus 页面最终可下载混成同一状态。

## 5. Changelog 与可重复执行

- 从完整 Git 历史生成 changelog 时，checkout 必须包含足够历史（示例使用 fetch-depth: 0）。
- changelog 应来自真实提交/用户提供的发布说明，不得编造修复、兼容性或测试结果。
- Nexus v3 的 POST /mods/{id}/changelogs 是**追加**而非覆盖。workflow 部分成功后重跑，可能再次追加同一段文字。
- Action 可能在“文件版本已创建、changelog 尚未完成”之间失败。重试前先查询文件版本与 changelog；不要把整个发布流程视为严格幂等操作。
- 使用 Actions concurrency 防止同一 mod/file 并行发布；必要时设置 cancel-in-progress: false，避免取消正在上传的工作造成不完整发布。

## 6. API 路径与上传协议

自定义客户端、理解 Action 行为或排查请求失败时，加载 [references/API-REFERENCE.md](references/API-REFERENCE.md)。优先使用官方 OpenAPI 与 Action 源码，不要从旧 v1 示例推断 v3 请求格式。

- v3 API base URL：**https://api.nexusmods.com/v3**。
- API key header 名为 **apikey**。官方 Action 设置 JSON Content-Type、apikey 和 User-Agent。
- 当前官方 Action 使用 POST /uploads/multipart，按预签名 URL 上传各分片、收集 ETag、完成 multipart、finalise、轮询 state 至 available，再创建 file version；它不创建新的 mod 页面。
- 100 MiB 以上文件必须使用 multipart；较小文件可使用单段上传。直接使用单段接口时，必须遵循预签名 URL 要求的 Content-Disposition。
- multipart part URL、complete_presigned_url 和单段 presigned_url 是临时签名 URL：不要打印、持久化或公开分享。
- 区分认证失败、权限不足、ID 不存在、请求字段不合法和文件上传失败；保留状态码与脱敏后的 Problem Details，不泄露凭据或预签名 URL。

## 7. 官方 API 变更门禁

每次发布前重新查看官方 OpenAPI 的 Upcoming Changes，不要把本节当作永不过期常量。当前官方 schema 已公告：

- **2026-11-23 起**：创建 mod file / 新版本请求的 description 限制为最多 255 字符。现在就把 description 控制在 255 字符内。
- **2026-12-01 起**：单段 POST /uploads 的 md5 字段变为必填；请求值使用 32 位十六进制摘要，上传 PUT 的 Content-MD5 header 使用同一 digest 的 Base64 编码。官方 Action 当前走 multipart；不要把单段 md5 约束错误套到 multipart 请求，也不要假设自定义单段客户端不需要它。

上述变更日期按官方 schema 公告记录；执行时以当日 OpenAPI 为准。

## 8. 发布验证清单

- [ ] 用户明确授权本次真实上传，并确认目标 mod/file、版本与发布环境。
- [ ] 构建和测试完成；ZIP 可读，目录层级、文件清单和文件哈希已检查。
- [ ] 无 API key、私人文件、构建缓存、游戏本体或未获授权资产进入 ZIP。
- [ ] file_id 对应目标 mod file；只有设置 changelog 时才需要 mod_id。
- [ ] Secret 配置正确；Action 引用已审查的固定版本/commit SHA。
- [ ] 版本字符串正确；description 不超过当前 API 限制。
- [ ] changelog 来自真实变更；评估失败重跑是否会重复追加。
- [ ] workflow 完成后记录 version_id、发布版本和 ZIP SHA-256。
- [ ] 在 Nexus Mods 页面验证新版本、文件名、描述、分类和下载设置；必要时用 mod manager 做安装验证。

## 9. 常见故障定位

| 症状 | 优先检查 |
|---|---|
| 401 / 无效 API key | Secret 名称、是否过期、是否误存为变量；检查 apikey header，不要回显值 |
| 403 | API key 所属账号是否拥有该 mod/file 上传权限、账号限制或端点权限 |
| 404 | file_id / mod_id 是否混淆，目标 file 是否存在、是否属于目标 mod |
| 400 / 422 | 版本字段、category、description 长度、请求格式和当前 OpenAPI schema |
| 分片 PUT 失败 | 每片字节数、预签名 URL 是否过期、HTTP 方法、ETag、网络代理/超时 |
| finalise 后长期未 available | 查询 GET /uploads/{id} 状态；不要盲目重新创建多个上传会话 |
| Action 找不到 ZIP | filename 必须是 runner 工作目录下的真实路径；确认构建步骤先于上传步骤 |
| 上传成功但 changelog 未写入 | 核对 mod_id、权限与 changelog 请求；先检查已有记录，再决定是否只补写 changelog |
| 重跑后 changelog 重复 | changelog API 是追加式；不要再次执行完整发布，先核对版本和现有条目 |

## 工作原则

1. 优先读当前官方文档、当前 Action 的 action.yml 与源码；Marketplace 示例只作为输入速查。
2. 对照用户实际仓库生成发布 workflow，不覆盖未请求的现有 CI/CD 行为。
3. 将真正上传视为外部副作用；没有明确授权时只构建、检查或准备 workflow。
4. 不输出、不复制、不写入任何 API key 或预签名 URL。
5. 上传失败时报告准确阶段（创建会话、分片、完成、finalise、available 轮询、创建 file version、写 changelog）；不得将部分成功描述为整体失败或整体成功。
