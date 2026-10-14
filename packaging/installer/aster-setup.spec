import os
import sys
from pathlib import Path

root = Path(SPECPATH).parents[1]
sys.path.insert(0, str(root))
from aster_release.build_support import check_bootstrap_rights
check_bootstrap_rights(root)
trust = Path(os.environ['ASTER_BUILD_TRUST_FILE']).resolve()
if not trust.is_file():
    raise ValueError('Generate authenticated distribution metadata first')
a = Analysis([str(root/'packaging/installer/bootstrap.py')], pathex=[str(root)], datas=[(str(trust), '.')], binaries=[],
    hiddenimports=['tkinter'], excludes=['torch','transformers','sentence_transformers','streamlit'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='AsterSetup-Windows-x64', console=False)
