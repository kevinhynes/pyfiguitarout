from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.graphics.instructions import InstructionGroup
from kivy.clock import Clock
from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '300')

from gp_to_kivy import KivySongBuilder
from spt_connect_user import spt_play_song
import random, time


class Main(BoxLayout):
    song = ObjectProperty(None)

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
        self.song.print_song_data_no_repeat()


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class Fretboard(BoxLayout):
    song = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.fret_bars = InstructionGroup()
        self.inlays = InstructionGroup()
        self.beat_num = 0
        with self.canvas:
            Color(0, 0, 0.75, 0.5)
            self.background = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        # instance is self, value is bound value that changed (size or pos).
        self._update_background()
        self._update_fret_bars()
        self._update_fret_ranges()
        self._update_inlays()

    def _update_background(self):
        self.background.pos = self.pos
        self.background.size = self.size

    def _update_fret_bars(self):
        temperament = 2**(1/12)  # Ratio of fret[i]/fret[i+1] for 12-tone equal temperament.
        self.fret_bar_width = self.width * (0.1/24.75) # Gibson ratio of fret bar width to scale length.

        # All fret_pos in fret_positions is in interval [0, 1).
        fret_positions = [1 - (1/(temperament**fret_num)) for fret_num in range(25)]
        # Move fret_position[0] up to make a box for the nut, scale fret_position[i] accordingly.
        nut_width_ratio = 0.03 # Percentage of nut_width vs fretboard.width.
        nut_offsets = [fret_pos + (1/temperament**fret_num)*nut_width_ratio \
                       for fret_num, fret_pos in enumerate(fret_positions)]
        offset_fret_positions = [fret_pos + offset for fret_pos, offset in zip(fret_positions, nut_offsets)]
        # Stretch all fret_positions so they fit the entire width of the fretboard.
        stretched_fret_positions = [fret_pos / offset_fret_positions[-1] for fret_pos in offset_fret_positions]
        # Calculate actual fret_positions.
        actual_fret_positions = [fret_pos*self.width + self.x for fret_pos in stretched_fret_positions]

        self.fret_bars.clear()
        self.fret_bars.add(Color(0, 0, 0, 1))
        for fret_pos in actual_fret_positions:
            self.fret_bars.add(Rectangle(size=[self.fret_bar_width, self.height], pos=[fret_pos, self.y]))
        self.canvas.add(self.fret_bars)

        self.fret_bar_positions = actual_fret_positions

    def _update_fret_ranges(self):
        start = self.x
        fret_ranges = []
        for fret_pos in self.fret_bar_positions:
            fret_ranges.append((start, fret_pos))
            start = (fret_pos + self.fret_bar_width)
        self.fret_ranges = fret_ranges

    def _update_inlays(self):
        self.inlays.clear()
        self.inlays.add(Color(0, 0, 0, 1))

        d = self.height * 0.15
        for i, fret_range in enumerate(self.fret_ranges):
            # Single circular inlay.
            if i in range(3, 10, 2) or i in range(15, 25, 2):
                x_pos = (sum(fret_range) / 2)
                y_pos = (self.height / 2) + self.y
                self.inlays.add(Ellipse(size=[d, d], pos=[x_pos - d/2, y_pos - d/2]))
            # Double circular inlay at fret 12.
            elif i == 12:
                x_pos = (sum(fret_range) / 2)
                y_pos1 = (self.height / 3) + self.y
                y_pos2 = 2*(self.height / 3) + self.y
                self.inlays.add(Ellipse(size=[d, d], pos=[x_pos - d / 2, y_pos1 - d / 2]))
                self.inlays.add(Ellipse(size=[d, d], pos=[x_pos - d / 2, y_pos2 - d / 2]))
        self.canvas.add(self.inlays)

    def play_notes(self):
        for string in range(1, 7):
            fret_num = random.randrange(25)
            self.ids[str(string)].play_note(fret_num)

    def play_song(self):
        track1 = self.song.song[0]
        self.track = track1
        self.start = time.time()
        spt_play_song(self.song)
        self._play_song()

    def restart_song(self):
        # spt_restart()
        self._play_song()

    def _play_song(self, seconds=None):
        # Clock will pass beat.seconds as an argument, it is not needed.
        beat = self.track[self.beat_num]
        self.beat_num += 1
        if self.beat_num == len(self.track):
            print("Total Time: ", time.time() - self.start)
            return
        self._play_beat(beat.frets)
        Clock.schedule_once(self._play_song, beat.seconds)

    def _play_beat(self, frets):
        for i, fret_num in enumerate(frets, 1):
            self.ids[str(i)]._play_note(fret_num)


class String(Widget):
    def __init__(self, active_fret=0, *args, **kwargs):
        super().__init__(**kwargs)
        self.active_fret = active_fret
        self.active_rect = InstructionGroup()
        with self.canvas:
            Color(0, 0, 0, 0)
            self.background = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        self._update_background(instance, value)
        self._update_note(instance, value)

    def _update_background(self, instance, value):
        self.background.pos = self.pos
        self.background.size = self.size

    def _update_note(self, instance, value):
        left, right = self.parent.fret_ranges[self.active_fret]
        width = right - left
        x_pos = left
        self.active_rect.clear()
        self.active_rect.add(Color(1, 1, 1, 0.5))
        self.active_rect.add(Rectangle(size=[width, self.height], pos=[x_pos, self.y]))
        self.canvas.add(self.active_rect)

    def _play_note(self, fret_num):
        if fret_num is None:
            self.active_rect.clear()
            return
        self.active_fret = fret_num
        self._update_note(None, None)


class FretlessApp(App):
    def build(self):
        main = Main()
        return main


if __name__ == "__main__":
    FretlessApp().run()