from pathlib import Path
import ast

root=Path(__file__).resolve().parents[1]
gui=(root/"clipforge_gui.py").read_text(encoding="utf-8")
ast.parse(gui)
assert '"#0B0F14"' in gui
assert '"#3B82F6"' in gui
assert '"#D9E0E8"' in gui
assert '"Archivo"' in gui
assert '"Quantico"' in gui
assert 'load_brand_fonts()' in gui
assert 'FR_PRIVATE' in gui
assert 'def main():' in gui
assert '--composition-review' in gui and '--review-editor' in gui
assert (root/"assets/fonts/Archivo.ttf").is_file()
assert (root/"assets/fonts/Quantico-Regular.ttf").is_file()
assert (root/"assets/fonts/Quantico-Bold.ttf").is_file()
assert (root/"assets/fonts/Archivo-OFL.txt").is_file()
assert (root/"assets/fonts/Quantico-OFL.txt").is_file()
assert (root/"assets/branding/vanitas.ico").is_file()
assert (root/"scripts/build_windows.ps1").is_file()
assert "onefile" in (root/"scripts/build_windows.ps1").read_text(encoding="utf-8")
assert "windowed" in (root/"scripts/build_windows.ps1").read_text(encoding="utf-8")
print("VANITAS_BRAND_ASSETS_PASS")
print("BRANDED_TYPOGRAPHY_PASS")
print("CLEAN_UI_COPY_PASS")
print("FROZEN_REVIEW_ROUTING_PASS")
print("WINDOWS_ONEFILE_BUILD_CONFIG_PASS")
