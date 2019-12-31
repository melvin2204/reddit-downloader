print("""Reddit Video Downloader v2 by Melvin2204
Currently only the v.redd.it domain is supported.
Please only enter Reddit comment links
""")

print("Loading dependencies...")
import re
import requests
import json
import xml.etree.ElementTree as ET
import tempfile
import os
import sys
import progress
import subprocess

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class RedditDownloader:
    # Headers for the communication with the Reddit servers
    USER_AGENT = "Reddit Video Downloader"
    REFERER = "https://github.com/melvin2204/reddit-downloader"
    METADATA_URL = "https://api.reddit.com/api/info/?id=t3_"
    TIMEOUT = 10

    OUTPUT_COMMENT = "Downloaded with Reddit Downloader V2"
    EXECUTABLE = resource_path("ffmpeg")
    FFMPEG_COMMAND = "{executable} -i {video_url} -i {audio_url} -c:v copy -c:a aac -strict experimental -metadata comment=\"{comment}\" -y -hide_banner -loglevel panic {outfile}.mp4"

    def __init__(self, url, outfile=None):
        self.url = url
        self.outfile = self.make_safe_filename(outfile)
        self.post_id = None
        self.error = False
        self.post_metadata = None
        self.dash_url = None
        self.dash_playlist = None
        self.audio_url = None
        self.audio_sampling_rate = None
        self.video_url = None
        self.video_framerate = None
        self.video_resolution = (None, None)
        self.video_tempfile = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
        self.audio_tempfile = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())

        if self.outfile.rstrip() == "":
            self.outfile = None

    # This function extracts the post id from the Reddit comments link.
    def extract_id(self, url):
        # Extract the id with comments to prevent selecting a different string that matches the pattern.
        pattern = re.compile("comments/([0-9]|[a-z]){6}/")
        result = pattern.search(url)

        # If no match is found
        if result is None:
            return False

        result = result.group(0)

        # Remove comments / and trailing /
        result = result.replace("comments/","")
        result = result.replace("/", "")
        self.post_id = result
        return True

    # Function to do a get request and return the data
    def do_get_request(self, url):
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": self.REFERER
        }
        response = requests.get(url,headers=headers,timeout=self.TIMEOUT)
        return response

    # Requests the metadata for the post id from the Reddit servers.
    def get_metadata(self):
        url = "{url}{post_id}".format(url=self.METADATA_URL,post_id=self.post_id)
        reddit_response = self.do_get_request(url)

        if reddit_response.status_code != 200:
            self.error = True
            print("An error occurred while retrieving the metadata: not 200 OK")
            return False

        # Load JSON from the string
        self.post_metadata = json.loads(reddit_response.text)

    # Check if the media is from v.redd.it
    def check_if_vreddit(self):
        is_vreddit = self.post_metadata['data']['children'][0]['data']['domain'] == "v.redd.it"
        is_video = self.post_metadata['data']['children'][0]['data']['is_video']

        if (not is_vreddit) and is_video:
            self.error = True

        return is_vreddit and is_video

    def json_key_exists(self, json, key):
        try:
            buffer = json[key]
        except KeyError:
            return False

        return True

    # Function to extract the dash file location from the meta data
    def get_dash_url(self):
        is_crosspost = self.json_key_exists(self.post_metadata['data']['children'][0]['data'],'crosspost_parent_list')

        if is_crosspost:
            self.dash_url = self.post_metadata['data']['children'][0]['data']['crosspost_parent_list'][0]['secure_media']['reddit_video']['dash_url']
        else:
            self.dash_url = self.post_metadata['data']['children'][0]['data']['secure_media']['reddit_video']['dash_url']

    # Function to extract the XML from the DASH playlist
    def get_dash_playlist(self):
        url = self.dash_url
        reddit_response = self.do_get_request(url)

        if reddit_response.status_code != 200:
            self.error = True
            print("An error occurred while retrieving the DASH playlist: not 200 OK")
            return False

        self.dash_playlist = ET.fromstring(reddit_response.text)

    # Extract the video and audio url from the playlist
    def parse_dash_playlist(self):
        audio_data = self.dash_playlist[0][1][0]
        video_data = self.dash_playlist[0][0]

        base_url = self.dash_url.replace("DASHPlaylist.mpd", "")

        self.audio_url = base_url + audio_data[1].text
        self.audio_sampling_rate = audio_data.attrib['audioSamplingRate']

        video_resolutions = []
        for resolution in video_data:
            video_attributes = resolution.attrib
            video_resolutions.append({
                "width": int(video_attributes['width']),
                "height": int(video_attributes['height']),
                "frameRate": int(video_attributes['frameRate']),
                "url": base_url + resolution[0].text,
                "mimeType": video_attributes['mimeType']
            })

        highest_resolution = self.get_highest_resolution(video_resolutions)
        self.video_url = highest_resolution['url']
        self.video_framerate = highest_resolution['frameRate']
        self.video_resolution = (highest_resolution['width'], highest_resolution['height'])

    # Select the highest resolution video from a list of resolutions
    def get_highest_resolution(self, video_resolutions):
        highest_resolution = video_resolutions[0]
        for resolution in video_resolutions:
            width1 = resolution['width']
            height1 = resolution['height']
            width2 = highest_resolution['width']
            height2 = highest_resolution['height']
            sum1 = width1 * height1
            sum2 = width2 * height2
            if sum1 > sum2:
                highest_resolution = resolution

        return highest_resolution

    # Function to make a string safe for a filename
    def make_safe_filename(self, s):
        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"

        return "".join(safe_char(c) for c in s).rstrip("_")

    # Generate a name for the output file if the user hasn't given one
    def generate_outfile_name(self):
        title = self.post_metadata['data']['children'][0]['data']['title']
        self.outfile = self.make_safe_filename(title)

    # Download media to a temp directory and show the progress
    def download_media(self, url, filename, text):
        local_filename = filename
        downloaded_bytes = 0
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_bytes = len(r.content)
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        downloaded_bytes += len(chunk)
                        progress.print_progress(downloaded_bytes, total_bytes, prefix="Downloading {}".format(text))
                        f.write(chunk)

    # Combine the audio with the video
    def combine_audio_video(self):
        command = self.FFMPEG_COMMAND.format(
            executable = self.EXECUTABLE,
            video_url = self.video_tempfile,
            audio_url = self.audio_tempfile,
            outfile = self.outfile,
            comment = self.OUTPUT_COMMENT
        )
        subprocess.call(command, shell=True)

    # Remove the temporary files
    def remove_temp_files(self):
        to_remove = (
            self.video_tempfile,
            self.audio_tempfile
        )
        for item in to_remove:
            os.remove(item)

    def start(self):
        if self.extract_id(self.url):
            print("Post ID found: "+ self.post_id)
        else:
            print("No post ID found.")
            return False

        self.get_metadata()
        if not self.check_if_vreddit():
            print("Not v.redd.it!")
            return False

        if self.outfile is None:
            self.generate_outfile_name()

        self.get_dash_url()
        self.get_dash_playlist()
        self.parse_dash_playlist()

        self.download_media(self.video_url, self.video_tempfile, "video")
        self.download_media(self.audio_url, self.audio_tempfile, "audio")

        print("Combining audio and video...")
        self.combine_audio_video()
        print("Done")

        self.remove_temp_files()

# Retrieve link
reddit_post = input("Reddit post URL: ")
filename = input("Output file: ")
downloader = RedditDownloader(reddit_post, filename)
downloader.start()
input("Press enter to exit")