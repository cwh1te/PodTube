#!/usr/bin/python3

from pytube import YouTube
from HandyLib import log, config
from HandyLib.file import mkdir, get_file_extension
import os, datetime, requests, json, yaml

if os.path.isfile("settings.yml"):
    settings = yaml.safe_load(open("settings.yml"))
else:
    settings = {}

# Check settings
if not "last_check" in settings:
    log("Welcome to PodTube!", "header", force=True)
    log("Looks like this is the first time we've run.", force=True)
    log("In the future, I'll just check for uploads published since now. Just for this time, though...", force=True)
    settings["video_count"] = input("How many uploads should we fetch from each channel? ")
if not "api_key" in settings:
    settings["api_key"] = input("Please give me an API key to use: ")
if not "channels" in settings:
    log("What channels do you want to watch for new uploads?", "end", force=True) # "end" log_type applies no styles
    settings["channels"] = []
    while True:
        channel = input()
        if not channel:
            break
        settings["channels"].append(channel)
if not "store_path" in settings:
    store_path = input("Where do you want me to store output? ")
    while not (os.path.exists(store_path)):
        log("Um... that path doesn't exist. Try again, buddy.", "warn", force=True)
        store_path = input("Where do you want me to store output? ")
    settings["store_path"] = store_path

# Quality settings
video_resolutions = {
    "0": "240p",
    "1": "360p",
    "2": "480p",
    "3": "720p",
    "4": "1080p",
    "5": "1440p",
    "6": "2160p",
}
while not "max_quality" in settings:
    quality = input("Please specify a maximum video quality (480p, 720p, etc.): ")
    for key in video_resolutions.keys():
        if quality == video_resolutions[key] or quality == video_resolutions[key][:-1]:
            settings["max_quality"] = int(key)
    if not "max_quality" in settings:
        log("Your selection was invalid. Try a standard resolution.", "warn", force=True)

def update_feed(video_info, audio_path):
    log("RSS feed not yet implemented. Sorry.", "fail")

def get_audio(video_info, video_path):
    while not "output_quality" in settings:
        settings["output_quality"] = int(input("Please specify audio quality (1-9): "))
    basename, ext = get_file_extension(video_path, False)
    audio_path = basename + ".mp3"
    cmd="ffmpeg -i '{0}' -acodec libmp3lame -aq {1} '{2}'".format(video_path, settings["output_quality"], audio_path)
    os.system(cmd)
    os.remove(video_path)
    update_feed(video_info, audio_path)

def get_video(video_info):
    save_path = os.path.join(settings["store_path"], video_info["snippet"]["channelTitle"])
    mkdir(save_path)
    upload = YouTube("https://www.youtube.com/watch?v={0}".format(video_info["id"]["videoId"]))
    video = None
    res = ""
    i = 0
    while not video:
        if not res:
            resolution = video_resolutions[str(settings["max_quality"] - i)]
            if upload.filter(resolution=resolution):
                res = resolution
            else:
                i += 1
            if i > settings["max_quality"]:
                log("No upload candidate matches quality criteria.", "warn")
                return
        else:
            if len(upload.filter(resolution=res)) > 1:
                if upload.filter("mp4", resolution=res):
                    video = upload.get('mp4', res)
            else:
                video = upload.get(None, res)
    video.download(save_path)
    get_audio(video_info, os.path.join(save_path, (video.filename + "." + video.extension)))

def get_subs():
    for channel in settings["channels"]:
        params = [
            ("key", settings["api_key"]),
            ("channelId", channel),
            ("part", "snippet,id"),
            ("order", "date"),
        ]
        if "last_check" in settings:
            params.append(("publishedAfter", settings["last_check"]))
            params.append(("maxResults", 50))
        elif "video_count" in settings:
            params.append(("maxResults", settings["video_count"]))
        else:
            log("Not sure how this happened, but I don't know what videos to download.", "fail")
            exit(1)
        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
        if not res.ok:
            log(res.text, "fail")
            exit(1)
        res = res.json()
        for video in res["items"]:
            get_video(video)
    settings["last_check"] = str(datetime.datetime.now().isoformat('T')) + "Z"
    settings.pop("video_count", None)

if __name__ == "__main__":
    get_subs()
    with open("settings.yml", "w") as f:
        yaml.dump(settings, f)
