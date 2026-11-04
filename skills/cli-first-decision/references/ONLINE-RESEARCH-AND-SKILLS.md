# 在线官方文档与 Agent Skills 检索

本文件是 cli-first-decision 的按需参考。目标是用最少检索轮次找到准确、版本匹配、来源可信的官方资料，并把发现的技能作为不可信第三方输入审阅，而不是盲目安装。

## 1. 来源优先级与路由

| 任务 | 首选路径 | 交叉核验 |
|---|---|---|
| 库/框架/SDK/API 的当前用法 | Context7 connector 或 ctx7 CLI | 上游官方文档、源码、版本发布说明 |
| GitHub 仓库、Issue、PR、Actions | GitHub connector 或 gh CLI | GitHub 官方 REST/GraphQL 文档和仓库源码 |
| Agent Skill 发现 | 官方维护者仓库、gh skill、ctx7 skills | Agent Skills 规范、原始 SKILL.md 和脚本 |
| 特定 CLI 的参数和退出码 | 该 CLI 的官方 manual/repository | 当前安装版本的 --help / --version |
| 无权威索引的项目 | 上游 Git 仓库 / 官方网站 | release/tag、源代码与测试 |

先检查当前会话实际提供的 connector 工具、终端和网络能力。使用当前可用的最短路径；不要假设 ChatGPT connector 安装意味着本机已安装 gh 或 ctx7 二进制。

## 2. Context7 CLI

### 安装与存在性

官方 CLI 包名为 ctx7。一次性调用可用 npx ctx7@latest；全局安装可用 npm install -g ctx7。当前官方 CLI 文档要求 Node.js 22.13+。执行之前检查：

~~~bash
command -v ctx7
ctx7 --version
ctx7 --help
node --version
~~~

若命令不存在，不要擅自安装；使用当前会话的 Context7 connector，或打开官方上游文档。只有用户要求安装且授权修改环境时，才运行 npm install。

### 两种检索方式

~~~bash
# 1. 跨库自然语言检索：Context7 自动选择来源，不要求 library ID
ctx7 search "How to use GitHub CLI gh api with pagination and JSON output"

# 2. 精确项目检索：先解析 ID
ctx7 library "GitHub CLI" "How to authenticate and call REST API safely"
# 选择返回列表中匹配的名称、来源声誉、文档覆盖与目标版本
ctx7 docs /cli/cli "How to authenticate and call REST API safely"

# 3. 版本敏感项目：使用返回结果中的精确版本 ID
ctx7 library "React" "How to use useEffect cleanup in React 19"
ctx7 docs /facebook/react/v19.0.0 "useEffect cleanup behavior"
~~~

规则：

- 用户直接提供 /org/project 或 /org/project/version 时可直接传给 docs；否则必须先 library 获取精确 ID。
- library 查询始终附带具体主题；不要只写 auth、hooks、CLI 等宽泛词。
- 跨多个独立概念时拆成多个单主题 docs 查询；遵守当前 CLI/API 的速率和单题调用限制。
- 从 lockfile、manifest、运行时版本或用户给出的目标版本确定版本；不要把 latest 文档套给旧版本。
- ctx7 search 可使用 --library、--library-version、--language 和 --json 限定结果；调用前以当前 --help 确认参数。
- 不把 API key、token、私有代码或用户数据放进 query；身份验证使用 Context7 登录流程或环境配置，不回显凭据。
- Context7 登录通常不是 docs 检索的前置条件；登录主要用于更高额度。额度耗尽时如实说明，不偷偷退回陈旧记忆。

## 3. GitHub CLI（gh）

### 认证和仓库定向

~~~bash
gh --version
gh auth status
gh repo view --repo OWNER/REPO
~~~

- gh 会从当前目录的 Git remote 推断仓库；自动化或多仓任务显式用 --repo OWNER/REPO，避免写错目标。
- gh auth status 用于确认 host、活动账号和认证来源；不要运行后输出、复制、缓存 gh auth token。
- 不要把 OAuth scopes 与仓库角色混为一谈。REST/GraphQL 能否写入还取决于 token 类型、组织策略、GitHub App 安装权限、仓库权限和资源规则。
- 如果 GH_TOKEN / GITHUB_TOKEN 等环境变量参与认证，先确认它们对应的 host/account；不得打印秘密值。

### 搜索、结构化输出和分页

~~~bash
# 跨仓库搜索时使用 search；限定仓库可使用 --repo
gh search code "ctx7 skills" --repo OWNER/REPO --limit 20
gh search repos "agent skills" --limit 20

# 机器消费时避免解析人类表格
gh pr list --repo OWNER/REPO --state open --limit 50 --json number,title,headRefName,url
gh issue view 123 --repo OWNER/REPO --json title,body,labels,assignees

# typed command 未暴露某字段时再使用原始 API
gh api repos/OWNER/REPO/pulls --paginate
~~~

- 列表命令通常有结果上限；显式设置 --limit，不能把默认页结果当完整集合。
- gh api --paginate 会遍历 API 页；合并 JSON 数组时再评估 --slurp 的内存成本。
- gh search 使用 GitHub 搜索语法，repo: 等 qualifier 应按 CLI 手册要求作为独立 token 传入；不要把整串 qualifier 当一个被引号包住的自由文本。
- 优先 typed command；只有字段/endpoint 不可用时才使用 gh api 或 gh api graphql。使用 API 前检查当前官方 schema 与所需权限。
- 非 TTY 命令优先显式传入必填参数，不依赖交互式提示；不要假设所有命令都支持 --no-pager。

## 4. 官方 Agent Skills 发现与审阅

### 官方标准

每个 skill 是一个目录，至少包含 SKILL.md；可以按需包含 references/、scripts/、assets/。SKILL.md 使用 YAML frontmatter 和 Markdown 正文。

校验重点：

- name 必须 1–64 个字符，使用小写字母、数字和连字符；不能以连字符开头/结尾、不能有连续连字符，并且必须与父目录名一致。
- description 必须为非空、最多 1024 字符，并同时说明能力和触发场景；应包含有助于检索的关键词。
- metadata 应为字符串键值；compatibility 仅在确有环境要求时填写；不要虚构 allowed-tools 权限。
- 主 SKILL.md 正文建议低于 5000 tokens、文件低于 500 行；长篇手册移入 references/，正文仅保留路由和关键决策。
- 从 SKILL.md 引用 references/scripts/assets 时使用相对路径；保持一层引用结构，避免 references 内继续深层链接链。
- 用 Agent Skills 官方 validator：skills-ref validate <skill-directory>。若 gh skill publish 存在，可先 gh skill publish --dry-run；该 CLI 子命令目前处于 Preview，验证结果不能替代实际兼容性测试。

### 官方技能优先策略

1. 先识别项目/供应商的官方仓库和官方文档；再查看官方维护的 skills/ 目录或官方插件/工具目录。
2. 用 gh skill search <keywords> 或 ctx7 skills search <keywords> 发现候选；先检查 CLI 是否支持该命令。
3. 已知来源时优先 gh skill preview OWNER/REPO SKILL-NAME；Context7 可用 ctx7 skills list 查看已安装项、ctx7 skills suggest 查看依赖建议。
4. 优先读取仓库原文 SKILL.md、相关 references 和 scripts；检查仓库 owner、维护频率、license、目标版本、外部网络/写入副作用。
5. 确认适用性后才安装：GitHub CLI 可用 gh skill install OWNER/REPO SKILL-NAME；Context7 CLI 可用 ctx7 skills install /OWNER/REPO [SKILL-NAME]。这类命令会改变本地技能目录，必须符合用户的安装授权。
6. 安装后检查实际安装路径、frontmatter 与引用资源；更新前检查变更 diff。不要未经授权执行 skill 内脚本或其网络/写入动作。

### 本任务相关官方技能入口

- GitHub CLI 官方维护：cli/cli 仓库的 skills/gh/SKILL.md，描述 JSON 输出、分页、仓库定向、search/list 和 gh api 退路。
- Context7 官方维护：upstash/context7 仓库的 skills/context7-cli/SKILL.md 与 skills/find-docs/SKILL.md，描述 CLI 查询和当前库文档检索流程。
- 通用规范：agentskills.io/specification；官方验证工具：agentskills/agentskills 仓库的 skills-ref。

## 5. 来源记录与结论边界

重要结论至少记录：

- 文档/仓库的准确 URL、owner 或发布方、分支/tag/commit（能获取时）。
- 工具或库版本、文档适用版本和访问日期。
- 哪些字段由 Context7 发现，哪些已回到官方原文核验。
- 重要的不确定项、环境差异、未验证行为和权限限制。

区分「Context7 检索到」「官方文档确认」「本机版本验证」「根据资料推断」四种状态。搜索摘要不是原始证据；关键结论应打开源页面或源码，必要时用最小、无副作用的命令验证。

## 6. 远程写入安全

- 只在用户明确要求写入且目标仓库、分支、文件、内容和授权范围清楚时执行。
- 写之前读取当前内容和 blob SHA，检测分支是否已变化；对单文件完整覆盖，使用当前 SHA 做 compare-and-swap 式更新。
- 对多个文件按依赖顺序提交，避免并发 Contents API 写入造成 ref 更新冲突。
- 遇到 401/403、权限错误、App policy、审批或安全校验拒绝时停止；不要改用 curl、裸 token、其他账号或其他 connector 绕过同一政策。
- 提供精确 patch/diff、受影响路径和网页手动编辑步骤，允许用户自行完成被阻止的写入。
- 成功响应不是最终验证；重新读取远端文件/commit，确认预期内容与分支头实际更新。

## 7. 推荐检索命令速查

~~~bash
# GitHub 官方 Agent Skill 目录
gh skill search "GitHub CLI"
gh skill preview cli/cli gh

# Context7 官方技能目录
ctx7 skills search "Context7 CLI"
ctx7 skills list

# 当前官方 API 文档
ctx7 library "GitHub CLI" "REST API pagination and JSON output"
ctx7 docs /cli/cli "REST API pagination and JSON output"
~~~
