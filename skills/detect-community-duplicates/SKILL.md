---
name: detect-community-duplicates
description: 检测小区表格中的重复小区并按团队模板格式输出 Excel 核查报告。适用于用户上传含小区列表的 xlsx/csv 文件并要求做重复检测、判重、去重分析的场景，触发词包括「重复小区」「小区重复」「com_name 重复」「shape 重复」「重复检测」「判重」「核查清单」。本技能提供归一化函数、重复类型分类、基准判定规则、4 sheet 报告模板（概览/重复组汇总/重复明细 7列模板/全量明细）和重算+AIGC 标识流程。
agent_created: true
---

# 检测小区重复（detect-community-duplicates）

## 概述

对小区表格（xlsx 或 csv，含 `com_name` 字段）按业务可识别规则做**纯统计式重复检测**，输出可直接交付业务方核查的 Excel 报告。核心能力：

- **三层判重**：精确重复 → 归一化重复（去前缀+标点+冒号+业务后缀）→ 必要时双维度交叉（com_name + card_address）
- **重复类型分类**：精确重复 / 前缀差异 / 标点差异 / 后缀差异
- **基准判定**：组内 hs 最大为基准（适配精确重复组和前缀更大组），其余为冗余
- **团队模板**：重复明细 sheet 7 列精简格式，第 1 条标「基准」绿底，第 2+ 条标「★冗余」红底
- **公式重算**：用 formulas 引擎重算所有公式并扫描错误，AIGC 标识写入

## 触发场景

- 用户提供含小区列表的表格文件（xlsx 或 csv），要求做重复检测
- 关键词：「重复小区」「小区重复」「com_name 重复」「shape 重复」「判重」「核查清单」「按 com_name 统计重复」
- 用户要求「按之前统计的格式输出」小区重复报告

## 工作流

### Step 1: 读取源文件并做字段普查

1. **识别真实格式**：扩展名 `.xlsx` 不一定是真 xlsx，先用 `file` 命令或 `xxd -l 64` 检查头部。若是 CSV 套壳（首字节不是 `50 4B 03 04`），改用 `csv.DictReader(encoding='utf-8-sig')` 读。GBK 编码会失败，统一用 utf-8-sig。
2. **字段普查**：列出所有字段名，统计每列非空数/唯一数/前 3 个示例值。识别字段映射：
   - `com_name` → 小区名称（必填）
   - `com_id` / `comId` → comId（主键，全表唯一）
   - `com_code` → 小区编码
   - `hs` → 户数（用于基准判定）
   - `pqmc` → 三级片区（用于明细 sheet 第 7 列）
   - `shape` → WKT 几何（用于 shape 维度检测）
   - `card_addres` → 卡片级地址（注意拼写少一个 s）
3. **非空率统计**：识别空值列（如 `com_addres` 全空、`community_name` 部分空）。

### Step 2: 精确重复检测

按 `com_name` 原值完全相同分组，统计重复组数、涉及行数、冗余条数。**精确重复通常很少或为 0**——大部分重复靠归一化才能发现。精确重复组在重复类型分类中标「精确重复」，是高置信度铁证。

### Step 3: 归一化重复检测（核心）

加载 `references/normalization.md` 查看完整归一化函数源码与设计原理。归一化分四步：

1. **去行政区前缀**：`(郑州市)?(金水区|惠济区|郑东新区|中原区|二七区|管城区|金水|惠济|商鼎)?`
2. **去行首冒号**：处理 `: 后牛岗社区` 这种带冒号前缀的脏数据
3. **去标点空白**：`[\s·．.,，、\-—_/\\|:：;；'""'']+`
4. **循环去末尾业务后缀**：`(小区|家属院|家属属院|院|社区|家园|花园|公寓|家属)$`，循环去直到稳定，处理「前牛岗社区 vs 前牛岗社区社区」（后缀重复两次）

归一化后按值分组，重复组 = 组内成员数 > 1 的组。

**执行脚本**：可直接 import `scripts/normalize.py` 中的 `normalize()` 函数，或按 references 中的源码内联实现。

### Step 4: 重复类型分类与基准判定

对每个重复组：

**重复类型**（按 `dup_type(grp)` 函数判定）：
- `精确重复`：组内所有 `com_name` 完全相同
- `标点差异`：组内有成员以冒号 `:` / `：` 开头
- `后缀差异`：去掉前缀+标点后组内成员仍不同（说明差异来自业务后缀，如 `财信花园` vs `财信花园小区`）
- `前缀差异`：其他情况（带/不带行政区前缀）

**基准判定规则**：**组内 hs 最大为基准**（建议保留），其余为冗余（建议合并/删除）。此规则对精确重复组（都不带前缀）和前缀更大组都适用，比"不带前缀=基准"更稳健通用。

**判定列**（输出到「重复组汇总」sheet）：
- 精确重复·冗余为碎片（冗余 hs < 基准 hs）
- 精确重复·需人工确认（冗余 hs ≥ 基准 hs）
- 冗余为碎片（户数更小）
- 带前缀为基准·需人工确认（带前缀那条 hs 更大，与前几份规律相反，不能简单按前缀判冗余）

### Step 5: 输出 Excel（按团队模板格式）

加载 `references/output_format.md` 查看完整 4 sheet 结构与样式约定。报告 4 个 sheet：

| Sheet | 内容 | 行数 |
|---|---|---|
| 概览 | 4 KPI + 统计口径对比 + N 条结论 + 户数档位柱状图 | ~30 |
| 重复组汇总 | 每组一行，含归一化名称/出现次数/冗余条数/基准写法/冗余写法/重复类型/判定 | = 重复组数 |
| **重复明细（团队模板 7 列）** | 逐条列出，第 1 条「基准」绿底，第 2+ 条「★冗余」红底 | = 涉及行数 |
| 全量明细 | 源表全量底表，带组号+冗余标记，所有统计由它跨表引用 | = 总行数 |

**重复明细 sheet 严格按团队模板 7 列格式**（模板文件：`/Volumes/团队文件-甘肃时空图云/06.郑州智水/00原始数据/小区空间信息匹配数据/重复小区核查/重复小区数据核查结果.xlsx`）：

| A 组号 | B 组内序号 | C 建议核查 | D 小区名称 | E 小区编码 | F comId | G 三级片区 |
|---|---|---|---|---|---|---|

- 表头在**第 1 行**（无标题区、无合并单元格）；行 2+ 为数据。注意：与其他 sheet 不同，此 sheet 不用 title_area + header_row 双行结构。
- 组号格式 `G001 / G002 ...`，零填充 3 位。
- 「建议核查」列：组内第 1 条标 `基准`（绿底 XL_OK_FILL=`E2EFDA` 字体 XL_OK_FONT=`375623`），第 2+ 条标 `★冗余`（红底 XL_WARN_FILL=`FFF2CC` 字体 XL_WARN_FONT=`C00000`）。注意冗余标记前带 `★` 符号。
- 字段映射：`com_name → D 小区名称`、`com_code → E 小区编码`、`com_id → F comId`、`pqmc → G 三级片区`（空值留空，不写 NULL）。
- 列宽：`[8, 10, 11, 36, 18, 34, 14]`；冻结 `D4`；自动筛选 `A3:G{end}`。
- 条件格式：C 列 `="★冗余"` → 红底+加粗红字；C 列 `="基准"` → 绿底。

**其他 3 个 sheet** 用统一辅助函数：`title_area`（标题区合并）、`header_row`（表头行+样式）、`body_style`（数据区边框+对齐）、`section`（分节标题）、`widths`（列宽批量）。颜色：标题底色 `2F5597` 白字，分节底色 `D9E1F2` 深字。

### Step 6: 重算公式与 AIGC 标识

1. **重算公式**：用 `workbuddy-sheetagent` skill 的 recalc.py 脚本重算所有公式并扫描错误：
   ```bash
   /Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python \
     "/Users/kejitang/.workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent/<version>/skills/workbuddy-sheet-generation/scripts/recalc.py" \
     "<输出文件>.xlsx" 120
   ```
   要求 `total_errors=0`。若失败，修正公式后重跑。

2. **AIGC 标识**：写入 AIGC 内容溯源标识：
   ```bash
   /Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python \
     "/Users/kejitang/.workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent/<version>/skills/workbuddy-sheet-generation/scripts/aigc_label.py" \
     "<输出文件>.xlsx" --platform WORKBUDDY
   ```

3. **校验**：用 openpyxl 读回 `data_only=True`，核对 KPI 值、口径行、重复明细标记分布、全量明细标记分布是否与控制台打印一致。

## 关键约定

加载 `references/conventions.md` 查看完整约定。要点：

- **命名**：`<业务域>_<统计对象>重复统计.xlsx`，工作目录 `outputs/.<文件名去扩展名>.ref/`（如 `.biz_com重复统计.ref/`），build.py 放在工作目录内
- **Python 环境**：`/Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python`（已装 openpyxl、formulas）
- **sheet 顺序**：概览 → 重复组汇总 → 重复明细 → 全量明细
- **冗余标记一致性**：全量明细与重复明细两表必须用同一基准规则（hs 最大为基准），否则会出现相互矛盾。全量明细冗余标记公式：`=IF($N="","",IF(COUNTIFS($N$4:$N$end,$N,$A$4:$A$end,"<"&$A)=0,"基准","冗余"))`（N=组号列，A=原始序号列）
- **多维度统计**：双维度（com_name + card_address）时，地址维度必须按户数结构分类（同址多主体/1主+碎片/碎片均分），不能直接判为重复——会把"国贸中心/国贸新领地"这种合理共址误判。地址标记三态：主记录/附属/并立，同址多小区组的非主行标「并立」（黄底），不标「附属」（红底）
- **空值处理**：`com_addres` 列常拼写少一个 d，全表为空属正常（卡片级地址不在小区表）；`shape` 为 NULL 字符串时按空处理
- **临时文件清理**：解压 xlsx 模板读取 XML 后，及时清理 `/tmp/tpl_extract` 等临时目录

## 资源清单

### scripts/
- **`normalize.py`** - 归一化函数模块，可直接 import：`from normalize import normalize, dup_type, classify_judgment`。包含 `normalize(s)` 归一化函数、`dup_type(grp)` 重复类型分类、`classify_judgment(grp)` 判定分类。

### references/
- **`normalization.md`** - 归一化函数完整源码、设计原理、扩展指南（如何加新区县前缀、新业务后缀）
- **`output_format.md`** - 4 sheet 输出结构详细说明、辅助函数源码、样式常量、条件格式规则、图表生成
- **`conventions.md`** - 命名约定、Python 环境、sheet 顺序、冗余标记一致性、多维度统计约定、空值处理、临时文件清理

## 常见踩坑

1. **CSV 套壳 .xlsx**：扩展名是 `.xlsx` 但实际是 CSV。openpyxl 报 `BadZipFile: File is not a zip file`。用 `file` 命令或 `xxd -l 64` 一验就知道。改用 `csv.DictReader(encoding='utf-8-sig')` 读，gbk 解码会失败。
2. **后缀差异漏判**：原归一化只去前缀+标点，会漏判 `财信花园` vs `财信花园小区`、`丰产路110号` vs `丰产路110号院`、`前牛岗社区` vs `前牛岗社区社区`（后缀重复）。必须循环去末尾业务后缀。
3. **基准规则错位**：「不带前缀=基准」在含精确重复组或前缀更大组的数据上会失效。改用 **hs 最大为基准** 通用稳健。
4. **两表标记不一致**：全量明细与重复明细若用不同基准规则，5 个「前缀户数更大」的组两表标记会相反。必须统一基准。
5. **地址维度误判**：双维度统计时，地址维度不能直接判重——会把"国贸中心/招银大厦"这种合理共址当成重复。必须按户数结构分类。
6. **模板 xlsx 不兼容 openpyxl**：团队模板文件用 WPS 保存，openpyxl 读时报 `Fill() takes no arguments`。用解压 + XML 解析读：`unzip -o tpl.xlsx -d tpl_extract`，再读 `xl/sharedStrings.xml` 和 `xl/worksheets/sheet*.xml`。
7. **冒号文件名跨平台**：时间戳文件名 `片区水表井清单_2026-10-19 15:27.xlsx` 在 macOS 上能创建，但传到 Windows 会报错（冒号非法字符）。稳妥起见用短横线。
