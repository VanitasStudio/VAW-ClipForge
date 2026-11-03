"""Store Gemini API key encrypted to the current Windows user via DPAPI.

The key is never passed on the command line or written into Python source.
Windows Credential isolation: encryption is tied to the current account.
"""
from __future__ import annotations
import base64
import os
import subprocess
from clipforge.silent_process import run as silent_run, popen as silent_popen
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "VAW-ClipForge"
SECRET_FILE = CONFIG_DIR / "gemini_key.dpapi"

def _powershell(script: str, secret_input: str = "") -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = silent_run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        input=secret_input, capture_output=True, text=True, timeout=25)
    if result.returncode:
        raise RuntimeError("Windows key protection failed. Check user profile/permissions.")
    return result.stdout

def save_key(value: str) -> None:
    value = value.strip()
    if not value or len(value) < 20 or len(value) > 500 or any(c.isspace() for c in value):
        raise ValueError("API key is empty or invalid-looking.")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    script = r"""
$ErrorActionPreference = 'Stop'
$path = Join-Path $env:APPDATA 'VAW-ClipForge\gemini_key.dpapi'
$key = [Console]::In.ReadToEnd().Trim()
$secret = ConvertTo-SecureString -String $key -AsPlainText -Force
$encrypted = ConvertFrom-SecureString -SecureString $secret
[System.IO.File]::WriteAllText($path, $encrypted)
"""
    _powershell(script, value)

def load_key() -> str:
    env = os.getenv("GEMINI_API_KEY", "").strip()
    if env:
        return env
    if not SECRET_FILE.exists():
        raise RuntimeError("Gemini API key not configured. Click 'Set Gemini Key'.")
    script = r"""
$ErrorActionPreference = 'Stop'
$path = Join-Path $env:APPDATA 'VAW-ClipForge\gemini_key.dpapi'
$encrypted = [System.IO.File]::ReadAllText($path)
$secret = ConvertTo-SecureString -String $encrypted
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try { [Console]::Out.Write([Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
"""
    value = _powershell(script).strip()
    if not value:
        raise RuntimeError("Could not retrieve Gemini API key.")
    return value

def has_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip()) or SECRET_FILE.is_file()

def delete_key() -> None:
    SECRET_FILE.unlink(missing_ok=True)
