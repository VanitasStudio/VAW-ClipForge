# VAW ClipForge v0.8 - Video URL Mode + 1080p Shorts

Installed on VAWRIEL-PC (November 3, 2026).
Project: D:\YouTubeAutomation\VAW-ClipForge

## Start
1. Open VAW ClipForge from Windows Desktop.
2. Choose Source Input: Local File or Video URL.
3. For Video URL: paste one public YouTube, TikTok or Vimeo link. Click Check Link for metadata-only validation if desired.
4. Select Output Quality: 1080p (default, vertical 1080x1920) or 720p (720x1280).
5. Choose AI/offline highlight selection, subtitle style, clip duration/count and auto-reframe.
6. Click GENERATE CLIPS. Confirm permitted use and, if Gemini is enabled, consent to cloud analysis.
7. Open Exports to review the final MP4. Optionally edit with Review / Timeline.

## URL import
- Uses yt-dlp and local FFmpeg. Only a single public video is supported; playlists/channels disabled.
- Automatically downloads highest accessible source up to 1080p, merges video and audio when separated.
- Supported sites: YouTube, TikTok, Vimeo. Access may fail when videos require login, DRM, geolocation or platform changes.
- The source is downloaded to D:\YouTubeAutomation\VAW-ClipForge\url-cache; the same URL is reused from cache next time.
- Clear URL Cache deletes only cached input media, not exports, but Review Studio needs source media for re-editing.
- No browser cookies, account bypass, DRM decryption, automatic uploads or publishing.
- Only process videos you own or have rights/license to reuse.

## 1080p quality
- Final Shorts output: 1080 x 1920, H.264 MP4, 30 FPS, AAC audio.
- Output 1080p is rendered from original input, not by upscaling old 720p exports.
- Landscape 1920x1080 cropped to vertical retains about 608x1080 input pixels, so 1080x1920 output cannot invent missing detail.
- Best clarity comes from true portrait 1080x1920 or 4K source; URL downloads currently cap input to 1080p to save space.
- Higher resolution requires more encoding time and disk.

## Testing done
- Installed yt-dlp 2026.10.26 and FFmpeg merger on VAWRIEL-PC.
- Public YouTube metadata extraction succeeded.
- Downloaded Big Buck Bunny official 23-second CC BY 3.0 excerpt by Blender Foundation with separate 1080p video/audio merged.
- Repeated exact same URL produced a cache hit without another download.
- End-to-end GUI test: public URL -> cached video -> offline scoring -> universal auto-crop -> MP4 1080x1920.
- Separate test: local synthetic spoken input -> 1080p crop -> Whisper captions -> burn to MP4.
- Main GUI layout and full resolution output validated; no Gemini call during QA.

Attribution needed if redistributing the Blender Foundation CC BY 3.0 test source.