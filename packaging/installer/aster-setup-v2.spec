# Single-file AsterSetup-Windows-x64.exe with the release lock compiled in (trust root).
import os
from pathlib import Path

root = Path(SPECPATH).parents[1]
lock = Path(os.environ['ASTER_RELEASE_LOCK']).resolve()
a = Analysis([str(root / 'packaging/installer/setup_app.py')], pathex=[str(root)], datas=[(str(lock), '.'), (str(root / 'configs/release/signing-public-key.pem'), 'configs/release')], binaries=[],
    hiddenimports=['tkinter', 'tkinter.ttk', 'aster_release.setup_engine', 'aster_release.v2', 'aster_library.install',
                   'aster_library.signing'],
    excludes=['torch', 'transformers', 'sentence_transformers', 'streamlit', 'numpy', 'scipy', 'PIL', 'fastapi',
              'uvicorn', 'pydantic', 'onnxruntime'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='AsterSetup-Windows-x64', console=False, icon=None)
