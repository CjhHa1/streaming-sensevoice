
"""
PyInstaller hook for bv package
确保bv.dictionary模块被正确包含
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集bv包的所有内容
datas, binaries, hiddenimports = collect_all('bv')

# 确保包含所有子模块
hiddenimports += collect_submodules('bv')

# 特别添加可能缺失的模块
hiddenimports += [
    'bv.dictionary',
    'bv.audio',
    'bv.audio.frame',
    'bv.frame',
    'bv.codec',
    'bv.codec.codec',
    'bv.codec.hwaccel',
]

print("✅ BV hook: 已收集bv包的模块和数据")
