from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ("clipforge_gui.py", "review_editor.py", "composition_review.py")
for name in ACTIVE:
    source = (ROOT / name).read_text(encoding="utf-8")
    ast.parse(source)
    assert "ttk.Combobox(" not in source, f"Native combobox remains in {name}"
    assert "from vanitas_widgets import" in source and "VanitasCombo" in source
    assert "tk.Scrollbar(" not in source, f"Native scrollbar remains in {name}"
    assert "tk.Spinbox(" not in source, f"Native spinbox remains in {name}"
    assert "tk.Checkbutton(" not in source, f"Native checkbox remains in {name}"
    assert "tk.Scale(" not in source, f"Native slider remains in {name}"
    assert "VanitasButton" in source
    if name == "review_editor.py":
        assert "VanitasSlider" in source
    if name != "composition_review.py":
        assert "VanitasScrollbar" in source
widgets = (ROOT / "vanitas_widgets.py").read_text(encoding="utf-8")
ast.parse(widgets)
for token in ("#0B0F14", "#111820", "#18222D", "#3B82F6", "Archivo", "<<ComboboxSelected>>"):
    assert token in widgets, token
review = (ROOT / "review_editor.py").read_text(encoding="utf-8")
assert '"#D9E0E8"' in review and '"Archivo"' in review
composition = (ROOT / "composition_review.py").read_text(encoding="utf-8")
assert "#0B0F14" in composition and "#3B82F6" in composition
build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
assert '"--hidden-import", "vanitas_widgets"' in build
print("VANITAS_CUSTOM_CONTROLS_PASS")
print("VANITAS_REVIEW_STUDIO_THEME_PASS")
print("NO_NATIVE_COMBOBOX_PASS")
