# Reddit downloader
This is a command line script to download videos from Reddit

# Usage
Simply run the executable and follow the steps. You can also run it from the command line with arguments.

To view all the possible arguments, run the program with the -h or --help flag. 
I've also listed the possible arguments here:
* -p [post]     Post URL: this is the URL of the post to download.
* -o [outfile]  Outfile: the filename of the output without file extension.
* -s            Silent: don't print any output. Won't automatically overwrite duplicate files. (Use in combination with `-O` to overwrite duplicates).
* -O            Overwrite: always overwrite duplicate files. (Can be used in combination with `-s`) 

# Example usage:
### Interactive mode
Command: `./reddit-downloader.exe`

Output: 
```
Reddit Video Downloader v2 by Melvin2204
Currently only the v.redd.it domain is supported.
Please only enter Reddit comment links
Reddit post URL: https://www.reddit.com/r/subreddit/comments/123456/post_title/
Output file (leave empty for post title): cool title
Found post ID: 132456
downloaded/cool_title.mp4 already exists, overwrite? (y/N): y
Downloading "Post title"
Downloading video |██████████████████████████████████████████████████████████████████████████████████████████| 100.0% '
Downloading audio |██████████████████████████████████████████████████████████████████████████████████████████| 100.0%
Combining audio and video...
Done. You can find your video in the "downloaded" folder
```



### Command line mode
Command: `./reddit-downloader.exe -p "https://www.reddit.com/r/subreddit/comments/123456/post_title/"`

Output:
```
Reddit Video Downloader v2 by Melvin2204
Currently only the v.redd.it domain is supported.
Please only enter Reddit comment links
Found post ID: 132456
Downloading "Post title"
Downloading video |██████████████████████████████████████████████████████████████████████████████████████████| 100.0% '
Downloading audio |██████████████████████████████████████████████████████████████████████████████████████████| 100.0%
Combining audio and video...
Done. You can find your video in the "downloaded" folder
```



Command: `./reddit-downloader.exe -p "https://www.reddit.com/r/subreddit/comments/123456/post_title/" -o "cool title"`

Output:
```
Reddit Video Downloader v2 by Melvin2204
Currently only the v.redd.it domain is supported.
Please only enter Reddit comment links
Found post ID: 132456
downloaded/cool_title.mp4 already exists, overwrite? (y/N): y
Downloading "Post title"
Downloading video |██████████████████████████████████████████████████████████████████████████████████████████| 100.0% '
Downloading audio |██████████████████████████████████████████████████████████████████████████████████████████| 100.0%
Combining audio and video...
Done. You can find your video in the "downloaded" folder
```



Command: `./reddit-downloader.exe -p "https://www.reddit.com/r/subreddit/comments/123456/post_title/" -o "cool title" -O`

Output:
```
Reddit Video Downloader v2 by Melvin2204
Currently only the v.redd.it domain is supported.
Please only enter Reddit comment links
Found post ID: 132456
Downloading "Post title"
Downloading video |██████████████████████████████████████████████████████████████████████████████████████████| 100.0% '
Downloading audio |██████████████████████████████████████████████████████████████████████████████████████████| 100.0%
Combining audio and video...
Done. You can find your video in the "downloaded" folder
```



Command: `./reddit-downloader.exe -p "https://www.reddit.com/r/subreddit/comments/123456/post_title/" -o "cool title" -s`

Output: no output because of -s flag.
