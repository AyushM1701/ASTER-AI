from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis([str(root / 'packaging/launcher.py')], pathex=[str(root)], hiddenimports=['tkinter'],
    excludes=['torch','transformers','sentence_transformers','streamlit','pydantic','pydantic_settings','numpy','PIL','uvicorn','fastapi','httpx','scipy','sklearn'], datas=[], binaries=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Aster', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='Aster')
