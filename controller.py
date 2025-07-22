#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘控制器模块
支持 keyboard 和 pyautogui 两种实现方式
"""

import time
import platform
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod

# 尝试导入 keyboard 库
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None

# 尝试导入 pyautogui 库
try:
    import pyautogui
    # 设置 pyautogui 的安全特性
    pyautogui.FAILSAFE = True  # 鼠标移到左上角会触发异常，作为紧急停止
    pyautogui.PAUSE = 0.1  # 每个函数调用后暂停0.1秒
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None


class KeyboardController(ABC):
    """键盘控制器抽象基类"""
    
    @abstractmethod
    def send_key(self, key: str) -> bool:
        """发送单个按键"""
        pass
    
    @abstractmethod
    def send_hotkey(self, *keys: str) -> bool:
        """发送组合键"""
        pass
    
    @abstractmethod
    def type_text(self, text: str, interval: float = 0.0) -> bool:
        """输入文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查控制器是否可用"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取控制器名称"""
        pass


class KeyboardLibController(KeyboardController):
    """使用 keyboard 库的控制器实现"""
    
    def __init__(self):
        self.available = KEYBOARD_AVAILABLE
        if self.available:
            print("✅ KeyboardLibController 初始化成功")
        else:
            print("❌ keyboard 库不可用")
    
    def send_key(self, key: str) -> bool:
        """发送单个按键"""
        if not self.available:
            return False
        
        try:
            print(f"🎹 [Keyboard] 发送按键: {key}")
            keyboard.send(key)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"❌ [Keyboard] 发送按键失败 ({key}): {e}")
            return False
    
    def send_hotkey(self, *keys: str) -> bool:
        """发送组合键"""
        if not self.available:
            return False
        
        try:
            hotkey_str = '+'.join(keys)
            print(f"🎹 [Keyboard] 发送组合键: {hotkey_str}")
            keyboard.send(hotkey_str)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"❌ [Keyboard] 发送组合键失败 ({'+'.join(keys)}): {e}")
            return False
    
    def type_text(self, text: str, interval: float = 0.0) -> bool:
        """输入文本"""
        if not self.available:
            return False
        
        try:
            print(f"⌨️  [Keyboard] 输入文本: {text[:20]}...")
            keyboard.write(text, delay=interval)
            return True
        except Exception as e:
            print(f"❌ [Keyboard] 输入文本失败: {e}")
            return False
    
    def is_available(self) -> bool:
        return self.available
    
    def get_name(self) -> str:
        return "keyboard"
    
class PyAutoGUIController(KeyboardController):
    """使用 pyautogui 库的控制器实现"""

    # pyautogui 的按键映射
    KEY_MAPPING = {
        # 功能键
        'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
        'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
        'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
        
        # 控制键
        'ctrl': 'ctrl', 'control': 'ctrl',
        'alt': 'alt', 'shift': 'shift',
        'cmd': 'command', 'win': 'win', 'windows': 'win',
        
        # 方向键
        'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
        
        # 特殊键
        'enter': 'enter', 'return': 'enter',
        'space': 'space', 'tab': 'tab',
        'escape': 'escape', 'esc': 'escape',
        'backspace': 'backspace', 'delete': 'delete',
        'home': 'home', 'end': 'end',
        'pageup': 'pageup', 'pagedown': 'pagedown',
        'insert': 'insert',
        'printscreen': 'printscreen', 'print screen': 'printscreen',
        
        # 音量控制键
        'volumemute': 'volumemute', 'volumeup': 'volumeup', 'volumedown': 'volumedown',
        
        # 媒体键
        'playpause': 'playpause', 'nexttrack': 'nexttrack', 'prevtrack': 'prevtrack',
    }
    
    def __init__(self):
        self.available = PYAUTOGUI_AVAILABLE
        if self.available:
            print("✅ PyAutoGUIController 初始化成功")
            # 获取屏幕尺寸，用于验证
            try:
                width, height = pyautogui.size()
                print(f"📺 屏幕尺寸: {width}x{height}")
            except:
                pass
        else:
            print("❌ pyautogui 库不可用")
    
    def _normalize_key(self, key: str) -> str:
        """规范化按键名称"""
        key_lower = key.lower()
        return self.KEY_MAPPING.get(key_lower, key_lower)
    
    def send_key(self, key: str) -> bool:
        """发送单个按键"""
        if not self.available:
            return False
        
        try:
            normalized_key = self._normalize_key(key)
            print(f"🎹 [PyAutoGUI] 发送按键: {key} -> {normalized_key}")
            pyautogui.press(normalized_key)
            return True
        except Exception as e:
            print(f"❌ [PyAutoGUI] 发送按键失败 ({key}): {e}")
            return False
    
    def send_hotkey(self, *keys: str) -> bool:
        """发送组合键"""
        if not self.available:
            return False
        
        try:
            normalized_keys = [self._normalize_key(k) for k in keys]
            print(f"🎹 [PyAutoGUI] 发送组合键: {'+'.join(keys)} -> {'+'.join(normalized_keys)}")
            
            # pyautogui 使用 hotkey 函数发送组合键
            pyautogui.hotkey(*normalized_keys)
            return True
        except Exception as e:
            print(f"❌ [PyAutoGUI] 发送组合键失败 ({'+'.join(keys)}): {e}")
            return False
    
    def type_text(self, text: str, interval: float = 0.0) -> bool:
        """输入文本"""
        if not self.available:
            return False
        
        try:
            print(f"⌨️  [PyAutoGUI] 输入文本: {text[:20]}...")
            pyautogui.typewrite(text, interval=interval)
            return True
        except Exception as e:
            print(f"❌ [PyAutoGUI] 输入文本失败: {e}")
            return False
    
    def is_available(self) -> bool:
        return self.available
    
    def get_name(self) -> str:
        return "pyautogui"
    


if __name__ == "__main__":
    controller = PyAutoGUIController()
    controller.send_key("a")
    controller.send_hotkey("ctrl", "a")
    controller.type_text("Hello, World!")
    controller.send_key("enter")
    controller.send_key("esc")
    controller.send_key("f1")
    controller.send_key("f2")