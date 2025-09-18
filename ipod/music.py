import os
import subprocess
import time
try:
    from alive_progress import alive_bar
except ModuleNotFoundError:
    print("Module needed: alive_progress\nInstall with: pip install alive_progress")
    exit()

# Generate AcoustID fingerprints,
# Takes a little longer, but helps when you want to tag files with Picard
ACOUSTID = False

# Path to needed executables
FFPROBE = r"G:\ffprobe.exe"
FFMPEG = r"G:\ffmpeg.exe"

# Path to operate on
ROOT_DIR = r"G:\Music"

# You're welcome, Dan.
DELETE_FLACS = True

# Desired max size of cover art, in px
# All art will be squared to this dimension
COVER_SIZE = 600

# Max sample rate, set at default for iPod
MAX_SAMPLE = 48000

# Don't convert anything, just print what we would run instead
DRY_RUN = False


if ACOUSTID:
    # If we should try importing it, try it, if it fails, disable the functionality
    try:
        import acoustid
        ACOUSTID = True
    except ModuleNotFoundError:
        ACOUSTID = False
        print("Module pyacoustid not found, will not fingerprint files")

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
    probe = " ".join([FFPROBE, "-v error", "-select_streams v:0", "-show_entries stream=codec_type,width,height", "-of default=noprint_wrappers=1:nokey=1", f'"{music_file}"'])
    try:
        
        result = subprocess.run(
            " ".join([FFPROBE, "-v error", "-select_streams v:0", "-show_entries stream=codec_type,width,height", "-of default=noprint_wrappers=1:nokey=1", f'"{music_file}"']),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        ).stdout.splitlines()
        # If cover is oversize, return false for second value
        # No need to check the result, as it will fail and move to the except clause if there's no cover.
        if int(result[1]) > COVER_SIZE or int(result[2]) > COVER_SIZE:
            return [True, False]
        else:
            return [True, True]
    except Exception as e:
        #print(f"Error probing file: {music_file}\n{e}")
        
        return [False,False]
    
def check_sample_rate(music_file):
    """Check sample rate, return """
    try:
        
        result = subprocess.run(
            " ".join([FFPROBE, "-v error", "-select_streams a:0", "-show_entries stream=sample_rate", "-of default=noprint_wrappers=1:nokey=1", f'"{music_file}"']),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        ).stdout.splitlines()

        # If sample rate is over the max, check if it's divisible by 48k or 44.1k
        # No need to check the result, as it will fail and move to the except clause if there's no cover.
        input_sample_rate = int(result[0])
        if input_sample_rate > MAX_SAMPLE :
            if input_sample_rate % MAX_SAMPLE == 0:
                return MAX_SAMPLE
            elif input_sample_rate % 44100 == 0:
                return 44100
            else:
                print(f"Sample rate of file is not divisible by 44.1kHz or {MAX_SAMPLE}kHz:\nSample rate: {result[0]}\tFile: {music_file}")
                return 0
        else:
            # No change needed
            return 0
    except Exception as e:
        print(f"Error probing file: {music_file}\n{e}")
        return 0
    
def find_cover_image(music_file):
    """Find cover art in the directory of the music file and return path"""
    filepath = os.path.split(music_file)[0]

    # We would like to use the already resized cover again for an album, 
    # Then fall back on the bundled one with the release, then fall back on the one downloaded from MusicBrainz 
    preferred = ["cover-resized.jpg", "cover.jpg", "cover-mb.jpg", "cover-mb.png"]

    # Pick through preference list in order
    for preference in preferred:
        for file in os.listdir(filepath):
            if file.lower() == preference:
                return os.path.join(filepath, file)
    
    # If nothing is found in preference list, take any image file, otherwise return nothing
    for file in os.listdir(filepath):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(filepath, file)
    return None

def resize_cover_image(input_file, output_file):
    """Extract, resize, and return a cover art"""
    input_ext = os.path.splitext(input_file)[1]
    if input_ext in [".m4a", ".mp3", ".flac", ".jpg",".png"]:
        print(f"Extracting image from: {input_file}")

        filter = f'scale={COVER_SIZE}:{COVER_SIZE}:force_original_aspect_ratio=decrease,pad={COVER_SIZE}:{COVER_SIZE}:(ow-iw)/2:(oh-ih)/2'

        resized_jpeg = subprocess.run(
                [
                    FFMPEG, "-i", f"{input_file}", "-v", "error", "-hide_banner", 
                    "-an", "-y", "-vf", filter,
                    f"{output_file}"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
        time.sleep(3)
        if not os.path.exists(output_file):
            print(resized_jpeg.stderr)
            raise FileNotFoundError("Resize failed")
    else:
        print(f"Unable to resize: {input_file}")

def convert_flac(flac_file):
    """Convert FLACs to ALAC, apply all the usual bits"""
    new_cover_filename = None
    cover = check_cover_art(flac_file)
    folder_cover = find_cover_image(flac_file)

    resize_filter =  f'-c:v mjpeg -vf "scale={COVER_SIZE}:{COVER_SIZE}:force_original_aspect_ratio=decrease,pad={COVER_SIZE}:{COVER_SIZE}:(ow-iw)/2:(oh-ih)/2"'
    attach_file = ""
    fingerprint_metadata = ""

    if folder_cover is not None and "cover-resized" in folder_cover:
        attach_file = f'-i "{folder_cover}" -map 1:v -c:v mjpeg '
        cover = check_cover_art(folder_cover)
    elif cover[0]:
        attach_file = "-map 0:v -c:v copy"
        folder_cover = flac_file
    elif folder_cover is not None:
        attach_file = f'-i "{folder_cover}" -map 1:v -c:v mjpeg  '
        cover = check_cover_art(folder_cover)
    else:
        print(f"No suitable cover image found for: {flac_file}")

    
    if cover[0] and not cover[1]:
        # Resize and save the cover, so we may use it again
        new_cover_filename = os.path.split(flac_file)[0] + r"\cover-resized.jpg"
        print(f"Resizing from: {folder_cover}")
        resize_cover_image(folder_cover, new_cover_filename)
    else:
        # Blank out the resize filter, as we do not need it
        resize_filter = ""

    sample_convert = ""
    sample_rate = check_sample_rate(flac_file)
    if sample_rate > 0:
        sample_convert = f"-ar {sample_rate}"

    alac_name = os.path.splitext(flac_file)[0] + ".m4a"
    if ACOUSTID:
        fingerprint = acoustid.fingerprint_file(flac_file)
        fingerprint_metadata = f'-metadata "AcoustID Fingerprint={fingerprint[1].decode('ascii')}"'

    conversion = " ".join([
        FFMPEG,  "-i", f'"{flac_file}"', attach_file, "-map 0:a", "-c:a alac", sample_convert, "-disposition:v:0 attached_pic",
        "-map_metadata 0",  fingerprint_metadata, '-metadata:s:v title="Album cover"',
        '-metadata:s:v comment="Cover (front)"', resize_filter, f'"{alac_name}"', "-y",
        ])
    if DRY_RUN:
        print(conversion)
        print("\n")
        return None
    else:
        print(f"\nRunning conversion on {flac_file}")
        try:
            output = subprocess.run(conversion,
                           stderr=subprocess.PIPE,
                           encoding='utf-8'
                           )
            
            if os.path.exists(alac_name) and DELETE_FLACS:
                print(f"Conversion succeeded, removing {flac_file}")
                os.remove(flac_file)
        except Exception as e:
            print(f"\nError converting file: {flac_file}\n{e}")
            print(f"Command to convert was: {conversion}")
            return None

def process_music_files(directory):
    """Coordinate all operations to be processed on music collection"""
    music = walk_music_files(directory)
    print(f"FLACs: {music["flac"]}\nALACs: {music["m4a"]}\nMP3s: {music["mp3"]}")


    with alive_bar(music["flac"]) as flac_bar:
        flac_bar.title("FLAC Files:")
        for flac in music["flac_list"]:
            alac = convert_flac(flac)
            flac_bar()
    
    with alive_bar(music["m4a"]) as m4a_bar:
        m4a_bar.title("M4A Files:")
        for m4a_file in music["m4a_list"]:
            # Run operations on ALAC/AAC files to make them more ipod friendly
            m4a_bar()
            m4a_cover = check_cover_art(m4a_file)
            sample_convert = "-c:a copy"
            sample_rate = check_sample_rate(m4a_file)
            if m4a_cover[1] and sample_rate == 0:
                # If the cover image and sample rate are good, skip it
                continue

            new_cover_filename = os.path.split(m4a_file)[0] + r"\cover-resized.jpg"
            attach_file = ""
            resize_filter = f'-c:v mjpeg -vf "scale={COVER_SIZE}:{COVER_SIZE}:force_original_aspect_ratio=decrease,pad={COVER_SIZE}:{COVER_SIZE}:(ow-iw)/2:(oh-ih)/2"'
            temp_m4a = os.path.splitext(m4a_file)[0] + "-temp" + ".m4a"

            folder_cover = find_cover_image(m4a_file)
            if folder_cover is not None and "cover-resized" in folder_cover:
                attach_file = f'-i "{folder_cover}" -map 1:v -c:v mjpeg '
                m4a_cover = check_cover_art(folder_cover)
            elif m4a_cover[0]:
                attach_file = "-map 0:v -c:v copy"
                folder_cover = m4a_file
            elif folder_cover is not None:
                attach_file = f'-i "{folder_cover}" -map 1:v -c:v mjpeg  '
                m4a_cover = check_cover_art(folder_cover)
            else:
                print(f"No suitable cover image found for: {m4a_file}")
                continue
                
            if m4a_cover[0] and not m4a_cover[1]:
                # Resize and save the cover, so we may use it again
                new_cover_filename = os.path.split(m4a_file)[0] + r"\cover-resized.jpg"
                print(f"Resizing from: {folder_cover}")
                resize_cover_image(folder_cover, new_cover_filename)
            else:
                # Blank out the resize filter, as we do not need it
                resize_filter = ""

            if sample_rate > 0:
                sample_convert = f"-c:a alac -ar {sample_rate}"

            conversion = " ".join([
                FFMPEG,  "-i", f'"{m4a_file}"', attach_file, "-map 0:a", sample_convert, "-disposition:v:0 attached_pic",
                "-map_metadata 0", '-metadata:s:v title="Album cover"',
                '-metadata:s:v comment="Cover (front)"', resize_filter, f'"{temp_m4a}"', "-y",
            ])
            if DRY_RUN:
                print(conversion)
                print("\n")
            else:
                print(f"\nRunning operations on: {m4a_file}")
                try:
                    output = subprocess.run(conversion,
                                stderr=subprocess.PIPE,
                                encoding='utf-8'
                                )
                    
                    if os.path.exists(temp_m4a):
                        print(f"Succeeded, moving temp file to {m4a_file}")
                        os.replace(temp_m4a, m4a_file)
                except Exception as e:
                    print(f"Error resizing file cover: {m4a_file}\n{e}")
                    print(f"Command to convert was: {conversion}")

                    
    
    music = walk_music_files(directory)
    print(f"FLACs: {music["flac"]}\nALACs: {music["m4a"]}\nMP3s: {music["mp3"]}")

        

if __name__ == "__main__":
    process_music_files(ROOT_DIR)