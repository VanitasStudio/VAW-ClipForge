from pathlib import Path
p=Path(__file__).with_name("patch_v04_gui.py")
rows=p.read_text(encoding="utf-8").splitlines()
rows=[("# already patched or safe to patch again" if
       (line.startswith("if sig not in s:") or line.startswith("if needle not in s:raise ValueError(\"Gemini render"))
       else line) for line in rows]
p.write_text("\n".join(rows)+"\n",encoding="utf-8")
print("Patch idempotence fixed")
