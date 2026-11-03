# Vanitas Studio UI identity

## Brand direction
Dark, premium, precise and editorial. Use the official Vanitas Studio logo as the master identity reference: obsidian surfaces, metallic silver typography and electric cobalt/ionic blue accents. The interface should feel like a polished creative workspace, not a neon gaming HUD.

## Typography
- Archivo: all functional UI, labels, controls, descriptions and readouts.
- Quantico: product wordmark and selected brand display elements only.

## Core palette
- Obsidian: #05070B
- Midnight navy: #101827
- Field surface: #0B111C
- Elevated surface: #172235
- Metallic silver: #DCE6F5
- Muted silver: #8E9DB4
- Electric cobalt: #075BFF
- Ionic blue: #20BFFF
- Dividers: #29364B

Warm orange is a Porto Web-specific theme choice and is not part of the master Vanitas Studio product palette.

## UI principles
- Rounded cards, buttons, controls and popup surfaces with consistent radii.
- Clear hierarchy, strong spacing and compact functional labels.
- Electric blue for primary actions, focus, selected states and restrained highlights.
- Metallic silver for text, iconography and secondary controls.
- Dark scrollbar track with a smooth rounded slate thumb; blue hover/drag feedback.
- Avoid geometric-cut/chamfered controls, warm-orange accents, excessive glow and glassmorphism.
- Keep any blue glow subtle and limited to focused/active emphasis.

## Windows packaging
The supported end-user entry point is dist/VAW-ClipForge.exe.
The Python source tree and .cmd scripts are development/maintenance artifacts.

## Branded controls
- Application dropdowns use VanitasCombo rather than native ttk combobox chrome.
- Dropdown popups use signed virtual-desktop coordinates, including negative monitor origins, and custom pointer/keyboard selection.
- Custom scrollbars, buttons, numeric steppers, checkboxes and Review Studio sliders share the logo-derived palette.
- Review Studio and Composition Review use the same dark/silver/electric-blue system.
- UI source files are UTF-8; user-facing labels use intentional punctuation to avoid mojibake.
