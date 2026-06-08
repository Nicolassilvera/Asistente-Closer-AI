# jarvis.spec — PyInstaller spec para Jarvis CRM
import os, sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

datas = [('src', 'src')]
if os.path.exists('ui/dist'):
    datas.append(('ui/dist', 'ui/dist'))

# Recolectar numpy, pygame y speech_recognition con todos sus binarios y datos
binaries  = []
hiddenimports_extra = []
for pkg in ['numpy', 'pygame', 'speech_recognition', 'pyaudio']:
    d, b, h = collect_all(pkg)
    datas    += d
    binaries += b
    hiddenimports_extra += h

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports_extra + [
        # FastAPI / Uvicorn
        'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
        'uvicorn.lifespan.off', 'uvicorn.lifespan.on',
        'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'fastapi', 'fastapi.staticfiles', 'fastapi.responses',
        'fastapi.middleware.cors',
        'pydantic', 'pydantic.v1',
        'starlette', 'starlette.staticfiles', 'starlette.routing',
        'starlette.middleware', 'starlette.middleware.cors',
        # HTTP / WebSocket
        'h11', 'websockets', 'anyio', 'anyio._backends._asyncio',
        'sniffio',
        # IA / scraping
        'groq', 'bs4',
        # DB
        'sqlite3', '_sqlite3',
        # Voz
        'edge_tts', 'aiohttp',
        # Utilidades
        'dotenv', 'rich', 'rich.console', 'rich.table', 'rich.prompt',
        'multiprocessing.pool', 'email.mime.text',
        # App modules
        'src.api.main', 'src.core.config', 'src.core.database',
        'src.core.repositories', 'src.core.logger', 'src.core.exceptions',
        'src.core.orchestrator', 'src.core.gpt_engine',
        'src.modules.whatsapp_monitor',
    ],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'pandas',
        'PIL', 'cv2', 'pytest', 'IPython', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JarvisCRM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JarvisCRM',
)
