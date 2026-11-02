---
name: game-item-spawner
description: 为游戏模组(Mod)搭建"网页点击生成物品"系统——内嵌本地HTTP服务器+网页物品浏览器+点击即生成。用于: 游戏(Unity/IL2CPP/Mono)逆向找物品生成API、模组加物品生成热键/点击生成、网页端物品目录浏览器(分类/搜索/点击生成)、GitHub Pages托管物品浏览器、BepInEx/MelonLoader模组开发。当用户提到"游戏生成物品""点击生成物品""物品浏览器""网页生成""spawn item""item spawner""生成器""逆向物品目录""给游戏加作弊生成功能"时使用。即使没直接说"网页",只要涉及"游戏内生成任意物品+可视化界面"就触发。
compatibility: 需要 dotnet/csc 编译模组、python3(跑mock验证服务器)、可选 gh CLI(发布GitHub Pages)
---

# 游戏物品生成器 (网页点击生成)

把一个"物品生成"功能做成: 游戏模组内嵌 HTTP 服务器 → 网页浏览器里点"生成" → 物品进游戏背包。**网页是入口, 模组是本机服务**——网页可以托管到 GitHub Pages, 任何玩家浏览器连自己机器上运行的模组。

## 为什么这个架构

- **网页只用 HTTP** — 和游戏解耦, 托管到任何静态站点都能用
- **浏览器 fetch localhost** — 指向玩家本机跑着的模组 (HTTPS 页面连 localhost HTTP 浏览器允许, 已实测)
- **HTTP 线程只校验并写入有界队列，主线程按单帧预算消费** — 默认最多排队 128 个请求、每帧最多创建 4 个物品；Unity/IL2CPP 游戏对象操作不得从 HTTP 线程执行

## 流程总览

```
1. 逆向: 找游戏物品创建/入包 API
2. 提取: 游戏资源 → item-catalog.json → assets/items_data.js
3. 服务: localhost HTTP → 有界请求队列 → 主线程按帧预算生成
4. 网页: 安全加载 items_data.js，以 DOM API 展示目录
5. 验证: mock 明确模拟入队和处理完成；真实游戏再验证入包
```

## 步骤 1: 逆向找生成 API

找到"游戏如何创建一件物品并放入背包"。这是整条链的核心, 通常藏在:

1. **工具**: IL2CPP DLL 用 `ilspycmd` 反编译 (BepInEx/Il2CppAssemblies 目录):
   ```
   ilspycmd GameAssembly/Assembly-CSharp.dll -o decomp/
   ```
2. **搜索线索** (在反编译源码里 grep):
   - `DirectoryMaster` / `ItemDatabase` / `ItemFactory` / `CreateItem` / `SpawnItem`
   - "Create" + "Item" 类方法; `UncheckedAccept` / `AddItem` / `AddToInventory`
   - `GameInventory` / `PlayerInventory` / `InventoryElement` / 主背包
3. **找主背包入口** (谁持有玩家库存): 类似 `EmporiumEntry.Instance.invElement` 的静态单例/管理器

**典型模式** (几乎每个游戏都有相似物, 名称不同):
```csharp
GameItem item = DirectoryMaster.Item(stableId, true);     // 按ID创建
((GameInventory)inv).MayHaveValidInventorySlot(item);     // 校验有格子
((GameInventory)inv).UncheckedAccept(item);               // 入包
```

**注意**: 物品 ID 列表常藏在**内嵌资源**里 (e.g. `item-catalog.json`)。用字符串扫描+平衡括号提取 (见 scripts/extract_catalog.py)。

## 步骤 2: 提取并构建物品目录

网页端需要由本地资源生成的目录文件。仓库提供两个连续脚本，不能跳过 JSON→JS 转换：

```bash
# 1. 从用户有权访问的 DLL/资源中提取 JSON
python scripts/extract_catalog.py /path/to/GameAssembly.dll '"records"' item-catalog.json

# 2. 验证目录记录并生成网页脚本（默认目标也可省略）
python scripts/json_to_js.py item-catalog.json --output assets/items_data.js
```

- extract_catalog.py 以 JSON 字符串规则处理括号，能忽略字符串中的 `{`、`}`，并在写出前验证完整 JSON。
- json_to_js.py 接受顶层数组或包含 `records` / `items` 数组的对象；要求每条记录有唯一的 `stableId`（或可映射的 `id`），并规范化名称、描述、分类和类型字段。
- 转换文件以 `window.ITEMS = [...]` 暴露数据；`items_browser.html` 从同目录加载 `items_data.js`。缺少、损坏或结构不符时网页会显示具体错误。
- `assets/items_data.js` 属于游戏专属生成物，已加入 .gitignore。只有在确认有权公开分发时，才将它复制到独立的 Pages 发布目录；不要默认把游戏目录上传到公共仓库。

字段至少包括 `stableId`、`nameZh`、`nameEn`、`categories`、`itemTypes`、`descriptionZh`、`descriptionEn`。目录字段均视为不可信输入，页面必须用 DOM 的 `textContent` / `createElement` 渲染，禁止把它们拼进 `innerHTML`。

## 步骤 3: 模组内嵌 HTTP 服务器

**黄金法则：HTTP 线程只验证请求并入队；游戏 API 只在主线程调用。**

脚本：`scripts/spawn_server.cs`。默认约束：

- 最多 128 个待处理请求；队列满时返回 HTTP 429 和 `state: "rejected"`，不会静默丢弃。
- 单个请求的 count 范围为 1–25。
- 每次 `DrainQueue()` 最多创建 4 个物品，避免一帧内处理大批量请求造成卡顿。
- `/api/spawn` 入队后返回 HTTP 202 和 requestId，状态是 `queued`，**不代表物品已经生成**。
- `/api/spawn/status?id=...` 返回 `queued`、`processing`、`succeeded`、`partial` 或 `failed`，并报告 requested/spawned 数量。
- `/api/health` 报告服务模式和队列容量。状态历史有上限，旧的终态记录会被清理。
- `Stop()` 停止监听线程并把未完成请求标记为失败/部分完成；Start/Stop 可重复调用。

### 生命周期接线

MelonLoader 模组：

```csharp
public override void OnInitializeMelon()
{
    SpawnHttpServer.Start();
}

public override void OnUpdate()
{
    SpawnHttpServer.DrainQueue(); // 每帧调用一次，必须是 Unity 主线程
}

public override void OnDeinitializeMelon()
{
    SpawnHttpServer.Stop();
}
```

BepInEx 模组在 `Awake()` 调用 `Start()`、在 `Update()` 调用 `DrainQueue()`、在 `OnDestroy()` 调用 `Stop()`。不要在 HTTP handler 中直接调用创建物品或修改背包的游戏 API。

### 游戏专属 API

只替换 `TrySpawnOne(stableId, out error)`：创建物品、获取玩家主背包、检查空位并执行入包。只有在游戏 API 明确返回成功后才返回 `true`；创建失败、背包为空、无空位或入包失败都应返回 `false` 并设置错误信息。模板默认实现故意返回失败，防止未接入游戏 API 时产生虚假的成功状态。

服务器仅监听 localhost。浏览器跨域请求的 `Origin` 必须与 `spawn_server.cs` 中 `AllowedOrigins` 精确匹配；mock 可用重复的 `--allow-origin https://your-trusted-origin.example` 添加来源。默认只允许 `http://localhost:8090` 和 `http://127.0.0.1:8090`。部署 GitHub Pages 时，必须把实际 Pages origin（仅 origin，不带路径）显式加入 allowlist；不要使用通配符 `*`。无 Origin 的本机工具（如 curl）仍可访问，因此这不是对本机恶意进程的身份验证或完整授权边界。

## 步骤 4: 网页物品浏览器

模板：`assets/items_browser.html`。运行前必须先生成同目录的 `items_data.js`。

- 用分类侧栏、搜索、卡片、详情面板和状态提示展示目录。
- 目录的 stableId、名称、描述、分类、itemTypes、kind、directory、addPolicy 等字段全部视为不可信数据。
- 动态内容一律通过 `document.createElement`、`textContent`、`dataset` 和 `replaceChildren` 写入；不得使用 `innerHTML`、`outerHTML` 或字符串模板构造包含目录字段的 HTML/属性。
- `/api/spawn` 返回 202 后，按钮先显示“已入队”；客户端再轮询 `/api/spawn/status`。只有游戏服务器报告 `state: "succeeded"` 才显示“已生成”。
- CORS 允许跨域读取响应不代表浏览器端已完成游戏动作；网络成功、HTTP 202、已入队和游戏 API 确认成功是不同阶段。

本机可用简单静态服务器打开页面，但必须确保 `items_browser.html` 与生成的 `items_data.js` 同目录：

```bash
python -m http.server 8090 --directory assets
```

## 步骤 5: 托管 + 验证

**mock 验证：** `python scripts/mock_spawn_server.py --port 26880`。本机静态站点使用默认 origin allowlist；额外网页来源请通过 `--allow-origin <exact-origin>` 明确授权。

1. 打开与 `items_data.js` 同目录的网页，确认目录加载、分类和搜索正常。
2. `/api/health` 显示 `mode: "mock"`；点击生成后先看到“已入队”，再轮询状态。
3. mock worker 完成模拟任务后返回 `state: "succeeded", mode: "mock"`；网页必须显示“Mock 模拟完成”，并说明未调用游戏 API、未修改真实背包。
4. 队列满、无效 itemId/count、未知 requestId、服务离线等情况应显示失败，不得显示成功。
5. mock 只能验证页面→HTTP→队列→状态查询→UI 的协议闭环，不能证明真实游戏 API、背包槽位或 IL2CPP 线程接线正确。
6. 在真实游戏中再验证：Start/Stop 生命周期、主线程消费、实际入包数量、部分失败和退出时未完成请求处理。

发布 GitHub Pages 前，先核对数据来源与再分发权利。请参阅 [DATA-SOURCES.md](DATA-SOURCES.md)；默认不公开发布从游戏 DLL 提取的目录。

## 陷阱速查

| 陷阱 | 症状 | 修复 |
|------|------|------|
| HTTP 线程直接调用游戏 API | 崩溃/跨线程异常 | HTTP 线程只校验和入队；主线程消费 |
| 无界请求队列 | 请求堆积、内存增长 | 限制队列容量并在满载时返回 429 |
| 主线程一次性清空队列 | 某帧卡顿 | 按固定单帧 item budget 处理 |
| 将 HTTP 202 当作生成成功 | UI 误报 | 先显示 queued，再查 status，只有 succeeded 才显示成功 |
| mock 成功冒充真游戏成功 | 无游戏时误判集成通过 | UI 显示 Mock 模拟完成并明确未修改真实背包 |
| 目录字段进入 HTML 字符串 | XSS / 属性注入 | 所有字段使用 DOM API 和 textContent |
| items_data.js 缺失/未更新 | 网页空白或旧数据 | 依次运行 extract_catalog.py、json_to_js.py，确认两个资源同目录 |
| 端口冲突 | 服务器启动失败 | 更换端口并同步更新页面 API 地址 |
| CORS 缺失 | 浏览器无法读取响应 | 配置可信页面需要的 CORS；不要把 CORS 当成访问控制 |
| 模组卸载后线程残留 | 端口占用/热重载失败 | 生命周期结束时调用 Stop() |
| csproj 缺引用 | 编译错误 | 根据使用的 Unity API 添加所需引用并核实 HintPath |

## 换游戏复用

骨架 (HTTP服务器+网页+队列+验证) **100%通用** — 换游戏只需改 3 处:
1. `SpawnItem` 里游戏 API (创建/主背包/入包)
2. `items_data.js` (该游戏物品目录)
3. 端口+仓库托管地址

**前提**: 游戏可注入 (BepInEx/MelonLoader), 物品创建API+主背包可访问。
