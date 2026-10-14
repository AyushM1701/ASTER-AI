from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis([str(root/'packaging/web_entry.py')], pathex=[str(root)], datas=[], binaries=[],
    hiddenimports=['uvicorn.logging','uvicorn.loops.asyncio','uvicorn.protocols.http.h11_impl','uvicorn.lifespan.on'],
    excludes=['streamlit','torch','transformers','sentence_transformers','numpy','pytest','tkinter'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='aster-web', console=True)
coll = COLLECT(exe, a.binaries, a.datas, name='aster-web')
