---
name: crash-dump-diagnosis
description: >-
  用真实转储（.dmp / .mdmp / minidump / WER crash dump）定位闪退根因，而不是猜原因。
  只要用户贴了一个转储路径、说「闪退」「崩溃」「一进战斗就没了」「无提示退出」，或提到 0xC0000005、access violation、调用栈、UE4SS 崩、Unreal 崩、游戏闪退，就该用本技能——即使他没有明说要「分析 dump」。
  覆盖：异常语义表、按 .pdata 自解 x64 栈、指令级定责、多 dump 同源判定、宿主脚本 VM（Lua 的 CallInfo/Proto/字节码反查源码行）、Unreal/UE4SS 已知崩溃签名、三档修复与报告模板。
  不适用：只想要「重装驱动 / 校验完整性」式泛建议，或既无转储也无栈证据的纯猜测。
metadata:
  triggers: [闪退, 崩溃分析, dump, minidump, 0xC0000005, access violation, 调用栈, UE4SS, Unreal]
  related: systematic-debugging
---

# 崩溃转储诊断

## 铁律

**先转储事实，后因果推断。** 禁止从「最近改了什么」倒推崩溃原因。

任何结论必须写成「模块+偏移 → 指令 → 寄存器值」三联式。写不出来的部分是假设，必须显式标注为假设，不能混进结论。

## 0. 工具链自检（第一步，别跳过）

- 有 cdb / windbg：`cdb -z <dump> -c ".symfix;.reload;!analyze -v;k;q"` 拿到方向，再 `r`/`u`/`kb`/`.frame` 逐帧确认。
- 没有（本机常态）：python + `pefile` + `capstone` 手解。`python -c "import pefile, capstone"` 失败则 `pip install pefile capstone`。
- 没有调试器也**不要**立刻去读业务源码：先出事实表，事实表出来后再回源码才有落点。

## 1. 提取基线事实（一次解析拿全）

minidump 的 stream 目录就是全部事实来源：4=ModuleList、5=MemoryList、6=Exception、9=Memory64List、24=ThreadNames。

```python
import struct, bisect
from pathlib import Path
b = Path(dump).read_bytes()
u32 = lambda o: struct.unpack_from('<I', b, o)[0]
u64 = lambda o: struct.unpack_from('<Q', b, o)[0]
st = {}
for i in range(u32(8)):
    p = u32(12) + i * 12
    st[u32(p)] = (u32(p + 4), u32(p + 8))
mods = []
rva = st[4][1]
for i in range(u32(rva)):
    m = rva + 4 + i * 108
    sp = u32(m + 20)
    mods.append((u64(m), u32(m + 8), b[sp + 4:sp + 4 + u32(sp)].decode('utf-16le', 'replace')))
mods.sort()                      # (base, size, path)，用 bisect 定归属
e = st[6][1]
print('code', hex(u32(e + 8)))            # 0xC0000005 = AV, 0xC0000409 = stack buffer overrun, 0xE06D7363 = C++ throw
print('addr', hex(u64(e + 24)), 'params', [hex(u64(e + 40 + i * 8)) for i in range(u32(e + 32))])
ctx = u32(e + 164)                        # CONTEXT 的 file offset：rip@+248 rsp@+152 rbp@+160 rcx@+128 rdx@+136 rbx@+144
```

判据（把异常翻译成人话）：

| 现象 | 含义 |
|---|---|
| `0xC0000005`，params[0]=0（读）或 1（写），params[1]=地址 | 地址 `0x0` ⇒ 空指针；地址是 `0xfffffffffXXXXXXX` 形态 ⇒ 已释放/未初始化内存里的残留值 |
| `0xC0000409` | 栈缓冲溢出或 `/GS` cookie 被踩，重点查 `memcpy`/`strcpy` 的**长度** |
| `0xE06D7363` | C++ 异常未捕获，栈里找 `RaiseException` 上一层 |
| `0x80000003` | `int3`/断言，看是否 `__debugbreak` 后跟日志 |

## 2. PC 落位：模块 + RVA + 函数边界 + 名字

1. 用模块表把 PC 换成 `(底模块, RVA)`。RVA 才是稳定身份，绝对地址每次启动都变。
2. 从**磁盘上的同一个 PE**（版本要对齐，先核对 `FileVersion`/时间戳）解析 `DIRECTORY_ENTRY_EXCEPTION`（`.pdata`，即 RUNTIME_FUNCTION 表）拿到函数边界 `[Begin, End)`。
3. 名字：`DIRECTORY_ENTRY_EXPORT` 里的 MSVC mangled 名用 `dbghelp.UnDecorateSymbolName` 还原。只有导出符号时才可靠；静态函数只能靠 RVA + 反汇编特征。
4. `pefile.PE(path, fast_load=True)` **必须**再 `parse_data_directories(directories=[...EXCEPTION, ...EXPORT])`，否则那些属性不存在（不是空，是不存在）。

## 3. 栈回溯：x64 靠 `.pdata`，不靠 rbp

`StackWalk64` 需要**每个模块**的 RUNTIME_FUNCTION；缺一个模块的 `.pdata`，链就断在那里，且它不会报错——只出一帧不代表只有一帧。要么给所有模块喂表，要么自己按 UNWIND_INFO 解。

自解每帧的算法（顺序很关键）：

1. `rva = pc - base`，二分找到 `(Begin, End, UnwindData)` 且 `rva < End` 的那条。
2. 读 UNWIND_INFO：`ver_flags@0`、`size_of_prolog@1`、`count@2`、`frame_reg@3&0xF`、`frame_off@(byte3>>4)*16`；unwind codes 从 `+4` 起，每条 2 字节 `(code_offset, op|info<<4)`。
3. `pl = rva - Begin`（当前指令相对函数头的偏移）。**倒序遍历** codes，跳过 `code_offset > pl` 的（尚未执行）。
4. op：0=PUSH_NONVOL（`reg = [rsp]; rsp += 8`）；1=ALLOC_LARGE（`rsp += imm`）；2=ALLOC_SMALL（`rsp += info*8+8`）；3=SET_FPREG（`rsp = framereg - frame_off`）；4/5=SAVE_NONVOL（`reg = [rsp+off]`，**先读再调 rsp**，倒序正好保证这一点）；10=PUSH_MACHFRAME（中断帧，直接取 rip/rsp）。
5. `ver_flags & 4` = CHAININFO：`+4+count*2+((count+1)//2)*2` 处是嵌套的 RUNTIME_FUNCTION，接着解。
6. 最后 `rip = [rsp]; rsp += 8`。

**叶函数捷径**：若当前 PC 所在函数没有 push/sub（如 CRT 的 `strlen`/`memcpy`），它没有栈帧，`[rsp]` 就是返回地址。先看 `[rsp]` 落在哪个模块，往往一步就抓到调用者。

## 4. 定责：读一条指令就够

- `mov rax, [rax]` 且 `rax` 来自 `call GetXxxPrivate` ⇒ 对象的**内部字段指针**为空/垃圾；去查该字段在类里的偏移（PDB 或引擎头文件），偏移能直接叫出字段名。
- 崩在 `strlen`/`strcpy`/`strlen` 的 SSE 循环（特征是常数 `0x7efefefefefefeff`、`0x8101010101010100`）⇒ 上游传了 **NULL 字符串**。往前找 5 字节处的 `call`，那就是罪魁的函数。
- 崩在 `memcpy`/`memmove` ⇒ 看 `rdx`（长度）与源/目的，常见是 `n` 未算或对象生命周期错。
- `rbx`/`r13` 常常是「参数索引、循环计数、标志位」，不是指针；别把所有寄存器都当对象看。
- 指针看起来像 `-(X+1)`（即 `0xfffffffff...`）而 `X` 是同一堆区里的另一个地址 ⇒ 这是**空闲链表/已释放块**的残留，不是活对象。

## 5. 多 dump 同源判定（决定「偶发」还是「必崩」）

把多个 dump 的 `(异常码, PC, RSP, RBP, 栈上前 0x400 字节)` 对齐：

- 全部相同 ⇒ **确定性单发路径**。这种 bug 一定能稳定复现，去找「每会话只执行一次」的代码（如 `if not flag then flag = true ... end` 的探针、首次 hook、首次加载）。
- 只有 PC 同、栈不同 ⇒ 同一函数的多个调用者，坏输入来自外部数据。
- PC 不同但栈顶几帧重叠 ⇒ 同一条链上的不同深度，多半是时序/生命周期。

顺带核 `modules` 数量、新增/缺失的 DLL、以及宿主日志尾部时间戳与 dump 时间的间隔（间隔 = 从最后一条日志到崩溃的窗口，用来判断「日志之后还做了什么」）。

## 6. 宿主脚本 VM 专章（Lua 为例，其它 VM 同构）

当宿主把脚本运行时**静态链进自己的 DLL**（UE4SS 就是这样，`0xC7xxxx–0xC9xxxx` 是 Lua 核心），崩溃常停在 VM 的 C API 上，此时唯一有用的证据是「脚本的哪一行」。

取 VM 状态的入口：

1. 从崩溃帧的寄存器里找 `lua_State*`。判据：`tt` 字节（+8）等于 8（LUA_TTHREAD）、`status`（+10）≤ 1、`top`（+16）、`ci`（+32）都能读且落在 dump 的映射页里。
2. 顺着 `L->ci` 走 `previous`（+0x10）拿调用链。CallInfo 布局：`func@0`、`top@8`、`prev@0x10`、`next@0x18`、`u.l.savedpc@0x20`。
3. **陷阱**：`u` 是联合体，C 函数帧里 `savedpc` 位置放的是 `k` 续延指针，内容往往是**上一个用过该 CallInfo 的 Lua 帧留下的脏值**。凡 `tt` 不是 Lua 闭包的帧，一律丢弃 `savedpc`，别拿它去匹配源码。
4. `func` 槽是 `StkIdRel`（指向栈槽的指针），不是 TValue 本身，要再读 16 字节。TValue 的 `tt` 字节在 +8：低 4 位是类型，`0x40` 位是「可回收」（`ctb()`），所以 Lua 闭包=0x46、C 闭包=0x66、userdata=0x47、短串=0x44，别被 0x40 位骗。
5. 拿 Lua 闭包的 `p`（+0x18，Proto*），Proto 关键偏移：`linedefined@44`、`lastlinedefined@48`、`sizecode@24`、`k@56`、`code@64`、`lineinfo@88`、`abslineinfo@96`、`source@120`。`source` 是 TString，内容在 +0x18，长度看 +11（短串）或 +16（长串）。
6. 行号：`luaG_getfuncline` = 每 128 条指令一个绝对锚点（abslineinfo），锚点后按 `lineinfo` 的带符号字节累加。`pc = (savedpc - code) / 4`。

dump 里 Proto 页常常缺失（minidump 只收栈页），此时改用**字节码反向匹配**：

```python
# 编译本地脚本 -> 每个 Proto 的 code 字节 -> 在 dump 的映射区里 find()
# 命中条件必须加一条：savedpc 落在 [命中地址, 命中地址 + len(code)) 内
# 否则 1~5 条指令的短 Proto 会海量误命中；且按 ninstr 降序展示，长匹配优先。
for pr in protos:
    i = blob.find(pr['code'])
    while i >= 0:
        va = region_start + i
        if va <= savedpc < va + len(pr['code']): hit(pr, (savedpc - va) // 4)
        i = blob.find(pr['code'], i + 1)
```

自己解 luac 5.4 二进制块时的坑（都实测踩过）：

- 头 33 字节（签名4+版本1+格式1+LUAC_DATA 6+sizes 5+INT 8+NUM 8），第 34 字节是 upvalue 数，Proto 从 34+ups 开始。
- **所有整数都是 varint**：7 位一组、**高位为 1 表示结束**；abslineinfo 的 pc/line 也是 varint（不是 int32）。
- 常量 tag：0=nil、1/0x11=bool、3=int(8字节)、0x13=float(8字节)、4/0x14=string。
- 解析校验用「**整体消费完**」：`c.p == len(chunk)` 不成立就是偏移猜错了；可以扫 30..80 当起点自校准。
- lupa 默认可能绑 Lua 5.5（字节码与 5.4 不兼容）：必须 `import lupa.lua54`；`LuaRuntime(encoding=None)` 时传 `bytes` 路径，否则报 `string expected, got POBJECT`。

## 7. Unreal / UE4SS 专章

已知崩溃签名（都是真跑出来的，不是教科书）：

| 签名 | 位置 | 含义 |
|---|---|---|
| `mov rax,[rax]` 后 AV，`rax` 为垃圾 | `UObjectBase::IsA` → `UStruct::GetSuperStruct` | 反射拿到了**失效 UObject**：`ClassPrivate` 槽是残留值，`+0x40` 的 SuperStruct 自然读不到。UE4SS 的 `IsA` 不做有效性检查 |
| `strlen(NULL)` | `Lua::get_string(int)` → `lua_tolstring` 返回 NULL | 脚本把 **userdata/table/nil** 当字符串传进绑定函数；UE4SS 缺空判断，`pcall` 兜不住原生 AV |
| `IsA` OK 但字段乱 | 结构体 out 参数反射写回（`push_structproperty`/`auto_construct_object`） | 把不可读的 Out 结构体再反射回 Lua 表，字段里的指针是脏的 |

定位要点：

- `UE4SS.dll` 的 `.pdata` 很全、导出是 MSVC mangled 名（`dbghelp.UnDecorateSymbolName` 直接还原），所以**函数身份可靠**；`PBZ.exe`/`UE4SS` 主模块的静态函数只能靠 RVA。
- 0x400~0x2000 窗口的「nearest export」会骗人（实测把 `0xBA0A44` 报成 `SinglePassScanner::string_to_vector+0x3f4`）。只信 `[fn begin, end)` 区间，不信就近导出。
- 日志与 dump 联合：宿主日志最后一条与 dump 时间的差值就是「死前窗口」；如果某条预期日志**始终没出现**，说明崩溃发生在它的参数求值阶段，那条语句就是嫌疑行。
- UE4SS 设置里 `FullMemoryDump=0` 时，只有栈和少量页；堆对象（Proto、闭包）常常读不到，别把「读不到」当「空指针」。

修复分层（永远同时给三档）：

1. **脚本/mod 侧最小改动**：删掉/改写触发那条表达式（例如用字符串键代替 `FName` userdata 键）；`pcall` 无效时不要假装它有效。
2. **宿主侧加固**：在边界函数加空判断/类型判断（`get_string` 加 `if (!p) return {};`），需重编译宿主。
3. **临时隔离**：停用该 mod / 该 hook / 该特性开关，留住可玩状态。

## 8. 报告模板

```
## 结论：<一句话根因，含模块+偏移>
### 直接崩溃点     表格：异常码 / 地址语义 / PC(RVA) / 指令 / 关键寄存器
### 谁把它弄崩的   帧表：帧号 | 模块!偏移 | 函数 | 备注（源码行若有）
### 触发条件      一次性？特定输入？时间窗口？多 dump 是否同源
### 证据         日志行号、dump 时间、失败指令原文
### 修复          三档（mod 侧 / 宿主侧 / 隔离）+ 每档代价
### 未确认       显式列出假设与需要复现验证的点
```

## 9. 两条真实案例（同一套判据跑出来的样子）

**A. 垃圾指针被当活对象**（UE4SS，`crash_2026_11_20_11_12_27.dmp`）

```
异常 0xC0000005 读 0xfffffffffdfe94ef   PC = UE4SS.dll+0xB0C10E   mov rax,[rax]
rax 来自对象 +0x10 的 ClassPrivate 槽 = 0xfffffffffdfe94af；崩溃地址 = 该值 +0x40（SuperStruct 偏移）
0xfffffffffdfe94af 形如 -(X+1)（X 是同一堆区的另一地址）⇒ 空闲块残留，不是活 UObject
帧链：IsA ← auto_construct_object ← push_structproperty ← 参数/出参编组器 ← process_lua_function
⇒ 结论：宿主把结构体 out 参数反射回脚本时拿到失效对象，且未校验有效性
```

**B. CRT 空串 + 脚本行回溯**（同一游戏，22 分钟内两个 dump 签名完全相同）

```
异常 0xC0000005 读 0x0   PC = ucrtbase.dll+0x2C9F1   mov rdx,[rax]   rcx=rax=0
最近导出 strlen，[rsp] = UE4SS.dll+0xBA4130（Lua::get_string 内）⇒ strlen(NULL)
上游 0x2BC58E 调 get_string(L, 1)，该槽是 FName userdata ⇒ lua_tolstring 返回 NULL
字节码匹配 CallInfo 链：main.lua:5179 的 act[FName("PreHitPointDuration")]
日志里预期的 "frames probe:" 行始终没出现 ⇒ 死在参数求值阶段；该探针每会话一次 ⇒ 必崩
```

## 10. 陷阱清单（都是踩过的）

1. `mem()` 返回 None = 页不在 dump 里，**不等于**内存是 NULL。别把不可读当证据。
2. `StackWalk64` 缺任一模块的 `.pdata` 就断链，且只返回一帧不报错。
3. `pefile` 不 `parse_data_directories` 就没有 EXCEPTION/EXPORT 属性；`pe.get_data(x)` 参数是 **RVA**，不是文件偏移。
4. 只看了眼 `rip` 就下结论。要看**寄存器+栈+前 16 字节指令**三样。
5. 把「堆对象页缺失」误判成「对象被释放」。
6. 单个 dump 定「偶发」。必须至少两个 dump 对齐才能谈概率。
7. 在原生 AV 面前相信 `pcall`/`try/catch`/`SetUnhandledExceptionFilter` 能救。都不能。
8. 用 `mtime` 判「日志新鲜度」（pnpm/CAS 会保留旧 mtime）；要看日志内容时间戳。
