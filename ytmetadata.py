from distutils.command.upload import upload
from urllib.parse import non_hierarchical
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
import json, datetime

# Class for album information
class AlbumInfo:
    id: str
    title: str
    total: int
    duration: int
    type: str
    artists: list[str]
    artist: str
    year: str
    art_url: str
    art_size: str

    def __init__(self):
        pass

# Class for song information
class SongInfo:
    id: str
    title: str
    duration: str
    artists: list[str]
    artist: str
    # Variables to store lyrics
    has_lyrics: bool
    lyrics: str
    # Variables only for songs with album
    has_album: bool
    album: AlbumInfo
    index: int

    def __init__(self):
        self.album = AlbumInfo()

class Album:
    id: str
    album: AlbumInfo
    songs: list[SongInfo]

    def __init__(self):
        self.album = AlbumInfo()
        self.songs = []

def get_song_info_from_album(ytm:YTMusic, song_id, album_id, song_info_arg:dict = None, do_logs:bool = True) -> SongInfo:
    si = SongInfo()
    si.id = song_id

    # Loading album information
    si.album = AlbumInfo()
    si.has_album = True
    si.album.id = album_id
    if do_logs: print("Loading album", album_id, "info for song...")
    album_info = ytm.get_album(album_id)
    si.album.title = album_info['title']
    si.album.type = album_info['type']
    si.album.total = album_info['trackCount']
    si.album.year = album_info['year']
    si.album.duration = album_info['duration_seconds']
    # Loading album artists
    artists = []
    for artist in album_info['artists']:
        artists.append(artist['name'])
    si.album.artists = artists
    si.album.artist = artists[0]
    # Loading album art info
    art = album_info['thumbnails'][-1]
    si.album.art_url = art['url']
    si.album.art_size = str(art['width']) + ' ' + str(art['height'])

    # Find song in album info
    song_index = 0
    album_song = None
    for song in album_info['tracks']:
        song_index += 1
        if song['videoId'] == song_id:
            album_song = song
            break
    if not album_song:
        # Song was not found in album info
        # Album info probably contains video link
        if do_logs: print("Album playlist contains music video, searching in YT Playlist...")
        if song_info_arg is None:
            song_info = ytm.get_song(song_id)
        else:
            song_info = song_info_arg
        si.title = song_info['videoDetails']['title']
        si.duration = song_info['videoDetails']['lengthSeconds']
        # Find song index in album by name
        song_index = 0
        for song in album_info['tracks']:
            song_index += 1
            if song['title'] == si.title or song['title'].find(si.title) != -1 or si.title.find(song['title']) != -1:
                album_song = song
                if do_logs: print("Found song version details!")
                break
        if not album_song:
            # Find song index in album if name is similar
            song_index = 0
            for song in album_info['tracks']:
                song_index += 1
                if song['title'].find(si.title) != -1 or si.title.find(song['title']) != -1:
                    album_song = song
                    if do_logs: print("Found song version details!")
                    break
    if not album_song:
        raise Exception("Failed to find song!")

    si.title = album_song['title']
    si.duration = album_song['duration_seconds']
    si.index = song_index
    # Get song artists
    artists = []
    for artist in album_song['artists']:
        artists.append(artist['name'])
    si.artists = artists
    si.artist = artists[0]

    if do_logs: print("Song info complete!")
    return si

def get_song_info(ytm:YTMusic, song_id, do_logs:bool = True) -> SongInfo:
    si = SongInfo()
    si.id = song_id
    
    if do_logs: print("Loading song ID:", song_id)
    song_info = ytm.get_song(song_id)

    if not 'videoDetails'in song_info:
        if do_logs: print("Song", song_id, "is unavailable!")
        raise Exception("Song is unvaialable")
    
    song_name = song_info['videoDetails']['title']
    song_author = song_info['videoDetails']['author']
    search_query = song_author + ' ' + song_name

    if do_logs: print("Searching for album by query:", search_query)

    song = None
    is_song = False
    # Search for songs matching the query
    search_results = ytm.search(search_query, filter='songs', limit=10, ignore_spelling=True)
    song_result = next((i for i in search_results if i['videoId'] == song_id), None)
    if song_result is not None:
        if do_logs: print("Song type is song, passing album info...")
        song = song_result
        is_song = True
        return get_song_info_from_album(ytm, song_id, song['album']['id'], song_info, do_logs=do_logs)
    else:
        # If no songs found, search for videos matching the query
        search_results = ytm.search(search_query, filter='videos', limit=10, ignore_spelling=True)
        song_result = next((i for i in search_results if i['videoId'] == song_id), None)
        if song_result is not None:
            if do_logs: print("Song type is video, proceeding without album.")
            song = song_result
            is_song = False
        else:
            # Raise exception if no song was found
            if do_logs: print("Song", song_id, "was not found in search!")
            raise Exception("Song was not found in search")        
    
    si.has_album = False
    si.title = si.album.title = song['title']
    si.duration = song['duration_seconds']
    si.index = si.album.total = 1
    si.album.year = song_info['microformat']['microformatDataRenderer']['uploadDate'][0 : 4]
    if do_logs: print("Song video title:", si.title, "duration:", si.duration)
    # Get song artists from search result
    artists = []
    for artist in song['artists']:
        artists.append(artist['name'])
    si.artists = si.album.artists = artists
    si.artist = si.album.artist = artists[0]
    # Get song thumbnail
    # For songs without album (videos)
    art = song_info['videoDetails']['thumbnail']['thumbnails'][-1]
    si.album.art_url = art['url']
    si.album.art_size = str(art['width']) + ' ' + str(art['height'])

    if do_logs: print("Song video info complete!")
    return si

def get_song_lyrics(ytm:YTMusic, song_id) -> str:
    try:
        watch_playlist = ytm.get_watch_playlist(song_id)
        lyrics_id = watch_playlist['lyrics']
        if lyrics_id:
            lyrics_result = ytm.get_lyrics(lyrics_id)
            if 'lyrics' in lyrics_result:
                return lyrics_result['lyrics']
        return ""
    except:
        return ""

def get_album(ytm:YTMusic, album_id, do_logs=True) -> Album:
    if do_logs: print("Loading album ID:", album_id)
    al = Album()
    al.id = al.album.id = album_id

    album_info = ytm.get_album(album_id)
    if 'title' not in album_info:
        if do_logs: print("Album", album_id, "unavailable!")
        raise Exception("Album unavailable")
    
    # Album parameters
    al.album.title = album_info['title']
    al.album.type = album_info['type']
    al.album.year = album_info['year']
    al.album.total = album_info['trackCount']
    al.album.duration = album_info['duration_seconds']
    if do_logs: 
        print("Album title:", al.album.title, ", type:", al.album.type)
        print("Total songs:", al.album.total)
    # Get album artists
    artists = []
    for artist in album_info['artists']:
        artists.append(artist['name'])
    al.album.artists = artists
    al.album.artist = artists[0]
    if do_logs: print("Album artists:", ', '.join(al.album.artists))
    # Album art
    art = album_info['thumbnails'][-1]
    al.album.art_url = art['url']
    al.album.art_size = str(art['width']) + ' ' + str(art['height'])

    # Use the YouTube playlist to get songs rather than music videos
    album_playlist_url = "https://youtube.com/playlist?list=" + album_info['audioPlaylistId']
    # list of IDs and durations from YouTube
    playlist_songs: list[list] = [[]]
    ytdl_config = { 'extract_flat': True, 'quiet': True }
    with YoutubeDL(ytdl_config) as ytdl:
        if do_logs: print("Loading playlist from YT:", album_info['audioPlaylistId'], end='')
        album_playlist = ytdl.extract_info(album_playlist_url, download=False)
        # with open('playlist_ytdl.json', 'w') as of:
        #     json.dump(ytdl.sanitize_info(album_playlist), of)
        for entry in album_playlist['entries']:
            playlist_songs.append([entry['id'], entry['duration']])
        if do_logs: print("SUCCESS!")
    
    #var_dump(playlist_songs)

    # Now we parse the song list of the album to list[SongInfo]
    # And place the IDs and durations from the YT playlist
    index = 0
    for song in album_info['tracks']:
        index += 1
        si = SongInfo()
        # Insert ID and duration from YT playlist
        si.id = playlist_songs[index][0]
        si.duration = playlist_songs[index][1]
        # Rest of metadata from YT Music album
        # We skip album and art since the album has it
        si.title = song['title']
        si.has_album = True
        si.album = al.album
        si.index = index
        # Get artists of song
        artists = []
        for artist in song['artists']:
            artists.append(artist['name'])
        si.artists = artists
        si.artist = artists[0]
        if do_logs: print("Song", index, ":", si.title)
        # Add song to list
        al.songs.append(si)
    
    if do_logs: print("Album is ready!")
    # Album data is ready for return
    return al

def get_playlist_songs(ytm:YTMusic, playlist_id, do_logs:bool=True, deep_logs:bool = False) -> list[SongInfo]:
    if do_logs: print("Loading playlist", playlist_id)
    playlist = ytm.get_playlist(playlist_id, limit=1000)

    if 'tracks' not in playlist:
        if do_logs: print("Playlist", playlist_id, "is unavailable")
        raise Exception("Playlist is unavailable")

    songs = []
    index = 0
    # For each song run appopriate call for either song or music video    
    for song in playlist['tracks']:
        index += 1
        if do_logs: print("Song", index, song['title'], "[" + song['videoId'] + "]", end='')
        si = SongInfo()
        if song['album']:
            # Calling method with album ID to skip a step
            si = get_song_info_from_album(ytm, song['videoId'], song['album']['id'], do_logs=deep_logs)
        else:
            if do_logs: print("[video]", end='')
            si = get_song_info(ytm, song['videoId'], do_logs=deep_logs)
        si.id = song['videoId']
        if do_logs: print("Loaded")
        songs.append(si)
    
    if do_logs: print("Playlist", playlist_id, "loaded succesfully!")
    return songs
