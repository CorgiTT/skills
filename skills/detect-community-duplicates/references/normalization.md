# 归一化函数（normalize）

## 设计原理

小区名称在业务系统里常因录入习惯差异出现多种写法但实际指同一小区，常见差异类型：

1. **行政区前缀差异**：`金水区卫生路2号院` vs `卫生路2号院`（最常见，占 80%+）
2. **标点前缀差异**：`: 后牛岗社区` vs `后牛岗社区`（脏数据带冒号前缀）
3. **业务后缀差异**：`财信花园` vs `财信花园小区`、`丰产路110号` vs `丰产路110号院`、`前牛岗社区` vs `前牛岗社区社区`（后缀重复两次）
4. **标点空白差异**：`绿城.百合` vs `绿城百合` vs `绿城·百合`

归一化函数按顺序处理以上四类差异，最终把不同写法归到同一归一化键。

## 完整源码

```python
import re

# 行政区前缀（含"郑州市"前缀的复合形式）
DIST_RE = r'(?:郑州市)?(?:金水区|惠济区|郑东新区|中原区|二七区|管城区|金水|惠济|商鼎)?'

# 标点空白（全角+半角，含中文标点）
PUNC_RE = r'[\s·．.,，、\-—_/\\|:：;；\'""'']+'

# 末尾业务后缀（可重复出现，如「前牛岗社区社区」会去两层）
SUFFIX_RE = r'(小区|家属院|家属属院|院|社区|家园|花园|公寓|家属)$'

# 空值标识
NULLISH = ('NULL', 'null', 'None', 'none')


def normalize(s):
    """对小区名称做归一化，返回归一化键。

    处理顺序：
    1. 全角括号转半角
    2. 去行政区前缀（金水区/郑东新区/...）
    3. 去行首冒号（处理脏数据如 ": 后牛岗社区"）
    4. 去所有标点空白
    5. 循环去末尾业务后缀，直到稳定
       （处理「财信花园 vs 财信花园小区」「前牛岗社区 vs 前牛岗社区社区」）
    """
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'^' + DIST_RE, '', s)
    s = re.sub(r'^[:：\s]+', '', s)
    s = re.sub(PUNC_RE, '', s)
    # 循环去末尾业务后缀
    prev = None
    while prev != s:
        prev = s
        s = re.sub(SUFFIX_RE, '', s)
    return s


def dup_type(grp):
    """判定重复组的差异类型。

    参数：grp = list of dict，每个 dict 含 'com_name' 键
    返回：'精确重复' / '标点差异' / '后缀差异' / '前缀差异'
    """
    names = {r['com_name'] for r in grp}
    if len(names) == 1:
        return '精确重复'
    if any(r['com_name'].startswith((':', '：')) for r in grp):
        return '标点差异'
    # 去掉前缀+标点后若仍不同，说明差异来自业务后缀
    base_names = {re.sub(PUNC_RE, '', re.sub(r'^' + DIST_RE, '', n)) for n in names}
    if len(base_names) > 1:
        return '后缀差异'
    return '前缀差异'


def classify_judgment(grp):
    """判定重复组的处置建议。

    参数：grp = list of dict，每个 dict 含 'com_name' 和 'hs'（字符串或整数）键
    返回：（判定字符串, 是否需人工确认）

    基准规则：组内 hs 最大为基准，其余为冗余。
    """
    def to_int(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    hs_vals = [to_int(r.get('hs', 0)) for r in grp]
    if not hs_vals:
        return ('空组', True)
    max_hs = max(hs_vals)
    # 找到基准（hs 最大）那条的索引
    base_idx = hs_vals.index(max_hs)
    base_name = grp[base_idx]['com_name']
    redundant_hs = sum(hs_vals) - max_hs

    dt = dup_type(grp)

    if dt == '精确重复':
        if redundant_hs < max_hs:
            return ('精确重复·冗余为碎片', False)
        else:
            return ('精确重复·需人工确认', True)

    # 判断基准是否带行政区前缀
    is_base_prefixed = base_name.startswith(('金水区', '郑州市金水区', '惠济区',
                                              '郑州市惠济区', '郑东新区', '郑州市'))
    if is_base_prefixed and redundant_hs < max_hs:
        return ('带前缀为基准·需人工确认', True)
    if redundant_hs < max_hs:
        return ('冗余为碎片（户数更小）', False)
    return ('冗余户数更大·需人工确认', True)
```

## 扩展指南

### 加新行政区前缀

在 `DIST_RE` 正则的 `(?:金水区|惠济区|郑东新区|...)` 组里追加新前缀。注意：

- 加简称（如「金水」）会同时去 `金水区` 和 `金水`，避免 `金水区XX` vs `金水XX` 漏判
- 不要加 `^` 锚点到子组里，否则只匹配 `^金水^...` 会报错
- 「商鼎」是营业所名，某些数据会带，加上避免漏判

### 加新业务后缀

在 `SUFFIX_RE` 的 `(小区|家属院|...)` 组里追加。注意：

- 顺序敏感：`家属院` 必须在 `院` 前面（否则 `家属院` 会被 `院` 截掉前半部分变成 `家属`）
- `家属属院` 是 `家属院` 的脏数据变体，单独列出
- 循环去后缀是关键，处理 `前牛岗社区社区` 这种后缀重复两次的情况

### 调试

```python
# 单元测试
cases = [
    ('金水区卫生路2号院', '卫生路2号'),
    ('卫生路2号院', '卫生路2号'),
    ('商都路21号财信花园', '商都路21号财信'),
    ('商都路21号财信花园小区', '商都路21号财信'),
    (': 后牛岗社区', '后牛岗'),
    ('后牛岗社区', '后牛岗'),
    ('薛夏南街76号前牛岗社区社区', '薛夏南街76号前牛岗'),
    ('薛夏南街76号前牛岗社区', '薛夏南街76号前牛岗'),
    ('绿城.百合', '绿城百合'),
    ('绿城百合', '绿城百合'),
]
for inp, expected in cases:
    got = normalize(inp)
    status = '✓' if got == expected else '✗ expected=%s got=%s' % (expected, got)
    print('%-40s -> %-30s %s' % (inp, got, status))
```

## 已知限制

- **同址不同名不判重**：如 `国贸中心` vs `招银大厦` 同址但不同名，归一化后仍不同。这是设计预期，地址维度单独判重会误判，需走双维度交叉。
- **门牌号差异不处理**：如 `景明街5号院` vs `景明街7号院` 归一化后仍不同。若需识别门牌号差异需走 fuzzy matching（如 Levenshtein 距离），但误判率高，不做。
- **业务后缀过激进**：去掉所有 `院` 后缀会让 `丰产路110号` 与 `丰产路110号` 合并，但理论上可能误合并 `丰产路110号` 与 `丰产路110号铺`（极罕见）。当前实现可接受，必要时加门牌号一致性校验。
