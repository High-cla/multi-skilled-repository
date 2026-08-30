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
- **HTTP线程只入队, 主线程OnUpdate消费** — 关键! IL2CPP/Unity 游戏对象操作必须主线程, 不能直接在 HTTP 回调线程里调用游戏 API

## 流程总览

```
1. 逆向: 找游戏物品生成API (DirectoryMaster.Item 类)
2. 提取物品目录 (ID/名称/分类 → JSON)
3. 模组内嵌 HTTP 服务器 (localhost:PORT, 队列+主线程消费)
4. 网页物品浏览器 (分类筛选+搜索+生成按钮)
5. 托管/本机打开 + 验证
```

---

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

## 步骤 2: 提取物品目录

目的: 网页端要有"哪些物品可生成"清单。若游戏有物品目录资源/表, 转成 JS 数组 (字段: id/name/categories/itemTypes/description...)。

**脚本**: scripts/extract_catalog.py — 从二进制 DLL 里扫描提取 JSON 资源 (UTF-8, 平衡括号)。输出 `items_data.js`:
```js
const ITEMS = [{ "stableId": "box_tampon", "nameZh": "...", "categories": ["GOODS"] }, ...];
```

## 步骤 3: 模组内嵌 HTTP 服务器

**黄金法则: 收到请求只入队, 主线程消费。** 不要直接在 HTTP 线程调游戏 API (会崩/跨线程异常)。

**代码骨架** (MelonLoader/BepInEx, 游戏无关部分可原样复用, 只需替换 SpawnItem 里游戏 API):
- scripts/spawn_server.cs — 完整服务器 (HttpListener + ConcurrentQueue + OnUpdate消费 + CORS头 + /api/health + /api/spawn?itemId=X&count=N)
- 端口选不常用 (26880 已验证; 多游戏同机可换)

**SpawnItem 是唯一的游戏专属部分** (替换成步骤1找到的API):
```csharp
private void SpawnItem(string stableId, int count) {
    var inv = YourInvProvider.MainInventory;        // ← 游戏专属: 主背包获取
    for (int i = 0; i < count; i++) {
        GameItem item = DirectoryMaster.Item(stableId, true);  // ← 游戏专属
        if (item == null) break;
        if (!((GameInventory)inv).MayHaveValidInventorySlot(item)) break;
        if (!((GameInventory)inv).UncheckedAccept(item)) break;
    }
}
```

**构建注意**: 若用 UnityEngine.Input/HttpListener 需要 csproj 加引用:
```xml
<Reference Include="UnityEngine.InputLegacyModule">
  <HintPath>...\MelonLoader\Il2CppAssemblies\UnityEngine.InputLegacyModule.dll</HintPath>
</Reference>
```
System.Net.HttpListener/HttpUtility 在核心程序集可用, 无需额外引用。

## 步骤 4: 网页物品浏览器

**模板**: assets/items_browser.html — 完整单页 (分类侧栏+搜索+卡片网格+生成按钮+服务器状态点+Toast)。**引用 items_data.js** (同目录)。

**核心逻辑** (已验证):
```js
const API = 'http://localhost:26880';
// 状态轮询: 5秒一次 checkServer() → /api/health → 绿点/红点
// 生成: fetch(API+'/api/spawn?itemId='+encodeURIComponent(id)+'&count=1') → toast反馈
```
- CORS: 服务器响应头 `Access-Control-Allow-Origin: *` 必须 (网页跨域 fetch)
- HTTPS 页面 (GitHub Pages) 连 http URL 的 localhost: 浏览器允许, 已实测

## 步骤 5: 托管 + 验证

**托管**: 3 种方式任选
1. **本机**: `python -m http.server 8090` (静态文件服务, 需与 items_data.js 同目录)
2. **GitHub Pages**: 仓库建 `docs/` → `gh api --method POST repos/OWNER/REPO/pages -f "source[branch]=master" -f "source[path]=/docs"` → 开 `https://USER.github.io/REPO/items_browser.html`
3. 任意静态托管 (同目录两文件)

**验证** (必须, 游戏未运行也能验):
1. `python scripts/mock_spawn_server.py --port 26880` — 起 mock HTTP 服务器 (模拟 /api/health+/api/spawn 响应, 同端口)
2. 浏览器开网页 → 等状态点变绿 → 点"生成" → 看 toast "已生成: xxx ×1" ← **全链路通过** (网页→HTTP→响应→UI反馈)
3. 网页在 HTTPS (GitHub Pages) 上再验一遍 (混合内容问题)
4. 关 mock → 状态点变红 (离线检测正常)

## 陷阱速查

| 陷阱 | 症状 | 修复 |
|------|------|------|
| 跨线程调游戏API | 崩溃/异常/无效果 | 只入队, OnUpdate主线程消费 |
| CORS缺失 | 浏览器fetch被拦 | 响应头加 Access-Control-Allow-Origin: * |
| 端口冲突 | 服务器起不来 (10013等) | 换端口 |
| file:// 协议打开网页 | 浏览器阻止fetch | 必须 http:// 打开 (本地server或Pages) |
| HTTPS页面连HTTP被拦 | fetch失败 | localhost豁免, 一般OK; 被拦则用本机http |
| 物品目录JSON提取错 | 网页空/乱 | 用extract_catalog.py平衡括号法 |
| csproj缺引用 | 编译错误 | UnityEngine.InputLegacyModule (若用Input) / 检查HintPath |

## 换游戏复用

骨架 (HTTP服务器+网页+队列+验证) **100%通用** — 换游戏只需改 3 处:
1. `SpawnItem` 里游戏 API (创建/主背包/入包)
2. `items_data.js` (该游戏物品目录)
3. 端口+仓库托管地址

**前提**: 游戏可注入 (BepInEx/MelonLoader), 物品创建API+主背包可访问。
