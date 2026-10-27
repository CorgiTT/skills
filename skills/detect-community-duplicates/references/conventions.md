# 关键约定

## 命名与目录

- **输出文件名**：`<业务域>_<统计对象>重复统计.xlsx`
  - 业务域 = 源文件名去扩展名（如 `biz_com`、`金水所小区`、`JS001ComData`）
  - 统计对象 = `com_name` 或 `shape` 或 `com_name+card_address`（双维度）
  - 示例：`biz_com_com_name重复统计.xlsx`、`金水所小区_com_name重复统计.xlsx`
- **工作目录**：`outputs/.<文件名去扩展名>.ref/`
  - 示例：`outputs/.biz_com重复统计.ref/`
  - 内含 `build.py`（建表脚本）
  - 不放输出文件本身（输出文件直接放 `outputs/` 顶级目录）
- **中间结果 JSON**：固定文件名（不加时间戳），便于断点续跑
  - 示例：`outputs/_cache/<片区编号>.json`、`outputs/_cache_user/<片区编号>.json`

## Python 环境

- **解释器**：`/Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python`
- **已装包**：openpyxl、formulas（公式重算引擎）、PyYAML
- **不要用**：系统 `/usr/bin/python3`（无 openpyxl）

## sheet 顺序

固定顺序：**概览 → 重复组汇总 → 重复明细 → 全量明细**。

双维度时追加：**名称重复组汇总 → 名称重复明细 → 地址重复组汇总 → 地址重复明细**，放在全量明细之前。

## 冗余标记一致性

**全量明细与重复明细两表必须用同一基准规则**（hs 最大为基准），否则会出现相互矛盾——5 个「前缀户数更大」的组两表标记会相反。

全量明细冗余标记公式（用 COUNTIFS 判断该行序号是否为该组内最小序号）：

```
=IF($N4="","",IF(COUNTIFS($N$4:$N$end,$N4,$A$4:$A$end,"<"&$A4)=0,"基准","冗余"))
```

- N 列 = 组号
- A 列 = 原始序号（从 1 开始的行号）
- 该行序号是该组内最小序号 → 基准
- 否则 → 冗余

重复明细的「建议核查」列直接硬编码 `基准` / `★冗余`（按 hs 降序排，第 1 条基准，其余冗余），不用公式。

## 多维度统计约定

双维度（com_name + card_address）统计时：

- **地址维度不能直接判重**！150 组里只有 14 组是「名称+地址双一致」真重复，其余是同址多小区（54 组，如国贸中心/招银大厦共址）、碎片化拆分（80 组，同一小区被配套设施/商铺 1 户记录拆开）等。
- **必须按户数结构分类**：
  - `同址多主体`：组内有 ≥2 条户数占比 ≥15%（不同小区共址，非重复）
  - `1主+碎片`：1 条户数占比 ≥50%（同一小区被碎片化拆分，建议合并）
  - `碎片均分`：无主记录（需人工确认）
- **地址组排序按判定优先级**：双一致 > 碎片化 > 同址多小区 > 碎片均分，便于优先处理。
- **地址标记三态**：
  - `主记录` = 组内户数最大（绿底，仅排序首位）
  - `附属` = 同一小区的碎片（红底，**可合并/删除**）
  - `并立` = 不同小区共址（黄底，**不能删**）

## 空值处理

- `com_addres` 列常拼写少一个 d（应为 `com_address`），全表为空属正常（卡片级地址不在小区表）
- `community_name` 有时大量为空（1169/1922 行），不影响 com_name 维度统计
- `shape` 为 `NULL` 字符串时按空处理，不参与 shape 维度统计
- `pqmc` 为 `NULL` 时，重复明细第 7 列留空（不写 `NULL`，不写空字符串以外的占位符）

## 文件格式识别

扩展名 `.xlsx` 不一定是真 xlsx。openpyxl 读 CSV 套壳会报 `BadZipFile: File is not a zip file`。

识别方法：

```bash
file <文件>.xlsx
# 真xlsx: Microsoft Excel 2007+
# CSV套壳: ASCII text / UTF-8 Unicode text

xxd -l 64 <文件>.xlsx
# 真xlsx: 首字节 50 4B 03 04 (ZIP magic)
# CSV套壳: 首字节是文本字符
```

CSV 套壳改用 `csv.DictReader(encoding='utf-8-sig')` 读，gbk 解码会失败。

## 团队模板 xlsx 不兼容 openpyxl

模板文件 `/Volumes/团队文件-甘肃时空图云/06.郑州智水/00原始数据/小区空间信息匹配数据/重复小区核查/重复小区数据核查结果.xlsx` 用 WPS 保存，openpyxl 读时报 `Fill() takes no arguments`。

读取方法：解压 + XML 解析

```bash
cp <模板>.xlsx /tmp/tpl.xlsx
unzip -o /tmp/tpl.xlsx -d /tmp/tpl_extract
ls /tmp/tpl_extract/xl/worksheets/  # sheet1.xml sheet2.xml sheet3.xml
```

```python
import xml.etree.ElementTree as ET
A = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ns = {'a': A}

# 读共享字符串表
t = ET.parse('/tmp/tpl_extract/xl/sharedStrings.xml').getroot()
strs = []
for si in t.findall('a:si', ns):
    txt = ''.join(x.text or '' for x in si.iter('{%s}t' % A))
    strs.append(txt)

# 读 sheet 数据
ws = ET.parse('/tmp/tpl_extract/xl/worksheets/sheet1.xml').getroot()
rows = ws.findall('.//a:row', ns)
for r in rows[:8]:
    cs = r.findall('a:c', ns)
    vals = []
    for c in cs:
        v = c.get('r')
        t = c.find('a:v', ns)
        val = t.text if t is not None else ''
        if c.get('t') == 's':
            val = strs[int(val)] if val else ''
        vals.append((v, val))
    print('行:', vals)
```

读完后及时清理：`rm -rf /tmp/tpl.xlsx /tmp/tpl_extract`

## 冒号文件名跨平台

时间戳文件名 `片区水表井清单_2026-10-19 15:27.xlsx` 在 macOS 上能创建，但传到 Windows 会报错（冒号是非法字符）。稳妥起见用短横线 `15-27` 或 ISO 8601 无冒号格式。

## 时间戳获取

不要手算 Unix 时间戳，用 shell 命令：

```bash
date '+%Y-%m-%d %H:%M'           # 文件名时间戳
date '+%Y-%m-%dT%H:%M:%S%z'     # ISO 8601（含时区，用于 scheduledAt）
```

## 公式重算与 AIGC 标识

完成后必跑两步：

```bash
# 1. 重算公式并扫描错误（要求 total_errors=0）
/Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python \
  "/Users/kejitang/.workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent/<version>/skills/workbuddy-sheet-generation/scripts/recalc.py" \
  "<输出文件>.xlsx" 120

# 2. 写入 AIGC 内容溯源标识
/Users/kejitang/.workbuddy/binaries/python/envs/default/bin/python \
  "/Users/kejitang/.workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent/<version>/skills/workbuddy-sheet-generation/scripts/aigc_label.py" \
  "<输出文件>.xlsx" --platform WORKBUDDY
```

`<version>` 部分需要先 `ls /Users/kejitang/.workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent/` 找到当前版本目录名。

校验：用 openpyxl `data_only=True` 读回，核对 KPI 值、口径行、重复明细标记分布、全量明细标记分布是否与控制台打印一致。

## 数据质量备注

报告「概览」sheet 末尾加 1 条「数据质量备注」结论，记录：
- 各字段非空率（如 `com_name 全表非空；com_name2 有 4 行为空；shape 全表非空`）
- 字段拼写问题（如 `com_addres 拼写少一个 d`）
- 业务所/区县分布（如 `businessof 619/622 为商鼎营业所；county 615 为郑州市`）
- 数据本身已做的归一化痕迹（如 `remark 列里有「归一化键=」字段`）
