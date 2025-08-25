import torch
import os
import json
import pickle
from pathlib import Path
from transformers import BitsAndBytesConfig
from .sensevoice import SenseVoiceSmall
from .streaming_sensevoice import StreamingSenseVoice, sensevoice_models

class QuantizedStreamingSenseVoice(StreamingSenseVoice):
    """8bit量化版本的StreamingSenseVoice"""
    
    def __init__(self, use_8bit: bool = True, **kwargs):
        self.use_8bit = use_8bit
        self.quantization_config = None
        
        # 创建一个包装函数来处理参数传递
        def quantized_load_model(*args, **load_kwargs):
            if len(args) >= 2:
                # 位置参数调用
                return self.load_model_quantized(args[0], args[1], use_8bit)
            elif 'model' in load_kwargs and 'device' in load_kwargs:
                # 关键字参数调用
                return self.load_model_quantized(load_kwargs['model'], load_kwargs['device'], use_8bit)
            else:
                # 混合调用
                model = args[0] if len(args) > 0 else load_kwargs.get('model')
                device = args[1] if len(args) > 1 else load_kwargs.get('device')
                print(f"🔄 正在加载量化模型: {model} on {device}")
                return self.load_model_quantized(model, device, use_8bit)
        
        # 修改模型加载方式
        original_load_model = StreamingSenseVoice.load_model
        StreamingSenseVoice.load_model = quantized_load_model
        
        super().__init__(**kwargs)
        
        # 恢复原始方法
        StreamingSenseVoice.load_model = original_load_model
    
    def load_model_quantized(self, model: str, device: str, use_8bit: bool = True) -> tuple:
        """加载量化模型"""
        key = f"{model}-{device}-{'8bit' if use_8bit else 'fp16'}"
        if key not in sensevoice_models:
            if use_8bit:
                # 配置8bit量化
                self.quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_threshold=6.0,  # 异常值阈值
                    llm_int8_skip_modules=["embed", "norm"]  # 跳过某些层
                )
                
                print(f"🔄 正在加载8bit量化模型: {model}")
                model_obj, kwargs = SenseVoiceSmall.from_pretrained(
                    model=model, 
                    device=device,
                    quantization_config=self.quantization_config
                )
                print(f"✅ 8bit量化模型加载完成，内存占用约为原模型的50%")
            else:
                print(f"🔄 正在加载标准精度模型: {model}")
                model_obj, kwargs = SenseVoiceSmall.from_pretrained(
                    model=model, 
                    device=device
                )
                print(f"✅ 标准精度模型加载完成")
            
            model_obj = model_obj.to(device)
            model_obj.eval()
            sensevoice_models[key] = (model_obj, kwargs)
        return sensevoice_models[key]
    
    def save_quantized_model(self, save_directory: str, model_name: str = "quantized_sensevoice"):
        """
        保存量化后的模型
        
        Args:
            save_directory: 保存目录路径
            model_name: 模型名称
        """
        save_path = Path(save_directory)
        save_path.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"🔄 正在保存量化模型到: {save_path}")
            
            # 1. 保存模型信息（不保存量化权重，因为会被反量化）
            model_save_path = save_path / model_name
            model_save_path.mkdir(exist_ok=True)
            
            # 对于量化模型，我们采用不同的保存策略
            if self.use_8bit:
                print("ℹ️ 8bit量化模型：只保存量化配置，不保存权重")
                print("   原因：bitsandbytes的量化是动态的，保存权重会被反量化")
                print("   加载时会重新下载模型并应用量化配置")
                
                # 创建一个标记文件表示这是量化模型
                quantized_marker = model_save_path / "quantized_model.txt"
                with open(quantized_marker, 'w') as f:
                    f.write(f"""这是一个8bit量化模型配置

                        量化类型: bitsandbytes 8bit
                        原始模型: {self.model_path}
                        设备: {self.device}

                        注意：
                        - 此目录不包含模型权重
                        - 加载时会自动重新下载原始模型并应用量化
                        - 这是正确的做法，因为bitsandbytes量化是动态的

                        加载方法：
                        QuantizedStreamingSenseVoice.load_from_saved("{save_path}")
                        """)
                
                # 保存内存使用情况
                memory_info = self.get_memory_info()
                memory_file = model_save_path / "memory_info.json"
                with open(memory_file, 'w') as f:
                    json.dump(memory_info, f, indent=2, default=str)
                    
                print("✅ 量化模型配置保存完成")
                
            else:
                # 对于非量化模型，保存实际权重
                print("💾 标准精度模型：保存完整权重")
                try:
                    # 尝试使用Hugging Face方式保存
                    if hasattr(self.model, 'save_pretrained'):
                        self.model.save_pretrained(
                            model_save_path,
                            safe_serialization=True
                        )
                        print("✅ 使用 save_pretrained 保存模型")
                    else:
                        # 使用PyTorch标准方式保存
                        model_file = model_save_path / "pytorch_model.bin"
                        torch.save(self.model.state_dict(), model_file)
                        
                        # 保存模型配置
                        if hasattr(self.model, 'config'):
                            config_file = model_save_path / "config.json"
                            with open(config_file, 'w') as f:
                                json.dump(self.model.config.__dict__, f, indent=2)
                        
                        print("✅ 使用 PyTorch 标准方式保存模型")
                        
                except Exception as save_error:
                    print(f"⚠️ 标准保存失败，使用备用方案: {save_error}")
                    # 备用保存方案：只保存权重
                    model_file = model_save_path / "model_weights.pth"
                    torch.save(self.model.state_dict(), model_file)
                    print("✅ 已保存模型权重到 model_weights.pth")
            
            # 2. 保存量化配置
            quant_config_path = save_path / "quantization_config.json"
            if self.quantization_config:
                with open(quant_config_path, 'w') as f:
                    json.dump({
                        "quantization_type": "8bit",
                        "use_8bit": self.use_8bit,
                        "llm_int8_threshold": 6.0,
                        "llm_int8_skip_modules": ["embed", "norm"],
                        "load_in_8bit": True
                    }, f, indent=2)
            
            # 3. 保存模型参数和配置
            model_info = {
                "model_path": self.model_path,
                "device": self.device,
                "chunk_size": self.chunk_size,
                "padding": self.padding,
                "beam_size": self.beam_size,
                "contexts": self.contexts,
                "use_8bit": self.use_8bit,
                "quantization_enabled": True
            }
            
            info_path = save_path / "model_info.json"
            with open(info_path, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            # 4. 保存tokenizer相关文件
            tokenizer_path = save_path / "tokenizer"
            tokenizer_path.mkdir(exist_ok=True)
            
            # 保存tokenizer信息（如果有的话）
            if hasattr(self, 'tokenizer') and self.tokenizer:
                tokenizer_info = {
                    "vocab_size": self.tokenizer.get_vocab_size(),
                    "bpe_model_available": hasattr(self, 'bpe_model') and self.bpe_model is not None
                }
                with open(tokenizer_path / "tokenizer_info.json", 'w') as f:
                    json.dump(tokenizer_info, f, indent=2)
            
            # 5. 保存前端配置（FBANK等）
            frontend_info = {
                "neg_mean": self.neg_mean.tolist() if hasattr(self, 'neg_mean') else None,
                "inv_stddev": self.inv_stddev.tolist() if hasattr(self, 'inv_stddev') else None,
                "window_type": "hamming"
            }
            
            frontend_path = save_path / "frontend_config.json"
            with open(frontend_path, 'w') as f:
                json.dump(frontend_info, f, indent=2)
            
            # 6. 生成README文件
            if self.use_8bit:
                readme_content = f"""# 8bit量化语音识别模型配置

## 模型信息
- 原始模型: {self.model_path}
- 量化类型: 8bit (bitsandbytes)
- 运行时内存节省: 约50%
- 设备: {self.device}

## 重要说明
⚠️ **此目录不包含模型权重文件**

原因：
- bitsandbytes的8bit量化是动态的，在推理时进行
- 保存的权重会被自动反量化，失去压缩效果
- 正确做法是保存量化配置，加载时重新应用

## 文件说明
- `{model_name}/quantized_model.txt`: 量化模型说明
- `{model_name}/memory_info.json`: 内存使用信息
- `quantization_config.json`: 量化配置参数
- `model_info.json`: 模型基本信息
- `frontend_config.json`: 前端处理配置

## 使用方法
```python
from streaming_sensevoice.quantized_sensevoice import QuantizedStreamingSenseVoice

# 加载量化模型配置（会重新下载并量化原始模型）
model = QuantizedStreamingSenseVoice.load_from_saved(
    save_directory="{save_path}",
    device="cuda"  # 或 "cpu"
)
```

## 内存效果
- 磁盘存储: 只保存配置文件（几KB）
- 运行时内存: 比原模型节省约50%
- 推理速度: 与原模型相近

## 为什么这样设计？
1. **bitsandbytes特性**: 量化是动态的，保存权重会反量化
2. **实际需求**: 量化的目的是减少运行时内存，不是减少存储
3. **可靠性**: 重新下载确保模型一致性
"""
            else:
                readme_content = f"""# 标准精度语音识别模型

## 模型信息
- 原始模型: {self.model_path}
- 精度: 标准精度 (float16/float32)
- 设备: {self.device}

## 文件说明
- `{model_name}/`: 模型权重和配置
- `model_info.json`: 模型基本信息
- `frontend_config.json`: 前端处理配置
- `tokenizer/`: 分词器相关文件

## 使用方法
```python
from streaming_sensevoice.quantized_sensevoice import QuantizedStreamingSenseVoice

# 加载保存的模型
model = QuantizedStreamingSenseVoice.load_from_saved(
    save_directory="{save_path}",
    device="cuda"  # 或 "cpu"
)
```

## 内存使用情况
- 模型大小: ~{self.get_model_size_mb():.1f}MB
"""
            
            readme_path = save_path / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            if self.use_8bit:
                print(f"✅ 8bit量化模型配置保存完成!")
                print(f"📁 保存路径: {save_path.absolute()}")
                print(f"💾 保存内容: 量化配置、模型信息、使用说明")
                print(f"ℹ️ 注意: 未保存权重文件（这是正确的）")
                print(f"📊 运行时内存节省: 约50%")
            else:
                print(f"✅ 标准精度模型保存完成!")
                print(f"📁 保存路径: {save_path.absolute()}")
                print(f"💾 包含文件: 模型权重、配置、使用说明")
            
            return str(save_path.absolute())
            
        except Exception as e:
            print(f"❌ 保存模型失败: {e}")
            raise e
    
    @classmethod
    def load_from_saved(cls, save_directory: str, device: str = "cuda"):
        """
        从保存的目录加载量化模型
        
        Args:
            save_directory: 保存目录路径
            device: 设备 ("cuda" 或 "cpu")
        
        Returns:
            QuantizedStreamingSenseVoice: 加载的量化模型实例
        """
        save_path = Path(save_directory)
        
        try:
            print(f"🔄 正在从 {save_path} 加载量化模型...")
            
            # 1. 读取模型信息
            info_path = save_path / "model_info.json"
            if not info_path.exists():
                raise FileNotFoundError(f"模型信息文件不存在: {info_path}")
            
            with open(info_path, 'r') as f:
                model_info = json.load(f)
            
            # 2. 读取量化配置
            quant_config_path = save_path / "quantization_config.json"
            use_8bit = True
            if quant_config_path.exists():
                with open(quant_config_path, 'r') as f:
                    quant_config = json.load(f)
                    use_8bit = quant_config.get("use_8bit", True)
            
            # 3. 创建实例，使用原始模型路径重新加载
            # 注意：由于SenseVoiceSmall的特殊性，我们重新从原始位置加载并应用量化
            original_model_path = model_info.get("model_path", "iic/SenseVoiceSmall")
            
            print(f"🔄 重新加载原始模型: {original_model_path}")
            instance = cls(
                chunk_size=model_info.get("chunk_size", 10),
                padding=model_info.get("padding", 8),
                beam_size=model_info.get("beam_size", 3),
                contexts=model_info.get("contexts"),
                device=device,
                model=original_model_path,  # 使用原始模型路径
                use_8bit=use_8bit
            )
            
            # 4. 如果有保存的权重，尝试加载（可选）
            saved_model_path = save_path / "quantized_sensevoice"
            if saved_model_path.exists():
                weight_files = [
                    "pytorch_model.bin",
                    "model_weights.pth"
                ]
                
                for weight_file in weight_files:
                    weight_path = saved_model_path / weight_file
                    if weight_path.exists():
                        try:
                            print(f"🔄 加载保存的权重: {weight_file}")
                            saved_weights = torch.load(weight_path, map_location=device)
                            instance.model.load_state_dict(saved_weights)
                            print(f"✅ 成功加载保存的权重")
                            break
                        except Exception as load_error:
                            print(f"⚠️ 加载权重失败: {load_error}, 使用新下载的模型")
                            break
            
            print(f"✅ 量化模型加载完成!")
            print(f"📊 量化类型: {'8bit' if use_8bit else '标准精度'}")
            print(f"💾 内存占用: 约为原模型的{'50%' if use_8bit else '100%'}")
            
            return instance
            
        except Exception as e:
            print(f"❌ 加载模型失败: {e}")
            raise e
    
    def get_model_size_mb(self) -> float:
        """获取模型大小（MB）"""
        if hasattr(self, 'model') and self.model:
            param_size = sum(p.numel() * p.element_size() for p in self.model.parameters())
            buffer_size = sum(b.numel() * b.element_size() for b in self.model.buffers())
            total_size = param_size + buffer_size
            return total_size / (1024 * 1024)  # 转换为MB
        return 0.0
    
    def get_memory_info(self) -> dict:
        """获取详细的内存使用信息"""
        if not hasattr(self, 'model') or not self.model:
            return {"error": "模型未加载"}
        
        info = {
            "model_size_mb": self.get_model_size_mb(),
            "quantization_enabled": self.use_8bit,
            "estimated_memory_saving": "~50%" if self.use_8bit else "0%",
            "device": self.device,
            "model_path": getattr(self, 'model_path', 'unknown')
        }
        
        # 如果在GPU上，获取GPU内存使用情况
        if self.device.startswith('cuda') and torch.cuda.is_available():
            info.update({
                "gpu_memory_allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
                "gpu_memory_reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
                "gpu_max_memory_mb": torch.cuda.max_memory_allocated() / (1024 * 1024)
            })
        
        return info