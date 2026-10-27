# 输出格式（4 sheet 报告模板）

## 总体结构

每份小区重复统计报告输出 1 个 .xlsx 文件，含 4 个 sheet（按顺序）：

| 序 | Sheet 名 | 内容 | 行数 |
|---|---|---|---|
| 1 | 概览 | 4 KPI + 统计口径对比 + N 条结论 + 户数档位柱状图 | ~30 |
| 2 | 重复组汇总 | 每组一行，含归一化名称/出现次数/冗余条数/基准写法/冗余写法/重复类型/判定 | = 重复组数 |
| 3 | 重复明细 | 逐条列出，第 1 条「基准」绿底，第 2+ 条「★冗余」红底 | = 涉及行数 |
| 4 | 全量明细 | 源表全量底表，带组号+冗余标记，所有统计由它跨表引用 | = 总行数 |

## 样式常量

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 颜色
XL_HEADER_FILL = '2F5597'   # 表头深蓝底
XL_HEADER_FONT = 'FFFFFF'   # 表头白字
XL_SECTION_FILL = 'D9E1F2'  # 分节浅蓝底
XL_OK_FILL = 'E2EFDA'       # 基准绿底
XL_OK_FONT = '375623'       # 基准绿字
XL_WARN_FILL = 'FFF2CC'     # 冗余黄底
XL_WARN_FONT = 'C00000'     # 冗余红字（深红，加粗）
XL_BORDER = 'BFBFBF'        # 边框浅灰

# 字体
XL_TITLE_FONT = Font(bold=True, size=14, color='2F5597')
XL_HEADER_FONT_OBJ = Font(color=XL_HEADER_FONT, bold=True, size=11)
XL_SECTION_FONT = Font(bold=True, size=12, color='2F5597')

# 边框
THIN = Side(style='thin', color=XL_BORDER)
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# 对齐
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center')
LEFT_WRAP = Alignment(horizontal='left', vertical='center', wrap_text=True)
```

## 辅助函数

```python
def title_area(ws, ncol, title, subtitle=None):
    """标题区：第 1 行标题（合并 A:H），第 2 行副标题（合并 A:H），表头放第 3 行。"""
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    ws.cell(row=1, column=1, value=title).font = XL_TITLE_FONT
    ws.cell(row=1, column=1).alignment = LEFT
    ws.row_dimensions[1].height = 22
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
        ws.cell(row=2, column=1, value=subtitle).font = Font(size=9, color='595959')
        ws.cell(row=2, column=1).alignment = LEFT_WRAP
        ws.row_dimensions[2].height = 16


def header_row(ws, row, headers):
    """表头行：深蓝底白字加粗，居中，带边框。"""
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill = PatternFill('solid', fgColor=XL_HEADER_FILL)
        c.font = XL_HEADER_FONT_OBJ
        c.alignment = CENTER
        c.border = BORDER
    ws.row_dimensions[row].height = 22


def body_style(ws, r0, r1, ncol, center_cols=()):
    """数据区：加边框，center_cols 指定的列居中。"""
    for r in range(r0, r1 + 1):
        for c in range(1, ncol + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BORDER
            if c in center_cols:
                cell.alignment = CENTER


def section(ws, row, ncol, title):
    """分节标题：浅蓝底深字。"""
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncol)
    c = ws.cell(row=row, column=1, value=title)
    c.fill = PatternFill('solid', fgColor=XL_SECTION_FILL)
    c.font = XL_SECTION_FONT
    c.alignment = LEFT
    ws.row_dimensions[row].height = 22


def widths(ws, w):
    """批量设列宽。"""
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x
```

## Sheet 1: 概览

结构（行号示意，可调）：

- 第 1-2 行：标题区（`title_area`）
- 第 4-5 行：4 个 KPI（每个跨 2 列），用公式引用其他 sheet
  - A4 `小区记录数` | A5 `=COUNTA(全量明细!$A$4:$A$<end>)`
  - C4 `精确重复组` | C5 `<硬编码精确重复组数>`
  - E4 `归一化重复组` | E5 `=COUNTA(重复组汇总!$A$4:$A$<end>)`
  - G4 `冗余条数` | G5 `=SUM(重复组汇总!$D$4:$D$<end>)`
- 第 7 行：分节「一、统计口径对比」（`section`）
- 第 8 行：表头（`header_row`）：`统计口径 / 重复组数 / 涉及行数 / 冗余条数 / 说明`
- 第 9 行：① 精确匹配（com_name 原值）
- 第 10 行：② 归一化匹配（去前缀+标点+冒号+业务后缀）
- 第 12 行：分节「二、统计结论」
- 第 13+ 行：N 条结论，每条占 1 行，标题合并 A:B，说明合并 C:H
- 第 21+ 行：分节「三、户数档位分布」+ 表头 + 数据 + 柱状图

KPI 单元格样式：A4/C4/E4/G4 浅蓝底深字加粗，A5/C5/E5/G5 大号红字加粗。

柱状图：用 `openpyxl.chart.BarChart`，数据源为户数档位表（≥1000户/100~999户/10~99户/<10户），标题「基准户数档位分布」。

## Sheet 2: 重复组汇总

- 第 1-2 行：标题区
- 第 3 行：表头
- 第 4+ 行：每组一行

表头（12 列）：

| A 组号 | B 归一化名称 | C 出现次数 | D 冗余条数 | E 组内户数合计 | F 基准写法 | G 基准户数 | H 冗余写法 | I 冗余户数 | J 户数差 | K 重复类型 | L 判定 |

公式列：
- C `=COUNTIF(全量明细!$N$4:$N$<end>,$A4)`（N=组号列）
- D `=C4-1`
- E `=SUMIF(全量明细!$N$4:$N$<end>,$A4,全量明细!$H$4:$H$<end>)`（H=hs 列）
- J `=G4-I4` 或 `=ABS(G4-I4)`

判定列（L）条件格式：
- 含「需人工确认」→ 红底加粗
- 含「碎片」→ 默认

## Sheet 3: 重复明细（团队模板 7 列）

**严格按团队模板格式**（模板文件：`/Volumes/团队文件-甘肃时空图云/06.郑州智水/00原始数据/小区空间信息匹配数据/重复小区核查/重复小区数据核查结果.xlsx`，sheet1）。

**与其他 sheet 不同**：此 sheet 不用 `title_area` + `header_row` 双行结构，**表头直接在第 1 行**（无标题区、无合并单元格）。

| A 组号 | B 组内序号 | C 建议核查 | D 小区名称 | E 小区编码 | F comId | G 三级片区 |
|---|---|---|---|---|---|---|

- 表头在第 1 行，行 2+ 为数据
- 组号格式 `G001 / G002 ...`，零填充 3 位
- 「建议核查」列：
  - 组内第 1 条标 `基准`（绿底 `XL_OK_FILL` + 字体 `XL_OK_FONT`）
  - 组内第 2+ 条标 `★冗余`（红底 `XL_WARN_FILL` + 字体 `XL_WARN_FONT` 加粗）
  - **注意冗余标记前带 `★` 符号**
- 字段映射：
  - `com_name → D 小区名称`
  - `com_code → E 小区编码`
  - `com_id → F comId`
  - `pqmc → G 三级片区`（空值留空，不写 NULL，不写空字符串以外的占位符）
- 列宽：`[8, 10, 11, 36, 18, 34, 14]`
- 冻结：`D4`（前 3 列 + 前 3 行冻结）
- 自动筛选：`A3:G<end>`（注意：表头在第 1 行，但筛选范围仍可从第 3 行起，或按需调整）
- 条件格式（C 列）：
  - `=$C4="★冗余"` → 红底 + 加粗红字
  - `=$C4="基准"` → 绿底

**实现示例**：

```python
ws3 = wb.create_sheet('重复明细')
NC3 = 7
# 注意：不调用 title_area，表头直接放第 1 行
header_row(ws3, 1, ['组号', '组内序号', '建议核查', '小区名称', '小区编码', 'comId', '三级片区'])
r0 = 2
idx = 0
for g, (key, grp) in enumerate(ordered, 1):
    # 组内按 hs 降序，最大的为基准
    sorted_grp = sorted(grp, key=lambda x: -to_int(x.get('hs', 0)))
    for j, r in enumerate(sorted_grp, 1):
        rr = r0 + idx
        idx += 1
        ws3.cell(row=rr, column=1, value='G%03d' % g)
        ws3.cell(row=rr, column=2, value=j)
        ws3.cell(row=rr, column=3, value='基准' if j == 1 else '★冗余')
        ws3.cell(row=rr, column=4, value=r['com_name'])
        ws3.cell(row=rr, column=5, value=r['com_code'])
        ws3.cell(row=rr, column=6, value=r['com_id'])
        ws3.cell(row=rr, column=7, value=r.get('pqmc', '') if r.get('pqmc') and r.get('pqmc') not in NULLISH else '')
r1 = r0 + DUP_ROW_N - 1
body_style(ws3, r0, r1, NC3, center_cols=(1, 2, 3, 5))
for rr in range(r0, r1 + 1):
    ws3.cell(row=rr, column=4).alignment = LEFT
    ws3.cell(row=rr, column=6).alignment = LEFT
    ws3.cell(row=rr, column=7).alignment = LEFT
ws3.conditional_formatting.add('C{}:C{}'.format(r0, r1),
    FormulaRule(formula=['$C{}="★冗余"'.format(r0)],
                fill=PatternFill('solid', fgColor=XL_WARN_FILL),
                font=Font(bold=True, color=XL_WARN_FONT)))
ws3.conditional_formatting.add('C{}:C{}'.format(r0, r1),
    FormulaRule(formula=['$C{}="基准"'.format(r0)],
                fill=PatternFill('solid', fgColor=XL_OK_FILL),
                font=Font(color=XL_OK_FONT)))
widths(ws3, [8, 10, 11, 36, 18, 34, 14])
ws3.freeze_panes = 'D4'
ws3.auto_filter.ref = 'A3:G{}'.format(r1)
```

## Sheet 4: 全量明细

- 第 1-2 行：标题区
- 第 3 行：表头
- 第 4+ 行：源表全量数据

表头含原始字段 + 两个公式计算列：
- N 列 `组号`：`=IF(COUNTIF(重复组汇总!$B$4:$B$<end>,<归一化名称>)>0, INDEX(重复组汇总!$A$4:$A$<end>, MATCH(<归一化名称>, 重复组汇总!$B$4:$B$<end>, 0)), "")`
- O 列 `冗余标记`：`=IF($N4="","",IF(COUNTIFS($N$4:$N$<end>,$N4,$A$4:$A$<end>,"<"&$A4)=0,"基准","冗余"))`（用 COUNTIFS 判断该行序号是否为该组内最小序号，是则为基准）

冗余标记列条件格式：
- `="冗余"` → 红底加粗
- `="基准"` → 绿底

冻结：`C4`（前 2 列 + 前 3 行冻结，便于横向滚动时保持组号/序号可见）。
自动筛选：`A3:O<end>`。

## 双维度统计时的额外 sheet

若用户要求双维度（com_name + card_address）统计，需额外输出 3 个 sheet（共 6 sheet）：

| 序 | Sheet 名 | 内容 |
|---|---|---|
| 5 | 名称重复组汇总 | 同 sheet 2 |
| 6 | 名称重复明细 | 同 sheet 3（团队模板 7 列） |
| 7 | 地址重复组汇总 | 多两列：户数结构、名称是否同名、地址质量、判定（双一致/碎片化/同址多小区/碎片均分） |
| 8 | 地址重复明细 | 多 1 列：标记三态（主记录/附属/并立） |

地址标记三态：
- `主记录` = 组内户数最大（绿底）
- `附属` = 同一小区的碎片（红底，可合并/删除）
- `并立` = 不同小区共址（黄底，**不能删**）

地址核心抽取函数（用于 card_address 维度）：

```python
def addr_core(s):
    """从卡片级地址抽出小区级核心。

    处理顺序：
    1. 全角括号转半角
    2. 去括号内容
    3. 去行政区前缀
    4. 按楼栋/单元/层/室截断
    5. 去尾部残留学号
    6. 循环去用途后缀（消火栓/消防表/消防/直饮水/临收/门面房/...）
    7. 去标点
    """
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'^' + DIST_RE, '', s)
    s = re.split(r'\d+号楼|\d+栋|\d+单|单元|\d+层|\d+室|\d+户|[A-Za-z]\d+号楼', s)[0]
    s = re.sub(r'\d+$', '', s)
    NOISE = r'(?:消火栓|消防表|消防|直饮水|临收|门面房|门面|商铺|车棚|门卫|商业|表|户|无此表|拉卡拉)+$'
    prev = None
    while prev != s:
        prev = s
        s = re.sub(NOISE, '', s)
    s = re.sub(PUNC_RE, '', s)
    return s
```

`minlen >= 6` 才参与地址维度分组，过滤过短的核心（如 "1号"）。
