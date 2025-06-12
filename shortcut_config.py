import os
import yaml
from typing import Dict, List, Optional

class ShortcutConfig:
    """快捷键配置管理器"""
    
    def __init__(self, config_file: str = "keyboard_shortcuts.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.shortcuts: List[Dict] = []
        self.command_to_keys: Dict[str, str] = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 是否成功加载配置
        """
        try:
            if not os.path.exists(self.config_file):
                print(f"⚠️ 配置文件 {self.config_file} 不存在")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'shortcuts' not in config:
                print("❌ 配置文件格式错误")
                return False
            
            self.shortcuts = config['shortcuts']
            self.command_to_keys = {
                shortcut['command']: shortcut['keys']
                for shortcut in self.shortcuts
            }
            
            print(f"✅ 已加载 {len(self.shortcuts)} 个快捷键配置")
            return True
            
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 是否成功保存配置
        """
        try:
            config = {'shortcuts': self.shortcuts}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            print(f"✅ 配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False
    
    def get_shortcut(self, command: str) -> Optional[str]:
        """
        获取指定命令的快捷键
        
        Args:
            command: 命令名称
            
        Returns:
            str or None: 快捷键组合，如果不存在则返回None
        """
        return self.command_to_keys.get(command)
    
    def set_shortcut(self, command: str, keys: str, description: str = "") -> bool:
        """
        设置命令的快捷键
        
        Args:
            command: 命令名称
            keys: 快捷键组合
            description: 命令描述
            
        Returns:
            bool: 是否成功设置
        """
        # 检查是否已存在该命令
        for shortcut in self.shortcuts:
            if shortcut['command'] == command:
                shortcut['keys'] = keys
                if description:
                    shortcut['description'] = description
                self.command_to_keys[command] = keys
                return self.save_config()
        
        # 如果命令不存在，添加新的快捷键配置
        new_shortcut = {
            'command': command,
            'keys': keys,
            'description': description
        }
        self.shortcuts.append(new_shortcut)
        self.command_to_keys[command] = keys
        return self.save_config()
    
    def remove_shortcut(self, command: str) -> bool:
        """
        删除命令的快捷键配置
        
        Args:
            command: 命令名称
            
        Returns:
            bool: 是否成功删除
        """
        for i, shortcut in enumerate(self.shortcuts):
            if shortcut['command'] == command:
                self.shortcuts.pop(i)
                self.command_to_keys.pop(command, None)
                return self.save_config()
        return False
    
    def print_shortcuts(self):
        """
        打印快捷键配置
        """
        print("\n📋 所有快捷键:")
        print("-" * 60)
        for shortcut in self.shortcuts:
            print(f"命令: {shortcut['command']}")
            print(f"快捷键: {shortcut['keys']}")
            print(f"描述: {shortcut['description']}")
            print("-" * 60) 