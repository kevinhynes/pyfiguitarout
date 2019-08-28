from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.graphics.instructions import InstructionGroup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock, ClockBaseInterrupt
from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '300')
Config.set("graphics", "kivy_clock", "interrupt")
Config.set("graphics", "maxfps", 90)
ClockBaseInterrupt.interrupt_next_only = False

from kivy.uix.screenmanager import ScreenManager, Screen

from gp_to_kivy import KivySongBuilder
# from spt_connect_user import spt_play_song
import random, time, timeit

chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()

class ScreenSwitcher(ScreenManager):
    pass


class Main(Screen):
    song = ObjectProperty(None)

    # def on_song(self, instance, value):
    #     self.song.del_measures(72)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load_song(self):
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


class RootNoteScrollContainer(GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        for note in chrom_scale:
            self.add_widget(Button(id=note, text=note, size_hint_y=None))


class Fretboard(BoxLayout):
    song = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.fret_bars = InstructionGroup()
        self.inlays = InstructionGroup()
        self.beat_num = 0
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
        self.fret_bar_width = self.width * (0.1/24.75)  # Gibson ratio of fret bar width to scale length.

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
        self.inlays.add(Color(1, 1, 1, 1))

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

    def _update_key_sig_colored_frets(self, key_sig):
        from itertools import compress
        from collections import deque
        note, mode = key_sig.split()
        # Representative of W-W-H-W-W-W-H (the major scale).
        interval_sequence = deque([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
        roygbiv = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']
        modes = {
            'Major': 0, 'Dorian': 2, 'Phrygian': 4, 'Lydian': 5, 'Mixolydian': 7, 'Minor': 9,
            'Locrian': 11
        }
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()

        mode_pattern = interval_sequence.copy()
        mode_pattern.rotate(-1 * modes[mode])
        note_pattern = chrom_scale.copy()
        while note != note_pattern[0]:
            note_pattern.rotate(-1)
        notes_in_key = list(compress(note_pattern, mode_pattern))
        color_map = {note: color for note, color in zip(notes_in_key, roygbiv)}

    def _clear_frets(self):
        for i in range(1, 7):
            self.ids[str(i)]._play_note(None)

    def play_notes(self):
        for string in range(1, 7):
            fret_num = random.randrange(25)
            self.ids[str(string)].play_note(fret_num)

    def play_song(self):
        track1 = self.song.song[0]
        self.track = track1
        self.start1 = time.time()
        self.start2 = timeit.default_timer()
        # spt_play_song(self.song)
        self._play_song()

    def restart_song(self):
        # spt_restart()
        self._play_song()

    def _play_song(self, seconds=None):
        # Clock will pass beat.seconds as an argument, it is not needed.
        beat = self.track[self.beat_num]
        Clock.schedule_once(self._play_song, beat.seconds)
        self._play_beat(beat.frets)
        self.beat_num += 1
        if self.beat_num == len(self.track):
            end1 = time.time()
            end2 = timeit.default_timer()
            print("Total Time (time): ", end1 - self.start1)
            print("Total Time (timeit): ", end2 - self.start2)
            self._clear_frets()
            return

    def _play_beat(self, frets):
        for i, fret_num in enumerate(frets, 1):
            self.ids[str(i)]._play_note(fret_num)


class String(Widget):
    string_tuning = ObjectProperty(None)

    def __init__(self, active_fret=None, *args, **kwargs):
        super().__init__(**kwargs)
        self.active_fret = active_fret
        self.active_rect = InstructionGroup()
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        self._update_note(instance, value)

    def _update_note(self, instance, value):
        self.active_rect.clear()
        if self.active_fret is None:
            return
        left, right = self.parent.fret_ranges[self.active_fret]
        width = right - left
        x_pos = left
        self.active_rect.add(Color(1, 1, 1, 0.2))
        self.active_rect.add(Rectangle(size=[width, self.height], pos=[x_pos, self.y]))
        self.canvas.add(self.active_rect)

    def _clear_note(self):
        self.active_rect.clear()

    def _play_note(self, fret_num):
        self.active_fret = fret_num
        self._update_note(None, None)


'''PAGE 2 - OBJECTS WITH TUNER'''
class KeySigChooser(FloatLayout):
    load_key_sig = ObjectProperty(None)


class KeySigDisplay(Screen):
    key_sig = ObjectProperty(None)
    fretboard = ObjectProperty(None)

    def on_key_sig(self, instance, value):
        print(instance, value)
        self.display_key_sig()

    def display_key_sig(self):
        self.fretboard._update_key_sig_colored_frets(self.key_sig)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load_key_sig(self):
        content = KeySigChooser(load_key_sig=self.load_key_sig)
        self._popup = Popup(title="Load Key Signature", content=content, size_hint=(0.9, 0.9))
        self._popup.open()

    def load_key_sig(self, key_sig):
        self.key_sig = key_sig
        self.dismiss_popup()


class FretboardWithTuner(BoxLayout):
    song = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.fret_bars = InstructionGroup()
        self.inlays = InstructionGroup()
        self.beat_num = 0
        self.color_map = {}
        self.bind(size=self._update_canvas, pos=self._update_canvas)
        Clock.schedule_once(self._tune_to_standard, 0)  # cannot use kv id's until __init__ is done.

    def _tune_to_standard(self, dt):
        for id, tuning in zip([6, 5, 4, 3, 2, 1], "EADGBE"):
            self.ids[str(id)].string_tuning.text = tuning

    def _update_canvas(self, instance, value):
        # instance is self, value is bound value that changed (size or pos).
        self._update_fret_bars()
        self._update_fret_ranges()
        self._update_inlays()

    def _update_fret_bars(self):
        temperament = 2**(1/12)  # Ratio of fret[i]/fret[i+1] for 12-tone equal temperament.
        self.fret_bar_width = self.width * (0.1/24.75)  # Gibson ratio of fret bar width to scale length.

        # All fret_pos in fret_positions is in interval [0, 1).
        fret_positions = [1 - (1/(temperament**fret_num)) for fret_num in range(25)]
        # Move fret_position[0] up to make a box for the nut, scale fret_position[i] accordingly.
        nut_width_ratio = 0.03  # Percentage of nut_width vs fretboard.width.
        offsets = [fret_pos + (1/temperament**fret_num)*nut_width_ratio \
                       for fret_num, fret_pos in enumerate(fret_positions)]
        offset_fret_positions = [fret_pos + offset for fret_pos, offset in zip(fret_positions, offsets)]
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
        self.inlays.add(Color(1, 1, 1, 1))

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

    def _update_key_sig_colored_frets(self, key_sig):
        from itertools import compress
        from collections import deque
        note, mode = key_sig.split()
        roygbiv = [[1, 0.102, 0.102, 1],  # red
                   [1, 0.549, 0.102, 1],  # orange
                   [1, 1, 0.102, 1],  # yellow
                   [0.102, 1, 0.102, 1],  # green
                   [0.102, 0.102, 1, 1],  # blue
                   [0.549, 0.102, 1, 1],  # indigo
                   [1, 0, 0.502, 1]]  # violet'
        modes = {
            'Major'  : 0, 'Dorian': 2, 'Phrygian': 4, 'Lydian': 5, 'Mixolydian': 7, 'Minor': 9,
            'Locrian': 11
        }
        # Representative of W-W-H-W-W-W-H (the major scale).
        mode_pattern = deque([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
        note_pattern = deque(chrom_scale[:])

        mode_pattern.rotate(-1 * modes[mode])
        while note != note_pattern[0]:
            note_pattern.rotate(-1)
        notes_in_key = list(compress(note_pattern, mode_pattern))
        self.color_map = {note: color for note, color in zip(notes_in_key, roygbiv)}

        for child in self.children:
            child._update_colored_frets()

    def _clear_frets(self):
        for i in range(1, 7):
            self.ids[str(i)]._play_note(None)


class StringWithTuner(Widget):
    string_tuning = ObjectProperty(None)

    def __init__(self, active_fret=None, *args, **kwargs):
        super().__init__(**kwargs)
        self.active_fret = active_fret
        self.active_rect = InstructionGroup()
        self.colored_frets = InstructionGroup()
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        self._update_note(instance, value)
        self._update_colored_frets()

    def _update_note(self, instance, value):
        self.active_rect.clear()
        if self.active_fret is None:
            return
        left, right = self.parent.fret_ranges[self.active_fret]
        width = right - left
        x_pos = left
        self.active_rect.add(Color(1, 1, 1, 0.2))
        self.active_rect.add(Rectangle(size=[width, self.height], pos=[x_pos, self.y]))
        self.canvas.add(self.active_rect)

    def _update_colored_frets(self):
        color_map = self.parent.color_map
        self.colored_frets.clear()
        note_idx = chrom_scale.index(self.string_tuning.text)
        i = 0
        while i < 25:
            note = chrom_scale[(note_idx + i) % 12]
            if note in color_map:
                left, right = self.parent.fret_ranges[i]
                width = right - left
                self.colored_frets.add(Color(*color_map[note]))
                self.colored_frets.add(Rectangle(size=[width, self.height], pos=[left, self.y]))
            i += 1
        self.canvas.add(self.colored_frets)

    def _clear_note(self):
        self.active_rect.clear()

    def _play_note(self, fret_num):
        self.active_fret = fret_num
        self._update_note(None, None)


class Tuner(Spinner):
    pass


class FretlessApp(App):
    pass

if __name__ == "__main__":
    FretlessApp().run()