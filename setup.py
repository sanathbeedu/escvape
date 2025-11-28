from setuptools import setup

APP = ["run_app.py"]
DATA_FILES = [
    "models",
    "web_frontend.html",
    "manifest.json",
]
OPTIONS = {
    "argv_emulation": True,
    "packages": [
        "fastapi",
        "uvicorn",
        "starlette",
        "anyio",
        "sniffio",
        "PIL",
        "numpy",
        "requests",
        "psutil",
        "charset_normalizer",
    ],
    # Ensure AnyIO's asyncio backend is included for FastAPI/Uvicorn
    "includes": [
        "anyio._backends._asyncio",
    ],
    # Do not bundle build tooling packages; they are not needed at runtime
    # and can cause duplicate dist-info errors during collection.
    "excludes": [
        "wheel",
        "pip",
        "setuptools",
        "PyInstaller",
    ],
    "plist": {
        "CFBundleName": "EscVapeDetector",
        "CFBundleDisplayName": "EscVapeDetector",
        "CFBundleIdentifier": "com.escvape.detector",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
