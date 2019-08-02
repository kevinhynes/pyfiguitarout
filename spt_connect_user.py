from pyfy import Spotify

# Get token here: https://developer.spotify.com/console/get-current-user/
# Request required endpoints and user-modify-playback-state
token = ""
spt = Spotify(token)

def spt_play_song(song):
    results = spt.search(q=song.gp_song.artist + " " + song.gp_song.title)
    track_id = results['tracks']['items'][0]['id']
    spt.play(track_ids=[track_id])

def spt_restart():
    spt.previous()  # 403 Forbidden...?
