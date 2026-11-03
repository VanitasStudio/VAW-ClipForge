"""Vanitas Studio custom Tk controls for VAW ClipForge.

All controls are drawn/styled in-process; no platform-native themed dropdown or
scrollbar chrome is used. Public methods intentionally mirror common Tk APIs.
"""
from __future__ import annotations

import tkinter as tk
import os
import ctypes
from pathlib import Path

PALETTE = {
    "bg": "#0B0F14",
    "surface": "#111820",
    "field": "#18222D",
    "raised": "#1D2A38",
    "hover": "#26384C",
    "line": "#263342",
    "text": "#D9E0E8",
    "muted": "#8793A3",
    "blue": "#3B82F6",
    "blue_hi": "#60A5FA",
    "orange": "#F97316",
    "white": "#FFFFFF",
}


def load_brand_fonts():
    """Register bundled Archivo and Quantico privately for this process."""
    if os.name != "nt":
        return
    font_dir = Path(__file__).resolve().parent / "assets" / "fonts"
    add_font = ctypes.windll.gdi32.AddFontResourceExW
    for filename in ("Archivo.ttf", "Quantico-Regular.ttf", "Quantico-Bold.ttf"):
        path = font_dir / filename
        if path.is_file():
            add_font(str(path), 0x10, None)


class VanitasCombo(tk.Frame):
    """Custom dropdown with a reliable popup and Combobox-compatible API."""

    def __init__(self, master, *, textvariable=None, state="readonly",
                 values=(), width=18, font=("Archivo", 10), **kwargs):
        bg = kwargs.pop("background", kwargs.pop("bg", PALETTE["surface"]))
        super().__init__(
            master, bg=bg, highlightthickness=1,
            highlightbackground=PALETTE["line"],
            highlightcolor=PALETTE["blue"], bd=0, takefocus=1,
        )
        self.variable = textvariable if textvariable is not None else tk.StringVar(master=self)
        self.state = state
        self.values = list(values)
        self.font = font
        self._popup = None
        self._listbox = None
        self._entry = tk.Entry(
            self, textvariable=self.variable, relief="flat", bd=0,
            bg=PALETTE["field"], fg=PALETTE["text"],
            insertbackground=PALETTE["text"], selectbackground=PALETTE["blue"],
            selectforeground=PALETTE["white"], font=font,
            readonlybackground=PALETTE["field"],
            disabledbackground=PALETTE["surface"],
            disabledforeground=PALETTE["muted"],
            highlightthickness=0,
        )
        self._entry.pack(side="left", fill="both", expand=True, padx=(9, 2), pady=5)
        self._arrow = tk.Canvas(
            self, width=30, height=30, bg=PALETTE["raised"],
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self._arrow.pack(side="right", fill="y", padx=1, pady=1)
        self._draw_arrow()
        self._arrow.bind("<Button-1>", self._toggle)
        self._entry.bind("<Button-1>", self._entry_click)
        self._entry.bind("<KeyPress-Down>", self._open_from_key)
        self._entry.bind("<FocusIn>", self._focus_in)
        self._entry.bind("<FocusOut>", self._focus_out)
        self.bind("<Button-1>", self._toggle)
        self.bind("<Enter>", self._hover)
        self.bind("<Leave>", self._leave)
        self.bind("<KeyPress-Down>", self._open_from_key)
        self.bind("<KeyPress-space>", self._open_from_key)
        self.configure(width=max(110, int(width * 9 + 42)), height=36)
        self.pack_propagate(False)
        self._sync_state()

    def _draw_arrow(self, active=False):
        self._arrow.delete("all")
        color = PALETTE["blue_hi"] if active else PALETTE["text"]
        self._arrow.create_line(10, 13, 15, 18, 20, 13, fill=color, width=2,
                                capstyle="round", joinstyle="round")

    def _sync_state(self):
        mode = "readonly" if self.state == "readonly" else self.state
        self._entry.configure(state=mode)
        self._arrow.configure(cursor="arrow" if mode == "disabled" else "hand2")
        self._draw_arrow(mode != "disabled")

    def _focus_in(self, _event=None):
        self.configure(highlightbackground=PALETTE["blue"])

    def _focus_out(self, _event=None):
        if not self._popup:
            self.configure(highlightbackground=PALETTE["line"])

    def _hover(self, _event=None):
        if not self._popup:
            self.configure(highlightbackground=PALETTE["hover"])

    def _leave(self, _event=None):
        if not self._popup:
            self.configure(highlightbackground=PALETTE["line"])

    def _entry_click(self, event=None):
        if self.state == "readonly":
            self._toggle(event)
            return "break"
        return None

    def _open_from_key(self, _event=None):
        self._open()
        return "break"

    def _toggle(self, _event=None):
        if self.state == "disabled":
            return "break"
        if self._popup and self._popup.winfo_exists():
            self._close()
        else:
            self._open()
        return "break"

    def _open(self):
        if self.state == "disabled" or not self.values:
            return
        if self._popup and self._popup.winfo_exists():
            return
        popup = tk.Toplevel(self)
        self._popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=PALETTE["line"])
        popup.transient(self.winfo_toplevel())
        try:
            popup.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.update_idletasks()
        width = max(self.winfo_width(), 150)
        rows = min(len(self.values), 8)
        row_height = 32
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 3
        screen_h = self.winfo_screenheight()
        if y + rows * row_height + 4 > screen_h:
            y = max(0, self.winfo_rooty() - rows * row_height - 4)
        popup.geometry(f"{width}x{rows * row_height + 4}+{x}+{y}")
        shell = tk.Frame(popup, bg=PALETTE["line"], padx=1, pady=1)
        shell.pack(fill="both", expand=True)
        listing = tk.Listbox(
            shell, activestyle="none", relief="flat", bd=0,
            bg=PALETTE["surface"], fg=PALETTE["text"],
            selectbackground=PALETTE["blue"], selectforeground=PALETTE["white"],
            font=self.font, highlightthickness=0, selectmode="browse",
            exportselection=False,
        )
        listing.pack(fill="both", expand=True)
        self._listbox = listing
        for index, value in enumerate(self.values):
            listing.insert("end", str(value))
            if str(value) == self.get():
                listing.selection_set(index)
                listing.activate(index)
                listing.see(index)
        listing.bind("<ButtonRelease-1>", self._choose_after_click)
        listing.bind("<Return>", self._choose)
        listing.bind("<KP_Enter>", self._choose)
        listing.bind("<Escape>", self._escape)
        popup.bind("<Escape>", self._escape)
        # A local grab keeps focus inside the popup until a choice is made.
        try:
            popup.grab_set()
        except tk.TclError:
            pass
        popup.lift()
        listing.focus_force()
        self.configure(highlightbackground=PALETTE["blue"])
        self._draw_arrow(True)

    def _choose_after_click(self, event=None):
        # Listbox's class binding updates selection after widget bindings.
        self.after_idle(self._choose)
        return "break"

    def _choose(self, _event=None):
        listing = self._listbox
        if listing is None:
            return "break"
        selection = listing.curselection()
        if selection:
            self.set(self.values[int(selection[0])])
            self.event_generate("<<ComboboxSelected>>")
        self._close()
        return "break"

    def _escape(self, _event=None):
        self._close()
        return "break"

    def _close(self):
        popup, self._popup = self._popup, None
        self._listbox = None
        if popup:
            try:
                popup.grab_release()
                popup.destroy()
            except tk.TclError:
                pass
        self.configure(highlightbackground=PALETTE["line"])
        self._draw_arrow(False)

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

    def current(self, index=None):
        if index is None:
            try:
                return self.values.index(self.get())
            except ValueError:
                return -1
        if 0 <= int(index) < len(self.values):
            self.set(self.values[int(index)])

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
            if "font" in kwargs:
                self.font = kwargs.pop("font")
                self._entry.configure(font=self.font)
        return super().configure(cnf, **kwargs)

    config = configure


class VanitasScrollbar(tk.Canvas):
    """Canvas-drawn scrollbar with chamfered thumb and no Windows native chrome."""

    def __init__(self, master, *, command=None, orient="vertical", **kwargs):
        self.command = command
        self.orient = orient
        self.first, self.last = 0.0, 1.0
        self._drag_offset = None
        width = 14 if orient == "vertical" else 90
        height = 90 if orient == "vertical" else 14
        super().__init__(
            master, width=width if orient == "vertical" else height,
            height=height if orient == "vertical" else width,
            bg=PALETTE["bg"], highlightthickness=0, bd=0,
            cursor="hand2", **kwargs,
        )
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<MouseWheel>", self._wheel)

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self._draw()

    def _metrics(self):
        if self.orient == "vertical":
            length = max(1, self.winfo_height())
            start, end = self.first * length, self.last * length
        else:
            length = max(1, self.winfo_width())
            start, end = self.first * length, self.last * length
        thumb = max(28, end - start)
        start = min(max(0, start), max(0, length - thumb))
        return length, start, start + thumb

    def _draw(self):
        self.delete("all")
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        if self.orient == "vertical":
            self.create_rectangle(3, 0, width - 3, height, fill=PALETTE["bg"], outline="")
            _, top, bottom = self._metrics()
            left, right = 2, width - 2
            points = [left + 3, top, right - 3, top, right, top + 4,
                      right, bottom - 4, right - 3, bottom, left + 3, bottom,
                      left, bottom - 4, left, top + 4]
        else:
            self.create_rectangle(0, 3, width, height - 3, fill=PALETTE["bg"], outline="")
            _, left, right = self._metrics()
            top, bottom = 2, height - 2
            points = [left + 4, top, right - 4, top, right, top + 3,
                      right, bottom - 3, right - 4, bottom, left + 4, bottom,
                      left, bottom - 3, left, top + 3]
        color = PALETTE["blue"] if self._drag_offset is not None else PALETTE["raised"]
        self.create_polygon(points, fill=color, outline=PALETTE["line"], width=1)
        if self.orient == "vertical":
            mid = (top + bottom) / 2
            self.create_line(width * .38, mid - 4, width * .62, mid - 4,
                             fill=PALETTE["muted"], width=1)
            self.create_line(width * .38, mid, width * .62, mid,
                             fill=PALETTE["muted"], width=1)
            self.create_line(width * .38, mid + 4, width * .62, mid + 4,
                             fill=PALETTE["muted"], width=1)
        else:
            mid = (left + right) / 2
            self.create_line(mid - 4, height * .38, mid - 4, height * .62,
                             fill=PALETTE["muted"], width=1)
            self.create_line(mid, height * .38, mid, height * .62,
                             fill=PALETTE["muted"], width=1)
            self.create_line(mid + 4, height * .38, mid + 4, height * .62,
                             fill=PALETTE["muted"], width=1)

    def _press(self, event):
        length, start, end = self._metrics()
        pos = event.y if self.orient == "vertical" else event.x
        if start <= pos <= end:
            self._drag_offset = pos - start
        else:
            self._moveto(max(0.0, min(1.0, pos / max(1, length))))
            self._drag_offset = (end - start) / 2
        self._draw()

    def _drag(self, event):
        if self._drag_offset is None:
            return
        length = self.winfo_height() if self.orient == "vertical" else self.winfo_width()
        _, start, end = self._metrics()
        thumb = end - start
        pos = event.y if self.orient == "vertical" else event.x
        fraction = (pos - self._drag_offset) / max(1, length - thumb)
        self._moveto(max(0.0, min(1.0, fraction)))

    def _release(self, _event=None):
        self._drag_offset = None
        self._draw()

    def _moveto(self, fraction):
        if self.command:
            self.command("moveto", fraction)

    def _wheel(self, event):
        if self.command:
            self.command("scroll", -1 if event.delta > 0 else 1, "units")
        return "break"


class VanitasSlider(tk.Canvas):
    """Canvas-drawn horizontal slider with a chamfered Vanitas thumb."""

    def __init__(self, master, *, variable=None, from_=0, to=100, resolution=1,
                 command=None, length=300, showvalue=False, bg=None,
                 troughcolor=None, activebackground=None, **kwargs):
        self.variable = variable if variable is not None else tk.DoubleVar(master=master)
        self.minimum, self.maximum = float(from_), float(to)
        self.resolution, self.command = float(resolution), command
        self.showvalue = bool(showvalue)
        self.track_color = troughcolor or PALETTE["raised"]
        self.active_color = activebackground or PALETTE["blue"]
        self._dragging = False
        super().__init__(master, width=length, height=36,
                         bg=bg or master.cget("bg"), highlightthickness=0, bd=0,
                         cursor="hand2", **kwargs)
        self._trace = self.variable.trace_add("write", self._variable_changed)
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _track(self):
        width = max(1, self.winfo_width())
        right = width - (48 if self.showvalue else 12)
        return 12.0, max(13.0, right)

    def _fraction(self):
        try:
            value = float(self.variable.get())
        except (ValueError, tk.TclError):
            value = self.minimum
        span = self.maximum - self.minimum
        return 0.0 if span <= 0 else max(0.0, min(1.0, (value-self.minimum)/span))

    def _draw(self):
        self.delete("all")
        left, right = self._track()
        y = max(12, self.winfo_height() / 2)
        x = left + (right-left) * self._fraction()
        self.create_line(left, y, right, y, fill=self.track_color, width=5, capstyle="round")
        self.create_line(left, y, x, y, fill=self.active_color, width=5, capstyle="round")
        self.create_polygon(x-7,y-6,x+5,y-6,x+8,y-3,x+8,y+3,
                            x+5,y+6,x-7,y+6,x-9,y+4,x-9,y-4,
                            fill=PALETTE["text"],outline=PALETTE["blue"],width=1)
        if self.showvalue:
            self.create_text(self.winfo_width()-5,y,text=f"{self.variable.get()}",
                             fill=PALETTE["muted"],font=("Archivo",8),anchor="e")

    def _variable_changed(self, *_args):
        self._draw()

    def _set_from_x(self, x, notify=True):
        left, right = self._track()
        fraction = max(0.0,min(1.0,(x-left)/max(1.0,right-left)))
        value = self.minimum + fraction*(self.maximum-self.minimum)
        if self.resolution > 0:
            value = round((value-self.minimum)/self.resolution)*self.resolution+self.minimum
        value = max(self.minimum,min(self.maximum,value))
        self.variable.set(round(value,4))
        if notify and self.command:
            self.command(str(self.variable.get()))

    def _press(self,event):
        self._dragging = True
        self._set_from_x(event.x)

    def _drag(self,event):
        if self._dragging:
            self._set_from_x(event.x)

    def _release(self,_event=None):
        self._dragging = False

    def get(self):
        return self.variable.get()

    def set(self,value):
        self.variable.set(value)

    def configure(self,cnf=None,**kwargs):
        for key,attribute in (("from_","minimum"),("to","maximum"),
                              ("resolution","resolution"),("command","command"),
                              ("showvalue","showvalue"),
                              ("troughcolor","track_color"),
                              ("activebackground","active_color")):
            if key in kwargs:
                setattr(self,attribute,kwargs.pop(key))
        if "length" in kwargs:
            length=kwargs.pop("length")
            tk.Canvas.configure(self,width=length)
        result=super().configure(cnf,**kwargs)
        if hasattr(self,"variable"):
            self._draw()
        return result

    config = configure

class VanitasEntry(tk.Entry):
    """Compact branded text field with restrained focus treatment."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", PALETTE["field"])
        kwargs.setdefault("fg", PALETTE["text"])
        kwargs.setdefault("insertbackground", PALETTE["white"])
        kwargs.setdefault("selectbackground", PALETTE["blue"])
        kwargs.setdefault("selectforeground", PALETTE["white"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", PALETTE["line"])
        kwargs.setdefault("highlightcolor", PALETTE["blue"])
        kwargs.setdefault("font", ("Archivo", 10))
        super().__init__(master, **kwargs)


class VanitasCheckbutton(tk.Frame):
    """Custom checkbox tile with a geometric check mark."""

    def __init__(self, master, *, text, variable=None, command=None,
                 font=("Archivo", 9), bg=None, fg=None, **kwargs):
        self.variable = variable if variable is not None else tk.BooleanVar(master=master)
        self.command = command
        self.text = text
        self._bg = bg or master.cget("bg") or PALETTE["surface"]
        self._fg = fg or PALETTE["text"]
        super().__init__(master, bg=self._bg, cursor="hand2", takefocus=1)
        self.mark = tk.Canvas(self, width=18, height=18, bg=self._bg,
                              highlightthickness=0, bd=0)
        self.mark.pack(side="left", padx=(1, 7))
        self.label = tk.Label(self, text=text, bg=self._bg, fg=self._fg,
                              font=font, anchor="w", cursor="hand2")
        self.label.pack(side="left", fill="x", expand=True)
        for widget in (self, self.mark, self.label):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", self._hover)
            widget.bind("<Leave>", self._leave)
            widget.bind("<space>", self._toggle)
        self._draw()

    def _draw(self, hover=False):
        self.mark.delete("all")
        color = PALETTE["blue"] if self.variable.get() else PALETTE["field"]
        border = PALETTE["blue_hi"] if hover else PALETTE["line"]
        self.mark.create_polygon(3, 2, 15, 2, 16, 4, 16, 14, 14, 16,
                                 3, 16, 2, 14, 2, 4,
                                 fill=color, outline=border, width=1)
        if self.variable.get():
            self.mark.create_line(5, 9, 8, 12, 13, 6,
                                  fill=PALETTE["white"], width=2,
                                  capstyle="round", joinstyle="round")

    def _toggle(self, _event=None):
        self.variable.set(not bool(self.variable.get()))
        self._draw()
        if self.command:
            self.command()
        return "break"

    def _hover(self, _event=None):
        self._draw(True)

    def _leave(self, _event=None):
        self._draw(False)

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            if hasattr(self, "label"):
                self.label.configure(text=self.text)
        if "state" in kwargs:
            state = kwargs.pop("state")
            cursor = "arrow" if state == "disabled" else "hand2"
            for widget in (self, getattr(self, "mark", self), getattr(self, "label", self)):
                widget.configure(cursor=cursor)
        return super().configure(cnf, **kwargs)


class VanitasSpinbox(tk.Frame):
    """Numeric field with branded increment/decrement controls."""

    def __init__(self, master, *, from_=0, to=100, increment=1,
                 textvariable=None, width=8, font=("Archivo", 10), **kwargs):
        bg = kwargs.pop("bg", kwargs.pop("background", PALETTE["surface"]))
        self.variable = textvariable if textvariable is not None else tk.StringVar(master=master)
        self.minimum, self.maximum, self.increment = float(from_), float(to), float(increment)
        super().__init__(master, bg=bg, highlightthickness=1,
                         highlightbackground=PALETTE["line"],
                         highlightcolor=PALETTE["blue"], bd=0)
        self.entry = VanitasEntry(self, textvariable=self.variable, width=width,
                                  font=font, highlightthickness=0, bg=PALETTE["field"])
        self.entry.pack(side="left", fill="both", expand=True, padx=(8, 2), pady=4)
        rail = tk.Frame(self, bg=PALETTE["raised"])
        rail.pack(side="right", fill="y", padx=1, pady=1)
        self.up = tk.Canvas(rail,width=26,height=15,bg=PALETTE["raised"],highlightthickness=0,bd=0,cursor="hand2")
        self.down = tk.Canvas(rail,width=26,height=15,bg=PALETTE["raised"],highlightthickness=0,bd=0,cursor="hand2")
        self.up.pack(fill="both",expand=True)
        self.down.pack(fill="both",expand=True)
        self.up.create_polygon(8,10,13,5,18,10,fill=PALETTE["muted"],outline="")
        self.down.create_polygon(8,5,13,10,18,5,fill=PALETTE["muted"],outline="")
        self.up.bind("<Button-1>",lambda _e:self.step(1))
        self.down.bind("<Button-1>",lambda _e:self.step(-1))
        self.entry.bind("<Return>", lambda _e: self._clamp())
        self.entry.bind("<FocusOut>", lambda _e: self._clamp())
        self.configure(height=36,width=max(82,int(width*9+34)))
        self.pack_propagate(False)

    def step(self, direction):
        try:
            value = float(self.variable.get())
        except (ValueError, tk.TclError):
            value = self.minimum
        value = max(self.minimum, min(self.maximum, value + direction * self.increment))
        self.variable.set(str(int(value)) if value.is_integer() else str(value))

    def _clamp(self):
        try:
            value = max(self.minimum, min(self.maximum, float(self.variable.get())))
        except (ValueError, tk.TclError):
            value = self.minimum
        self.variable.set(str(int(value)) if value.is_integer() else str(value))

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

    def configure(self, cnf=None, **kwargs):
        if "state" in kwargs and hasattr(self, "entry"):
            state = kwargs.pop("state")
            self.entry.configure(state=state)
            cursor = "arrow" if state == "disabled" else "hand2"
            self.up.configure(cursor=cursor)
            self.down.configure(cursor=cursor)
        return super().configure(cnf, **kwargs)

    config = configure


class VanitasButton(tk.Canvas):
    """Chamfered Vanitas action button with a fully custom-drawn surface."""

    def __init__(self, master, *, primary=False, **kwargs):
        self.primary = primary
        self.text = kwargs.pop("text", "")
        self.command = kwargs.pop("command", None)
        self.state = kwargs.pop("state", "normal")
        self.font = kwargs.pop("font", ("Archivo", 9, "bold"))
        self.padx = int(kwargs.pop("padx", 13))
        self.pady = int(kwargs.pop("pady", 8))
        self._base = PALETTE["blue"] if primary else PALETTE["raised"]
        self._hover = PALETTE["blue_hi"] if primary else PALETTE["hover"]
        self._fg = kwargs.pop("fg", PALETTE["white"])
        self._hovering = False
        self._pressed = False
        super().__init__(master, bg=master.cget("bg"), highlightthickness=0,
                         bd=0, cursor="hand2", takefocus=1, **kwargs)
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", self._invoke)
        self.bind("<space>", self._invoke)
        self._draw()

    def _draw(self):
        self.delete("all")
        import tkinter.font as tkfont
        font = tkfont.Font(self, font=self.font)
        width = max(58, font.measure(self.text) + self.padx * 2 + 10)
        height = max(34, font.metrics("linespace") + self.pady * 2 + 8)
        tk.Canvas.configure(self, width=width, height=height)
        self._width, self._height = width, height
        if self.state == "disabled":
            fill, fg = PALETTE["surface"], PALETTE["muted"]
        elif self._pressed:
            fill, fg = self._hover, self._fg
        elif self._hovering:
            fill, fg = self._hover, self._fg
        else:
            fill, fg = self._base, self._fg
        border = PALETTE["blue_hi"] if self.primary and self._hovering else PALETTE["line"]
        points = [5, 1, width - 7, 1, width - 1, 7, width - 1, height - 6,
                  width - 6, height - 1, 5, height - 1, 1, height - 5, 1, 6]
        self.create_polygon(points, fill=fill, outline=border, width=1)
        self.create_line(6, 2, width - 8, 2,
                         fill=PALETTE["blue_hi"] if self.primary else PALETTE["hover"],
                         width=1)
        self.create_text(width / 2, height / 2, text=self.text,
                         fill=fg, font=self.font)
        tk.Canvas.configure(self, cursor="arrow" if self.state == "disabled" else "hand2")

    def _on_enter(self, _event=None):
        self._hovering = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hovering = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event=None):
        if self.state == "disabled":
            return "break"
        self._pressed = True
        self._draw()
        return "break"

    def _on_release(self, event=None):
        if self.state == "disabled":
            return "break"
        inside = event is None or (0 <= event.x <= self.winfo_width()
                                   and 0 <= event.y <= self.winfo_height())
        self._pressed = False
        self._draw()
        if inside:
            self._invoke()
        return "break"

    def _invoke(self, _event=None):
        if self.state != "disabled" and self.command:
            self.command()
        return "break"

    def invoke(self):
        return self._invoke()

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "state" in kwargs:
            self.state = kwargs.pop("state")
        if "font" in kwargs:
            self.font = kwargs.pop("font")
        if "padx" in kwargs:
            self.padx = int(kwargs.pop("padx"))
        if "pady" in kwargs:
            self.pady = int(kwargs.pop("pady"))
        if "fg" in kwargs:
            self._fg = kwargs.pop("fg")
        result = super().configure(cnf, **kwargs)
        if hasattr(self, "text"):
            self._draw()
        return result

    config = configure

    def cget(self, key):
        values = {"text": self.text, "state": self.state,
                  "command": self.command, "font": self.font}
        return values[key] if key in values else super().cget(key)

    def __getitem__(self, key):
        return self.cget(key)

    def __setitem__(self, key, value):
        self.configure(**{key: value})
