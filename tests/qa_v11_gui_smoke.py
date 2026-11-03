from clipforge_gui import ClipForge
app=ClipForge()
app.root.withdraw()
app.root.update_idletasks()
assert app.root.title()=="VAW ClipForge v1.1 | AI Editorial Studio"
assert "All Capital Subtitle" in tuple(app.caption_picker["values"])
assert app.caption_style.get()=="karaoke"
app.caption_label.set("All Capital Subtitle")
app.set_caption_from_label()
assert app.caption_style.get()=="all_caps"
assert app.caption_hint.cget("text").startswith("All Capital Subtitle")
assert app.run_btn.cget("text")=="GENERATE CLIPS"
assert app.key_status is not None
print("TKINTER_UI_BUILD_PASS")
print("CAPTION_COMBOBOX_BINDING_PASS")
print("ALL_CAPITAL_SELECTION_PASS")
print("PRIMARY_ACTION_AND_KEY_STATUS_PASS")
app.root.destroy()
