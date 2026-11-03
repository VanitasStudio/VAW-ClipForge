# Vanitas Studio UI identity

## Brand direction
Dark, premium, precise and editorial. Keep the interface calm and highly legible.
Use geometric forms, sharp cuts, negative space and restrained accent color.
Avoid excessive neon, glow, glassmorphism, blur panels and arcade styling.

## Typography
- Archivo: all functional UI, labels, controls, descriptions and readouts.
- Quantico: product wordmark and selected brand display elements only.

## Core palette
- Base: #0B0F14
- Surface: #111820
- Elevated surface: #1D2A38
- Platinum: #D9E0E8
- Muted text: #8793A3
- Vanitas Blue: #3B82F6
- Orange accent: #F97316 (restrained use)
- Dividers: #263342

## UI principles
- Clear hierarchy; remove redundant explanatory paragraphs.
- Functional labels over verbose descriptions.
- Strong spacing, consistent alignment and compact controls.
- No decorative glow or glassmorphism.
- Use brand mark as a geometric V/prism signature, not as decoration on every control.

## Windows packaging
The supported end-user entry point is dist/VAW-ClipForge.exe.
The Python source tree and .cmd scripts are development/maintenance artifacts.

## Branded controls (v1.2.1)
- All application dropdowns use the custom VanitasCombo control, not native ttk combobox chrome.
- Dropdown popups, selection states and focus borders use the Vanitas palette and Archivo typography.
- Main workspace and Review Studio scrollbars use branded colors.
- Review Studio and Composition Review share the same dark palette and functional typography.
- UI source files are UTF-8; user-facing labels use plain, intentional punctuation to avoid mojibake.
