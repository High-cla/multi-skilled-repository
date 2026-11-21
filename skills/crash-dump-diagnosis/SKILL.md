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


## 0.1 WinDbg 标准取证路径（Windows 首选）

本技能主要覆盖 Windows PE / WER / Minidump，尤其是 x64 用户态进程与 UE4SS。若输入是 Linux ELF core 或 macOS core，不要套用下文的 MINIDUMP stream、PE `.pdata` 或 WinDbg 命令；应切换到对应平台的 GDB / LLDB 工作流。

先识别 dump 类型与目标架构，再选命令集。用户态进程 dump 与内核 bugcheck dump 不是同一种证据模型，不能把 `.ecxr`、`.bugcheck` 等命令混用。

### 用户态 dump

```text
windbg -z C:\Dumps\app.dmp
.symfix C:\Symbols
.sympath+ C:\Build\PrivatePdb
.exepath+ C:\Build\Images
.reload /f
!analyze -v
.exr -1
.ecxr
r
u @rip-10 @rip+20
kv
~* kv
lm
lmv m suspect_module
!address @rip
```

执行顺序与判读：

1. `!analyze -v` 先提供异常/线程/模块线索，不是最终根因判决；`IMAGE_NAME`、`MODULE_NAME` 或 bucket 可能只是故障现场，不等于责任模块。
2. `.exr -1` 读取最近异常记录；`.ecxr` 切换到异常发生时保存的寄存器上下文。切换后再执行 `r`、反汇编和 `kv`，避免误用当前调试器线程上下文。
3. x64 使用 `@rip`；x86 应改用 `@eip`。检查故障指令前后指令、参与寻址的寄存器、异常参数和对应内存区域，建立「模块 + RVA + 指令 + 寄存器」证据链。
4. `~* kv` 查看其他线程栈，`lm` / `lmv` 核对模块基址、映像版本和符号状态；`!address` 帮助判断地址所在区域。线程栈、异常线程和实际责任线程可能不同。
5. 若 dump 缺少某页，命令无法读取该地址时只记录为「dump 未包含 / 不可访问」，不能据此认定该指针为 NULL、对象已释放或内存损坏。

### 内核 bugcheck dump

```text
windbg -z C:\Windows\MEMORY.DMP
.symfix C:\Symbols
.reload /f
.bugcheck
!analyze -v
kv
lm t n
!thread
```

内核分析从 `.bugcheck` 与 `!analyze -v` 开始。若输出给出 trap frame，使用 `.trap <TrapFrame地址>`；若给出 context record，使用 `.cxr <ContextRecord地址>`，然后再查看 `r`、`kv`。不要在没有对应记录地址时盲目切换上下文。进一步检查进程/线程、IRQL、驱动和设备对象时，必须依据 dump 类型及可用扩展命令决定；小型内存转储往往不包含所需对象页。

## 0.2 符号、映像与 dump 完整性

- 符号路径建议分开配置：`.symfix C:\Symbols` 使用 Microsoft 公共符号服务器并缓存到本地；`.sympath+ <私有 PDB 目录>` 添加应用自己的 PDB；`.exepath+ <匹配的 EXE/DLL 目录>` 提供映像文件；随后 `.reload /f` 强制重新加载。
- PDB 必须与生成该 dump 的二进制匹配，不能只凭文件名相同判断。核对 PDB 的签名标识（GUID/Age）、映像版本、时间戳与 checksum；不匹配的符号可能产生错误函数名或行号。
- Microsoft 公共符号通常足以改善系统模块的函数级栈回溯，但不保证包含局部变量、私有类型布局或源代码行信息。缺少 private symbols 时，明确降低结论粒度，不要用相邻导出符号冒充真实函数边界。
- 需要排查符号加载失败时，可临时执行 `!sym noisy`，再 `.reload /f <module>`；查看诊断信息后用 `!sym quiet` 关闭详细日志。记录哪些模块成功加载符号、哪些只有 export / deferred symbols。
- 用户态 minidump 只保存其 stream 描述和被选中的内存页；不同生成选项会改变可读内存范围。内核 Small Memory Dump（固定 64 KB）只包含有限的 bugcheck、上下文、栈和模块信息；Kernel Memory Dump 主要保存内核使用的内存，不包含用户态进程内存；Complete / Active dump 保存范围更广，但文件体积与敏感数据暴露风险也更高。
- 先用 WinDbg 的 dump 信息和实际可读性确认证据边界，再解释缺失字段。不能把「minidump 中没有该地址」推断为「运行时地址无效」。如果必须还原堆对象、Lua Proto 或完整调用参数，应明确说明需要更完整的 dump 或复现采集。
- 最低采集清单：原始 dump（不要只给截图）、崩溃时间与时区、OS build、进程/模块版本、匹配的 EXE/DLL/PDB、崩溃前日志，以及同一会话的其他 dump。分享前提醒用户检查 dump 中可能包含的路径、用户名、令牌和业务数据。

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
4. 先按每个操作码声明的额外 slot 数把 unwind codes 解析成完整操作，再按 prolog 执行顺序的逆序应用；**额外 operand slot 不是独立 opcode**。常见 op：0=PUSH_NONVOL（从 `[rsp]` 恢复寄存器并 `rsp += 8`）；1=ALLOC_LARGE（`OpInfo=0` 时下一 slot 是 `imm16*8`，`OpInfo=1` 时下两 slot 组成 `imm32`）；2=ALLOC_SMALL（`rsp += info*8+8`）；3=SET_FPREG（`rsp = frame_reg - frame_off*16`）；4/5=SAVE_NONVOL / SAVE_NONVOL_FAR（恢复非易失寄存器，5 使用 32 位偏移）；8/9=SAVE_XMM128 / SAVE_XMM128_FAR（恢复 XMM 寄存器，偏移单位/编码按对应 opcode 解）；10=PUSH_MACHFRAME（`OpInfo` 指示是否含 error code，按机器帧布局恢复 RIP/RSP，不能再按普通函数尾声执行一次 `rip=[rsp]`）。
5. `UNWIND_INFO` 的 `Flags` 位与 `Version` 要分别解释：`UNW_FLAG_EHANDLER` / `UNW_FLAG_UHANDLER` 表示后面跟异常/终止处理程序信息；`UNW_FLAG_CHAININFO`（flags bit 2）才表示后面跟 chained `RUNTIME_FUNCTION`。CHAININFO 记录位于 `4 + ((count + 1) & ~1) * 2`，即 4 字节头加上按偶数 slot 对齐后的 unwind-code 数组之后；不要把未对齐位置当作链记录。
6. 以上是常见 x64 操作码的解读框架，不是完整的 Windows unwinder 实现。必须处理 opcode 额外 slot、版本差异、epilog、handler 与 chained unwind info；遇到不支持的编码、异常栈或不完整模块表时，优先以 WinDbg / DbgEng 的结果交叉验证，不能静默跳过后仍声称栈完整。
7. 完成普通函数的 unwind 操作后，才从恢复后的栈顶读取返回地址并调整 RSP；若已通过 `UWOP_PUSH_MACHFRAME` 恢复中断帧，则使用机器帧中的 RIP/RSP，不再重复执行普通返回地址弹栈。

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

当宿主把脚本运行时静态链进自己的 DLL 时（某些 UE4SS 构建即属于此类），崩溃可能停在 VM 的 C API 上，此时应尽可能恢复「脚本的哪一行」。Lua 运行时版本、结构体布局和地址范围必须以实际 UE4SS 二进制 / commit 验证；`0xC7xxxx–0xC9xxxx` 只可视作特定样本的地址线索，不是通用范围。

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

### 7.1 UE4SS 专项工作流（优先于泛化排查）

本节以 UE4SS 官方仓库当前文档、配置模板和 Lua API 为准。**不要把旧版本 UE4SS / Lua 的结构偏移、函数 RVA、AOB、配置项默认值当作跨版本常量。** 任何内存布局分析都必须绑定到实际加载的 `UE4SS.dll`、对应游戏 EXE/DLL、UE 版本和 UE4SS commit。

#### A. 先确认实际加载的 UE4SS 与游戏环境

最少记录以下信息：

- 游戏 EXE 完整路径、游戏版本、Unreal Engine major/minor 版本，以及目标构建配置（Shipping / Test / Development）。
- 实际加载的 `UE4SS.dll` 路径、文件版本 / SHA-256、UE4SS Release 或 commit；不要只看压缩包名称，因为 proxy DLL、`override.txt`、`--ue4ss-path` 和不同 working directory 可能让游戏加载另一份 DLL。
- `UE4SS-settings.ini`、所有生效的 `mods.txt`、Mods 目录结构，以及每个 Mod 的版本。留意 `[Overrides]`、`ModsFolderPath`、`ModsFolderPaths`、`ControllingModsTxt` 和 `UE4SS_MODS_PATHS`，否则容易分析错 Mod 清单。
- 完整 `UE4SS.log`（不要只截最后几行）。官方安装文档建议在 UE4SS 主 DLL 所在目录检查该文件，确认时间戳是本次运行且无初始化错误。

官方支持的 proxy DLL 参数 `--disable-ue4ss` 可用于暂时禁用 UE4SS；仅在 proxy DLL 安装方式下使用。`--ue4ss-path` 可显式指定待测 DLL。做 A/B 时一次只改变一个变量，并保留每轮日志和 dump。

#### B. 最小化隔离：区分 UE4SS 核心、Mod 与游戏本体

按下面顺序做对照，不要一开始就重装或同时改多个开关：

1. **原版基线**：确认不加载 UE4SS / Mods 时能否复现。若原版同样崩溃，不能仅凭 dump 中出现 UE4SS 模块就定责。
2. **UE4SS 无第三方 Mod**：保持同一 UE4SS DLL 和配置，只禁用第三方 Mods（保留必要的内置组件时需在报告中注明）。崩溃消失后，再按 `mods.txt` 分组或二分启用，锁定最小复现 Mod 集。
3. **单变量配置实验**：只在启动阶段崩溃、且日志/调用栈指向 UObject 数组初始化或缓存路径时，按官方建议单独尝试 `[General] bUseUObjectArrayCache = false`。若问题消失，记录为缓存路径相关证据；不能把它当成所有 UE4SS 崩溃的通用修复。
4. 若证据指向对象迭代 / hash table 查询路径，可单独验证 `bForceGUObjectArrayForIteration = true`；这是诊断性对照，不应和其他设置一起盲目切换。
5. 若崩溃发生在 Mod 热重载或自动重载阶段，检查 `EnableHotReloadSystem`、`EnableAutoReloadingLuaMods` 和触发时间；先关闭重载机制验证是否与卸载生命周期相关。

不要把「关掉 UE4SS 后不崩」直接写成「UE4SS 核心 bug」：它只证明故障依赖 UE4SS 注入路径，仍须继续区分 UE4SS 本体、第三方 Mod、引擎版本兼容和 hook 交互。

#### C. UE4SS 自带 dump 与采集完整度

检查 `UE4SS-settings.ini` 的 `[CrashDump]`：

```ini
[CrashDump]
EnableDumping = 1
FullMemoryDump = 0
```

- 先确认 `EnableDumping` 是否启用，并保留 UE4SS 自动生成的原始 dump。
- 若当前 dump 中缺少 Lua Proto、闭包、UObject 或堆对象页，才考虑在可控复现环境中将 `FullMemoryDump` 改为 `1` 进行一次完整采集；这会显著增加文件体积，也可能暴露进程中的敏感数据。采集完成后恢复原设置。
- 同时保存 `UE4SS.log`、崩溃时间、游戏进程模块列表、`UE4SS-settings.ini`、Mods 清单及相同会话的其他 dump。不要把日志截断、文件修改时间或缺失页作为单独的根因证据。

#### D. Lua Hook / UObject / 参数封送

根据 UE4SS Lua API，`RegisterHook` 的目标 `UFunction` 必须在注册时已存在于内存中；它返回 `PreId` 和 `PostId`，卸载时要正确注销。`/Script/` 路径的回调参数语义与其他路径不同，必须按 API 文档核对 pre/post 时机，不能靠猜。

```lua
local pre_id, post_id = RegisterHook(
    "/Script/Engine.PlayerController:ClientRestart",
    function(Context, NewPawn)
        local controller = Context:get()
        local pawn = NewPawn:get()

        if controller and controller:IsValid() then
            print(controller:GetFullName())
        end
        if pawn and pawn:IsValid() then
            print(pawn:GetFullName())
        end
    end
)
```

分析规则：

- Hook 参数通常是 `RemoteUnrealParam` 包装对象；需要按 API 用 `:get()` 取出 UObject，再检查 `:IsValid()`。区分 Lua `nil`、无效 UObject、有效 UObject 和非 UObject userdata/table/string，不要把它们隐式混成字符串或对象指针。
- 对 `UObject` 做反射、读取属性或调用 UFunction 前先验证对象有效性；地图切换、对象销毁、GC、异步回调及缓存对象跨场景复用，都是重点检查的生命周期边界。
- 记录 hook 的完整 UFunction 路径、Pre/Post ID、触发线程、对象 FullName、参数类型和回调进入/退出日志。日志调用也必须避免对无效对象继续做反射。
- `RegisterHook` 只支持 `UFunction`，不支持 delegate；目标函数必须已加载。若注册时机早于函数加载，先解决注册时序，不要把 hook 未生效误诊成崩溃根因。
- `pcall` 只能处理 Lua 可捕获错误，不能保证拦截 UE4SS / Unreal 原生代码中的 access violation、悬空指针或跨线程竞态。

#### E. 异步线程、游戏线程与 Lua VM 卸载

如果栈、日志或复现条件涉及 async callback、mod hot reload、`OnUnload`、`lua_close`、`hook_lua`、`ProcessEvent` 或 `EngineTick`，将线程与生命周期作为一等诊断对象：

- 从异步线程触发、但需要访问 UObject / Unreal 反射 API 的工作，检查是否通过 `ExecuteInGameThread(callback)` 或明确可用的游戏线程执行机制调度；不要仅凭 Lua 层没有报错就认定跨线程访问安全。
- 检查 `RegisterHook` 是否在 Mod 卸载时正确 `UnregisterHook`，两个 ID 是否匹配，是否存在 hook 仍执行时 Lua VM 已被关闭的路径。
- 将崩溃时间与 `OnUnload`、热重载、异步线程停止/Join、待执行 game-thread action 清理、hook 注销和 `lua_close` 对齐。若 dump 显示同一 Lua state 被多个线程并发访问，先确认是否有缺失同步或状态销毁竞态。
- UE4SS 当前源码的 LuaMod 卸载路径包含停止并 Join async thread、同步 game-thread 执行、清理待执行动作、注销 hooks 后再关闭 Lua state 等保护步骤。排查自定义 Mod 时，应将其生命周期与该顺序对照；若崩溃位于 UE4SS 内部，也必须核对 dump 对应的确切源码 commit，不能从其他版本源码推断。

#### F. AOB 缺失 / 引擎版本错配 / 反射布局异常

先区分「UE4SS 初始化失败」与「运行中崩溃」：

- 若日志明确显示 AOB / signature 未找到、GUObjectArray、GMalloc、FName 或相关扫描失败，优先按 UE4SS 官方 *Fixing compatibility problems* 流程验证引擎版本、构建配置和签名；不要把扫描失败直接解释成 Lua Mod 崩溃。
- `UE4SS_Signatures` 目录可为特定游戏提供自定义 AOB / callback。只有通过反汇编确认匹配的是目标函数、并验证返回地址确实指向函数或全局变量后，才采用自定义签名。错误 AOB 可能把错误地址注入后续反射逻辑，形成二次崩溃。
- 核对 `[EngineVersionOverride]` 中 `MajorVersion`、`MinorVersion`、`DebugBuild`、`Stats` 和 `PointerHash`。只在自动检测有证据表明错误时做单项覆盖；错误的对象布局、STATS 偏移或 hash 算法可能让 UObject / FField / 属性访问表现为随机损坏。
- 若崩溃发生在 `GUObjectArray`、对象 hash table、`FName`、`FField`、`UObject::GetClassPrivate`、`IsA`、`ProcessEvent` 或 `StaticConstructObject` 周围，先把引擎版本、游戏构建、UE4SS commit 和实际加载 DLL 对齐，再分析指针。不能把另一款游戏或另一 UE 小版本的固定偏移照搬过来。

#### G. PDB 与源码必须和实际 UE4SS 二进制匹配

UE4SS 官方 README 明确指出 PDB 不会被打包进 minidump，调试时必须使用与崩溃 DLL 完全匹配的 PDB。若是自行构建版本，记录构建时的 Git commit；分析时 checkout 同一个 commit 并重新构建，以生成匹配符号。仅下载同名最新 PDB 不足以证明匹配。

本技能原有的 Lua `CallInfo` / `Proto` 偏移、UE4SS 函数 RVA、`0xC7xxxx–0xC9xxxx` 等地址特征，只能作为对应已验证构建的线索。必须先用模块版本、PDB、反汇编或源码确认该布局；禁止把它们当作所有 UE4SS 版本的通用 ABI。

#### H. UE4SS 结论必须给出归属类别

最终结论至少归入以下之一，并附证据与置信度：

1. **Game / Unreal**：不加载 UE4SS 仍可复现，或实际故障路径在游戏自身代码且 UE4SS 仅为旁观模块。
2. **UE4SS core / compatibility**：与 UE4SS 注入或内部扫描/反射/缓存有关；已排除第三方 Mod，且符号与版本匹配。
3. **Lua Mod**：禁用特定 Mod 后稳定消失，重新启用可复现；最好定位到脚本文件、行号、hook 或参数类型。
4. **C++ Mod**：调用栈落在该 Mod 的原生代码，或二分隔离到单个 C++ Mod；需匹配该 Mod 的 PDB。
5. **Interaction / lifecycle**：单个组件单独运行正常，但特定 Mod 组合、Hook 顺序、异步线程、地图切换或热重载时崩溃。
6. **Unknown / insufficient dump**：明确列出缺失的 dump 页、PDB、日志或复现条件；不得把推测伪装成确定根因。

### 7.2 UE4SS 官方参考资料

- UE4SS 官方仓库：[UE4SS-RE/RE-UE4SS](https://github.com/UE4SS-RE/RE-UE4SS)。
- [Installation Guide](https://docs.ue4ss.com/dev/installation-guide.html)：日志位置、DLL 加载、Mods 清单、配置与启动参数。
- [UE4SS-settings.ini](https://github.com/UE4SS-RE/RE-UE4SS/blob/main/assets/UE4SS-settings.ini)：对象缓存、执行线程、引擎版本覆盖、Hooks、CrashDump 开关。
- [RegisterHook API](https://docs.ue4ss.com/dev/lua-api/global-functions/registerhook.html)：Hook 注册时机、参数封送、Pre/Post ID 及注销。
- [ExecuteInGameThread API](https://docs.ue4ss.com/dev/lua-api/global-functions/executeingamethread.html)：把回调调度到游戏线程。
- [Fixing Compatibility Problems](https://docs.ue4ss.com/dev/guides/fixing-compatibility-problems.html)：AOB 缺失与自定义签名。
- [Advanced Compatibility Guide](https://docs.ue4ss.com/dev/guides/fixing-compatibility-problems-advanced.html)：签名定位与反汇编流程。
- [UE4SS README — Debugging](https://github.com/UE4SS-RE/RE-UE4SS#debugging-under-wine)：使用与崩溃 DLL 完全匹配的 PDB；以仓库当前 README 为准。

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

## 11. 官方参考资料（WinDbg / Context7）

- Microsoft Learn — [Analyzing a User-Mode Dump File](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/analyzing-a-user-mode-dump-file)：打开用户态 dump、命令行选项与 minidump 证据限制。
- Microsoft Learn — [Getting Started with WinDbg](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/getting-started-with-windbg)：符号路径、`.symfix`、`.sympath`、`.reload` 与基本栈回溯。
- Microsoft Learn — [Varieties of Kernel-Mode Dump Files](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/varieties-of-kernel-mode-dump-files)：Small、Kernel、Complete、Automatic 与 Active dump 的覆盖范围。
- Microsoft Learn — [Kernel Memory Dump](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/kernel-memory-dump) 与 [Small Memory Dump](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/small-memory-dump)：内核 dump 的包含/排除范围及 64 KB 小型转储限制。
- Context7 检索使用的文档库：`/websites/learn_microsoft_en-us_windows-hardware_drivers_debugger`（WinDbg 官方文档镜像；以 Microsoft Learn 原文为准）。
