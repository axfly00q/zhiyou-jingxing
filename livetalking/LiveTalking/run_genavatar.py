"""Wrapper for genavatar.py — sets PYTHONPATH so `from avatars.wav2lip import face_detection` works."""
import os
import sys

# 把 LiveTalking 根目录加入 sys.path，使包导入正常
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 切换工作目录，因为 genavatar.py 内部用相对路径 ./data/avatars/...
os.chdir(_HERE)

# 直接执行原脚本
script = os.path.join(_HERE, 'avatars', 'wav2lip', 'genavatar.py')
with open(script, 'r', encoding='utf-8') as f:
    code = f.read()
exec(compile(code, script, 'exec'), {'__name__': '__main__', '__file__': script})
