from pathlib import Path
p=Path(__file__).with_name("patch_v04_gui.py")
rows=p.read_text(encoding="utf-8").splitlines()
for i,line in enumerate(rows):
    if line.startswith("if end not in s:"):
        rows[i] = '# end match intentionally uses except anchor instead'
    if line.startswith("j=s.index(end,i)+len(end)"):
        rows[i] = 'j=s.index("            except Exception as exc:",i)'
p.write_text("\n".join(rows)+"\n",encoding="utf-8")
print("Adjusted patch to use robust worker boundary")
