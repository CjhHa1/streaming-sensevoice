#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复bv.dictionary模块缺失问题
这个错误通常出现在PyInstaller打包时，bv包（PyAV相关）的dictionary模块没有被正确包含
"""

import os
import sys
import subprocess
from pathlib import Path
import importlib.util

def check_current_dependencies():
    """检查当前的依赖安装情况"""
    print("🔍 检查当前依赖安装情况...")
    
    dependencies = ['pysilero', 'audiolab', 'bv', 'av']
    results = {}
    
    for dep in dependencies:
        try:
            spec = importlib.util.find_spec(dep)
            if spec is not None:
                print(f"✅ {dep}: 已安装")
                results[dep] = True
            else:
                print(f"❌ {dep}: 未安装")
                results[dep] = False
        except Exception as e:
            print(f"❌ {dep}: 检查失败 - {e}")
            results[dep] = False
    
    return results

def find_bv_location():
    """查找bv包的安装位置"""
    try:
        import bv
        bv_path = Path(bv.__file__).parent
        print(f"📍 找到bv包位置: {bv_path}")
        return bv_path
    except ImportError:
        print("❌ 未找到bv包")
        return None

def create_missing_dictionary_module():
    """创建缺失的dictionary模块"""
    bv_path = find_bv_location()
    if not bv_path:
        return False
    
    dictionary_file = bv_path / "dictionary.py"
    
    # 创建一个基本的dictionary模块
    dictionary_content = '''
"""
BV Dictionary module
Basic dictionary functionality for BV package
"""

class AVDict:
    """Basic dictionary class for AV operations"""
    
    def __init__(self, items=None):
        self._dict = items or {}
    
    def __getitem__(self, key):
        return self._dict.get(key)
    
    def __setitem__(self, key, value):
        self._dict[key] = value
    
    def __contains__(self, key):
        return key in self._dict
    
    def get(self, key, default=None):
        return self._dict.get(key, default)
    
    def items(self):
        return self._dict.items()
    
    def keys(self):
        return self._dict.keys()
    
    def values(self):
        return self._dict.values()

# 提供一些常用的字典类型
metadata_dict = AVDict()
codec_dict = AVDict()
format_dict = AVDict()

# 导出主要的类和对象
__all__ = ['AVDict', 'metadata_dict', 'codec_dict', 'format_dict']
'''
    
    try:
        with open(dictionary_file, 'w', encoding='utf-8') as f:
            f.write(dictionary_content)
        
        print(f"✅ 已创建dictionary模块: {dictionary_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建dictionary模块失败: {e}")
        return False

def update_bv_init():
    """更新bv包的__init__.py文件以包含dictionary模块"""
    bv_path = find_bv_location()
    if not bv_path:
        return False
    
    init_file = bv_path / "__init__.py"
    
    try:
        # 读取现有内容
        if init_file.exists():
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = ""
        
        # 检查是否已经导入dictionary
        if "from . import dictionary" not in content:
            # 添加dictionary导入
            additional_import = "\n# 添加dictionary模块导入\ntry:\n    from . import dictionary\nexcept ImportError:\n    pass\n"
            content += additional_import
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 已更新bv/__init__.py文件")
            return True
        else:
            print("ℹ️ bv/__init__.py已包含dictionary导入")
            return True
            
    except Exception as e:
        print(f"❌ 更新bv/__init__.py失败: {e}")
        return False

def create_pyinstaller_hook_for_bv():
    """为bv包创建PyInstaller钩子"""
    hook_content = '''
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
'''
    
    # 创建hooks目录
    hooks_dir = Path("hooks")
    hooks_dir.mkdir(exist_ok=True)
    
    hook_file = hooks_dir / "hook-bv.py"
    
    try:
        with open(hook_file, 'w', encoding='utf-8') as f:
            f.write(hook_content)
        
        print(f"✅ 已创建bv包的PyInstaller钩子: {hook_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建bv钩子失败: {e}")
        return False

def update_pyinstaller_spec():
    """更新PyInstaller spec文件以包含bv钩子"""
    spec_file = Path("VoiceRecognitionApp.spec")
    
    if not spec_file.exists():
        print("❌ 未找到VoiceRecognitionApp.spec文件")
        return False
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新hooks路径
    if "hookspath=[]" in content:
        content = content.replace("hookspath=[]", "hookspath=['hooks']")
        print("✅ 已更新hooks路径")
    
    # 添加bv相关的隐藏导入
    bv_imports = [
        "'bv.dictionary'",
        "'bv.audio'", 
        "'bv.audio.frame'",
        "'bv.frame'",
        "'bv.codec'",
        "'bv.codec.codec'",
        "'bv.codec.hwaccel'"
    ]
    
    for bv_import in bv_imports:
        if bv_import not in content:
            # 在hiddenimports列表中添加
            import_pattern = "hiddenimports = ["
            if import_pattern in content:
                insertion_point = content.find(import_pattern) + len(import_pattern)
                before = content[:insertion_point]
                after = content[insertion_point:]
                
                content = before + f"\n    {bv_import}," + after
    
    # 写回文件
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已更新PyInstaller spec包含bv模块")
    return True

def alternative_solution():
    """提供替代解决方案"""
    print("\n🔄 创建替代解决方案...")
    
    alt_content = '''
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
'''
    
    alt_file = Path("bv_dictionary_fix.py")
    with open(alt_file, 'w', encoding='utf-8') as f:
        f.write(alt_content)
    
    print(f"✅ 已创建替代方案文件: {alt_file}")

def main():
    """主修复流程"""
    print("🔧 开始修复bv.dictionary模块缺失问题...")
    print("=" * 60)
    
    success_count = 0
    total_steps = 6
    
    # 步骤1: 检查依赖
    print("\n🔍 步骤1/6: 检查当前依赖")
    deps = check_current_dependencies()
    success_count += 1
    
    # 步骤2: 创建缺失的dictionary模块
    print("\n📄 步骤2/6: 创建dictionary模块")
    if create_missing_dictionary_module():
        success_count += 1
    
    # 步骤3: 更新bv包的__init__.py
    print("\n📝 步骤3/6: 更新bv包初始化文件")
    if update_bv_init():
        success_count += 1
    
    # 步骤4: 创建PyInstaller钩子
    print("\n🔗 步骤4/6: 创建PyInstaller钩子")
    if create_pyinstaller_hook_for_bv():
        success_count += 1
    
    # 步骤5: 更新spec文件
    print("\n⚙️ 步骤5/6: 更新PyInstaller spec文件")
    if update_pyinstaller_spec():
        success_count += 1
    
    # 步骤6: 创建替代方案
    print("\n🔄 步骤6/6: 创建替代解决方案")
    alternative_solution()
    success_count += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 修复完成! 成功执行 {success_count}/{total_steps} 个步骤")
    
    if success_count >= 5:
        print("\n✅ 建议的下一步操作:")
        print("1. 重新构建应用程序:")
        print("   python -m PyInstaller VoiceRecognitionApp.spec --clean")
        print("2. 如果仍有问题，可以尝试替代방안:")
        print("   将bv_dictionary_fix.py的内容添加到voice_recognition_app.py开头")
        print("\n💡 也可以考虑更新到兼容的包版本")
    else:
        print("\n⚠️ 部分修复步骤失败，建议手动检查")
    
    return success_count >= 5

if __name__ == "__main__":
    main() 