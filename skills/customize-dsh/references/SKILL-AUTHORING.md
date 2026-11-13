# 技能格式、创作与评测参考

本文区分通用 Agent Skills 格式、Anthropic 的创作方法和 DSH filesystem provider 的实现扩展。三者不可混为一谈。

## 1. 可移植 Agent Skills 格式

规范原文：[agentskills.io/specification](https://agentskills.io/specification) · [规范源码](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)。

- 技能是包含 `SKILL.md` 的目录；可选 `scripts/`、`references/`、`assets/` 等资源目录。
- `SKILL.md` 必须以 YAML frontmatter 开始，至少包含 `name` 与 `description`。
- `name`：1–64 个字符，仅小写字母、数字和连字符；不得以连字符开头/结尾，不得连续使用 `--`；必须与父目录名一致。
- `description`：1–1024 个字符，描述技能能力和适用场景，并包含有助于识别任务的关键词；不得含尖括号。
- 可选字段：`license`、`compatibility`（1–500 字符）、`metadata`（字符串键值映射）；`allowed-tools` 仍属实验字段，客户端支持程度不同。
- 正文是 Markdown 指令，没有强制章节结构；使用相对路径链接资源。规范建议将引用保持为一层，避免深层引用链。
- 渐进式披露：启动时只需读取 name/description；触发后读取 SKILL.md；只有具体任务需要时才读取 references/scripts/assets。
- 规范建议主 SKILL.md 少于 500 行；这属于设计建议，不是 frontmatter 格式字段。

不要把某个客户端/市场目录的额外 frontmatter 字段或打包元数据误认为通用规范要求。

## 2. DSH filesystem provider 扩展

DSH 的技能 provider 是 `ctx.skills` registry 中的一个 provider；目录扫描规则只适用于本地 filesystem provider，不代表远程或内嵌 provider 的能力。

按目标 DSH 版本的官方 [Skills subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)、[filesystem provider README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md) 与配置目录核验：
- 已配置 root 的直接条目可包含目录包 `<name>/SKILL.md` 或扁平文件 `<name>.md`；不会递归扫描任意深度的 `**/SKILL.md`。
- 当前实现可能支持 `whenToUse`、`disable-model-invocation`、`user-invocable` 等 provider-specific frontmatter 字段。它们不属于通用 Agent Skills 规范；字段名、类型、默认值和非法值行为都要按安装版本 README/schema/source 核验。
- 技能目录的 rank、scope、重复名称裁决、watch/invalidation 和资源加载时机以目标版本为准。
- 对跨客户端发布，使用通用必需字段和目录包格式；只有部署明确依赖 DSH 专属行为时才添加扩展字段，并在文档中标注其 DSH 限定。

## 3. 技能创作方法（Anthropic skill-creator）

[Anthropic skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) 是 Anthropic 的技能创作与评测实现/方法参考，不是通用格式规范。其核心方法可移植，但脚本、CLI、subagent 和 viewer 依赖 Claude 环境，不应未经核验直接复制为 DSH 运行要求。

### 新建技能
1. 明确技能要解决的真实任务、触发范围、输入/输出、用户可观察的成功条件与禁止范围。
2. 先从真实工作流、项目材料和真实失败模式提炼步骤，不从泛泛最佳实践拼贴。
3. 写出最小 SKILL.md 草稿，并为真实用户任务准备 2–3 个端到端场景；对于客观可验证的输出，补充可检查的 expectations/assertions。
4. 在可用环境运行场景，检查技能是否触发、是否遵循说明、输出是否正确，以及是否增加不必要步骤。
5. 根据失败和用户反馈修改，再以相同场景回归；扩大场景覆盖，直到没有显著改进或用户确认满意。

### 修改已有技能
1. 保存原版快照，记录原始版本和当前 evals；先用原版跑 baseline，不要先改再猜原行为。
2. 将测试分为正向场景、边界场景和近似负向场景。负向场景应与技能共享词汇/概念，但实际应由相邻技能或普通工具处理。
3. 修改后使用相同任务集复测。区分行为质量回归、触发误差、规则漏执行与多余步骤。
4. 只为有客观判定标准的任务编写硬断言；主观任务采用人工评价或清晰 rubric，不伪造确定性指标。
5. 保留证据：输入、输出、版本、运行环境、评测结果、未解决局限。

## 4. description 触发评测

Anthropic 的描述优化方法建议使用约 20 个真实查询，其中约 8–10 个应触发、8–10 个不应触发。至少覆盖：
- 正向：正式/口语/缩写表达、长短不同、未直接说出技能名但确实需要技能的任务。
- 负向：与技能相邻、关键词重叠、容易被误判但实际应由其他技能处理的 near-miss。
- 重复运行：模型触发具有随机性；在可行时对每个 query 多次运行并记录 trigger rate，而不是只看单次结果。
- 评估：分别观察正例召回、负例特异度、precision、recall 与 false-positive rate，不要只汇总 overall accuracy。
- 防过拟合：固定 train/validation split；只用 train 失败指导描述修改，以 held-out validation 结果选版本。避免把训练用例中的专有名词直接塞进 description。

这些是 Anthropic skill-creator 的评测建议，不是 Agent Skills 标准的强制条款。若当前客户端无法可靠观察 skill invocation，明确报告无法测量触发率，改做人工路由检查。

## 5. 验证层次

依次检查：
1. **格式**：`skills-ref validate <skill-dir>`。验证通过只说明通用结构合法。
2. **发现与加载**：在目标客户端/DSH profile 中确认技能可被发现、正确加载正文，且引用路径有效。
3. **任务行为**：使用真实正向/负向/边界场景，检查输出和指令遵循。
4. **触发质量**：若客户端可观察调用记录，评测 description 正负触发；不要把格式验证结果当作触发质量证明。

不要为验证而自动安装技能、执行未知脚本或使用只适用于 Claude Code 的 `claude -p`/subagent/eval viewer 命令；只有在相应环境真实具备且用户授权时才使用。
