
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from ytmusicapi import YTMusic
from spleeter.separator import Separator
import yt_dlp

import os

app = FastAPI()

def split_song(song_name, artist):
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
        # 'cookiefile': 'cookies.txt',
        'outtmpl': os.path.join(download_dir, f'{song_name} - {artist}.%(ext)s'),
    }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        print(f"Downloaded {song_name} - {artist}.mp3")

    # Construct the actual downloaded file path
    downloaded_file_name = ydl.prepare_filename(info_dict).replace('.webm', '.mp3') # yt-dlp might download as webm first
    audio_path = os.path.join(download_dir, os.path.basename(downloaded_file_name))


    output_dir = 'Split_songs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    separator.separate_to_file(audio_path, output_dir, codec='mp3')


    # Display the separated audio files

    output_song_name = os.path.splitext(os.path.basename(audio_path))[0]
    vocals_path = os.path.join(output_dir, output_song_name, 'vocals.mp3')
    accompaniment_path = os.path.join(output_dir, output_song_name, 'accompaniment.mp3')
    

@app.get("/split")
def split(song_name: str = Query(...), artist: str = Query(...)):
    try:
        split_song(song_name, artist)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    song_dir = f"{song_name} - {artist}"
    base_path = os.path.join("Split_songs", song_dir)

    vocals_path = os.path.join(base_path, "vocals.mp3")
    accompaniment_path = os.path.join(base_path, "accompaniment.mp3")

    if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
        raise HTTPException(status_code=500, detail="Separation failed")

    return {
        "vocals": f"/vocals?song={song_dir}",
        "accompaniment": f"/accompaniment?song={song_dir}"
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
