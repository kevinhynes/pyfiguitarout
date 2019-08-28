from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.label import Label
from kivy.clock import Clock, ClockBaseInterrupt
from kivy.graphics import Rectangle, Color
from kivy.config import Config
Config.set("graphics", "kivy_clock", "interrupt")
Config.set("graphics", "maxfps", 90)
ClockBaseInterrupt.interrupt_next_only = False
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '300')

from gp_to_kivy import KivySongBuilder
from music_theory import key_sig_color_map
# from spt_connect_user import spt_play_song
import time, timeit


class Main(BoxLayout):
    song = ObjectProperty(None)

    # def on_song(self, instance, value):
    #     self.song.del_measures(72)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load File", content=content, size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, filepath):
        print("Main.load()... filepath: {}".format(filepath))
        self.song = KivySongBuilder(filepath[0])
        self.dismiss_popup()

    def print_song_data(self):
        self.song.print_song_data()


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class Fretboard(BoxLayout):
    song = ObjectProperty(None)
    tracks = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.beat_num = 0
        for string in range(6):
            self.add_widget(String(num=string, note_val=0))

    def on_song(self, arg1, arg2):
        self.clear_widgets()
        self.tracks = self.song.song
        for string in self.song.gp_song.tracks[0].strings:
            self.add_widget(String(num=string.number, note_val=string.value))

    def play_song(self, instance):
        # spt_play_song(self.song)
        self.start1 = time.time()
        self.start2 = timeit.default_timer()
        self._play_song()

    def _play_song(self, instance=None):
        beat = self.tracks[0][self.beat_num]
        Clock.schedule_once(self._play_song, beat.seconds)
        self._play_beat(beat.frets)
        self.beat_num += 1
        if self.beat_num == len(self.tracks[0]):
            end1 = time.time()
            end2 = timeit.default_timer()
            print("Total Time (time): ", end1 - self.start1)
            print("Total Time (timeit): ", end2 - self.start2)
            return

    def _play_beat(self, these_notes):
        # Kivy adds boxes below, so self.children[0] points to top string.
        # Reverse the list so the right string gets played.
        for string, fret_num in zip(self.children[::-1], these_notes):
            if fret_num is not None or string.active_fret is not None:
                string.draw_frets(fret_num)


class String(BoxLayout):
    def __init__(self, num, note_val, **kwargs):
        super(String, self).__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = 1/6
        self.spacing = 4
        self.num = num
        self.note_val = note_val
        fret_colors = {
            "red": [1, 0, 0, 1],
            "orange": [1, 0.5, 0, 1],
            "yellow": [1, 1, 0, 1],
            "green": [0, 1, 0, 1],
            "blue": [0, 0, 1, 1],
            "indigo": [0.3, 0, 0.5, 1],
            "violet": [0.8, 0, 0.8, 1],
            "black": [0, 0, 0, 1]
        }
        temperament = 2**(1/12)  # Ratio of fret[i]/fret[i+1] for 12-tone equal temperament.
        notes = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        for fret_num in range(25):
            octave, semitone = divmod(self.note_val+fret_num, 12)
            note = notes[semitone]
            color = key_sig_color_map.get(note, "black")
            fret = Fret(fret_color=fret_colors[color], size_hint_x=(1 / temperament ** fret_num),
                        text=str(fret_num))
            if fret_num == 0:
                fret.size_hint_x = fret.size_hint_x * 0.3
            self.add_widget(fret, index=fret_num)
        self.active_fret = self.children[0]

        # Kivy adds boxes to the left.  Flip this so first fret is on the left.
        # This does not work exactly as expected; fret 0 is still self.children[24].
        # Should not be manipulating self.children directly, but cannot find a work around.
        self.children[:] = self.children[::-1]

    def draw_frets(self, fret_num):
        if self.active_fret:
            self.active_fret.canvas.clear()
        # Need to use [24-fret_num] because BoxLayout stores its children right to left.
        if fret_num is not None:
            self.active_fret = self.children[24-fret_num]
            self.active_fret.color_fret()


class Fret(Label):
    def __init__(self, fret_color, **kwargs):
        super(Fret, self).__init__(**kwargs)
        self.fret_color = fret_color
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.fret = Rectangle(size=self.size, pos=self.center)
        self.bind(size=self.update_fret, pos=self.update_fret)

    def update_fret(self, *args):
        self.canvas.clear()
        self.fret.size = self.size
        self.fret.pos = self.pos

    def color_fret(self):
        with self.canvas:
            self.canvas.add(Color(*self.fret_color))
            self.canvas.add(Rectangle(size=self.size, pos=self.pos))


class PyFiGUItarOutApp(App):
    def build(self):
        main = Main()
        return main


if __name__ == '__main__':
    PyFiGUItarOutApp().run()