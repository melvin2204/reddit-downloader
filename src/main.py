import re
import requests
import json
import xml.etree.ElementTree as ET
import tempfile
import os
import sys
import progress
import subprocess
import arguments


# Get command line arguments
args = arguments.parse_args()

# Set verbosity
if args.silent:
    verbosity = False
else:
    verbosity = True


# Make a correct path for files in the PyInstaller executable
def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        return relative_path

    return os.path.join(base_path, relative_path)

# Overload the print function to enable/disable verbosity
old_print = print
def print(*args, **kwargs):
    global verbosity
    if verbosity:
        old_print(*args, **kwargs)
    else:
        return None


# Reddit downloader class
class RedditDownloader:
    # Headers for the communication with the Reddit servers
    USER_AGENT = "Reddit Video Downloader"
    REFERER = "https://github.com/melvin2204/reddit-downloader"
    METADATA_URL = "https://api.reddit.com/api/info/?id=t3_"
    TIMEOUT = 10

    # Settings for ffmpeg and downloading
    OUTPUT_COMMENT = "Downloaded with Reddit Downloader V2"
    EXECUTABLE = resource_path("ffmpeg")
    FFMPEG_COMMAND = "{executable} -i {video_url} -i {audio_url} -c:a aac -c:v copy -strict experimental -y -hide_banner -loglevel {ffmpeg_loglevel} {arguments} {outfile}.mp4"
    FFMPEG_COMMAND_NO_AUDIO = "{executable} -i {video_url} -c:v copy -strict experimental -y -hide_banner -loglevel {ffmpeg_loglevel} {arguments} {outfile}.mp4"
    OUTPUT_DIR = "downloaded"

    def __init__(self, url, outfile=None, extra_arguments="", ffmpeg_loglevel="fatal"):
        self.url = url
        self.outfile = self.make_safe_filename(outfile)
        self.post_id = None
        self.error = False
        self.post_metadata = None
        self.dash_url = None
        self.dash_playlist = None
        self.has_audio = None
        self.audio_url = None
        self.audio_sampling_rate = None
        self.video_url = None
        self.video_framerate = None
        self.video_resolution = (None, None)
        self.video_tempfile = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
        self.audio_tempfile = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
        self.extra_arguments = extra_arguments
        self.ffmpeg_loglevel = ffmpeg_loglevel

        # Check if user actually entered something
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

        # Grab result
        result = result.group(0)

        # Remove comments / and trailing /
        result = result.replace("comments/","")
        result = result.replace("/", "")
        self.post_id = result
        return True

    # Function to do a get request and return the data
    def do_get_request(self, url, stream=False):
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": self.REFERER
        }
        response = requests.get(
            url,
            headers=headers,
            timeout=self.TIMEOUT,
            stream=stream
        )
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
        is_crosspost = self.json_key_exists(self.post_metadata['data']['children'][0]['data'], 'crosspost_parent_list')

        if is_crosspost:
            is_vreddit = self.post_metadata['data']['children'][0]['data']['crosspost_parent_list'][0]['domain'] == "v.redd.it"
            is_video = self.post_metadata['data']['children'][0]['data']['crosspost_parent_list'][0]['is_video']
        else:
            is_vreddit = self.post_metadata['data']['children'][0]['data']['domain'] == "v.redd.it"
            is_video = self.post_metadata['data']['children'][0]['data']['is_video']

        if not (is_vreddit and is_video):
            self.error = True

        return (is_vreddit and is_video)

    # Check if a JSON key exists
    def json_key_exists(self, json, key):
        try:
            buffer = json[key]
        except KeyError:
            return False

        return True

    # Check if an XML tag exists
    def xml_tag_exists(self, xml, index):
        try:
            buffer = xml[index]
        except IndexError:
            return False

        return True

    # Function to extract the dash file location from the meta data
    def get_dash_url(self):
        is_crosspost = self.json_key_exists(self.post_metadata['data']['children'][0]['data'],'crosspost_parent_list')

        if is_crosspost:
            self.dash_url = self.post_metadata['data']['children'][0]['data']['crosspost_parent_list'][0]['secure_media']['reddit_video']['dash_url']
        else:
            self.dash_url = self.post_metadata['data']['children'][0]['data']['secure_media']['reddit_video']['dash_url']

        # Reddit now puts a query string behind the dash url, which breaks this program.
        self.dash_url = self.dash_url.split("?")[0]

    # Function to extract the XML from the DASH playlist
    def get_dash_playlist(self):
        url = self.dash_url

        reddit_response = self.do_get_request(url)

        if reddit_response.status_code != 200:
            self.error = True
            print("An error occurred while retrieving the DASH playlist: not 200 OK")
            return False

        # Parse response as XML
        self.dash_playlist = ET.fromstring(reddit_response.text)

    # Extract the video and audio url from the playlist
    def parse_dash_playlist(self):
        self.has_audio = self.xml_tag_exists(self.dash_playlist[0], 0)

        # If the video has audio, select the audio data from the playlist
        if self.has_audio:
            audio_data = self.dash_playlist[0][0][0]

        # Select video data from the playlist
        video_data = self.dash_playlist[0][1]

        # Grab the base URL from the playlist to download the video and audio
        base_url = self.dash_url.replace("DASHPlaylist.mpd", "")

        # If the video has audio, select the URL and metadata
        if self.has_audio:
            self.audio_url = base_url + audio_data[1].text
            self.audio_sampling_rate = audio_data.attrib['audioSamplingRate']

        # Select all possible video resolutions and other metadata
        video_resolutions = []
        for resolution in video_data:
            video_attributes = resolution.attrib
            video_resolutions.append({
                "width": int(video_attributes['width']),
                "height": int(video_attributes['height']),
                "frameRate": int(video_attributes['frameRate']),
                "url": base_url + resolution[0].text,
            })

        # Select the video with the most pixels
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

        return ("".join(safe_char(c) for c in s).rstrip("_"))[0:100]

    # Generate a name for the output file if the user hasn't given one. This name will be the post's title
    def generate_outfile_name(self):
        title = self.post_metadata['data']['children'][0]['data']['title']
        self.outfile = self.make_safe_filename(title)

    # Download media to a temp directory and show the progress
    def download_media(self, url, filename, text):
        local_filename = filename
        downloaded_bytes = 0
        with open(local_filename, "wb") as f:
            r = self.do_get_request(url, stream=True)
            total_bytes = int(r.headers.get('content-length'))
            for chunk in r.iter_content(chunk_size=4096):
                # Filter keep-alive data
                if chunk:
                    f.write(chunk)
                    # Calculate progress
                    downloaded_bytes += len(chunk)
                    # Only print progress if verbosity is on
                    if verbosity:
                        progress.print_progress(downloaded_bytes, total_bytes, prefix="Downloading {}".format(text))


    # Check if the file has already been downloaded
    def check_if_alread_downloaded(self):
        out_path = "{out_folder}/{out_file}".format(out_folder=self.OUTPUT_DIR, out_file=self.outfile)
        if not os.path.exists(self.OUTPUT_DIR):
            os.mkdir(self.OUTPUT_DIR)

        # Check if file already exists
        if os.path.exists(out_path + ".mp4"):

            # Overwrite if overwrite flag is set
            if args.overwrite:
                return True

            # Don't overwrite if silent flag is set
            if args.silent:
                return False

            choice = input("{} already exists, overwrite? (y/N): ".format(out_path + ".mp4"))
            if choice != "y":
                return False

        return True

    # Combine the audio with the video
    def combine_audio_video(self):
        out_path = "{out_folder}/{out_file}".format(out_folder=self.OUTPUT_DIR,out_file=self.outfile)

        if self.has_audio:
            audio_url = self.audio_tempfile
            ffmpeg_command = self.FFMPEG_COMMAND
        else:
            audio_url = ""
            ffmpeg_command = self.FFMPEG_COMMAND_NO_AUDIO

        command = ffmpeg_command.format(
            executable=self.EXECUTABLE,
            video_url=self.video_tempfile,
            audio_url=audio_url,
            outfile=out_path,
            comment=self.OUTPUT_COMMENT,
            arguments=self.extra_arguments,
            ffmpeg_loglevel=self.ffmpeg_loglevel
        )
        subprocess.call(command, shell=True)

    # Remove the temporary files
    def remove_temp_files(self):
        to_remove = (
            self.video_tempfile,
            self.audio_tempfile
        )
        for item in to_remove:
            try:
                os.remove(item)
            except FileNotFoundError:
                pass

    def start(self):
        # Extract the post ID from the URL
        if self.extract_id(self.url):
            print("Found post ID: {}".format(self.post_id))
        else:
            print("No post ID found. (is it a Reddit comments link?)")
            return False

        # Download the post metadata from the Reddit API
        self.get_metadata()

        # Check if the media is supported
        if not self.check_if_vreddit():
            print("Not v.redd.it!")
            return False

        # Check if the user has left the output file name empty, if so, set the post title as name
        if self.outfile is None:
            self.generate_outfile_name()

        # Check if the post has already been downloaded, if so, ask to continue
        if not self.check_if_alread_downloaded():
            print("Aborted by user.")
            return False
        else:
            print("Downloading \"{}\"".format(self.post_metadata['data']['children'][0]['data']['title']))

        # Get the URL from the DASH playlist, download it and parse it to XML
        self.get_dash_url()
        self.get_dash_playlist()
        self.parse_dash_playlist()

        # Download the video tracks
        self.download_media(self.video_url, self.video_tempfile, "video")

        # If the post has audio, download it too
        if self.has_audio:
            self.download_media(self.audio_url, self.audio_tempfile, "audio")
            print("Combining audio and video...")
        else:
            print("Converting video...")

        # Combine the audio and video tracks
        self.combine_audio_video()

        # Remove the generated temporary files
        self.remove_temp_files()

        print("Done. You can find your video in the \"{}\" folder".format(self.OUTPUT_DIR))
        return True

if __name__ == '__main__':
    print("""
    Reddit Video Downloader v2 by Melvin2204
    Currently only the v.redd.it domain is supported.
    Please only enter Reddit comment links
    """)

    if args.post is not None:
        # Set paramaters based on command line arguments
        reddit_post = args.post

        if args.outfile is not None:
            filename = args.outfile
        else:
            filename = ""

        if args.ffmpeg_loglevel is not None:
            ffmpeg_loglevel = args.ffmpeg_loglevel
        else:
            ffmpeg_loglevel = "fatal"

        if args.ffmpeg_add_arguments is not None:
            extra_arguments = args.ffmpeg_add_arguments
        else:
            extra_arguments = ""

        downloader = RedditDownloader(url=reddit_post, outfile=filename, extra_arguments=extra_arguments, ffmpeg_loglevel=ffmpeg_loglevel)
    else:
        # Set parameters based on terminal input
        reddit_post = input("Reddit post URL: ")
        filename = input("Output file (leave empty for post title): ")
        downloader = RedditDownloader(url=reddit_post, outfile=filename)

    downloader.start()

    # Check if running from PyInstaller package or if user is in interactive mode
    if getattr(sys, 'frozen', False) or args.post is None:
        input("Press enter to exit...")
