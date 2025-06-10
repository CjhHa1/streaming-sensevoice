#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全版语音识别应用
避免PyInstaller打包时的inspect问题
"""

import sys
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import re
import subprocess
import os
import webbrowser
from difflib import SequenceMatcher

# 尝试导入pyperclip，如果失败则使用备用方案
try:
    import pyperclip
except ImportError:
    print("⚠️ pyperclip未安装，剪贴板功能将使用系统命令")
    pyperclip = None

# 在导入funasr相关模块之前，修补inspect模块
import inspect
original_findsource = inspect.findsource

def safe_findsource(object):
    """安全版本的findsource，避免PyInstaller环境中的错误"""
    try:
        return original_findsource(object)
    except (OSError, IOError):
        # 如果无法获取源代码，返回空的源代码和行号
        return ([], 0)

# 替换原始的findsource函数
inspect.findsource = safe_findsource

try:
    from streaming_sensevoice import StreamingSenseVoice
except Exception as e:
    print(f"⚠️ StreamingSenseVoice导入失败: {e}")
    print("🔄 尝试使用备用语音识别方案...")
    
    # 如果StreamingSenseVoice导入失败，使用备用方案
    class MockStreamingSenseVoice:
        def __init__(self, contexts=None, model=None):
            self.contexts = contexts
            self.model = model
            print("⚠️ 使用模拟语音识别服务")
            
        def reset(self):
            pass
            
        def streaming_inference(self, audio_data, is_last=False):
            # 模拟识别结果
            if is_last and len(audio_data) > 1000:
                yield {
                    "text": "[模拟识别结果] 检测到语音输入",
                    "timestamps": "0.0-2.0"
                }
    
    StreamingSenseVoice = MockStreamingSenseVoice


class CommandProcessor:
    """命令处理器类，用于识别和执行语音命令"""
    
    def __init__(self, app_instance=None):
        """
        初始化命令处理器
        
        Args:
            app_instance: VoiceRecognitionApp实例，用于回调应用方法
        """
        self.app = app_instance
        self.clipboard_content = ""  # 用于存储剪贴板内容
        
        # 命令执行控制
        self.last_command = None  # 最后执行的命令
        self.last_command_time = 0  # 最后执行命令的时间
        self.command_cooldown = 2.0  # 命令冷却时间（秒）
        self.last_recognized_text = ""  # 最后识别的文本
        self.text_repeat_threshold = 0.8  # 文本重复阈值
        
        # 测试PowerShell环境
        self.powershell_available = self.test_powershell_environment()
        
        # 定义命令映射表
        self.commands = {
            # 应用控制命令
            "退出": self.exit_app,
            "关闭": self.exit_app,
            "停止": self.stop_recognition,
            "暂停": self.stop_recognition,
            "结束": self.exit_app,
            
            # 系统操作命令
            "刷新": self.refresh,
            "复制": self.copy,
            "粘贴": self.paste,
            "剪切": self.cut,
            "撤销": self.undo,
            "重做": self.redo,
            "保存": self.save,
            "全选": self.select_all,
            
            # 测试命令
            "测试复制": self.test_copy_function,
            
            # 窗口操作命令
            "最小化": self.minimize_window,
            "最大化": self.maximize_window,
            "关闭窗口": self.close_window,
            "切换窗口": self.switch_window,
            
            # 浏览器操作命令
            "打开浏览器": self.open_browser,
            "新建标签": self.new_tab,
            "关闭标签": self.close_tab,
            "刷新页面": self.refresh_page,
            
            # 文件操作命令
            "打开文件": self.open_file,
            "新建文件": self.new_file,
            "打开记事本": self.open_notepad,
            "打开计算器": self.open_calculator,
            
            # 音量控制命令
            "增大音量": self.volume_up,
            "减小音量": self.volume_down,
            "静音": self.mute,
            
            # 屏幕截图命令
            "截图": self.screenshot,
            "截屏": self.screenshot,
        }
        
        # 命令同义词映射
        self.synonyms = {
            "退出应用": "退出",
            "关闭程序": "退出",
            "停止识别": "停止",
            "暂停识别": "暂停",
            "结束程序": "退出",
            
            "刷新页面": "刷新",
            "刷新当前页面": "刷新",
            "复制文本": "复制",
            "粘贴文本": "粘贴",
            "剪切文本": "剪切",
            "撤销操作": "撤销",
            "重做操作": "重做",
            "保存文件": "保存",
            "全部选择": "全选",
            
            "窗口最小化": "最小化",
            "窗口最大化": "最大化",
            "关闭当前窗口": "关闭窗口",
            "切换到下一个窗口": "切换窗口",
            
            "打开网页浏览器": "打开浏览器",
            "新建浏览器标签": "新建标签",
            "关闭浏览器标签": "关闭标签",
            "刷新网页": "刷新页面",
            
            "调高音量": "增大音量",
            "调低音量": "减小音量",
            "静音模式": "静音",
            
            "屏幕截图": "截图",
            "屏幕截屏": "截图",
        }
    
    def test_powershell_environment(self):
        """测试PowerShell环境是否可用"""
        try:
            print("🔧 正在测试PowerShell环境...")
            result = subprocess.run(
                ["powershell", "-Command", "echo 'PowerShell测试成功'"], 
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                print("✅ PowerShell环境测试成功")
                return True
            else:
                print("❌ PowerShell环境测试失败")
                print(f"返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ PowerShell环境测试超时")
            return False
        except FileNotFoundError:
            print("❌ PowerShell未找到，可能未安装或不在PATH中")
            return False
        except Exception as e:
            print(f"❌ PowerShell环境测试异常: {e}")
            return False
    
    def similarity(self, a, b):
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, a, b).ratio()
    
    def find_command(self, text):
        """
        从识别文本中查找匹配的命令
        
        Args:
            text (str): 识别的文本
            
        Returns:
            str or None: 匹配的命令名称，如果没有找到则返回None
        """
        text = text.strip().lower()
        
        # 1. 精确匹配
        for cmd in self.commands:
            if cmd in text:
                return cmd
        
        # 2. 同义词匹配
        for synonym, cmd in self.synonyms.items():
            if synonym in text:
                return cmd
        
        # 3. 开头匹配（针对像"刷新新"这样的情况）
        for cmd in self.commands:
            if text.startswith(cmd) or cmd in text:
                return cmd
        
        # 4. 模糊匹配（相似度阈值设为0.6）
        best_match = None
        best_score = 0.6  # 最低相似度阈值
        
        for cmd in self.commands:
            score = self.similarity(text, cmd)
            if score > best_score:
                best_score = score
                best_match = cmd
        
        # 5. 检查同义词的模糊匹配
        for synonym in self.synonyms:
            score = self.similarity(text, synonym)
            if score > best_score:
                best_score = score
                best_match = self.synonyms[synonym]
        
        # 6. 容错匹配：去除文本末尾可能的误识别字符
        if not best_match and len(text) > 2:
            # 尝试去掉最后一个字符再匹配
            truncated_text = text[:-1]
            for cmd in self.commands:
                if cmd == truncated_text or cmd in truncated_text:
                    return cmd
        
        return best_match
    
    def execute_command(self, command_name):
        """
        执行指定的命令
        
        Args:
            command_name (str): 命令名称
            
        Returns:
            bool: 执行是否成功
        """
        if command_name in self.commands:
            try:
                # 检查是否需要PowerShell的命令
                powershell_commands = [
                    "刷新", "复制", "粘贴", "剪切", "撤销", "重做", "保存", "全选",
                    "最小化", "最大化", "关闭窗口", "切换窗口", "新建标签", "关闭标签",
                    "打开文件", "新建文件", "增大音量", "减小音量", "静音", "截图"
                ]
                # 注意：测试复制命令不在此列表中，因为它有自己的错误处理
                
                if command_name in powershell_commands and not self.powershell_available:
                    print(f"❌ 命令 '{command_name}' 需要PowerShell支持，但PowerShell不可用")
                    print("💡 请检查PowerShell是否正确安装并可以正常执行")
                    return False
                
                print(f"🔧 执行命令: {command_name}")
                result = self.commands[command_name]()
                return result if result is not None else True
            except Exception as e:
                print(f"❌ 命令执行失败: {e}")
                return False
        else:
            print(f"❌ 未知命令: {command_name}")
            return False
    
    def process_text(self, text):
        """
        处理识别文本，查找并执行命令
        
        Args:
            text (str): 识别的文本
            
        Returns:
            bool: 是否找到并执行了命令
        """
        # 检查文本是否重复（避免流式识别中的重复结果）
        if self.is_text_repeated(text):
            return False
        
        command = self.find_command(text)
        if command:
            # 检查命令冷却
            if self.is_command_in_cooldown(command):
                print(f"⏰ 命令 '{command}' 正在冷却中，请稍后再试")
                return False
            
            print(f"🎯 识别到命令: {command}")
            result = self.execute_command(command)
            
            if result:
                # 更新最后执行的命令和时间
                self.last_command = command
                self.last_command_time = time.time()
                self.last_recognized_text = text
            
            return result
        return False
    
    def is_text_repeated(self, text):
        """检查文本是否与最近识别的文本重复"""
        if not self.last_recognized_text:
            return False
        
        # 计算与最后识别文本的相似度
        similarity = self.similarity(text.lower().strip(), self.last_recognized_text.lower().strip())
        return similarity > self.text_repeat_threshold
    
    def is_command_in_cooldown(self, command):
        """检查命令是否在冷却期内"""
        if not self.last_command or self.last_command != command:
            return False
        
        current_time = time.time()
        time_since_last = current_time - self.last_command_time
        return time_since_last < self.command_cooldown
    
    def reset_command_state(self):
        """重置命令执行状态"""
        self.last_command = None
        self.last_command_time = 0
        self.last_recognized_text = ""
    
    # ===== 应用控制命令 =====
    def exit_app(self):
        """退出应用"""
        print("👋 正在退出应用...")
        if self.app:
            self.app.stop_recognition()
        os._exit(0)
    
    def stop_recognition(self):
        """停止语音识别"""
        print("🛑 停止语音识别")
        if self.app:
            self.app.stop_recognition()
        return True
    
    # ===== 系统操作命令 =====
    def refresh(self):
        """刷新当前窗口/页面"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{F5}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔄 已发送刷新命令")
                return True
            else:
                print(f"❌ 刷新命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 刷新命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 刷新失败: {e}")
            return False
    
    def copy(self):
        """复制到剪贴板"""
        try:
            print("🔧 开始执行复制命令...")
            
            # 方案1：使用更可靠的按键发送方法（避免KeyboardInterrupt）
            try:
                import win32api
                import win32con
                import time
                
                print("🔧 使用win32api发送按键序列...")
                
                # 确保有足够的延迟，让按键被正确处理
                # 按下Ctrl键
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                time.sleep(0.05)  # 50ms延迟
                
                # 按下C键
                win32api.keybd_event(ord('C'), 0, 0, 0)
                time.sleep(0.05)  # 50ms延迟
                
                # 释放C键
                win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.05)  # 50ms延迟
                
                # 释放Ctrl键
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.1)  # 100ms延迟确保按键处理完成
                
                print("📋 已发送复制命令 (win32api按键)")
                return True
                
            except ImportError:
                print("⚠️ win32api不可用，尝试备用方案...")
            except Exception as e:
                print(f"⚠️ win32api方案失败: {e}")
            
            # 方案2：使用修正的PowerShell SendKeys
            try:
                print("🔧 使用PowerShell SendKeys...")
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", "-Command", 
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "Start-Sleep -Milliseconds 100; "
                    "[System.Windows.Forms.SendKeys]::SendWait('{CTRL down}c{CTRL up}'); "
                    "Start-Sleep -Milliseconds 100"
                ], capture_output=True, text=True, timeout=10)
                
                print(f"🔧 PowerShell命令执行完成，返回码: {result.returncode}")
                
                if result.returncode == 0:
                    print("📋 已发送复制命令 (PowerShell SendKeys)")
                    return True
                else:
                    print(f"❌ PowerShell方案失败，返回码: {result.returncode}")
                    if result.stderr:
                        print(f"错误输出: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ PowerShell方案异常: {e}")
            
            # 方案3：使用VBScript发送按键
            try:
                print("🔧 使用VBScript发送按键...")
                
                # 创建临时VBScript文件
                vbs_content = '''
                Set WshShell = WScript.CreateObject("WScript.Shell")
                WScript.Sleep 100
                WshShell.SendKeys "^c"
                WScript.Sleep 100
                '''
                
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.vbs', delete=False) as vbs_file:
                    vbs_file.write(vbs_content)
                    vbs_path = vbs_file.name
                
                try:
                    result = subprocess.run([
                        "cscript", "//NoLogo", vbs_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        print("📋 已发送复制命令 (VBScript)")
                        return True
                    else:
                        print(f"❌ VBScript方案失败，返回码: {result.returncode}")
                        
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(vbs_path)
                    except:
                        pass
                    
            except Exception as e:
                print(f"❌ VBScript方案异常: {e}")
            
            # 方案4：使用pyautogui（如果可用）
            try:
                import pyautogui
                print("🔧 使用pyautogui发送按键...")
                
                # 设置延迟
                pyautogui.PAUSE = 0.1
                
                # 发送Ctrl+C
                pyautogui.hotkey('ctrl', 'c')
                
                print("📋 已发送复制命令 (pyautogui)")
                return True
                
            except ImportError:
                print("⚠️ pyautogui不可用")
            except Exception as e:
                print(f"❌ pyautogui方案异常: {e}")
            
            # 方案5：通过模拟菜单操作
            try:
                print("🔧 使用模拟右键菜单...")
                result = subprocess.run([
                    "powershell", "-ExecutionPolicy", "Bypass", "-Command", 
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.SendKeys]::SendWait('+{F10}'); "  # Shift+F10打开右键菜单
                    "Start-Sleep -Milliseconds 300; "
                    "[System.Windows.Forms.SendKeys]::SendWait('c'); "       # 按C选择复制
                    "Start-Sleep -Milliseconds 100"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print("📋 已发送复制命令 (右键菜单)")
                    return True
                else:
                    print(f"❌ 右键菜单方案失败")
                    
            except Exception as e:
                print(f"❌ 右键菜单方案异常: {e}")
            
            print("❌ 所有复制方案都失败了")
            print("💡 请确保：")
            print("   1. 当前有应用处于前台且有选中的文本")
            print("   2. 前台应用支持Ctrl+C复制操作")
            print("   3. 系统没有阻止键盘模拟操作")
            return False
                        
        except Exception as e:
            print(f"❌ 复制失败: {e}")
            print(f"异常类型: {type(e).__name__}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            return False
    
    def paste(self):
        """从剪贴板粘贴"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("📋 已发送粘贴命令")
                return True
            else:
                print(f"❌ 粘贴命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 粘贴命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 粘贴失败: {e}")
            return False
    
    def cut(self):
        """剪切到剪贴板"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^x')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("✂️ 已发送剪切命令")
                return True
            else:
                print(f"❌ 剪切命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 剪切命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 剪切失败: {e}")
            return False
    
    def undo(self):
        """撤销操作"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^z')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("↶ 已发送撤销命令")
                return True
            else:
                print(f"❌ 撤销命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 撤销命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 撤销失败: {e}")
            return False
    
    def redo(self):
        """重做操作"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^y')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("↷ 已发送重做命令")
                return True
            else:
                print(f"❌ 重做命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 重做命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 重做失败: {e}")
            return False
    
    def save(self):
        """保存文件"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^s')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("💾 已发送保存命令")
                return True
            else:
                print(f"❌ 保存命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 保存命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def select_all(self):
        """全选"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^a')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔘 已发送全选命令")
                return True
            else:
                print(f"❌ 全选命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 全选命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 全选失败: {e}")
            return False
    
    # ===== 窗口操作命令 =====
    def minimize_window(self):
        """最小化当前窗口"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('% n')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🗗 已发送最小化命令")
                return True
            else:
                print(f"❌ 最小化命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 最小化命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 最小化失败: {e}")
            return False
    
    def maximize_window(self):
        """最大化当前窗口"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('% x')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🗖 已发送最大化命令")
                return True
            else:
                print(f"❌ 最大化命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 最大化命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 最大化失败: {e}")
            return False
    
    def close_window(self):
        """关闭当前窗口"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{F4}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("❌ 已发送关闭窗口命令")
                return True
            else:
                print(f"❌ 关闭窗口命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 关闭窗口命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 关闭窗口失败: {e}")
            return False
    
    def switch_window(self):
        """切换窗口"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{TAB}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔄 已发送切换窗口命令")
                return True
            else:
                print(f"❌ 切换窗口命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 切换窗口命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 切换窗口失败: {e}")
            return False
    
    # ===== 浏览器操作命令 =====
    def open_browser(self):
        """打开默认浏览器"""
        try:
            webbrowser.open('about:blank')
            print("🌐 已打开浏览器")
            return True
        except Exception as e:
            print(f"❌ 打开浏览器失败: {e}")
            return False
    
    def new_tab(self):
        """新建浏览器标签"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^t')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🗂️ 已发送新建标签命令")
                return True
            else:
                print(f"❌ 新建标签命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 新建标签命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 新建标签失败: {e}")
            return False
    
    def close_tab(self):
        """关闭浏览器标签"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^w')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("❌ 已发送关闭标签命令")
                return True
            else:
                print(f"❌ 关闭标签命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 关闭标签命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 关闭标签失败: {e}")
            return False
    
    def refresh_page(self):
        """刷新页面"""
        return self.refresh()
    
    # ===== 文件操作命令 =====
    def open_file(self):
        """打开文件对话框"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^o')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("📁 已发送打开文件命令")
                return True
            else:
                print(f"❌ 打开文件命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 打开文件命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 打开文件失败: {e}")
            return False
    
    def new_file(self):
        """新建文件"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^n')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("📄 已发送新建文件命令")
                return True
            else:
                print(f"❌ 新建文件命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 新建文件命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 新建文件失败: {e}")
            return False
    
    def open_notepad(self):
        """打开记事本"""
        try:
            subprocess.Popen(["notepad.exe"])
            print("📝 已打开记事本")
            return True
        except Exception as e:
            print(f"❌ 打开记事本失败: {e}")
            return False
    
    def open_calculator(self):
        """打开计算器"""
        try:
            subprocess.Popen(["calc.exe"])
            print("🧮 已打开计算器")
            return True
        except Exception as e:
            print(f"❌ 打开计算器失败: {e}")
            return False
    
    # ===== 音量控制命令 =====
    def volume_up(self):
        """增大音量"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{VOLUME_UP}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔊 已增大音量")
                return True
            else:
                print(f"❌ 增大音量命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 增大音量命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 增大音量失败: {e}")
            return False
    
    def volume_down(self):
        """减小音量"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{VOLUME_DOWN}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔉 已减小音量")
                return True
            else:
                print(f"❌ 减小音量命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 减小音量命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 减小音量失败: {e}")
            return False
    
    def mute(self):
        """静音/取消静音"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{VOLUME_MUTE}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("🔇 已切换静音状态")
                return True
            else:
                print(f"❌ 静音命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 静音命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 静音操作失败: {e}")
            return False
    
    # ===== 屏幕截图命令 =====
    def screenshot(self):
        """屏幕截图"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{PRTSC}')"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print("📸 已截取屏幕")
                return True
            else:
                print(f"❌ 截图命令执行失败，返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ 截图命令执行超时")
            return False
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return False
    
    def test_copy_function(self):
        """测试复制功能是否正常工作"""
        try:
            print("🧪 测试复制功能...")
            
            # 方法1：尝试使用pyperclip检查剪贴板
            if pyperclip:
                try:
                    before_copy = pyperclip.paste()
                    print(f"📋 复制前剪贴板内容: '{before_copy[:50]}...' (仅显示前50字符)")
                    
                    # 执行复制
                    success = self.copy()
                    
                    if success:
                        time.sleep(0.2)  # 等待复制完成
                        after_copy = pyperclip.paste()
                        print(f"📋 复制后剪贴板内容: '{after_copy[:50]}...' (仅显示前50字符)")
                        
                        if before_copy != after_copy:
                            print("✅ 复制功能测试成功！剪贴板内容已改变")
                            return True
                        else:
                            print("⚠️ 复制命令执行了，但剪贴板内容没有改变")
                            print("💡 可能原因：没有选中文本，或当前应用不支持复制")
                            return False
                    else:
                        print("❌ 复制命令执行失败")
                        return False
                        
                except Exception as e:
                    print(f"❌ pyperclip测试失败: {e}")
            
            # 方法2：使用Windows API检查剪贴板
            try:
                import win32clipboard
                print("🔧 使用win32clipboard检查剪贴板...")
                
                win32clipboard.OpenClipboard()
                try:
                    before_copy = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT) if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT) else ""
                finally:
                    win32clipboard.CloseClipboard()
                
                print(f"📋 复制前剪贴板内容: '{before_copy[:50] if before_copy else '(空)'}...'")
                
                # 执行复制
                success = self.copy()
                
                if success:
                    time.sleep(0.2)  # 等待复制完成
                    
                    win32clipboard.OpenClipboard()
                    try:
                        after_copy = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT) if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT) else ""
                    finally:
                        win32clipboard.CloseClipboard()
                    
                    print(f"📋 复制后剪贴板内容: '{after_copy[:50] if after_copy else '(空)'}...'")
                    
                    if before_copy != after_copy:
                        print("✅ 复制功能测试成功！剪贴板内容已改变")
                        return True
                    else:
                        print("⚠️ 复制命令执行了，但剪贴板内容没有改变")
                        return False
                        
            except ImportError:
                print("⚠️ win32clipboard不可用")
            except Exception as e:
                print(f"❌ win32clipboard测试失败: {e}")
            
            # 如果没有剪贴板检查工具，只能假设复制成功
            print("⚠️ 无法检查剪贴板内容，假设复制成功")
            return self.copy()
            
        except Exception as e:
            print(f"❌ 测试复制功能失败: {e}")
            return False


class SimpleVAD:
    """改进的音量检测VAD，避免重复识别问题"""
    
    def __init__(self, threshold=0.02, speech_pad_ms=500, min_speech_ms=300):
        self.threshold = threshold
        self.speech_pad_samples = int(speech_pad_ms * 16000 / 1000)  # 静音填充长度
        self.min_speech_samples = int(min_speech_ms * 16000 / 1000)  # 最小语音长度
        self.is_speech = False
        self.speech_buffer = []
        self.silence_counter = 0
        self.speech_start_time = 0
        self.last_energy = 0
        self.energy_history = []
        self.energy_history_length = 10  # 保留最近10帧的能量历史
        
    def _calculate_energy(self, audio_chunk):
        """计算音频能量，使用RMS方法"""
        return np.sqrt(np.mean(audio_chunk ** 2))
    
    def _is_speech_energy(self, energy):
        """判断当前能量是否为语音"""
        # 使用动态阈值：基础阈值 + 历史能量的标准差
        if len(self.energy_history) > 3:
            energy_std = np.std(self.energy_history)
            dynamic_threshold = max(self.threshold, self.threshold + energy_std * 0.5)
        else:
            dynamic_threshold = self.threshold
        
        return energy > dynamic_threshold
        
    def __call__(self, audio_chunk):
        """处理音频块并返回语音段"""
        # 计算音频能量
        energy = self._calculate_energy(audio_chunk)
        
        # 更新能量历史
        self.energy_history.append(energy)
        if len(self.energy_history) > self.energy_history_length:
            self.energy_history.pop(0)
        
        is_voice = self._is_speech_energy(energy)
        
        if is_voice:
            if not self.is_speech:
                # 语音开始
                self.is_speech = True
                self.speech_buffer = []
                self.silence_counter = 0
                self.speech_start_time = time.time()
                print(f"🎤 语音开始 (能量: {energy:.4f}, 阈值: {self.threshold:.4f})")
                yield {"start": True}, np.array([])
            
            # 添加到语音缓冲区
            self.speech_buffer.extend(audio_chunk)
            self.silence_counter = 0
            # 不在语音过程中输出中间结果，避免重复处理
            
        else:  # 静音
            if self.is_speech:
                self.silence_counter += len(audio_chunk)
                self.speech_buffer.extend(audio_chunk)  # 包含静音部分
                
                # 检查是否应该结束语音
                speech_duration = len(self.speech_buffer) / 16000.0 * 1000  # 转换为毫秒
                
                if (self.silence_counter >= self.speech_pad_samples and 
                    speech_duration >= self.min_speech_samples / 16000.0 * 1000):
                    # 语音结束
                    self.is_speech = False
                    speech_data = np.array(self.speech_buffer)
                    
                    print(f"🎤 语音结束 (时长: {speech_duration:.1f}ms, 样本: {len(speech_data)})")
                    
                    # 清理缓冲区，防止重复
                    self.speech_buffer = []
                    self.silence_counter = 0
                    
                    yield {"end": True}, speech_data
                    
                    # 语音结束后，添加一个短暂的静默期，避免立即重新触发
                    time.sleep(0.1)
        
        self.last_energy = energy


class VoiceRecognitionApp:
    """安全版语音识别应用主类"""
    
    def __init__(self, contexts=None, model_path=None, enable_commands=True):
        """
        初始化语音识别应用
        
        Args:
            contexts: 上下文列表，用于提高识别准确率
            model_path: 本地模型路径，如果指定则使用本地模型
            enable_commands: 是否启用命令识别功能
        """
        self.contexts = contexts or []
        self.model_path = model_path or "iic/SenseVoiceSmall"
        self.model = None
        self.vad = None
        self.is_running = False
        self.selected_device_id = None
        self.recognition_thread = None
        
        # 识别结果去重
        self.last_recognition_result = ""
        self.last_recognition_timestamps = None
        
        # 命令识别功能
        self.enable_commands = enable_commands
        if self.enable_commands:
            self.command_processor = CommandProcessor(self)
            print("✅ 命令识别功能已启用")
        else:
            self.command_processor = None
            print("⚠️  命令识别功能已禁用")
        
        # 用于区分是否为用户真实的退出意图
        self.user_exit_requested = False
        self.keyboard_interrupt_count = 0
        
    def get_microphone_devices(self):
        """获取可用的麦克风设备列表"""
        try:
            devices = sd.query_devices()
            microphones = []
            
            for idx, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    microphones.append({
                        'id': idx,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                        'hostapi': sd.query_hostapis(device['hostapi'])['name']
                    })
            
            return microphones
        except Exception as e:
            print(f"❌ 获取麦克风设备失败: {e}")
            return []
    
    def print_available_microphones(self):
        """打印所有可用的麦克风设备"""
        microphones = self.get_microphone_devices()
        
        if not microphones:
            print("❌ 未找到可用的麦克风设备")
            return False
            
        print("\n🎤 可用的麦克风设备:")
        print("-" * 60)
        for mic in microphones:
            print(f"设备ID: {mic['id']:2d} | 名称: {mic['name']}")
            print(f"           | 声道数: {mic['channels']} | 采样率: {mic['sample_rate']:.0f}Hz")
            print(f"           | 音频API: {mic['hostapi']}")
            print("-" * 60)
        
        return True
    
    def select_microphone_by_id(self, device_id):
        """通过设备ID选择麦克风"""
        microphones = self.get_microphone_devices()
        device_ids = [mic['id'] for mic in microphones]
        
        if device_id in device_ids:
            self.selected_device_id = device_id
            selected_device = next(mic for mic in microphones if mic['id'] == device_id)
            print(f"✅ 已选择麦克风: {selected_device['name']}")
            return True
        else:
            print(f"❌ 设备ID {device_id} 不存在")
            return False
    
    def select_microphone_interactive(self):
        """交互式选择麦克风"""
        if not self.print_available_microphones():
            return False
            
        while True:
            try:
                device_id = int(input("\n请输入要使用的麦克风设备ID: "))
                if self.select_microphone_by_id(device_id):
                    return True
            except ValueError:
                print("❌ 请输入有效的数字ID")
            except KeyboardInterrupt:
                print("\n操作已取消")
                return False
    
    def initialize_models(self):
        """初始化语音识别模型"""
        print("🔄 正在初始化语音识别模型...")
        try:
            # 初始化语音识别模型
            self.model = StreamingSenseVoice(contexts=self.contexts, model=self.model_path)
            
            # 初始化改进的VAD
            print("✅ 使用改进的音量检测VAD")
            self.vad = SimpleVAD(threshold=0.02, speech_pad_ms=500, min_speech_ms=300)
            
            print("✅ 模型初始化完成")
            return True
        except Exception as e:
            print(f"❌ 模型初始化失败: {e}")
            print("💡 请检查网络连接和模型下载状态")
            return False
    
    def print_available_commands(self):
        """打印可用的语音命令"""
        print("\n🎙️  可用的语音命令:")
        print("-" * 60)
        
        categories = {
            "应用控制": ["退出", "关闭", "停止", "暂停"],
            "系统操作": ["刷新", "复制", "粘贴", "剪切", "撤销", "重做", "保存", "全选"],
            "测试功能": ["测试复制"],
            "窗口操作": ["最小化", "最大化", "关闭窗口", "切换窗口"],
            "浏览器操作": ["打开浏览器", "新建标签", "关闭标签", "刷新页面"],
            "文件操作": ["打开文件", "新建文件", "打开记事本", "打开计算器"],
            "音量控制": ["增大音量", "减小音量", "静音"],
            "屏幕操作": ["截图", "截屏"]
        }
        
        for category, commands in categories.items():
            print(f"📁 {category}:")
            for cmd in commands:
                print(f"   • {cmd}")
            print()
        
        print("💡 提示: 支持模糊匹配和同义词识别")
        print("-" * 60)
    
    def process_audio_stream(self):
        """处理音频流的线程函数"""
        samples_per_read = int(0.1 * 16000)  # 每次读取0.1秒的音频
        
        try:
            with sd.InputStream(
                device=self.selected_device_id,
                channels=1, 
                dtype="float32", 
                samplerate=16000
            ) as stream:
                print("🎧 开始监听音频...")
                print("💡 说话清晰一些，避免环境噪音干扰")
                print("📊 当前VAD阈值: 0.02 (动态调整)")
                
                while self.is_running:
                    try:
                        samples, _ = stream.read(samples_per_read)
                        
                        # 使用改进的VAD处理音频
                        for speech_dict, speech_samples in self.vad(samples[:, 0]):
                            if "start" in speech_dict:
                                self.model.reset()
                                # 重置命令处理器状态，确保新的语音输入干净处理
                                if self.enable_commands and self.command_processor:
                                    self.command_processor.reset_command_state()
                                # 重置识别结果去重状态
                                self.last_recognition_result = ""
                                self.last_recognition_timestamps = None
                            
                            # 只处理完整的语音段（语音结束时）
                            if "end" in speech_dict and len(speech_samples) > 0:
                                try:
                                    print("🔄 正在处理语音...")
                                    # 进行语音识别，传入完整的语音段
                                    recognition_results = []
                                    for res in self.model.streaming_inference(speech_samples * 32768, is_last=True):
                                        if res["text"].strip():
                                            recognition_results.append(res)
                                    
                                    # 只处理最后一个非空结果（最终结果）
                                    if recognition_results:
                                        final_result = recognition_results[-1]
                                        print(f"🗣️  识别结果: {final_result['text']}")
                                        print(f"⏱️  时间戳: {final_result['timestamps']}")
                                        
                                        # 处理最终识别结果
                                        self.on_recognition_result(final_result, is_final=True)
                                except Exception as e:
                                    print(f"⚠️ 识别过程中出现错误: {e}")
                                
                    except Exception as e:
                        if self.is_running:
                            print(f"❌ 音频处理错误: {e}")
                        
        except Exception as e:
            print(f"❌ 音频流错误: {e}")
    
    def is_duplicate_result(self, result):
        """检查识别结果是否重复"""
        text = result.get("text", "").strip()
        timestamps = result.get("timestamps", None)
        
        # 如果文本和时间戳都相同，则认为是重复结果
        if (text == self.last_recognition_result and 
            timestamps == self.last_recognition_timestamps):
            return True
        
        # 更新最后的识别结果
        self.last_recognition_result = text
        self.last_recognition_timestamps = timestamps
        return False
    
    def on_recognition_result(self, result, is_final=False):
        """识别结果回调函数，处理语音识别结果和命令识别"""
        text = result.get("text", "").strip()
        
        if not text:
            return
        
        # 检查是否为重复结果
        if self.is_duplicate_result(result):
            print("🔄 跳过重复识别结果")
            return
        
        # 只在最终结果时处理命令识别，避免中间结果重复触发
        if is_final and self.enable_commands and self.command_processor:
            # 尝试处理为命令
            if self.command_processor.process_text(text):
                return  # 如果识别到命令并执行，则不进行其他处理
        
        # 这里可以添加其他自定义的结果处理逻辑
        # 例如：记录日志、发送到其他服务等
        pass
    
    def start_recognition(self):
        """开始语音识别"""
        if not self.selected_device_id:
            print("❌ 请先选择麦克风设备")
            return False
            
        if self.is_running:
            print("⚠️  服务已在运行中")
            return False
        
        self.is_running = True
        self.recognition_thread = threading.Thread(target=self.process_audio_stream)
        self.recognition_thread.daemon = True
        self.recognition_thread.start()
        
        print("🎤 语音识别已启动，请开始说话...")
        print("按 Ctrl+C 停止识别")
        
        return True
    
    def stop_recognition(self):
        """停止语音识别"""
        if self.is_running:
            self.is_running = False
            if self.recognition_thread:
                self.recognition_thread.join(timeout=2)
            print("🛑 语音识别已停止")
        else:
            print("⚠️  服务未在运行")
    
    def start_service(self, device_id=None):
        """启动语音识别服务"""
        print("🚀 启动安全版语音识别服务...")
        
        # 选择麦克风设备
        if device_id is not None:
            if not self.select_microphone_by_id(device_id):
                return False
        else:
            if not self.select_microphone_interactive():
                return False
        
        # 初始化模型
        if not self.initialize_models():
            return False
        
        print("✅ 服务启动成功")
        if self.enable_commands:
            print("🎯 命令识别功能已启用，可以使用语音命令控制系统")
            print("🛡️ 已启用命令防重复机制，相同命令间隔2秒执行")
            print("🔧 VAD优化：动态阈值 + 最小语音长度检测")
            print("🚫 识别结果去重：避免重复输出相同结果")
            self.print_available_commands()
        return True
    
    def run(self, device_id=None):
        """运行应用主循环"""
        last_interrupt_time = 0
        
        try:
            # 启动服务
            if not self.start_service(device_id):
                sys.exit(1)
            
            # 开始识别
            if not self.start_recognition():
                sys.exit(1)
            
            print("💡 按两次 Ctrl+C 或在1秒内按一次 Ctrl+C 来真正退出程序")
            
            # 保持运行
            while self.is_running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            current_time = time.time()
            self.keyboard_interrupt_count += 1
            
            # 如果是第一次KeyboardInterrupt，或者距离上次中断时间超过2秒
            if self.keyboard_interrupt_count == 1 or (current_time - last_interrupt_time) > 2.0:
                print(f"\n⚠️ 捕获到KeyboardInterrupt (第{self.keyboard_interrupt_count}次)")
                print("💡 这可能是程序内部触发的，不是用户退出意图")
                print("💡 如果要退出程序，请在2秒内再次按 Ctrl+C")
                last_interrupt_time = current_time
                
                # 重置计数器（在2秒后）
                def reset_counter():
                    time.sleep(2.1)
                    if time.time() - last_interrupt_time > 2.0:
                        self.keyboard_interrupt_count = 0
                
                import threading
                threading.Thread(target=reset_counter, daemon=True).start()
                
                # 继续运行
                self.run_continue_after_interrupt()
                
            else:
                # 短时间内收到第二次KeyboardInterrupt，真正退出
                print(f"\n\n👋 正在退出... (用户确认退出，第{self.keyboard_interrupt_count}次KeyboardInterrupt)")
                self.user_exit_requested = True
                self.stop_recognition()
                
        except Exception as e:
            print(f"❌ 应用运行错误: {e}")
            print(f"异常类型: {type(e).__name__}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
        finally:
            if not self.user_exit_requested:
                print("🔄 程序意外结束，正在清理...")
            self.stop_recognition()
    
    def run_continue_after_interrupt(self):
        """在KeyboardInterrupt后继续运行"""
        try:
            # 继续保持运行
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            # 如果在短时间内再次收到KeyboardInterrupt
            current_time = time.time()
            self.keyboard_interrupt_count += 1
            print(f"\n\n👋 正在退出... (用户确认退出，第{self.keyboard_interrupt_count}次KeyboardInterrupt)")
            self.user_exit_requested = True
            self.stop_recognition()


def main():
    """主函数"""
    print("🎙️  安全版语音识别应用 - 带命令识别功能")
    print("=" * 50)
    print("✅ 使用改进的音量检测VAD，避免重复识别")
    print("🛡️ 修复了PyInstaller兼容性问题")
    print("🎯 集成智能语音命令识别系统")
    print("🚫 多层去重机制：彻底解决重复识别问题")
    print("🔧 智能命令匹配：容错识别不准确的结果")
    print("💡 确保在安静环境中使用，说话清晰完整")
    
    # 可以设置上下文关键词提高识别准确率
    # 添加命令相关的上下文词汇
    contexts = [
        "停止", "开始", "退出", "刷新", "复制", "粘贴", "剪切", 
        "撤销", "重做", "保存", "全选", "最小化", "最大化", 
        "关闭", "切换", "打开", "新建", "截图", "静音"
    ]
    
    # 创建应用实例 - 默认启用命令识别
    app = VoiceRecognitionApp(contexts=contexts, enable_commands=True)
    
    # 如果要禁用命令识别功能，可以设置 enable_commands=False
    # app = VoiceRecognitionApp(contexts=contexts, enable_commands=False)
    
    # 运行应用
    app.run()


if __name__ == "__main__":
    main() 