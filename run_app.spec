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

# Add translations folder
if os.path.exists('core/translations'):
    datas += [('core/translations', 'core/translations')]

# Add config.yaml if exists
if os.path.exists('config.yaml'):
    datas += [('config.yaml', '.')]

# Initialize hiddenimports list early (before ChromaDB collection)
hiddenimports = []

# Add ChromaDB data files and modules
try:
    # Collect ChromaDB data files - including all Python files
    chromadb_datas = collect_data_files('chromadb', include_py_files=True)
    if chromadb_datas:
        datas += chromadb_datas
        print(f"Collected {len(chromadb_datas)} ChromaDB data files")
    
    # Also try to collect submodules and add to hiddenimports
    try:
        chromadb_modules = collect_submodules('chromadb')
        if chromadb_modules:
            # Add collected modules to hiddenimports (will be extended later)
            for module in chromadb_modules:
                if module not in hiddenimports:
                    hiddenimports.append(module)
            print(f"Collected {len(chromadb_modules)} ChromaDB submodules")
    except Exception as e:
        print(f"Warning: Could not collect ChromaDB submodules: {e}")
except Exception as e:
    print(f"Warning: Could not collect ChromaDB files: {e}")

# Add FAISS and sentence-transformers data files
try:
    # Collect sentence-transformers data files (models, etc.)
    try:
        st_datas = collect_data_files('sentence_transformers', include_py_files=True)
        if st_datas:
            datas += st_datas
            print(f"Collected {len(st_datas)} sentence-transformers data files")
    except Exception as e:
        print(f"Warning: Could not collect sentence-transformers files: {e}")
    
    # Collect transformers data files (for sentence-transformers dependencies)
    try:
        transformers_datas = collect_data_files('transformers', include_py_files=True)
        if transformers_datas:
            # Limit to essential files to avoid huge size
            essential_transformers = [d for d in transformers_datas if any(x in d[0] for x in ['tokenization', 'modeling', 'configuration'])]
            if essential_transformers:
                datas += essential_transformers
                print(f"Collected {len(essential_transformers)} transformers data files")
    except Exception as e:
        print(f"Warning: Could not collect transformers files: {e}")
except Exception as e:
    print(f"Warning: Could not collect FAISS/sentence-transformers files: {e}")

# Add ChromaDB binary dependencies if they exist
# Note: Rust components may be in separate packages or loaded dynamically
try:
    import chromadb
    chromadb_path = os.path.dirname(chromadb.__file__)
    print(f"ChromaDB installation path: {chromadb_path}")
    
    # Try to find and include all binary files (DLLs, PYD, SO, etc.)
    binary_count = 0
    for root, dirs, files in os.walk(chromadb_path):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__' and not d.startswith('.')]
        
        for file in files:
            if file.endswith(('.dll', '.so', '.dylib', '.pyd')):
                file_path = os.path.join(root, file)
                # Calculate relative path
                rel_dir = os.path.relpath(root, chromadb_path)
                if rel_dir == '.':
                    dest_path = 'chromadb'
                else:
                    dest_path = f'chromadb/{rel_dir}'
                datas.append((file_path, dest_path))
                binary_count += 1
                print(f"Found ChromaDB binary: {file} -> {dest_path}")
    
    if binary_count == 0:
        print("Warning: No ChromaDB binary files found. Rust components may not be included.")
        print("This is expected if ChromaDB uses dynamically loaded extensions.")
        
except Exception as e:
    print(f"Warning: Could not collect ChromaDB binaries: {e}")

# Add hidden imports (hiddenimports already initialized above)
hiddenimports.extend([
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
    # ChromaDB imports
    # Note: chromadb.api.rust is a native Rust module, not a Python module
    # It may not be importable directly, but ChromaDB will try to load it dynamically
    'chromadb',
    'chromadb.config',
    'chromadb.api',
    'chromadb.api.types',
    'chromadb.api.models',
    'chromadb.api.segment',
    'chromadb.api.segment.impl',
    'chromadb.api.segment.impl.manager',
    'chromadb.api.segment.impl.manager.local',
    'chromadb.api.segment.impl.metadata',
    'chromadb.api.segment.impl.metadata.sqlite',
    'chromadb.db',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.migrations',
    'chromadb.migrations.embeddings_queue',
    'chromadb.execution',
    'chromadb.execution.executor',
    'chromadb.execution.executor.local',
    'chromadb.quota',
    'chromadb.quota.simple_quota_enforcer',
    'chromadb.rate_limit',
    'chromadb.rate_limit.simple_rate_limit',
    'chromadb.utils',
    'chromadb.utils.embedding_functions',
    'chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2',
    'chromadb.telemetry',
    'chromadb.telemetry.posthog',
    'chromadb.auth',
    'chromadb.base_types',
    'chromadb.errors',
    'chromadb.serde',
    'chromadb.types',
    'chromadb.logging',
    # ChromaDB dependencies
    'onnxruntime',
    'tokenizers',
    'numpy',
    'yaml',
    'aiofiles',
    'jinja2',
    'pydantic',
    'dotenv',
    'core.ai_providers',
    'core.logic',
    'core.logger',
    'core.i18n',
    'core.monitoring',
    'core.config',
    'core.validation',
    'core.port_manager',
    'core.cache',
    'conferences.rada',
    'vector_db.client',
    'vector_db.faiss_client',
    # FAISS dependencies
    'faiss',
    'sentence_transformers',
    'sentence_transformers.models',
    'sentence_transformers.util',
    'sentence_transformers.readers',
    'sentence_transformers.datasets',
    'torch',
    'transformers',
    'transformers.models',
    'transformers.tokenization_utils',
    'transformers.modeling_utils',
    'transformers.configuration_utils',
    'huggingface_hub',
    'numpy',
    'scipy',
    'scikit-learn',
])

# Try to collect ChromaDB binaries separately (for binaries section)
# Note: Many ChromaDB binaries are already included via datas above
binaries = []
try:
    import chromadb
    chromadb_path = os.path.dirname(chromadb.__file__)
    
    # Look for Rust extension modules and other critical binaries
    for root, dirs, files in os.walk(chromadb_path):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            # Look for Rust-related binaries
            if 'rust' in file.lower() and file.endswith(('.pyd', '.so', '.dll', '.dylib')):
                file_path = os.path.join(root, file)
                binaries.append((file_path, '.'))
                print(f"Found ChromaDB Rust binary: {file}")
except Exception as e:
    print(f"Warning: Could not collect ChromaDB binaries for binaries section: {e}")

a = Analysis(
    ['run_app_exe.py'],  # Use run_app_exe.py instead of run_app.py
    pathex=[],
    binaries=binaries,
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
    icon='static/favicon.ico',  # Application icon for EXE file
)

# Optimize build
# Remove unnecessary files to reduce size
# Note: UPX compression is enabled above, which helps reduce exe size
# For further optimization, consider:
# - Using --onefile mode (already used)
# - Excluding unused modules
# - Using --strip option (already enabled via strip=False, but can be enabled if needed)