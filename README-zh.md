# 🎙️ 语音识别应用

基于 StreamingSenseVoice 的实时语音识别应用，支持语音命令控制系统操作。特别优化了长语音输入支持。

## 📋 功能特性

- 🎤 **实时语音识别**：基于 StreamingSenseVoice 的流式语音识别
- 🎯 **语音命令控制**：通过语音控制系统操作（刷新、复制、粘贴等）
- 🔧 **智能设备选择**：自动检测并选择麦克风设备
- ⚙️ **灵活配置**：支持自定义上下文关键词和回调函数
- 🚀 **改进的 VAD 算法**：
  - 更好的长语音支持
  - 动态噪声基底适应
  - 能量平滑处理
  - 灵活的语音边界检测
  - 支持短暂停顿

## 🚀 快速安装

### 1. 环境要求

- **操作系统**：Windows 10/11（语音命令针对 Windows 优化）
- **Python 版本**：3.7 及以上
- **硬件要求**：支持 16kHz 采样率的麦克风

### 2. 安装依赖

```bash
# 克隆项目（如果是从 Git 获取）
git clone <repository-url>
cd streaming-sensevoice

# 安装 Python 依赖包
pip install -r requirements.txt
```

### 3. 验证安装

```bash
# 测试导入是否成功
python -c "from voice_recognition_app import VoiceRecognitionApp; print('安装成功！')"
```

## 📖 使用说明

### 基础使用

```bash
# 启动语音识别应用
python voice_recognition_app.py
```

启动后程序会：
1. 自动检测可用的麦克风设备
2. 让您选择要使用的麦克风
3. 开始实时语音识别
4. 支持语音命令控制

### 指定麦克风设备

```python
from voice_recognition_app import VoiceRecognitionApp

app = VoiceRecognitionApp()

# 查看可用设备
app.print_available_microphones()

# 使用指定设备
app.run(device_id=0)
```

## 🎯 支持的语音命令

### 应用控制
- **"退出"** / **"关闭"** / **"结束"**：退出应用
- **"停止"** / **"暂停"**：停止语音识别

### 系统操作
- **"刷新"**：刷新当前窗口（F5）
- **"复制"**：复制选中内容（Ctrl+C）
- **"粘贴"**：粘贴剪贴板内容（Ctrl+V）
- **"剪切"**：剪切选中内容（Ctrl+X）
- **"撤销"**：撤销操作（Ctrl+Z）
- **"重做"**：重做操作（Ctrl+Y）
- **"保存"**：保存文件（Ctrl+S）
- **"全选"**：全选内容（Ctrl+A）

### 窗口管理
- **"最小化"**：最小化当前窗口
- **"最大化"**：最大化当前窗口
- **"关闭窗口"**：关闭当前窗口（Alt+F4）
- **"切换窗口"**：切换应用程序（Alt+Tab）

### 应用程序
- **"打开浏览器"**：打开默认浏览器
- **"打开记事本"**：打开 Windows 记事本
- **"打开计算器"**：打开 Windows 计算器
- **"新建标签"**：新建浏览器标签（Ctrl+T）
- **"关闭标签"**：关闭当前标签（Ctrl+W）

### 音量控制
- **"增大音量"** / **"调高音量"**：提高系统音量
- **"减小音量"** / **"调低音量"**：降低系统音量
- **"静音"**：切换静音状态

### 其他操作
- **"截图"** / **"截屏"**：截取屏幕（PrtSc）

## 💻 编程使用

### 基本示例

```python
from voice_recognition_app import VoiceRecognitionApp

# 创建应用实例（带上下文关键词）
contexts = [
    "停止", "开始", "退出", "刷新", "复制", "粘贴", "剪切", 
    "撤销", "重做", "保存", "全选", "最小化", "最大化", 
    "关闭", "切换", "打开", "新建", "截图", "静音"
]
app = VoiceRecognitionApp(contexts=contexts)

# 运行应用
app.run()
```

### 自定义处理

```python
from voice_recognition_app import VoiceRecognitionApp

class MyVoiceApp(VoiceRecognitionApp):
    def on_recognition_result(self, result, is_final=False):
        text = result["text"].strip()
        print(f"识别结果：{text}")
        
        # 自定义处理逻辑
        if "你好" in text:
            print("检测到问候语")
        elif "停止" in text:
            self.stop_recognition()

# 使用自定义应用
app = MyVoiceApp()
app.run()
```

## ⚙️ 配置选项

### 启用/禁用语音命令

```python
# 启用语音命令（默认）
app = VoiceRecognitionApp(enable_commands=True)

# 禁用语音命令（仅语音识别）
app = VoiceRecognitionApp(enable_commands=False)
```

### VAD 参数配置

当前 VAD 使用以下优化参数：
- 激活阈值：0.015（更容易检测到语音）
- 静音填充：800ms（更长的容忍时间）
- 最小语音：200ms（降低最小语音长度要求）
- 最大静音：1500ms（避免过早结束）
- 能量平滑窗口：5（减少误判）


### 语音命令配置

修改`keyboard_shortcust.yaml`文件，在末尾注册新的command，例如：

```
- command: "战斗"
  keys: "ctrlqweoqhweuihon"
  description: "战斗"
```
keys为keyboard库执行的按键顺序

## ❗ 常见问题

### 1. 找不到麦克风设备

**解决方法：**
- 确保麦克风已正确连接
- 检查系统音频设备设置
- 重启应用程序

### 2. 权限错误

**解决方法：**
- 确保应用有麦克风访问权限
- 在 Windows 设置中允许应用访问麦克风
- 必要时以管理员身份运行

### 3. 语音识别不准确

**解决方法：**
- 确保在安静环境中使用
- 说话清晰，语速适中
- 调整麦克风位置和音量
- 检查麦克风质量

### 4. 语音命令不响应

**解决方法：**
- 确保启用了语音命令功能
- 检查目标应用窗口是否处于活动状态
- 某些应用可能有特殊的快捷键处理方式

### 5. 模型加载失败

**解决方法：**
- 检查网络连接（首次运行需要下载模型）
- 确保安装了所有依赖包
- 重新安装依赖：`pip install -r requirements.txt`

## 📞 技术支持

如果遇到问题：
1. 查看控制台输出的错误信息
2. 检查麦克风设备和权限设置
3. 确认依赖包是否正确安装
4. 参考常见问题解决方案

---

**注意**：
1. 本应用的语音命令功能专为 Windows 系统优化，在其他操作系统上可能需要相应修改。
2. 支持长语音输入，不会过早中断，适合各种语音输入场景。
3. 使用改进的 VAD 算法，具有更好的噪声适应能力和语音检测稳定性。 