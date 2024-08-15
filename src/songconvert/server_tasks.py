import demucs.separate
import shlex
import os
import shutil
import contextlib
import subprocess
import json
from ffmpeg import FFmpeg
from pathlib import Path
from ultrastarparser import Song


def create_vocals_instrumental(song: Song, model: str = "htdemucs_ft"):
    songfolder = Path(song.songfolder)
    audio_path = Path(os.path.join(songfolder, song.get_primary_audio()))

    vocals_path = songfolder.joinpath(song.common_name + " [VOC].mp3")
    instrumental_path = songfolder.joinpath(song.common_name + " [INSTR].mp3")

    if vocals_path.exists() and instrumental_path.exists():
        print(f"Vocals and instrumental already created for {song.common_name}")
        return

    demucs_args = shlex.split(
        f'--mp3 --two-stems=vocals -n {model} "{audio_path.as_posix()}" -o "{songfolder.as_posix()}"'
    )
    with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
        demucs.separate.main(demucs_args)

    mp3_name = song.get_primary_audio().replace(".mp3", "")
    separated_folder = os.path.join(song.songfolder, model, mp3_name)

    # Move vocals to the song folder
    vocals = os.path.join(separated_folder, "vocals.mp3")
    shutil.move(vocals, os.path.join(song.songfolder, vocals_path))
    song.set_attribute("VOCALS", vocals_path.name)
    song.flush()

    # Move instrumental to the song folder
    instrumental = os.path.join(separated_folder, "no_vocals.mp3")
    shutil.move(instrumental, os.path.join(song.songfolder, instrumental_path))
    song.set_attribute("INSTRUMENTAL", instrumental_path.name)
    song.flush()

    # Remove the separated folder
    shutil.rmtree(os.path.join(song.songfolder, model))
    print(f"Vocals and instrumental created for {song.common_name}")


def reencode_video(song: Song, crf: int = 17):
    """
    Reencodes the video with nvidia_hevc and with audio.
    """
    songfolder = Path(song.songfolder)
    audio_path = songfolder.joinpath(song.get_primary_audio())
    video_path = songfolder.joinpath(song.get_attribute("VIDEO"))
    video_name = video_path.stem

    if video_path is None or not video_path.exists():
        print(f"Reencoding video {song.common_name} is impossible.")
        return

    # Check video. If aac audio is present, skip reencoding.
    ffprobe_args = [
        "ffprobe",
        "-show_format",
        "-show_streams",
        "-loglevel",
        "quiet",
        "-print_format",
        "json",
        video_path.as_posix(),
    ]

    ffprobe_json: dict
    ffprobe_json = json.loads(subprocess.check_output(ffprobe_args))
    streams = ffprobe_json["streams"]
    for stream in streams:
        if stream["codec_type"] == "audio" and stream["codec_name"] == "aac":
            print(
                f"Video {video_path.name} already has aac audio. Skipping reencoding."
            )
            return

    print(f"Reencoding video {video_path.name}.")
    ffmpeg_video = (
        FFmpeg()
        .input(video_path)
        .input(audio_path)
        .output(
            video_path.parent.joinpath("tempvideo.mp4"),
            acodec="aac",
            vcodec="hevc_nvenc",
            crf=crf,
            preset="p7",
        )
    )
    ffmpeg_video.execute()

    video_path.unlink()
    video_path.parent.joinpath("tempvideo.mp4").rename(
        video_path.parent.joinpath(video_name + ".mp4")
    )

    print(f"Reencoding video {video_path.name} done.")
