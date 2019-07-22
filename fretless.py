from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.graphics.instructions import InstructionGroup

class Fretboard(BoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(* args, **kwargs)
        self.fret_bars = InstructionGroup()
        self.inlays = InstructionGroup()
        with self.canvas:
            Color(1, 1, 1, 0.5)
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
        self.fret_bars.add(Color(0,0,0,1))
        for fret_pos in actual_fret_positions:
            self.fret_bars.add(Rectangle(size=[self.fret_bar_width, self.height], pos=[fret_pos, self.y]))
        self.canvas.add(self.fret_bars)

        self.fret_bar_positions = actual_fret_positions

    def _update_fret_ranges(self):
        start = 0
        fret_ranges = []
        for fret_pos in self.fret_bar_positions:
            fret_ranges.append((start, fret_pos))
            start = (fret_pos + self.fret_bar_width)
        self.fret_ranges = fret_ranges

    def _update_inlays(self):
        self.inlays.clear()
        self.inlays.add(Color(0,0,0,1))

        d = self.height * 0.075
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
        self.canvas.after.add(self.inlays)



class String(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(* args, **kwargs)


class ScratchApp(App):
    def build(self):
        fretboard = Fretboard()
        return fretboard


if __name__ == "__main__":
    ScratchApp().run()