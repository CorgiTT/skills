# -*- coding: utf-8 -*-
"""
小区名称归一化模块（detect-community-duplicates skill 配套脚本）

可直接 import：
    from normalize import normalize, dup_type, classify_judgment, to_int

也可作为独立脚本运行做单元测试：
    python normalize.py
"""

import re
import sys

# ---------------- 正则常量 ----------------

# 行政区前缀（含"郑州市"前缀的复合形式）
# 注意：加简称（如「金水」）会同时去「金水区」和「金水」，避免漏判
DIST_RE = r'(?:郑州市)?(?:金水区|惠济区|郑东新区|中原区|二七区|管城区|金水|惠济|商鼎)?'

# 标点空白（全角+半角，含中文标点）
PUNC_RE = r'[\s·．.,，、\-—_/\\|:：;；\'""\'\']+'

# 末尾业务后缀（可重复出现，如「前牛岗社区社区」会去两层）
# 注意：家属院 必须在 院 前面，否则 院 会先截掉 家属院 的后半部分
SUFFIX_RE = r'(小区|家属院|家属属院|院|社区|家园|花园|公寓|家属)$'

# 空值标识
NULLISH = ('NULL', 'null', 'None', 'none')


# ---------------- 核心函数 ----------------

def normalize(s):
    """对小区名称做归一化，返回归一化键。

    处理顺序：
    1. 全角括号转半角
    2. 去行政区前缀（金水区/郑东新区/...）
    3. 去行首冒号（处理脏数据如 ": 后牛岗社区"）
    4. 去所有标点空白
    5. 循环去末尾业务后缀，直到稳定
       （处理「财信花园 vs 财信花园小区」「前牛岗社区 vs 前牛岗社区社区」）

    参数：s (str) - 原始小区名称
    返回：归一化后的字符串

    示例：
        >>> normalize('金水区卫生路2号院')
        '卫生路2号'
        >>> normalize('卫生路2号院')
        '卫生路2号'
        >>> normalize('商都路21号财信花园')
        '商都路21号财信'
        >>> normalize('商都路21号财信花园小区')
        '商都路21号财信'
        >>> normalize(': 后牛岗社区')
        '后牛岗'
        >>> normalize('薛夏南街76号前牛岗社区社区')
        '薛夏南街76号前牛岗'
    """
    if not s:
        return ''
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

    判定优先级：
    1. 组内所有 com_name 完全相同 → 精确重复
    2. 组内有成员以冒号 : / ： 开头 → 标点差异
    3. 去掉前缀+标点后仍不同（差异来自业务后缀）→ 后缀差异
    4. 其他（带/不带行政区前缀）→ 前缀差异
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


def to_int(v):
    """安全转 int，处理 None/空串/字符串数字。"""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def classify_judgment(grp):
    """判定重复组的处置建议。

    参数：grp = list of dict，每个 dict 含 'com_name' 和 'hs' 键
    返回：(判定字符串, 是否需人工确认)

    基准规则：组内 hs 最大为基准，其余为冗余。

    判定分类：
    - 精确重复·冗余为碎片（冗余 hs < 基准 hs，建议合并）
    - 精确重复·需人工确认（冗余 hs ≥ 基准 hs）
    - 冗余为碎片（户数更小，建议合并）
    - 带前缀为基准·需人工确认（带前缀那条 hs 更大，与前几份规律相反）
    - 冗余户数更大·需人工确认
    - 空组（无数据）
    """
    if not grp:
        return ('空组', True)

    hs_vals = [to_int(r.get('hs', 0)) for r in grp]
    max_hs = max(hs_vals)
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
    is_base_prefixed = base_name.startswith(
        ('金水区', '郑州市金水区', '惠济区', '郑州市惠济区',
         '郑东新区', '郑州市郑东新区', '郑州市'))

    if is_base_prefixed and redundant_hs < max_hs:
        return ('带前缀为基准·需人工确认', True)
    if redundant_hs < max_hs:
        return ('冗余为碎片（户数更小）', False)
    return ('冗余户数更大·需人工确认', True)


# ---------------- 单元测试 ----------------

def _run_tests():
    """运行单元测试。"""
    cases = [
        # (输入, 期望输出, 说明)
        ('金水区卫生路2号院', '卫生路2号', '前缀+后缀'),
        ('卫生路2号院', '卫生路2号', '后缀'),
        ('商都路21号财信花园', '商都路21号财信', '无后缀'),
        ('商都路21号财信花园小区', '商都路21号财信', '后缀差异·小区'),
        ('丰产路110号', '丰产路110号', '无后缀'),
        ('丰产路110号院', '丰产路110号', '后缀差异·院'),
        ('红专路117号', '红专路117号', '无后缀'),
        ('红专路117号院', '红专路117号', '后缀差异·院'),
        ('育翔街59号小孟庄', '育翔街59号小孟庄', '无后缀'),
        ('育翔街59号小孟庄院', '育翔街59号小孟庄', '后缀差异·院'),
        (': 后牛岗社区', '后牛岗', '标点前缀+后缀'),
        ('后牛岗社区', '后牛岗', '后缀'),
        ('薛夏南街76号前牛岗社区社区', '薛夏南街76号前牛岗', '后缀重复两次'),
        ('薛夏南街76号前牛岗社区', '薛夏南街76号前牛岗', '后缀'),
        ('绿城.百合', '绿城百合', '标点'),
        ('绿城百合', '绿城百合', '无变化'),
        ('郑州市金水区卫生路2号院', '卫生路2号', '复合前缀'),
        ('郑东新区107公路1号亚星公司家属院', '107公路1号亚星公司', '前缀+后缀'),
        ('107公路1号亚星公司家属院', '107公路1号亚星公司', '后缀'),
        ('兴达路16号来童寨小区', '兴达路16号来童寨', '后缀'),
        ('', '', '空字符串'),
    ]

    passed = 0
    failed = 0
    for inp, expected, note in cases:
        got = normalize(inp)
        if got == expected:
            passed += 1
            status = '✓'
        else:
            failed += 1
            status = '✗ expected=%r got=%r' % (expected, got)
        print('  %-44s -> %-30s %s [%s]' % (inp, got, status, note))

    print()
    print('通过 %d / 失败 %d / 共 %d' % (passed, failed, len(cases)))
    return failed == 0


if __name__ == '__main__':
    print('=== 归一化函数单元测试 ===')
    ok = _run_tests()
    sys.exit(0 if ok else 1)
