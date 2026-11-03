"""Vanitas Studio native-feeling custom Tk controls for ClipForge."""
from __future__ import annotations
import tkinter as tk

PALETTE = {
    "bg": "#0B0F14", "surface": "#111820", "field": "#18222D",
    "raised": "#1D2A38", "hover": "#26384C", "line": "#263342",
    "text": "#D9E0E8", "muted": "#8793A3", "blue": "#3B82F6",
}

class VanitasCombo(tk.Frame):
    """Custom branded combobox; avoids platform-native ttk/Chrome-like chrome."""
    def __init__(self, master, *, textvariable=None, state="readonly",
                 values=(), width=18, font=("Archivo", 10), **kwargs):
        bg = kwargs.pop("background", kwargs.pop("bg", PALETTE["surface"]))
        super().__init__(master, bg=bg, highlightthickness=1,
                         highlightbackground=PALETTE["line"],
                         highlightcolor=PALETTE["blue"], bd=0, takefocus=0)
        self.variable = textvariable or tk.StringVar(master=self)
        self.state = state
        self.values = list(values)
        self.font = font
        self._popup = None
        self._entry = tk.Entry(
            self, textvariable=self.variable, relief="flat", bd=0,
            bg=PALETTE["field"], fg=PALETTE["text"],
            insertbackground=PALETTE["text"], selectbackground=PALETTE["blue"],
            selectforeground="#FFFFFF", font=font,
            readonlybackground=PALETTE["field"],
            disabledbackground=PALETTE["surface"],
            disabledforeground=PALETTE["muted"],
        )
        self._entry.pack(side="left", fill="both", expand=True, padx=(9, 2), pady=6)
        self._arrow = tk.Label(
            self, text="⌄", width=3, bg=PALETTE["raised"],
            fg=PALETTE["muted"], font=("Archivo", 12, "bold"), cursor="hand2"
        )
        self._arrow.pack(side="right", fill="y", padx=1, pady=1)
        self._arrow.bind("<Button-1>", self._toggle)
        self._entry.bind("<Button-1>", self._toggle if state == "readonly" else lambda e: None)
        self._entry.bind("<FocusIn>", self._focus_in)
        self._entry.bind("<FocusOut>", self._focus_out)
        self.bind("<Enter>", lambda e: self.configure(highlightbackground=PALETTE["hover"]))
        self.bind("<Leave>", lambda e: self.configure(highlightbackground=PALETTE["line"]))
        self.configure(width=max(110, int(width * 9 + 38)), height=34)
        self.pack_propagate(False)
        self._sync_state()

    def _sync_state(self):
        mode = "readonly" if self.state == "readonly" else self.state
        self._entry.configure(state=mode)
        self._arrow.configure(state="disabled" if mode == "disabled" else "normal")

    def _focus_in(self, _event=None):
        self.configure(highlightbackground=PALETTE["blue"])

    def _focus_out(self, _event=None):
        self.configure(highlightbackground=PALETTE["line"])

    def _toggle(self, _event=None):
        if self.state == "disabled":
            return "break"
        if self._popup and self._popup.winfo_exists():
            self._close()
        else:
            self._open()
        return "break"

    def _open(self):
        if not self.values:
            return
        popup = tk.Toplevel(self)
        self._popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=PALETTE["line"])
        popup.transient(self.winfo_toplevel())
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 3
        popup.geometry(f"{self.winfo_width()}x{min(len(self.values), 8) * 32 + 4}+{x}+{y}")
        shell = tk.Frame(popup, bg=PALETTE["line"], padx=1, pady=1)
        shell.pack(fill="both", expand=True)
        listing = tk.Listbox(
            shell, activestyle="none", relief="flat", bd=0,
            bg=PALETTE["surface"], fg=PALETTE["text"],
            selectbackground=PALETTE["blue"], selectforeground="#FFFFFF",
            font=self.font, highlightthickness=0,
            selectmode="browse"
        )
        listing.pack(fill="both", expand=True)
        for index, value in enumerate(self.values):
            listing.insert("end", value)
            if str(value) == self.get():
                listing.selection_set(index)
                listing.see(index)
        listing.bind("<ButtonRelease-1>", self._choose)
        listing.bind("<Return>", self._choose)
        listing.bind("<Escape>", lambda e: self._close())
        popup.bind("<FocusOut>", lambda e: self.after(80, self._dismiss_if_unfocused))
        listing.focus_set()

    def _choose(self, event=None):
        if not self._popup:
            return
        widget = event.widget if event else None
        selection = widget.curselection() if widget else ()
        if selection:
            self.set(self.values[selection[0]])
            self.event_generate("<<ComboboxSelected>>")
        self._close()

    def _dismiss_if_unfocused(self):
        if self._popup and self._popup.winfo_exists():
            try:
                if self._popup.focus_get() is None:
                    self._close()
            except tk.TclError:
                self._close()

    def _close(self):
        if self._popup:
            try:
                self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

    def cget(self, key):
        if key == "values":
            return tuple(self.values)
        if key == "state":
            return self.state
        if key == "textvariable":
            return self.variable
        return super().cget(key)

    def __getitem__(self, key):
        return self.cget(key)

    def __setitem__(self, key, value):
        self.configure(**{key: value})

    def configure(self, cnf=None, **kwargs):
        if hasattr(self, "_entry") and kwargs:
            if "state" in kwargs:
                self.state = kwargs.pop("state")
                self._sync_state()
            if "values" in kwargs:
                self.values = list(kwargs.pop("values"))
        return super().configure(cnf, **kwargs)

    config = configure
