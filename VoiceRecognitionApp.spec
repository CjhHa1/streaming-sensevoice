# -*- mode: python ; coding: utf-8 -*-
"""
语音识别应用的PyInstaller spec文件
修复funasr的inspect兼容性问题
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 应用基本信息
app_name = 'VoiceRecognitionApp'
main_script = 'voice_recognition_app.py'

# 收集数据文件
datas = []

# 添加streaming_sensevoice模块的所有文件
try:
    datas += [('streaming_sensevoice', 'streaming_sensevoice')]
except:
    pass

# 尝试收集其他数据文件
try:
    datas += collect_data_files('funasr')
except:
    pass

try:
    datas += collect_data_files('modelscope')
except:
    pass

# 收集隐藏导入
hiddenimports = [
    # 基础依赖
    'numpy',
    'torch',
    'torchaudio',
    'sounddevice',
    'soundfile',
    'inspect',
    
    # 语音识别相关
    'asr_decoder',
    'funasr',
    'online_fbank',
    'modelscope',
    'transformers',
    
    # 可选依赖
    'onnx',
    'onnxruntime',
    'librosa',
    'scipy',
    'sklearn',
    'requests',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    
    # PyTorch相关
    'torch.nn',
    'torch.nn.functional',
    'torch.optim',
    'torch.utils',
    'torch.utils.data',
    
    # FunASR相关（尝试包含但不强制）
    'funasr.register',
    'funasr.models',
    'funasr.frontends',
    'funasr.utils',
    
    # 其他可能需要的模块
    'pkg_resources.py2_warn',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
]

# 尝试收集子模块
try:
    hiddenimports += collect_submodules('streaming_sensevoice')
except:
    pass

try:
    hiddenimports += collect_submodules('funasr', filter=lambda name: 'test' not in name)
except:
    pass

# 排除的模块
excludes = [
    'tkinter',
    'matplotlib.backends._backend_pdf',
    'matplotlib.backends._backend_ps',  
    'matplotlib.backends._backend_svg',
    'IPython',
    'notebook',
    'jupyter',
    'pytest',
    'scipy.spatial.distance._hausdorff',
    # 排除所有有问题的包
    'pysilero',
    'audiolab',
    'bv',
    'av',
    'webrtcvad',
    # 排除一些可能有问题的测试模块
    'funasr.test',
    'funasr.tests',
]

# 分析阶段
a = Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 去重
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 生成可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 不使用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以在这里指定图标路径
) 