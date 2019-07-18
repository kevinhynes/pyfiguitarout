###PyFiGUItarOut

Kivy + PyGuitarPro + Spotify + Music Theory

Create a fretboard visualization with a GuitarPro5 file and a Spotify premium account.

For now, store your GuitarPro file in the root directory and set it as the default 
file for KivySongBuilder in gp_to_kivy.py.

Get your Spotify token here: https://developer.spotify.com/console/get-current-user/
with user-modify-playback-state scope access. 

Spotify should be actively playing something before running kivy_app.py and pressing
PLAY.

<br/>


To use sample track without Spotify token (fretboard visualization only), remove line 33 in
kivy_app.py before running.