#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化模型测试文件
"""

import pytest
import torch
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # 从主模块导入
    from streaming_sensevoice import QuantizedStreamingSenseVoice
    QUANTIZATION_AVAILABLE = True
except ImportError:
    try:
        # 如果主模块导入失败，尝试直接从子模块导入
        from streaming_sensevoice.quantized_sensevoice import QuantizedStreamingSenseVoice
        QUANTIZATION_AVAILABLE = True
    except ImportError as e:
        QUANTIZATION_AVAILABLE = False
        import_error = str(e)

@pytest.mark.skipif(not QUANTIZATION_AVAILABLE, reason=f"量化功能不可用: {import_error if not QUANTIZATION_AVAILABLE else ''}")
class TestQuantizedStreamingSenseVoice:
    """量化模型测试类"""
    
    def test_model_creation(self):
        """测试量化模型创建"""
        # 使用CPU避免GPU依赖
        model = QuantizedStreamingSenseVoice(
            model="iic/SenseVoiceSmall",
            device="cpu",
            use_8bit=True,
            chunk_size=5,  # 使用较小的chunk减少测试时间
            padding=2
        )
        
        assert model.use_8bit == True
        assert model.device == "cpu"
        assert model.chunk_size == 5
        assert model.padding == 2
    
    def test_memory_info(self):
        """测试内存信息获取"""
        model = QuantizedStreamingSenseVoice(
            model="iic/SenseVoiceSmall",
            device="cpu",
            use_8bit=True,
            chunk_size=5,
            padding=2
        )
        
        memory_info = model.get_memory_info()
        
        assert isinstance(memory_info, dict)
        assert "model_size_mb" in memory_info
        assert "quantization_enabled" in memory_info
        assert "estimated_memory_saving" in memory_info
        assert memory_info["quantization_enabled"] == True
        assert memory_info["estimated_memory_saving"] == "~50%"
    
    def test_model_save_and_load(self):
        """测试模型保存和加载"""
        # 创建临时目录
        # 取当前目录作为临时目录
        from pathlib import Path
        temp_dir = Path(__file__).parent
        temp_path = Path(temp_dir)
        print(temp_path)
        # 创建量化模型
        original_model = QuantizedStreamingSenseVoice(
            model="iic/SenseVoiceSmall",
            device="cpu",
            use_8bit=True,
            chunk_size=5,
            padding=2
        )
        
        # 保存模型
        save_path = original_model.save_quantized_model(
            save_directory=str(temp_path / "saved_model"),
            model_name="test_quantized"
        )
        
        assert Path(save_path).exists()
        
        # 检查保存的文件
        saved_files = list(Path(save_path).rglob("*"))
        expected_files = [
            "model_info.json",
            "quantization_config.json", 
            "frontend_config.json",
            "README.md"
        ]
        
        saved_file_names = [f.name for f in saved_files if f.is_file()]
        for expected_file in expected_files:
            assert expected_file in saved_file_names, f"缺少文件: {expected_file}"
        
        # 加载模型
        loaded_model = QuantizedStreamingSenseVoice.load_from_saved(
            save_directory=save_path,
            device="cpu"
        )
        
        # 验证加载的模型属性
        assert loaded_model.use_8bit == original_model.use_8bit
        assert loaded_model.device == "cpu"
    
    def test_standard_vs_quantized(self):
        """测试标准模型与量化模型的对比"""
        # 标准模型
        standard_model = QuantizedStreamingSenseVoice(
            model="iic/SenseVoiceSmall",
            device="cpu",
            use_8bit=False,
            chunk_size=5,
            padding=2
        )
        
        # 量化模型
        quantized_model = QuantizedStreamingSenseVoice(
            model="iic/SenseVoiceSmall",
            device="cpu", 
            use_8bit=True,
            chunk_size=5,
            padding=2
        )
        
        standard_info = standard_model.get_memory_info()
        quantized_info = quantized_model.get_memory_info()
        
        # 验证量化模型确实启用了量化
        assert standard_info["quantization_enabled"] == False
        assert quantized_info["quantization_enabled"] == True
        
        # 验证内存节省估算
        assert quantized_info["estimated_memory_saving"] == "~50%"
        assert standard_info["estimated_memory_saving"] == "0%"

def test_quantization_import():
    """测试量化相关包的导入"""
    try:
        import torch
        import transformers
        from transformers import BitsAndBytesConfig
        assert True, "所有必需的包都可以导入"
    except ImportError as e:
        pytest.skip(f"缺少必需的包: {e}")

if __name__ == "__main__":
    # 简单的功能测试
    print("🧪 运行量化模型基础测试...")
    
    if QUANTIZATION_AVAILABLE:
        print("✅ 量化功能可用")
        
        try:
            # 基础测试
            TestQuantizedStreamingSenseVoice().test_model_save_and_load()
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    else:
        print(f"❌ 量化功能不可用: {import_error}")