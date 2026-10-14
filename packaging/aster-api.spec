from pathlib import Path
from importlib.util import find_spec
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root/'backend/app/prompts'), 'backend/app/prompts')]
for package in ['sentence_transformers', 'transformers']:
    datas += collect_data_files(package)
    datas += copy_metadata(package, recursive=True)
a = Analysis([str(root/'packaging/api_entry.py')], pathex=[str(root)], datas=datas,
    hiddenimports=['uvicorn.logging','uvicorn.loops.asyncio','uvicorn.protocols.http.h11_impl','uvicorn.lifespan.on', 'sklearn.utils._cython_blas'],
    excludes=['streamlit','chromadb','torchxrayvision','tensorflow','jax','IPython','notebook','pytest','matplotlib','tkinter','pandas','pyarrow'], binaries=[])
# Torchvision 0.29 uses _C_stable/image_stable loaded by file path. The
# pinned PyInstaller hook only searches the older _C/image names.
vision_root = Path(find_spec('torchvision').origin).parent
a.binaries += [('torchvision/' + path.name, str(path), 'BINARY')
               for path in sorted(vision_root.iterdir()) if path.suffix in {'.pyd', '.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='aster-api', console=True)
coll = COLLECT(exe, a.binaries, a.datas, name='aster-api')
