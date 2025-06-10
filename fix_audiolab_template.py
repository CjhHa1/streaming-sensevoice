#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复audiolab模板文件缺失问题
这个脚本会找到audiolab包并创建缺失的filter.txt模板文件
"""

import os
import sys
import pkg_resources
from pathlib import Path

def find_audiolab_path():
    """查找audiolab包的安装路径"""
    try:
        import audiolab
        return Path(audiolab.__file__).parent
    except ImportError:
        print("❌ 未找到audiolab包，请先安装")
        return None

def create_filter_template():
    """创建filter.txt模板文件"""
    # 这是audiolab/av/filter.py中需要的基本模板内容
    filter_template = """
# FFmpeg filter template
# This template is used by audiolab for audio filtering operations

{% if filter_name %}
{{ filter_name }}
{% endif %}

{% if parameters %}
{% for param in parameters %}
{{ param }}
{% endfor %}
{% endif %}
"""
    
    audiolab_path = find_audiolab_path()
    if not audiolab_path:
        return False
    
    # 查找av目录
    av_path = audiolab_path / "av"
    if not av_path.exists():
        print(f"❌ 未找到av目录: {av_path}")
        return False
    
    # 创建模板文件
    template_file = av_path / "filter.txt"
    
    try:
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(filter_template.strip())
        
        print(f"✅ 成功创建模板文件: {template_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建模板文件失败: {e}")
        return False

def fix_pyinstaller_spec():
    """修复PyInstaller spec文件，添加数据文件收集"""
    spec_file = Path("VoiceRecognitionApp.spec")
    
    if not spec_file.exists():
        print("❌ 未找到VoiceRecognitionApp.spec文件")
        return False
    
    # 读取spec文件内容
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经添加了audiolab数据文件收集
    if "collect_data_files('audiolab')" not in content:
        # 在收集数据文件的部分添加audiolab
        insertion_point = content.find("# 尝试收集其他数据文件")
        if insertion_point != -1:
            before = content[:insertion_point]
            after = content[insertion_point:]
            
            new_content = before + """# 收集audiolab数据文件
try:
    datas += collect_data_files('audiolab')
    print("✅ 已添加audiolab数据文件收集")
except Exception as e:
    print(f"⚠️ 收集audiolab数据文件失败: {e}")

""" + after
            
            # 写回文件
            with open(spec_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ 已更新PyInstaller spec文件")
            return True
    
    print("ℹ️ PyInstaller spec文件已包含audiolab数据文件收集")
    return True

def main():
    """主函数"""
    print("🔧 开始修复audiolab模板文件问题...")
    
    # 步骤1：创建缺失的模板文件
    if create_filter_template():
        print("✅ 模板文件修复完成")
    else:
        print("❌ 模板文件修复失败")
        return False
    
    # 步骤2：修复PyInstaller配置
    if fix_pyinstaller_spec():
        print("✅ PyInstaller配置修复完成")
    else:
        print("❌ PyInstaller配置修复失败")
        return False
    
    print("\n🎉 修复完成！请重新编译您的应用程序。")
    print("\n📋 下一步操作:")
    print("1. 运行: python -m PyInstaller VoiceRecognitionApp.spec")
    print("2. 或者运行: python build_exe.py")
    
    return True

if __name__ == "__main__":
    main() 