# PyInstaller spec for the Sigma macOS app.
#
# Build with: make app
#
# The excludes below matter. PyInstaller walks whatever is importable in the
# active environment, and without them a development machine drags numpy,
# IPython, Jupyter and matplotlib into the bundle — hundreds of megabytes the
# app never touches.

import sys
from pathlib import Path

sys.setrecursionlimit(5000)

PROJECT = Path(SPECPATH)
STATIC = PROJECT / "src" / "sigma" / "web" / "static"
ICON = PROJECT / "build" / "logo.icns"

EXCLUDES = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "IPython",
    "jupyter",
    "jupyter_client",
    "jupyter_core",
    "notebook",
    "ipykernel",
    "jedi",
    "zmq",
    "tornado",
    "pytest",
    "_pytest",
    "setuptools",
    "pip",
    "PIL",
    "tkinter",
    "test",
    "unittest",
]

analysis = Analysis(
    [str(PROJECT / "src" / "sigma" / "main.py")],
    pathex=[str(PROJECT / "src")],
    binaries=[],
    datas=[(str(STATIC), "sigma/web/static")],
    hiddenimports=["uvicorn.logging", "uvicorn.protocols", "uvicorn.lifespan"],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Sigma",
    console=False,
    strip=False,
    upx=False,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Sigma",
)

app = BUNDLE(
    collection,
    name="Sigma.app",
    icon=str(ICON) if ICON.exists() else None,
    bundle_identifier="com.fzunigam.sigma",
    info_plist={
        "CFBundleName": "Sigma",
        "CFBundleDisplayName": "Sigma",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.finance",
        "NSHumanReadableCopyright": "MIT",
    },
)
