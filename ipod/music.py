import os
import subprocess
import tempfile

# Path to needed executables
FFPROBE = r"G:\ffprobe.exe"
FFMPEG = r"G:\ffmpeg.exe"

# Path to operate on
ROOT_DIR = r"G:\Music"

# Desired max size of cover art, in px
# All art will be squared to this dimension
COVER_SIZE = 600

def walk_music_files(root_folder):
    """Walk through the root folder, and store counts and lists of files matching certain extensions"""
    file_list = {
        "m4a" : 0,
        "m4a_list" : [],
        "flac" : 0,
        "flac_list" : [],
        "mp3" : 0,
        "mp3_list" : [],
        "unmatched" : 0,
        "unmatched_list" : []
    }
    for path, subdirs, files in os.walk(root_folder):
        for file in files:
            fullpath = os.path.join(path,file)
            # Split path extension
            match os.path.splitext(file)[1]:
                case ".m4a":
                    file_list["m4a"] += 1
                    file_list["m4a_list"].append(fullpath)
                case ".flac":
                    file_list["flac"] += 1
                    file_list["flac_list"].append(fullpath)
                case ".mp3":
                    file_list["mp3"] += 1
                    file_list["mp3_list"].append(fullpath)   
                case _:
                    file_list["unmatched"] += 1
                    file_list["unmatched_list"].append(fullpath)
    return file_list

def check_cover_art(music_file):
    """Check if cover art exists, return t/f and size"""
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type,width,height", "-of", "default=noprint_wrappers=1:nokey=1", music_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.splitlines()
        
        return ["video" in result,result[1],result[2]]
    except Exception as e:
        print(f"Error probing file: {music_file}\n{e}")
        return False

def find_cover_image(music_file):
    """Find cover art in the directory of the music file and return path"""
    filepath = os.path.split(music_file)
    preferred = ["cover.jpg", "cover.png", "folder.jpg"]
    for file in os.listdir(filepath):
        if file.lower() in preferred:
            return os.path.join(filepath, file)
        elif file.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(filepath, file)
        else:
            return None

def resize_cover_image(music_file):
    """Extract, resize, and return a cover art"""

    # Extract
    # .\ffmpeg.exe -hide_banner -loglevel error -i "$input" -an -vcodec copy "TEMPORARY FILE" -y       

def convert_flac(flac_file):
    """Convert FLACs to ALAC, apply all the usual bits"""
    cover = check_cover_art(flac_file)
    if not cover:
        cover = find_cover_image(flac_file)
    elif cover[1] > COVER_SIZE or cover[2] > COVER_SIZE: 
        new_cover = resize_cover_image(flac_file)



def process_music_files(music):
    """Coordinate all operations to be processed on music collection"""
    #for flac in music["flac_list"]:
    #    convert_flac(flac)
    for file in music["m4a_list"]:
        cover_exists = check_cover_art(file)
        if not cover_exists[0]:
            cover = find_cover_image(file)
        elif cover_exists[1] > COVER_SIZE or cover_exists[2] > COVER_SIZE:
            print(f"File has large cover art, resizing: {file}")

            continue
        else:
            print(f"File has correctly sized cover art, skipping: {file}")
            continue

if __name__ == "__main__":
    music = walk_music_files(ROOT_DIR)
    process_music_files(music)