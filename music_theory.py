from collections import deque, defaultdict
import itertools


'''
Mode	Tonic relative
        to major scale	Interval sequence	    Example
Major	    I	        W-W-H-W-W-W-H	        C-D-E-F-G-A-B-C
Dorian	    II	        W-H-W-W-W-H-W	        D-E-F-G-A-B-C-D
Phrygian    III	        H-W-W-W-H-W-W	        E-F-G-A-B-C-D-E
Lydian	    IV	        W-W-W-H-W-W-H	        F-G-A-B-C-D-E-F
Mixolydian  V	        W-W-H-W-W-H-W	        G-A-B-C-D-E-F-G
Minor	    VI	        W-H-W-W-H-W-W	        A-B-C-D-E-F-G-A
Locrian	    VII	        H-W-W-H-W-W-W	        B-C-D-E-F-G-A-B

Harmonic Minor          W-H-W-W-H-W+H-H         A-B-C-D-E-F-G#-A
Melodic Minor           W-H-W-W-W-W-H           A-B-C-D-E-F#-G#-A
'''

roygbiv = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']
notes = deque(['A', 'A#/Bb', 'B', 'C', 'C#/Db', 'D',
               'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab'])

# Representative of W-W-H-W-W-W-H (the major scale).
interval_sequence = deque([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])

# Maps mode names to starting position of major scale pattern.
modes = {'Major': 0, 'Dorian': 2, 'Phrygian': 4, 'Lydian': 5,
         'Mixolydian': 7, 'Minor': 9, 'Locrian': 11}

def get_key_sig_color_map(note, mode):
    # Representative of W-W-H-W-W-W-H (the major scale).
    interval_sequence = deque([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])

    modes = {
        'Major'  : 0, 'Dorian': 2, 'Phrygian': 4, 'Lydian': 5, 'Mixolydian': 7, 'Minor': 9,
        'Locrian': 11}

    chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()

    mode_pattern = interval_sequence.copy()
    mode_pattern.rotate(-1*modes[mode])

    note_pattern = chrom_scale.copy()
    while note != note_pattern[0]:
        note_pattern.rotate(-1)
    notes_in_key = list(itertools.compress(note_pattern, mode_pattern))

    color_map = {note: color for note, color in zip(notes_in_key, roygbiv)}
    return color_map

 
def generate_key_sigs():
    key_signatures_to_notes = {}
    notes_to_key_signatures = defaultdict(list)
    for note in notes:
        for mode in modes:
            this_key = note + " " + mode
            mode_pattern = interval_sequence.copy()
            mode_pattern.rotate(-1 * modes[mode])

            note_pattern = notes.copy()
            while note != note_pattern[0]:
                note_pattern.rotate(-1)
            note_pattern = list(itertools.compress(note_pattern, mode_pattern))

            note_pattern_val = 0
            for n in note_pattern:
                note_pattern_val += list(notes).index(n)
            notes_to_key_signatures[note_pattern_val].append(this_key)
            key_signatures_to_notes[this_key] = note_pattern[:]
    return key_signatures_to_notes, notes_to_key_signatures


key_sig_color_map = get_key_sig_color_map("C", "Major")

