# Frozen API for v2 releases: grounded engine, ONNX models, no torch/transformers.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / 'backend/app/prompts'), 'backend/app/prompts'), (str(root / 'configs/release/signing-public-key.pem'), 'configs/release')]
datas += collect_data_files('skimage')
for package in ('onnxruntime', 'tokenizers', 'scikit-image', 'scipy', 'pypdfium2', 'pypdf', 'cryptography'):
    datas += copy_metadata(package)
hidden = ['uvicorn.logging', 'uvicorn.loops.asyncio', 'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on',
          'backend.app.services.pdf_worker', 'backend.app.services.pdf_raster_worker', 'aster_library.embed',
          'aster_library.signing', 'aster_library.install', 'skimage.transform', 'pypdfium2_raw']
hidden += collect_submodules('skimage.transform')
a = Analysis([str(root / 'packaging/api_entry.py')], pathex=[str(root)], datas=datas, hiddenimports=hidden,
    excludes=['torch', 'torchvision', 'torchxrayvision', 'transformers', 'sentence_transformers', 'chromadb', 'streamlit',
              'tensorflow', 'jax', 'IPython', 'notebook', 'pytest', 'matplotlib', 'tkinter', 'pandas', 'pyarrow', 'sklearn'],
    binaries=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='aster-api', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='aster-api')
