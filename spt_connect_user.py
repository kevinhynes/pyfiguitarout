from pyfy import Spotify
from gp_to_kivy import song

# Get token here: https://developer.spotify.com/console/get-current-user/
# Request required endpoints and user-modify-playback-state
token = ""
spt = Spotify(token)

results = spt.search(q=song.gp_song.artist + " " + song.gp_song.title)
track_id = results['tracks']['items'][0]['id']
spt.play(track_ids=[track_id])


