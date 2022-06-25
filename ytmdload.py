import ytmetadata
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
from PIL import Image
import io
from io import BytesIO
import requests
import music_tag
import time
from os import path
from urllib.parse import urlparse
from urllib.parse import parse_qs

def clean_filename(filename:str, replace:chr='_'):
    allowed_chars = ' .,!@#$()[]-+=_'
    new_fn = ''

    for char in filename:
        if char.isalnum() or char in allowed_chars:
            new_fn += char
        else:
            new_fn += replace

    new_fn.strip()

    if new_fn[-1] == '.':
        new_fn = new_fn[:-1]

    return new_fn

# URL = 'PLLLy4XORhHbkiinUreH76OWm7ny7z89gS'
#URL = 'OLAK5uy_lvGn6U_oFqZA-RyRQRyKAlb4ysg5bAO5U'

out_path = 'D:/music'
out_format = 'opus'

do_dl_archive = True
dl_archive_file = out_path + '/Downloaded.txt'

do_lyrics = True

ytdl_opts = {
    'format': out_format + '/bestaudio/best',
    'postprocessors':[{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': out_format,
        'preferredquality': '0'
    }],
    'quiet': True,
    'outtmpl': ''
}
ytm = YTMusic()

URLs = []

# Read multiple URLs from command line
print("Type in URLs or IDs to download, separated by new lines:")
print("Submit blank line to download.")
inpt = 'ignore'
while inpt:
    inpt = input()
    if inpt:
        URLs.append(inpt)

# Load download archive list
dl_archive_ids = []
if do_dl_archive:
    print("Loading download archive file...", end='')
    if path.isfile(dl_archive_file):
        with open(dl_archive_file, 'r') as f:
            dl_archive_ids = f.read().splitlines()
        print(" Loaded succesfully!")
    else:
        print(" No download archive file!")

# Song count and starting time for end statistics
song_count = 0
start_time = time.time()

# Parse each URL
for URL in URLs:
    if URL.startswith('http'):
        parsed_url = urlparse(URL)
        parsed_qs = parse_qs(parsed_url.query)
        if 'watch' in URL and 'v' in parsed_qs:
            id = parsed_qs['v'][0]
        elif 'playlist' in URL and 'list' in parsed_qs:
            id = parsed_qs['list'][0]
        elif 'browse' in URL:
            # Get last part of URL representing album ID
            # starting with 'MPREb_'
            id = parsed_url.path.rsplit("/", 1)[-1]
        else:
            print("ERROR: Invalid URL Address!")
            exit()

    if id.startswith('PLLL'):
        # ID represents a playlist
        # Get songs from playlist
        print("Getting playlist songs...")
        songs = ytmetadata.get_playlist_songs(ytm, id)
    elif id.startswith('OLAK5uy_'):
        # ID represents an album playlist
        # Get album ID then album songs
        id = ytm.get_album_browse_id(id)
        print("Getting album songs...")
        songs = ytmetadata.get_album(ytm, id).songs
    elif id.startswith('MPREb_'):
        # ID represents an album
        # Get album songs
        print("Getting album songs...")
        songs = ytmetadata.get_album(ytm, id).songs
    else:
        # ID represents a song
        # Get song info and put into array to simplify loop after
        songs = []
        songs.append(ytmetadata.get_song_info(ytm, id, do_logs=False))

    for song in songs:
        print("Downloading", song.title, '-', ', '.join(song.artists) , '(' + song.id + ')')

        # Skip song if it's already been downloaded
        if do_dl_archive:
            if song.id in dl_archive_ids:
                print("Song already in archive!")
                # Go to next song
                continue
        
        # Increase song count (for end statistics)
        song_count += 1

        # Sanitize song title to be OK with OS
        safe_title = clean_filename(song.title)
        safe_artist = clean_filename(song.artist)
        safe_album = clean_filename(song.album.title)
        # Create output path template
        # Desired_Location/Artist_Name/Album_Name/Index - Track_Name.Format
        file_path_s = out_path + '/' + safe_artist + '/' + safe_album + '/' + str(song.index) + ' - ' + safe_title + '.'
        file_path = file_path_s + out_format

        # Download audio
        ytdl_opts['outtmpl'] = file_path_s + '%(ext)s'
        with YoutubeDL(ytdl_opts) as ytdl:
            ytdl.download(song.id)

        # Open audio file for metadata editing        
        song_file = music_tag.load_file(file_path)
        # Add metadata to file
        song_file['tracktitle'] = song.title
        song_file['artist'] = '; '.join(song.artists)
        if song.has_album:
            song_file['comment'] = "Song ID: " + song.id + "\nAlbum ID: " + song.album.id
        else:
            song_file['comment'] = "Song ID: " + song.id
        song_file['tracknumber'] = song.index
        song_file['album'] = song.album.title
        song_file['albumartist'] = '; '.join(song.album.artists)
        song_file['totaltracks'] = song.album.total
        song_file['year'] = song.album.year
        response = requests.get(song.album.art_url)
        img = Image.open(BytesIO(response.content))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        song_file['artwork'] = img_byte_arr

        # Get song lyrics
        if do_lyrics:
            print("   Please wait, getting lyrics...", end='')
            lyrics = ytmetadata.get_song_lyrics(ytm, song.id)
            if lyrics:
                print(" Lyrics OK!")
                song_file['lyrics'] = lyrics
            else:
                print(" No lyrics found or API error!")

        # Save metadata to audio file
        song_file.save()

        # Add song into download archive list and file
        if do_dl_archive:
            dl_archive_ids.append(song.id)
            with open(dl_archive_file, 'a') as of:
                of.write('\n' + song.id)

# All downloads finished, print finish message:
print("Download finished,", song_count, "tracks in {}".format(time.time() - start_time) ,"! Enjoy :)")
input("Press Enter to exit...")