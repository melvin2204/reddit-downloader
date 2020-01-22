import argparse

parser = argparse.ArgumentParser(description='Download v.redd.it media via the command line.')

parser.add_argument(
    "-p",
    "--post",
    help="URL of the post to download",
    action="store"
)
parser.add_argument(
    "-o",
    "--outfile",
    help="name of the output file (leave empty for post title)",
    action="store"
)
parser.add_argument(
    "-s",
    "--silent",
    help="don't print any output to the terminal. (Won't overwrite file if it exists)",
    action="store_true"
)
parser.add_argument(
    "-O",
    "--overwrite",
    help="overwrite output file if it already exists",
    action="store_true"
)


def parse_args():
    args = parser.parse_args()
    return args