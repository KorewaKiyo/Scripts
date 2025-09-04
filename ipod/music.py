import os
import subprocess
import time

try:
    import acoustid
except ModuleNotFoundError:
    print("Module pyacoustid not found, will not fingerprint files")

# Path to needed executables
FFPROBE = r"G:\ffprobe.exe"
FFMPEG = r"G:\ffmpeg.exe"

# Path to operate on
ROOT_DIR = r"G:\MusicCopy"

# Desired max size of cover art, in px
# All art will be squared to this dimension
COVER_SIZE = 600

DRY_RUN = False

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
        return ["video" in result,int(result[1]),int(result[2])]
    except Exception as e:
        print(f"Error probing file: {music_file}\n{e}")
        return [False,0,0]

def find_cover_image(music_file):
    """Find cover art in the directory of the music file and return path"""
    filepath = os.path.split(music_file)[0]

    # We would like to use the already resized cover again for an album, 
    # Then fall back on the bundled one with the release, then fall back on the one downloaded from MusicBrainz 
    preferred = ["cover-resized.jpg", "cover.jpg", "cover-mb.jpg"]

    # Pick through preference list in order
    for preference in preferred:
        for file in os.listdir(filepath):
            if file.lower() == preference:
                return os.path.join(filepath, file)
    
    # If nothing is found in preference list, take any image file, otherwise return nothing
    for file in os.listdir(filepath):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(filepath, file)
        else:
            return None

def resize_cover_image(input_file, output_file):
    """Extract, resize, and return a cover art"""
    input_ext = os.path.splitext(input_file)[1]
    if input_ext in [".m4a", ".mp3", ".flac", ".jpg",".png"]:
        print(f"Extracting image from: {input_file}")

        filter = f"scale={COVER_SIZE}:{COVER_SIZE}:force_original_aspect_ratio=decrease,pad={COVER_SIZE}:{COVER_SIZE}:(ow-iw)/2:(oh-ih)/2"

        resized_jpeg = subprocess.run(
                [
                    FFMPEG, "-i", input_file, "-v", "error", "-hide_banner", 
                    "-an", "-y", "-vf", filter,
                    output_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        time.sleep(3)
    else:
        print(f"Unable to resize: {input_file}")

def convert_flac(flac_file):
    """Convert FLACs to ALAC, apply all the usual bits"""
    new_cover_filename = None
    cover = check_cover_art(flac_file)
    folder_cover = find_cover_image(flac_file)

    resize_filter =  f"-c:v mjpeg -vf 'scale={COVER_SIZE}:{COVER_SIZE}:force_original_aspect_ratio=decrease,pad={COVER_SIZE}:{COVER_SIZE}:(ow-iw)/2:(oh-ih)/2'"
    attach_file = ""
    if folder_cover is not None and "cover-resized" in folder_cover:
        attach_file = f"-i {folder_cover} -map 1:v"
        cover = check_cover_art(folder_cover)
    elif cover[0]:
        attach_file = "-c:v copy"
        folder_cover = flac_file
    elif folder_cover is not None:
        attach_file = f"-i {folder_cover} -map 1:v"
        cover = check_cover_art(folder_cover)
    else:
        print(f"No suitable cover image found for: {flac_file}")

    if cover[1] > COVER_SIZE or cover[2] > COVER_SIZE:
        # Resize and save the cover, so we may use it again
        new_cover_filename = os.path.split(flac_file)[0] + r"\cover-resized.jpg"
        print(f"Resizing from: {folder_cover}")
        cover = resize_cover_image(folder_cover, new_cover_filename)
    else:
        # Blank out the resize filter, as we do not need it
        resize_filter = ""

    alac_name = os.path.splitext(flac_file)[0] + ".m4a"
    conversion = [FFMPEG, "-i", flac_file, attach_file,
         "-map_metadata 0", "-map 0:a", "-metadata:s:v title='Album cover'", "-metadata:s:v comment='Cover (front)'"
         " -c:a alac", "-disposition:v:0 attached_pic", resize_filter, alac_name
        ]
    if DRY_RUN:
        print(" ".join(conversion))
        print("\n")
        return None
    else:
        try:
            output = subprocess.run(conversion,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           text=True,
                           )
            return alac_name
        except Exception as e:
            print(f"Error converting file: {flac_file}\n{e}")
            return None

def process_music_files(directory):
    """Coordinate all operations to be processed on music collection"""
    music = walk_music_files(directory)
    for flac in music["flac_list"]:
        alac = convert_flac(flac)
        if alac is not None:
            os.remove(flac)
    for file in music["m4a_list"]:
        continue
        cover_exists = check_cover_art(file)

        if not cover_exists[0]:
            cover = find_cover_image(file)
        elif cover_exists[1] > COVER_SIZE or cover_exists[2] > COVER_SIZE:
            print(f"File has large cover art, resizing: {file}")
            resize_cover_image(file)
            continue
        else:
            print(f"File has correctly sized cover art, skipping: {file}")
            continue

if __name__ == "__main__":
    process_music_files(ROOT_DIR)