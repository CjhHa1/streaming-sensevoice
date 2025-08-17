#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import requests
import json
from difflib import SequenceMatcher
from shortcut_config import ShortcutConfig
# 尝试导入pyperclip，如果失败则使用备用方案

try:
    import pyperclip
except ImportError:
    print("⚠️ pyperclip未安装，剪贴板功能将使用系统命令")
    pyperclip = None
    
# 导入keyboard库用于键盘模拟

try:
    import keyboard
    print("✅ keyboard库已导入，将使用键盘模拟进行命令执行")
    KEYBOARD_AVAILABLE = True
except ImportError:
    print("⚠️ keyboard库未安装，将使用备用方案")
    keyboard = None
    KEYBOARD_AVAILABLE = False

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
from streaming_sensevoice import StreamingSenseVoice

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
        
        # 检查keyboard库是否可用
        self.keyboard_available = KEYBOARD_AVAILABLE
        if self.keyboard_available:
            print("✅ 键盘模拟功能已启用")
        else:
            print("⚠️ keyboard库不可用，将使用备用方案")
        
        # 加载快捷键配置
        self.shortcut_config = ShortcutConfig()
        
        # 定义需要特殊处理的命令
        self.special_commands = {
            "退出": self.exit_app,
            "关闭": self.exit_app,
            "停止": self.stop_recognition,
            "暂停": self.stop_recognition,
            "结束": self.exit_app,
            "测试复制": self.test_copy_function,
            "打开浏览器": self.open_browser,
            "打开记事本": self.open_notepad,
            "打开计算器": self.open_calculator,
        }
        
        # 从配置动态构建所有可用命令
        self.commands = {}
        self.commands.update(self.special_commands)
        for shortcut_info in self.shortcut_config.shortcuts:
            command_name = shortcut_info['command']
            if command_name not in self.commands:
                # 对于非特殊命令，统一使用快捷键执行器
                # 使用 lambda cmd=command_name: ... 来正确捕获 command_name
                self.commands[command_name] = lambda cmd=command_name: self.execute_shortcut(cmd)

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
    
    def send_hotkey(self, *keys):
        """
        使用keyboard库发送快捷键
        
        Args:
            *keys: 按键序列，例如 'ctrl', 'c' 或 'alt', 'f4'
            
        Returns:
            bool: 执行是否成功
        """
        if not self.keyboard_available:
            print("❌ keyboard库不可用，无法发送快捷键")
            return False
        
        try:
            # 使用keyboard.send发送组合键
            hotkey_str = '+'.join(keys)
            print(f"🎹 发送快捷键: {hotkey_str}")
            keyboard.send(hotkey_str)
            time.sleep(0.1)  # 小延迟确保按键被正确处理
            return True
        except Exception as e:
            print(f"❌ 发送快捷键失败 ({hotkey_str}): {e}")
            return False
    
    def send_key(self, key):
        """
        发送单个按键
        
        Args:
            key: 按键名称，例如 'f5', 'print screen'
            
        Returns:
            bool: 执行是否成功
        """
        if not self.keyboard_available:
            print("❌ keyboard库不可用，无法发送按键")
            return False
        
        try:
            print(f"🎹 发送按键: {key}")
            keyboard.send(key)
            time.sleep(0.1)  # 小延迟确保按键被正确处理
            return True
        except Exception as e:
            print(f"❌ 发送按键失败 ({key}): {e}")
            return False
    
    def execute_shortcut(self, command):
        """
        执行命令对应的快捷键
        
        Args:
            command: 命令名称
            
        Returns:
            bool: 执行是否成功
        """
        shortcut = self.shortcut_config.get_shortcut(command)
        if not shortcut:
            print(f"❌ 未找到命令 '{command}' 的快捷键配置")
            return False
        
        # 将快捷键字符串分割成按键列表
        keys = shortcut.split('+')
        # 区分是组合键还是单个功能键
        if len(keys) > 1:
            return self.send_hotkey(*keys)
        else:
            return self.send_key(keys[0])
    
    def print_available_commands(self):
        """打印可用的语音命令和对应的快捷键"""
        self.shortcut_config.print_shortcuts()
        
    def open_browser(self):
        """打开默认浏览器"""
        try:
            webbrowser.open('about:blank')
            print("🌐 已打开浏览器")
            return True
        except Exception as e:
            print(f"❌ 打开浏览器失败: {e}")
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
            
    def test_copy_function(self):
        """测试复制功能是否正常工作"""
        print("🧪 测试复制功能...")
        
        # 获取复制前的剪贴板内容
        before_copy = ""
        if pyperclip:
            try:
                before_copy = pyperclip.paste()
                print(f"📋 复制前剪贴板内容: '{before_copy[:50]}...' (仅显示前50字符)")
            except Exception as e:
                print(f"⚠️ 无法读取剪贴板: {e}")
        
        # 执行复制命令
        success = self.copy()
        
        if not success:
            print("❌ 复制命令执行失败")
            return False
        
        # 检查复制后的剪贴板内容
        if pyperclip:
            try:
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
            except Exception as e:
                print(f"⚠️ 无法验证剪贴板变化: {e}")
        
        print("⚠️ 无法检查剪贴板内容，假设复制成功")
        return True

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
        
        # 使用 self.commands 的键作为完整的命令列表
        all_commands = list(self.commands.keys())
        
        # 1. 精确匹配
        for cmd in all_commands:
            if cmd in text:
                return cmd
        
        # 2. 同义词匹配
        for synonym, cmd in self.synonyms.items():
            if synonym in text:
                return cmd
        
        # 3. 开头匹配（针对像"刷新新"这样的情况）
        for cmd in all_commands:
            if text.startswith(cmd):
                return cmd
        
        # 4. 模糊匹配（相似度阈值设为0.6）
        best_match = None
        best_score = 0.6
        
        for cmd in all_commands:
            score = self.similarity(text, cmd)
            if score > best_score:
                best_score = score
                best_match = cmd
        
        # 5. 检查同义词的模糊匹配
        for synonym, cmd_target in self.synonyms.items():
            score = self.similarity(text, synonym)
            if score > best_score:
                best_score = score
                best_match = cmd_target
        
        # 6. 容错匹配
        if not best_match and len(text) > 2:
            truncated_text = text[:-1]
            for cmd in all_commands:
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
                print(f"🔧 执行命令: {command_name}")
                # 调用在 __init__ 中映射好的方法
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
        if self.is_text_repeated(text):
            return False
        
        command = self.find_command(text)
        if command:
            if self.is_command_in_cooldown(command):
                print(f"⏰ 命令 '{command}' 正在冷却中，请稍后再试")
                return False
            
            print(f"🎯 识别到命令: {command}")
            result = self.execute_command(command)
            
            if result:
                self.last_command = command
                self.last_command_time = time.time()
                self.last_recognized_text = text
            
            return result
        return False

    def is_text_repeated(self, text):
        """检查文本是否与最近识别的文本重复"""
        if not self.last_recognized_text:
            return False
        similarity = self.similarity(text.lower().strip(), self.last_recognized_text.lower().strip())
        return similarity > self.text_repeat_threshold

    def is_command_in_cooldown(self, command):
        """检查命令是否在冷却期内"""
        if self.last_command != command:
            return False
        current_time = time.time()
        return (current_time - self.last_command_time) < self.command_cooldown

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


class ImprovedVAD:
    """改进的音量检测VAD，更好地支持长语音输入"""
    
    def __init__(self, 
                 threshold=0.015,  # 降低阈值，更容易检测到语音
                 speech_pad_ms=800,  # 增加静音填充时间
                 min_speech_ms=200,  # 降低最小语音长度要求
                 max_silence_ms=1500,  # 最大静音时长，避免过早结束
                 energy_smooth_window=5):  # 能量平滑窗口
        
        self.threshold = threshold
        self.speech_pad_samples = int(speech_pad_ms * 16000 / 1000)
        self.min_speech_samples = int(min_speech_ms * 16000 / 1000)
        self.max_silence_samples = int(max_silence_ms * 16000 / 1000)
        
        self.is_speech = False
        self.speech_buffer = []
        self.silence_counter = 0
        self.speech_counter = 0  # 语音持续计数器
        self.speech_start_time = 0
        
        # 能量历史和平滑
        self.energy_history = []
        self.energy_history_length = 20
        self.energy_smooth_window = energy_smooth_window
        
        # 动态阈值调整
        self.noise_floor = 0.01  # 噪声基底
        self.dynamic_threshold_factor = 1.5  # 动态阈值系数
        
        # 语音活动历史
        self.activity_history = []
        self.activity_window = 10
        
    def _calculate_energy(self, audio_chunk):
        """计算音频能量，使用RMS方法"""
        return np.sqrt(np.mean(audio_chunk ** 2))
    
    def _smooth_energy(self, energy):
        """对能量进行平滑处理"""
        self.energy_history.append(energy)
        if len(self.energy_history) > self.energy_history_length:
            self.energy_history.pop(0)
        
        # 计算移动平均
        if len(self.energy_history) >= self.energy_smooth_window:
            window = self.energy_history[-self.energy_smooth_window:]
            return np.mean(window)
        return energy
    
    def _update_noise_floor(self, energy):
        """更新噪声基底估计"""
        if not self.is_speech and len(self.energy_history) > 5:
            # 在非语音期间更新噪声基底
            recent_energies = self.energy_history[-10:]
            self.noise_floor = np.percentile(recent_energies, 30)
    
    def _is_speech_energy(self, energy, smoothed_energy):
        """判断当前能量是否为语音"""
        # 更新噪声基底
        self._update_noise_floor(energy)
        
        # 计算动态阈值
        dynamic_threshold = max(
            self.threshold,
            self.noise_floor * self.dynamic_threshold_factor
        )
        
        # 使用平滑后的能量进行判断
        is_voice = smoothed_energy > dynamic_threshold
        
        # 更新活动历史
        self.activity_history.append(1 if is_voice else 0)
        if len(self.activity_history) > self.activity_window:
            self.activity_history.pop(0)
        
        # 如果最近有足够的语音活动，保持语音状态
        if len(self.activity_history) >= 3:
            recent_activity = sum(self.activity_history[-3:])
            if recent_activity >= 2:  # 最近3帧中有2帧是语音
                return True
        
        return is_voice
    
    def __call__(self, audio_chunk):
        """处理音频块并返回语音段"""
        # 计算音频能量
        energy = self._calculate_energy(audio_chunk)
        smoothed_energy = self._smooth_energy(energy)
        
        is_voice = self._is_speech_energy(energy, smoothed_energy)
        
        if is_voice:
            self.speech_counter += len(audio_chunk)
            
            if not self.is_speech:
                # 语音开始
                self.is_speech = True
                self.speech_buffer = []
                self.silence_counter = 0
                self.speech_counter = len(audio_chunk)
                self.speech_start_time = time.time()
                print(f"🎤 语音开始 (能量: {energy:.4f}, 平滑能量: {smoothed_energy:.4f}, 阈值: {self.threshold:.4f})")
                yield {"start": True}, np.array([])
            
            # 添加到语音缓冲区
            self.speech_buffer.extend(audio_chunk)
            self.silence_counter = 0  # 重置静音计数器
            
        else:  # 静音
            if self.is_speech:
                self.silence_counter += len(audio_chunk)
                self.speech_buffer.extend(audio_chunk)  # 包含静音部分
                
                # 计算语音持续时间
                speech_duration_ms = len(self.speech_buffer) / 16000.0 * 1000
                silence_duration_ms = self.silence_counter / 16000.0 * 1000
                
                # 判断是否应该结束语音
                # 条件1：静音时间超过阈值且语音时间足够长
                # 条件2：静音时间超过最大静音时长（避免永远不结束）
                should_end = False
                
                if speech_duration_ms >= self.min_speech_samples / 16000.0 * 1000:
                    if silence_duration_ms >= self.speech_pad_samples / 16000.0 * 1000:
                        should_end = True
                        end_reason = "正常结束"
                    elif silence_duration_ms >= self.max_silence_samples / 16000.0 * 1000:
                        should_end = True
                        end_reason = "最大静音时长"
                
                if should_end:
                    # 语音结束
                    self.is_speech = False
                    speech_data = np.array(self.speech_buffer)
                    
                    print(f"🎤 语音结束 - {end_reason} (时长: {speech_duration_ms:.1f}ms, 静音: {silence_duration_ms:.1f}ms)")
                    
                    # 清理状态
                    self.speech_buffer = []
                    self.silence_counter = 0
                    self.speech_counter = 0
                    self.activity_history = []  # 清空活动历史
                    
                    yield {"end": True}, speech_data
                    
                    # 短暂延迟，避免立即重新触发
                    time.sleep(0.1)


class VoiceRecognitionApp:
    """语音识别"""
    
    def __init__(self, contexts=None, model_path=None, enable_commands=True, user_id=None, mouse_profile=None):
        """
        初始化语音识别应用
        
        Args:
            contexts: 上下文列表，用于提高识别准确率
            model_path: 本地模型路径，如果指定则使用本地模型
            enable_commands: 是否启用命令识别功能
            user_id: 发送到聊天接口的用户ID
            mouse_profile: 发送到聊天接口的鼠标配置/画像
        """
        self.contexts = contexts or []
        self.model_path = model_path or "iic/SenseVoiceSmall"
        self.model = None
        self.vad = None
        self.is_running = False
        self.selected_device_id = None
        self.recognition_thread = None
        
        # 聊天接口附加参数
        self.user_id = user_id if user_id is not None else (os.getenv("USERNAME") or os.getenv("USER") or "local_user")
        self.mouse_profile = mouse_profile if mouse_profile is not None else {}
        
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
            print("✅ 使用改进的VAD，支持长语音输入")
            self.vad = ImprovedVAD(
                threshold=0.015,  # 更低的阈值
                speech_pad_ms=800,  # 更长的静音填充
                min_speech_ms=200,  # 更短的最小语音要求
                max_silence_ms=1500,  # 最大静音时长
                energy_smooth_window=5  # 能量平滑
            )
            
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
                print("💡 改进的VAD设置：")
                print("   - 更低的激活阈值 (0.015)")
                print("   - 更长的静音容忍时间 (800ms)")
                print("   - 最大静音时长限制 (1500ms)")
                print("   - 能量平滑处理，减少误判")
                print("   - 动态噪声基底调整")
                
                while self.is_running:
                    try:
                        samples, _ = stream.read(samples_per_read)
                        
                        # 使用改进的VAD处理音频
                        for speech_dict, speech_samples in self.vad(samples[:, 0]):
                            if "start" in speech_dict:
                                self.model.reset()
                                # 重置命令处理器状态
                                if self.enable_commands and self.command_processor:
                                    self.command_processor.reset_command_state()
                                # 重置识别结果去重状态
                                self.last_recognition_result = ""
                                self.last_recognition_timestamps = None
                            
                            # 只处理完整的语音段（语音结束时）
                            if "end" in speech_dict and len(speech_samples) > 0:
                                try:
                                    print("🔄 正在处理语音...")
                                    # 进行语音识别
                                    recognition_results = []
                                    for res in self.model.streaming_inference(speech_samples * 32768, is_last=True):
                                        if res["text"].strip():
                                            recognition_results.append(res)
                                    
                                    # 处理识别结果
                                    if recognition_results:
                                        final_result = recognition_results[-1]
                                        print(f"🗣️  识别结果: {final_result['text']}")
                                        print(f"⏱️  时间戳: {final_result['timestamps']}")
                                        
                                        # 处理最终识别结果
                                        self.on_recognition_result(final_result, is_final=True)
                                    else:
                                        print("⚠️ 未识别到有效内容")
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
        
        # 只在最终结果时处理命令识别
        if is_final and self.enable_commands and self.command_processor:
            # 尝试处理为命令
            if self.command_processor.process_text(text):
                print("🎯 识别到命令，已执行")
                return  # 如果识别到命令并执行，则不进行其他处理
        
        # 如果不是命令，发送到聊天接口
        if is_final:
            self.send_to_chat(text)
    
    def send_to_chat(self, text):
        """
        将识别到的非命令文本发送到聊天接口
        
        Args:
            text (str): 识别的文本内容
        """
        try:
            url = "http://127.0.0.1:8000/chat"
            payload = {
                "message": text,
                "user_id": self.user_id,
                "mouse_profile": self.mouse_profile
            }
            
            print(f"💬 发送到聊天接口: {text}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ 成功发送到聊天接口")
                try:
                    response_data = response.json()
                    if "response" in response_data:
                        print(f"🤖 聊天回复: {response_data['response']}")
                except json.JSONDecodeError:
                    print("📄 收到回复，但格式不是JSON")
            else:
                print(f"⚠️ 聊天接口返回状态码: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到聊天接口 (http://127.0.0.1:8000/chat)")
            print("💡 请确保聊天服务正在运行")
        except requests.exceptions.Timeout:
            print("⏰ 聊天接口请求超时")
        except Exception as e:
            print(f"❌ 发送到聊天接口时出错: {e}")
    
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
        print("💡 现在支持更长的语音输入，不会过早中断")
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
        print("🚀 启动改进版语音识别服务...")
        print("🎯 特性：支持长语音输入，避免短语音中断")
        
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
            print("🎯 命令识别功能已启用")
            print("🛡️ 改进的VAD算法：")
            print("   - 动态噪声基底适应")
            print("   - 能量平滑处理")
            print("   - 灵活的语音边界检测")
            print("   - 支持长语音和短暂停顿")
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
    print("🎙️  改进版语音识别应用 - 支持长语音输入")
    print("=" * 50)
    print("✅ 使用改进的VAD算法，更好地处理长语音")
    print("🛡️ 动态噪声基底适应，减少误判")
    print("🎯 灵活的语音边界检测，支持短暂停顿")
    print("⚡ 能量平滑处理，提高识别稳定性")
    print("🔧 优化的参数设置：")
    print("   - 激活阈值: 0.015 (更容易激活)")
    print("   - 静音填充: 800ms (更长的容忍时间)")
    print("   - 最大静音: 1500ms (避免无限等待)")
    print("💡 适合各种语音输入场景，包括长句子和复杂表达")
    
    # 可以设置上下文关键词提高识别准确率
    contexts = [
        "停止", "开始", "退出", "刷新", "复制", "粘贴", "剪切", 
        "撤销", "重做", "保存", "全选", "最小化", "最大化", 
        "关闭", "切换", "打开", "新建", "截图", "静音"
    ]
    
    # 创建应用实例
    app = VoiceRecognitionApp(contexts=contexts, enable_commands=True)
    
    # 运行应用
    app.run()


if __name__ == "__main__":
    main()