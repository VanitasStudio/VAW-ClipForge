from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ("clipforge/clipforge_gui.py", "clipforge/review_editor.py", "clipforge/composition_review.py")
for name in ACTIVE:
    source = (ROOT / name).read_text(encoding="utf-8")
    ast.parse(source)
    assert "ttk.Combobox(" not in source, f"Native combobox remains in {name}"
    assert "from clipforge.vanitas_widgets import" in source and "VanitasCombo" in source
    assert "tk.Scrollbar(" not in source, f"Native scrollbar remains in {name}"
    assert "tk.Spinbox(" not in source, f"Native spinbox remains in {name}"
    assert "tk.Checkbutton(" not in source, f"Native checkbox remains in {name}"
    assert "tk.Scale(" not in source, f"Native slider remains in {name}"
    assert "VanitasButton" in source
    if name == "clipforge/review_editor.py":
        assert "VanitasSlider" in source
    if name != "clipforge/composition_review.py":
        assert "VanitasScrollbar" in source
widgets = (ROOT / "clipforge/vanitas_widgets.py").read_text(encoding="utf-8")
ast.parse(widgets)
for token in ("#05070B", "#101827", "#0B111C", "#075BFF", "Archivo", "<<ComboboxSelected>>"):
    assert token in widgets, token
review = (ROOT / "clipforge/review_editor.py").read_text(encoding="utf-8")
assert '"#DCE6F5"' in review and '"Archivo"' in review
composition = (ROOT / "clipforge/composition_review.py").read_text(encoding="utf-8")
assert "#05070B" in composition and "#075BFF" in composition
build = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
assert '"--hidden-import", "clipforge.vanitas_widgets"' in build
assert "winfo_vrootx" in widgets and "{x:+d}{y:+d}" in widgets
assert "listing.selection_set(index)" in widgets
assert "width = 18 if orient == \"vertical\"" in widgets
for token in ("#05070B", "#101827", "#DCE6F5", "#075BFF", "#20BFFF"):
    assert token in widgets, token
assert "#FF8746" not in widgets
print("VANITAS_CUSTOM_CONTROLS_PASS")
print("VANITAS_REVIEW_STUDIO_THEME_PASS")
print("NO_NATIVE_COMBOBOX_PASS")
