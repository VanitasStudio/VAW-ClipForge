from pathlib import Path
import tkinter as tk
import unittest

from vanitas_widgets import (
    VanitasCombo, VanitasScrollbar, VanitasSlider, VanitasSpinbox,
    VanitasCheckbutton, VanitasEntry, VanitasButton,
)


class VanitasControlsRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.geometry("640x420+40+40")
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except tk.TclError:
            pass

    def tearDown(self):
        for child in self.root.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass
        self.root.update()

    def test_combo_opens_from_arrow_and_selects_option(self):
        value = tk.StringVar(value="Local File")
        combo = VanitasCombo(
            self.root, textvariable=value, state="readonly",
            values=["Local File", "Video URL"], width=20,
        )
        combo.pack()
        self.root.update()
        combo._arrow.event_generate("<Button-1>")
        self.root.update()
        self.assertIsNotNone(combo._popup)
        self.assertEqual(combo._listbox.size(), 2)
        self.assertGreater(combo._popup.winfo_rootx(), -100000)
        self.assertGreater(combo._popup.winfo_rooty(), -100000)
        combo._listbox.event_generate("<ButtonPress-1>",x=12,y=45)
        combo._listbox.event_generate("<ButtonRelease-1>",x=12,y=45)
        self.root.update()
        self.assertEqual(value.get(), "Video URL")
        self.assertIsNone(combo._popup)

    def test_combo_dismisses_when_clicking_outside(self):
        combo = VanitasCombo(self.root, values=["A", "B"], state="readonly")
        combo.pack()
        outside = tk.Button(self.root, text="Outside")
        outside.pack()
        self.root.update()
        combo._open()
        self.root.update()
        self.assertIsNotNone(combo._popup)
        self.assertFalse(bool(combo._popup.grab_current()))
        outside.event_generate("<Button-1>")
        self.root.update()
        self.assertIsNone(combo._popup)
        self.assertIsNone(combo._listbox)

    def test_combo_keyboard_open_and_selection_event(self):
        value = tk.StringVar(value="A")
        combo = VanitasCombo(self.root, textvariable=value, values=["A", "B"])
        combo.pack()
        events = []
        combo.bind("<<ComboboxSelected>>", lambda _e: events.append(value.get()))
        self.root.update()
        combo.focus_force()
        self.root.update()
        combo.event_generate("<KeyPress-Down>")
        self.root.update()
        self.assertIsNotNone(combo._popup)
        combo._listbox.selection_clear(0, "end")
        combo._listbox.selection_set(1)
        combo._choose()
        self.root.update()
        self.assertEqual(events, ["B"])

    def test_scrollbar_canvas_draw_and_set(self):
        calls = []
        bar = VanitasScrollbar(self.root, command=lambda *args: calls.append(args))
        bar.pack(fill="y")
        self.root.update()
        bar.set(0.25, 0.5)
        self.root.update()
        self.assertGreaterEqual(len(bar.find_all()), 1)
        self.assertEqual((bar.first, bar.last), (0.25, 0.5))
        bar._moveto(0.75)
        self.assertEqual(calls[-1], ("moveto", 0.75))

    def test_slider_drag_updates_variable_and_callback(self):
        value = tk.DoubleVar(value=0)
        changed = []
        slider = VanitasSlider(self.root, variable=value, from_=0, to=100,
                               command=lambda current: changed.append(float(current)),
                               length=220)
        slider.pack()
        self.root.update()
        slider.event_generate("<Button-1>",x=205,y=18)
        self.root.update()
        self.assertGreater(value.get(), 90)
        self.assertTrue(changed)
        slider.configure(to=200)
        self.assertEqual(slider.maximum, 200)

    def test_spinbox_steps_and_clamps(self):
        value = tk.IntVar(value=4)
        spin = VanitasSpinbox(self.root, from_=1, to=5, textvariable=value)
        spin.pack()
        self.root.update()
        self.assertGreaterEqual(spin.winfo_width(), 82)
        spin.step(1)
        self.assertEqual(value.get(), 5)
        spin.step(1)
        self.assertEqual(value.get(), 5)
        value.set(0)
        spin._clamp()
        self.assertEqual(value.get(), 1)

    def test_checkbutton_toggles_shared_variable(self):
        value = tk.BooleanVar(value=False)
        check = VanitasCheckbutton(self.root, text="Enable", variable=value)
        check.pack()
        self.root.update()
        check.event_generate("<Button-1>")
        self.root.update()
        self.assertTrue(value.get())

    def test_rounded_button_invokes_and_supports_state_updates(self):
        calls = []
        button = VanitasButton(self.root, text="Run", command=lambda: calls.append("run"), primary=True)
        button.pack()
        self.root.update()
        button.event_generate("<ButtonPress-1>",x=12,y=12)
        button.event_generate("<ButtonRelease-1>",x=12,y=12)
        self.root.update()
        self.assertEqual(calls, ["run"])
        button.configure(text="Working", state="disabled")
        self.assertEqual(button.cget("text"), "Working")
        button.invoke()
        self.assertEqual(calls, ["run"])

    def test_rounded_surfaces_use_smooth_canvas_primitives(self):
        from vanitas_widgets import _rounded_rect
        canvas = tk.Canvas(self.root, width=120, height=40)
        canvas.pack()
        _rounded_rect(canvas, 1, 1, 119, 39, 9, fill="#075BFF", outline="#20BFFF")
        self.root.update()
        kinds = [canvas.type(item) for item in canvas.find_all()]
        self.assertIn("oval", kinds)
        self.assertIn("arc", kinds)
        self.assertNotIn("polygon", kinds)

    def test_all_controls_are_tk_native_custom_classes(self):
        self.assertTrue(issubclass(VanitasEntry, tk.Entry))
        self.assertTrue(issubclass(VanitasButton, tk.Canvas))
        self.assertTrue(issubclass(VanitasScrollbar, tk.Canvas))


if __name__ == "__main__":
    unittest.main()
