
from fastapi import FastAPI, Query, HTTPException, File, Form, UploadFile
from fastapi.responses import FileResponse
from ytmusicapi import YTMusic
from spleeter.separator import Separator
import yt_dlp
import os
import shutil

app = FastAPI()

def split_song(song_name, artist, cookies_path=None):
    yt = YTMusic()
    separator = Separator('spleeter:2stems')
    search_results = yt.search(f'{song_name} - {artist}', filter="songs")
    if not search_results:
        print(f"No results found for {song_name} by {artist}")
        return

    video_id = search_results[0]['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    download_dir = 'Downloaded_songs'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(download_dir, f'{song_name} - {artist}.%(ext)s'),
    }

    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        print(f"Downloaded {song_name} - {artist}.mp3")

    downloaded_file_name = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')
    audio_path = os.path.join(download_dir, os.path.basename(downloaded_file_name))

    output_dir = 'Split_songs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    separator.separate_to_file(audio_path, output_dir, codec='mp3')

    output_song_name = os.path.splitext(os.path.basename(audio_path))[0]
    vocals_path = os.path.join(output_dir, output_song_name, 'vocals.mp3')
    accompaniment_path = os.path.join(output_dir, output_song_name, 'accompaniment.mp3')


@app.post("/split")
async def split_with_cookies(
    song_name: str = Form(...),
    artist: str = Form(...),
    cookies_file: UploadFile = File(...)
):
    cookies_path = f"/tmp/{cookies_file.filename}"
    try:
        with open(cookies_path, "wb") as f:
            shutil.copyfileobj(cookies_file.file, f)

        output_song_name = split_song(song_name, artist, cookies_path)  # ✅ returned name

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(cookies_path):
            os.remove(cookies_path)

    base_path = os.path.join("Split_songs", output_song_name)

    vocals_path = os.path.join(base_path, "vocals.mp3")
    accompaniment_path = os.path.join(base_path, "accompaniment.mp3")

    if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
        raise HTTPException(status_code=500, detail="Separation failed")

    return {
        "vocals": f"/vocals?song={output_song_name}",
        "accompaniment": f"/accompaniment?song={output_song_name}"
    }

@app.get("/vocals")
def get_vocals(song: str):
    path = os.path.join('Split_songs', song, 'vocals.mp3')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Vocals not found")
    return FileResponse(path, media_type="audio/mpeg", filename="vocals.mp3")

@app.get("/accompaniment")
def get_accompaniment(song: str):
    path = os.path.join('Split_songs', song, 'accompaniment.mp3')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Accompaniment not found")
    return FileResponse(path, media_type="audio/mpeg", filename="accompaniment.mp3")
