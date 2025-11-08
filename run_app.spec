# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Local Brain

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Add resource folders (directly, not as packages)
datas = []
# Add templates folder
if os.path.exists('templates'):
    datas += [('templates', 'templates')]
# Add static folder
if os.path.exists('static'):
    datas += [('static', 'static')]
# Add prompts folder
if os.path.exists('prompts'):
    datas += [('prompts', 'prompts')]
# Add archetypes.yaml as backup (if not next to exe)
# Note: file can also be next to exe for editing
if os.path.exists('archetypes.yaml'):
    datas += [('archetypes.yaml', '.')]

# Add hidden imports
hiddenimports = [
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.logging',
    'google.generativeai',
    'openai',
    'chromadb',
    'chromadb.config',
    'yaml',
    'aiofiles',
    'jinja2',
    'pydantic',
    'dotenv',
    'core.ai_providers',
    'core.logic',
    'conferences.rada',
    'vector_db.client',
]

a = Analysis(
    ['run_app_exe.py'],  # Use run_app_exe.py instead of run_app.py
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LocalBrain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compression (can be disabled if issues occur)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging (can be changed to False)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Can add icon: icon='static/favicon.ico'
)