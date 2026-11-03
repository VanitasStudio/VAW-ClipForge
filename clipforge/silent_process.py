"""Run Windows command-line tools without opening visible terminal windows.

This module is used by ClipForge production subprocesses (FFmpeg, PowerShell,
background UI launch). No shell=True, no hidden process left running unexpectedly.
Works as ordinary subprocess calls on non-Windows platforms.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any

def _no_window(kwargs:dict[str,Any]) -> dict[str,Any]:
    options=dict(kwargs)
    if os.name!="nt":
        return options
    options["creationflags"]=int(options.get("creationflags",0)) | getattr(subprocess,"CREATE_NO_WINDOW",0x08000000)
    current=options.get("startupinfo")
    if current is None:
        current=subprocess.STARTUPINFO()
    current.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    current.wShowWindow=subprocess.SW_HIDE
    options["startupinfo"]=current
    return options

def run(*args,**kwargs):
    return subprocess.run(*args,**_no_window(kwargs))

def popen(*args,**kwargs):
    return subprocess.Popen(*args,**_no_window(kwargs))

def verify_hidden_flags():
    """Return the effective Windows startup options without starting any child."""
    result=_no_window({})
    return {
        "os":os.name,
        "creationflags":result.get("creationflags",0),
        "showwindow":getattr(result.get("startupinfo"),"wShowWindow",None),
        "uses_show_window":bool(getattr(result.get("startupinfo"),"dwFlags",0) & getattr(subprocess,"STARTF_USESHOWWINDOW",1)),
    }
