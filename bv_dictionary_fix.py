
# 替代方案：处理bv.dictionary模块缺失
# 可以在voice_recognition_app.py开头添加这段代码

import sys
from types import ModuleType

def create_mock_bv_dictionary():
    """创建模拟的bv.dictionary模块"""
    mock_dict = ModuleType('bv.dictionary')
    
    # 添加基本的字典类
    class AVDict:
        def __init__(self, items=None):
            self._dict = items or {}
        
        def __getitem__(self, key):
            return self._dict.get(key)
        
        def __setitem__(self, key, value):
            self._dict[key] = value
        
        def get(self, key, default=None):
            return self._dict.get(key, default)
    
    mock_dict.AVDict = AVDict
    mock_dict.metadata_dict = AVDict()
    mock_dict.codec_dict = AVDict()
    mock_dict.format_dict = AVDict()
    
    return mock_dict

# 在导入pysilero之前注入模拟模块
if 'bv.dictionary' not in sys.modules:
    sys.modules['bv.dictionary'] = create_mock_bv_dictionary()
    print("✅ 已注入bv.dictionary模拟模块")
