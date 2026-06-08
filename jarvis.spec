# jarvis.spec — PyInstaller spec para Jarvis CRM
import os, sys

block_cipher = None

# Incluir ui/dist solo si fue buildeado
datas = [('src', 'src')]
if os.path.exists('ui/dist'):
    datas.append(('ui/dist', 'ui/dist'))
if os.path.exists('.env'):
    datas.append(('.env', '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
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
        'groq', 'bs4', 'beautifulsoup4',
        # DB
        'sqlite3', '_sqlite3',
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
        'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
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
    console=True,   # True = ventana de consola (para ver logs); cambiar a False para modo silencioso
    icon=None,      # Reemplazar con 'icon.ico' si tenés un ícono
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
