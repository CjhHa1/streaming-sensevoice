#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键命令测试脚本
测试所有配置的快捷键命令是否能正常执行
"""

import time
import sys
import os
from typing import Dict, List, Tuple
import threading

# 尝试导入所需库
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
    print("✅ keyboard库已导入")
except ImportError:
    print("❌ keyboard库未安装，请运行: pip install keyboard")
    KEYBOARD_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
    print("✅ psutil库已导入")
except ImportError:
    print("⚠️ psutil库未安装，将无法检测进程状态")
    PSUTIL_AVAILABLE = False

# 导入配置管理器
from shortcut_config import ShortcutConfig

class ShortcutTester:
    """快捷键测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.config = ShortcutConfig()
        self.test_results: List[Dict] = []
        self.dangerous_commands = {
            "退出", "关闭", "关闭窗口", "关闭标签", "停止"
        }
        self.safe_commands = {
            "刷新", "复制", "粘贴", "剪切", "撤销", "重做", 
            "保存", "全选", "最小化", "最大化", "切换窗口",
            "新建标签", "打开文件", "新建文件", "截图", "战斗"
        }
        self.audio_commands = {
            "增大音量", "减小音量", "静音"
        }
        
    def is_dangerous_command(self, command: str) -> bool:
        """检查命令是否为危险命令（可能关闭应用）"""
        return command in self.dangerous_commands
    
    def is_audio_command(self, command: str) -> bool:
        """检查命令是否为音频命令"""
        return command in self.audio_commands
    
    def send_hotkey(self, keys: str) -> bool:
        """
        发送快捷键
        
        Args:
            keys: 按键组合，例如 'ctrl+c'
            
        Returns:
            bool: 执行是否成功
        """
        
        if not KEYBOARD_AVAILABLE:
            return False
        
        try:
            print(f"  🎹 发送快捷键: {keys}")
            
            # 分割按键组合
            key_parts = keys.split('+')
            
            if len(key_parts) > 1:
                # 组合键
                keyboard.send(keys)
            else:
                # 单个按键
                keyboard.send(keys)
            
            time.sleep(0.2)  # 等待按键处理
            return True
            
        except Exception as e:
            print(f"  ❌ 发送快捷键失败: {e}")
            return False
    
    def test_command(self, command: str, keys: str, skip_dangerous: bool = True) -> Dict:
        """
        测试单个命令
        
        Args:
            command: 命令名称
            keys: 快捷键组合
            skip_dangerous: 是否跳过危险命令
            
        Returns:
            Dict: 测试结果
        """
        print(f"\n📋 测试命令: {command}")
        print(f"⌨️ 快捷键: {keys}")
        
        result = {
            'command': command,
            'keys': keys,
            'success': False,
            'skipped': False,
            'reason': '',
            'error': None
        }
        
        # 检查是否为危险命令
        if skip_dangerous and self.is_dangerous_command(command):
            result['skipped'] = True
            result['reason'] = '危险命令，已跳过'
            print(f"  ⚠️ 跳过危险命令: {command}")
            return result
        
        # 检查是否为音频命令
        if self.is_audio_command(command):
            print(f"  🔊 音频命令，请注意音量变化")
        
        try:
            # 执行快捷键
            success = self.send_hotkey(keys)
            
            if success:
                result['success'] = True
                result['reason'] = '快捷键发送成功'
                print(f"  ✅ 命令执行成功")
            else:
                result['reason'] = '快捷键发送失败'
                print(f"  ❌ 命令执行失败")
                
        except Exception as e:
            result['error'] = str(e)
            result['reason'] = f'执行异常: {e}'
            print(f"  ❌ 执行异常: {e}")
        
        return result
    
    def test_all_commands(self, skip_dangerous: bool = True, test_audio: bool = False) -> List[Dict]:
        """
        测试所有命令
        
        Args:
            skip_dangerous: 是否跳过危险命令
            test_audio: 是否测试音频命令
            
        Returns:
            List[Dict]: 所有测试结果
        """
        print("🚀 开始测试所有快捷键命令...")
        print(f"💀 危险命令跳过: {'是' if skip_dangerous else '否'}")
        print(f"🔊 音频命令测试: {'是' if test_audio else '否'}")
        print("=" * 60)
        
        self.test_results = []
        
        for shortcut in self.config.shortcuts:
            command = shortcut['command']
            keys = shortcut['keys']
            
            # 检查是否跳过音频命令
            if not test_audio and self.is_audio_command(command):
                result = {
                    'command': command,
                    'keys': keys,
                    'success': False,
                    'skipped': True,
                    'reason': '音频命令，已跳过',
                    'error': None
                }
                print(f"\n📋 跳过音频命令: {command}")
                self.test_results.append(result)
                continue
            
            # 测试命令
            result = self.test_command(command, keys, skip_dangerous)
            self.test_results.append(result)
            
            # 在命令之间添加延迟
            time.sleep(0.5)
        
        return self.test_results
    
    def test_selected_commands(self, commands: List[str], skip_dangerous: bool = True) -> List[Dict]:
        """
        测试选定的命令
        
        Args:
            commands: 要测试的命令列表
            skip_dangerous: 是否跳过危险命令
            
        Returns:
            List[Dict]: 测试结果
        """
        print(f"🎯 开始测试选定的 {len(commands)} 个命令...")
        print("=" * 60)
        
        self.test_results = []
        
        for command in commands:
            keys = self.config.get_shortcut(command)
            if not keys:
                result = {
                    'command': command,
                    'keys': '',
                    'success': False,
                    'skipped': True,
                    'reason': '命令不存在于配置中',
                    'error': None
                }
                print(f"\n❌ 命令 '{command}' 不存在于配置中")
                self.test_results.append(result)
                continue
            
            # 测试命令
            result = self.test_command(command, keys, skip_dangerous)
            self.test_results.append(result)
            
            # 在命令之间添加延迟
            time.sleep(0.5)
        
        return self.test_results
    
    def print_test_summary(self):
        """打印测试结果摘要"""
        if not self.test_results:
            print("📊 没有测试结果")
            return
        
        total = len(self.test_results)
        successful = len([r for r in self.test_results if r['success']])
        failed = len([r for r in self.test_results if not r['success'] and not r['skipped']])
        skipped = len([r for r in self.test_results if r['skipped']])
        
        print("\n" + "=" * 60)
        print("📊 测试结果摘要:")
        print("=" * 60)
        print(f"总计: {total} 个命令")
        print(f"✅ 成功: {successful} 个")
        print(f"❌ 失败: {failed} 个")
        print(f"⚠️ 跳过: {skipped} 个")
        print(f"📈 成功率: {successful/total*100:.1f}%")
        
        # 详细结果
        print("\n📋 详细结果:")
        print("-" * 60)
        
        for result in self.test_results:
            status = "✅" if result['success'] else ("⚠️" if result['skipped'] else "❌")
            print(f"{status} {result['command']:12} | {result['keys']:15} | {result['reason']}")
        
        # 失败的命令
        failed_commands = [r for r in self.test_results if not r['success'] and not r['skipped']]
        if failed_commands:
            print("\n❌ 失败的命令:")
            print("-" * 40)
            for result in failed_commands:
                print(f"• {result['command']}: {result['reason']}")
                if result['error']:
                    print(f"  错误: {result['error']}")
    
    def export_results(self, filename: str = "test_results.txt"):
        """导出测试结果到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("快捷键命令测试结果\n")
                f.write("=" * 50 + "\n")
                f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                total = len(self.test_results)
                successful = len([r for r in self.test_results if r['success']])
                failed = len([r for r in self.test_results if not r['success'] and not r['skipped']])
                skipped = len([r for r in self.test_results if r['skipped']])
                
                f.write(f"总计: {total} 个命令\n")
                f.write(f"成功: {successful} 个\n")
                f.write(f"失败: {failed} 个\n")
                f.write(f"跳过: {skipped} 个\n")
                f.write(f"成功率: {successful/total*100:.1f}%\n\n")
                
                f.write("详细结果:\n")
                f.write("-" * 50 + "\n")
                
                for result in self.test_results:
                    status = "成功" if result['success'] else ("跳过" if result['skipped'] else "失败")
                    f.write(f"{result['command']:12} | {result['keys']:15} | {status} | {result['reason']}\n")
                    if result['error']:
                        f.write(f"  错误: {result['error']}\n")
            
            print(f"📁 测试结果已导出到: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ 导出结果失败: {e}")
            return False


def show_menu():
    """显示菜单"""
    print("\n🎯 快捷键测试工具")
    print("=" * 40)
    print("1. 测试所有命令（跳过危险命令）")
    print("2. 测试所有命令（包括危险命令）")
    print("3. 测试安全命令")
    print("4. 测试音频命令")
    print("5. 测试指定命令")
    print("6. 显示所有可用命令")
    print("7. 导出测试结果")
    print("0. 退出")
    print("=" * 40)


def get_user_choice() -> str:
    """获取用户选择"""
    while True:
        try:
            choice = input("请选择操作 (0-7): ").strip()
            if choice in ['0', '1', '2', '3', '4', '5', '6', '7']:
                return choice
            else:
                print("❌ 无效选择，请输入 0-7 之间的数字")
        except KeyboardInterrupt:
            print("\n👋 已取消操作")
            return '0'


def main():
    """主函数"""
    print("🚀 快捷键命令测试脚本")
    print("=" * 50)
    
    if not KEYBOARD_AVAILABLE:
        print("❌ keyboard库不可用，无法进行测试")
        print("💡 请运行: pip install keyboard")
        return
    
    # 创建测试器
    tester = ShortcutTester()
    
    # 检查配置是否加载成功
    if not tester.config.shortcuts:
        print("❌ 没有找到快捷键配置")
        return
    
    print(f"✅ 已加载 {len(tester.config.shortcuts)} 个快捷键配置")
    
    while True:
        show_menu()
        choice = get_user_choice()
        
        if choice == '0':
            print("👋 再见!")
            break
            
        elif choice == '1':
            print("\n🛡️ 测试所有命令（跳过危险命令）...")
            tester.test_all_commands(skip_dangerous=True, test_audio=False)
            tester.print_test_summary()
            
        elif choice == '2':
            print("\n⚠️ 警告: 即将测试所有命令，包括可能关闭程序的危险命令!")
            confirm = input("确定要继续吗？(y/N): ").strip().lower()
            if confirm == 'y':
                tester.test_all_commands(skip_dangerous=False, test_audio=False)
                tester.print_test_summary()
            else:
                print("已取消测试")
                
        elif choice == '3':
            print("\n✅ 测试安全命令...")
            safe_commands = list(tester.safe_commands)
            tester.test_selected_commands(safe_commands)
            tester.print_test_summary()
            
        elif choice == '4':
            print("\n🔊 警告: 即将测试音频命令，可能会改变系统音量!")
            confirm = input("确定要继续吗？(y/N): ").strip().lower()
            if confirm == 'y':
                audio_commands = list(tester.audio_commands)
                tester.test_selected_commands(audio_commands, skip_dangerous=False)
                tester.print_test_summary()
            else:
                print("已取消测试")
                
        elif choice == '5':
            print("\n📝 请输入要测试的命令（用逗号分隔）:")
            tester.config.print_shortcuts()
            command_input = input("命令: ").strip()
            if command_input:
                commands = [cmd.strip() for cmd in command_input.split(',')]
                tester.test_selected_commands(commands)
                tester.print_test_summary()
            
        elif choice == '6':
            print("\n📋 所有可用命令:")
            tester.config.print_shortcuts()
            
        elif choice == '7':
            if tester.test_results:
                filename = input("输入文件名 (默认: test_results.txt): ").strip()
                if not filename:
                    filename = "test_results.txt"
                tester.export_results(filename)
            else:
                print("❌ 没有测试结果可导出，请先运行测试")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc() 