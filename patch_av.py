from pathlib import Path
p=Path(__file__).with_name("auto_captions.py")
s=p.read_text(encoding="utf-8")
s=s.replace('''    model=get_model(size,log)
    segments,info=model.transcribe''',
'''    # PyAV 19 removed metadata_errors argument while faster-whisper 1.2.1 still
    # passes it. Adapt the decoder call without modifying any installed packages.
    import av
    if not getattr(av.open,"_vaw_compat",False):
        original_open=av.open
        def compat_open(*args,**kwargs):
            kwargs.pop("metadata_errors",None)
            return original_open(*args,**kwargs)
        compat_open._vaw_compat=True
        av.open=compat_open
    model=get_model(size,log)
    segments,info=model.transcribe''')
p.write_text(s,encoding="utf-8")
print("PyAV compatibility patch applied")
