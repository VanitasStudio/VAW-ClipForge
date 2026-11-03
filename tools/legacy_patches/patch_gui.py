from pathlib import Path
p=Path(__file__).with_name("clipforge_gui.py")
s=p.read_text(encoding="utf-8")
s=s.replace(
    "from secure_config import save_key, has_key, delete_key",
    "from secure_config import save_key, has_key, delete_key\nfrom test_gemini import test_gemini_connection",
)
s=s.replace(
    '        self.button(r,"Remove Key",self.remove_key).pack(side="left")',
    '        self.button(r,"Remove Key",self.remove_key).pack(side="left")\n'
    '        self.button(r,"Test API",self.test_api).pack(side="left",padx=(8,0))',
)
method='''    def test_api(self):
        if not has_key():
            messagebox.showwarning("Key missing","Set the Gemini API key first.")
            return
        model=self.model.get().strip()
        self.log("Testing Gemini model access (text only)...")
        def work():
            try:
                result=test_gemini_connection(model)
                self.messages.put(("api_ok",result))
            except Exception as exc:
                self.messages.put(("api_error",str(exc)))
        threading.Thread(target=work,daemon=True).start()
'''
s=s.replace("    def remove_key(self):",method+"    def remove_key(self):")
s=s.replace(
    '                if kind=="log":\n                    self.log(msg)\n                else:',
    '                if kind=="log":\n                    self.log(msg)\n'
    '                elif kind=="api_ok":\n'
    '                    self.log(msg)\n'
    '                    messagebox.showinfo("API ready",msg)\n'
    '                elif kind=="api_error":\n'
    '                    self.log(msg)\n'
    '                    messagebox.showerror("API test failed",msg)\n'
    '                else:',
)
p.write_text(s,encoding="utf-8")
print("GUI_PATCHED",p.exists())
