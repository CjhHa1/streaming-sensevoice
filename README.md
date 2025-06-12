# Voice Recognition App

Real-time voice recognition application based on StreamingSenseVoice with voice command support.

## Features

- **Real-time Speech Recognition**: Streaming voice recognition with VAD
- **Voice Commands**: Control system operations through voice
- **Multiple Microphones**: Auto-detect and select audio devices
- **Customizable**: Support custom contexts and callbacks

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python voice_recognition_app.py
```

## Voice Commands
Commands are managed by config file: `keyboard_shortcuts.yaml`
### System Control
- **退出/关闭**: Exit application
- **刷新**: Refresh (F5)
- **复制/粘贴**: Copy/Paste (Ctrl+C/V)
- **保存**: Save (Ctrl+S)
- **撤销/重做**: Undo/Redo (Ctrl+Z/Y)

### Window Operations
- **最小化/最大化**: Minimize/Maximize window
- **切换窗口**: Switch windows (Alt+Tab)
- **关闭窗口**: Close window (Alt+F4)

### Applications
- **打开浏览器**: Open browser
- **打开记事本**: Open Notepad
- **打开计算器**: Open Calculator
- **新建标签**: New tab (Ctrl+T)

### Audio Control
- **增大音量/减小音量**: Volume up/down
- **静音**: Mute toggle
- **截图**: Screenshot (PrtSc)

## Customized Commands
If you prefer add some self-defined commands(with Keyboard ShortCuts), please add your short cut in file `keyboard_shortcuts.yaml`, like:
```
# 添加打开任务管理器
- command: "打开任务管理器"
  keys: "ctrl+shift+esc"
  description: "打开Windows任务管理器"
```


## Usage Examples

### Basic Usage
```python
from voice_recognition_app import VoiceRecognitionApp

# Create and run app
app = VoiceRecognitionApp(contexts=["停止", "开始"])
app.run()
```

### Custom Commands
```python
class CustomApp(VoiceRecognitionApp):
    def on_recognition_result(self, result):
        text = result["text"].strip()
        if "停止" in text:
            self.stop_recognition()
        print(f"Result: {text}")

app = CustomApp()
app.run()
```

### Device Selection
```python
app = VoiceRecognitionApp()
app.print_available_microphones()  # List devices
app.run(device_id=0)              # Use specific device
```

## API Reference

### VoiceRecognitionApp Class

| Method | Description |
|--------|-------------|
| `get_microphone_devices()` | Get available microphone devices |
| `start_service(device_id=None)` | Start voice recognition service |
| `start_recognition()` | Begin voice recognition |
| `stop_recognition()` | Stop voice recognition |
| `run(device_id=None)` | Run main application loop |

### Configuration

```python
# Enable/disable voice commands
app = VoiceRecognitionApp(enable_commands=True)  # Default

# Custom context keywords
contexts = ["停止", "开始", "退出", "刷新", "复制"]
app = VoiceRecognitionApp(contexts=contexts)
```

## System Requirements

- **OS**: Windows 10/11 (voice commands optimized for Windows)
- **Python**: 3.7+
- **Audio**: 16kHz sample rate microphone

## Troubleshooting

### Common Issues

1. **No microphone detected**
   ```bash
   python voice_recognition_app.py --list-devices
   ```

2. **Permission errors**
   - Ensure microphone access permissions
   - Run as administrator if needed

3. **Command recognition issues**
   - Use clear speech in quiet environment
   - Check microphone quality and position

4. **Model loading failures**
   - Check internet connection (model download)
   - Verify all dependencies installed

### Debug Output
- `🗣️ 识别结果`: Speech recognition text
- `🎯 识别到命令`: Matched command
- `🔧 执行命令`: Executing command

## Building Executable

```bash
# Build with PyInstaller
pyinstaller VoiceRecognitionApp.spec
```

## Development

### Adding Custom Commands

```python
# Extend CommandProcessor class
class CustomProcessor(CommandProcessor):
    def __init__(self, app_instance):
        super().__init__(app_instance)
        self.commands["新命令"] = self.custom_command
    
    def custom_command(self):
        print("Executing custom command")
        return True
```

### Adding Synonyms

```python
# In CommandProcessor.__init__
self.synonyms["别名"] = "原命令"
```

---

**Note**: Voice commands are optimized for Windows systems. Other operating systems may require modifications.
