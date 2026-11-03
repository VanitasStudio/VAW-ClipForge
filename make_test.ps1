$ErrorActionPreference='Stop'
$root="D:\YouTubeAutomation\VAW-ClipForge\samples"
New-Item -ItemType Directory -Path $root -Force | Out-Null
$wave=Join-Path $root 'spoken-test.wav'
$voice=New-Object -ComObject SAPI.SpVoice
$stream=New-Object -ComObject SAPI.SpFileStream
$stream.Open($wave,3,$false)
$voice.AudioOutputStream=$stream
$null=$voice.Speak("Welcome to Workflow Zero. This is a local test of automatic video clipping and subtitles. A simple Python script sorts sample files into categories without paid software. That is what makes this workflow useful. Always check the output before posting.")
$stream.Close()
$ff=& 'C:\Python314\python.exe' -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
& $ff -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=640x360:rate=15' -i $wave -shortest -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 96k (Join-Path $root 'spoken-test.mp4')
Write-Output ('VOICE_CLIP_EXISTS='+(Test-Path (Join-Path $root 'spoken-test.mp4')))
