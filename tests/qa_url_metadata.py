from url_source import check_link
for url in ("https://vimeo.com/76979871",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw"):
    site=url.split("/")[2]
    print("METADATA_START",site,flush=True)
    try:
        data=check_link(url)
        print("METADATA_OK",site,repr(data.get("title")),data.get("duration"),
              data.get("height"),"CACHED",data.get("cached"),flush=True)
    except Exception as e:
        print("METADATA_ERROR",site,type(e).__name__,str(e)[:190],flush=True)
