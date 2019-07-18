import guitarpro
from math import isclose
import heapq
from collections import Counter

class KivyBeat:
    def __init__(self, seconds: float, frets: list, notes: list=None):
        self.seconds = seconds
        self.frets = frets
        self.notes = notes


class KivySongBuilder:
    def __init__(self, file="tgr-nm-01-g1.gp5"):
        self.gp_song = guitarpro.parse(file)
        self.gp_key_sig = self._gp_key_sig_parser(self.gp_song)
        self.gp_tunings = self._gp_tuning_parser(self.gp_song)
        self._build_song()
        self.key_sigs_per_measure = self._detect_song_key_signatures()
        self.note_counts = self._note_counter()
        # Might not need functions associated with all_beats_captured.
        self.all_beats_captured = self._sum_and_check_song()

    def _gp_tuning_parser(self, gp_song):
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        tunings = []
        for track in gp_song.tracks:
            tuning = []
            for string in track.strings:
                octave, open_string = divmod(string.value, 12)
                note = chrom_scale[open_string]
                tuning.append([string.number, note])
            tunings.append(tuning[:])
        return tunings

    def _gp_key_sig_parser(self, gp_song):
        circ_of_fifths_maj = ["C", "G", "D", "A", "E", "B", "F#/Gb", "C#/Db", "G#/Ab", "D#/Eb",
                              "A#/Bb",
                              "F"]
        circ_of_fifths_min = ["A", "E", "B", "F#/Gb", "C#/Db", "G#/Ab", "D#/Eb", "A#/Bb", "F", "C",
                              "G",
                              "D"]
        circ_of_fifths = [circ_of_fifths_maj, circ_of_fifths_min]
        modes = ["Major", "Minor"]
        pos, mode = gp_song.key.value
        return circ_of_fifths[mode][pos], modes[mode]

    def _build_song(self):
        '''
        Build song for Kivy app's use, and song_data for developer use (data validation).

        song:  [track, track, ...]
        track: [KivyBeat, KivyBeat, KivyBeat, ...]
        song_data:  [track_data, track_data, ...]
        track_data: [[gp_measure.header, KivyBeat, KivyBeat, ...],
                     [gp_measure.header, KivyBeat, KivyBeat, ...], ...]
        '''
        song, song_data = [], []
        for track in self.gp_song.tracks:
            track, track_data = self._build_track(track)
            song.append(track)
            song_data.append(track_data)
        self.song, self.song_data = song, song_data

    def _build_track(self, gp_track):
        '''Build list of each beat's length in seconds (including rests).

        Guitar Pro Songs contain a list of Tracks (each guitar?).
        Each Track contains a list of all Measures.
        Each Measure contains a list of 2 Voices (for GP5 files).
        [Voices can be thought of as a left and right hand on the piano, one for playing bass and
        the other for the melody.]
        Each Voice contains a list of Beats.
        Each Beat has a Duration and a list of Notes.
        Each Note is described by a String (1-6) and fret (0-24?) --> Note.string, Note.value.
        If there is no Beat.note object, rest for the Beat.duration.

        Dev Notes:
            - Different Voices in the same Measure may have different start/end times.
            - PyGuitarPro does not appear to be parsing measure.header.repeatAlternative correctly.
            - When Beat is a quarter note, beat.duration.time == 960.  No idea why.

        TODO:
            - Flatten voices into one track? Safe to ignore completely? Create two "voice tracks" per
            track? This will mean every kivy fretboard will need input for 2 "voice tracks"?  Currently
            the only way to have notes last for different beat lengths (i.e quarter note and eight note
            starting at the same time... letting a note "ring out"). Strings could schedule their own
            call backs?  Then I'd need a list of lists for track beats.  Each sublist representing all
            the track_beats for that string only.
            - Figure out what's up with Measure.MeasureHeader.repeatAlternative.. maybe use GPX branch?
        '''
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        track, track_data = [], []
        measure, repeat_group_data = [], []

        for gp_measure in gp_track.measures:
            measure_data = [gp_measure.header]
            # For some reason there are 2 voices, second one holds default values and would otherwise
            # add default beat.duration values that would get read as quarter note rests (in tgr-nm-01).
            for gp_voice in gp_measure.voices[:-1]:
                for gp_beat in gp_voice.beats:
                    seconds = gp_beat.duration.time / 960 * (self.gp_song.tempo / 60) ** (-1)

                    frets, notes = [None] * 6, []
                    for gp_note in gp_beat.notes:
                        frets[gp_note.string-1] = gp_note.value

                        octave, semitone = divmod(gp_note.realValue, 12)
                        note = chrom_scale[semitone]
                        notes += [note]

                    beat = KivyBeat(seconds, frets, notes)
                    measure.append(beat)
                    measure_data.append(beat)
                repeat_group_data.append(measure_data[:])

                # If we're starting a repeat group, let measure build until its closed.
                if gp_measure.header.isRepeatOpen:
                    continue
                # Else if we're closing a measure, multiply it by number of repeats and clear it.
                elif gp_measure.header.repeatClose > 0:
                    measure[:] = measure[:] * gp_measure.header.repeatClose
                    track.extend(measure)
                    measure.clear()

                    repeat_group_data[:] = repeat_group_data[:] * gp_measure.header.repeatClose
                    track_data.extend(repeat_group_data)
                    repeat_group_data.clear()
                # Otherwise this is just a regular measure. Add it and clear it.
                # So far measure.header.repeatAlternative is always 0.
                else:
                    track.extend(measure)
                    measure.clear()

                    track_data.extend(repeat_group_data)
                    repeat_group_data.clear()
        return track, track_data

    @property
    def length(self):
        lengths = []
        for track in self.song:
            seconds = 0
            for beat in track:
                seconds += beat.seconds
            min, sec = str(int(seconds // 60)), str(int(seconds % 60))
            lengths.append(min + ":" + sec)
        return lengths

    def print_song(self):
        for i, track in enumerate(self.song):
            for j, beat in enumerate(track):
                print("\t", j, beat.frets, beat.notes, beat.seconds)

    def print_song_data(self):
        for i, track in enumerate(self.song_data, 1):
            seconds = 0
            header_time = 0
            for j, measure in enumerate(track, 1):
                header = measure[0]
                print("Track {}  MeasureHeader {}  Measure {}".format(i, header.number, j))
                print("isRepeatOpen: {}  repeatClose: {}  repeatAlternative: {}".format(header.isRepeatOpen,
                                                                                        header.repeatClose,
                                                                                        header.repeatAlternative))
                for beat in measure[1:]:
                    print("\t", beat.frets, beat.notes, beat.seconds)
                    seconds += beat.seconds
                header_time += header.length/960 * (self.gp_song.tempo / 60) ** (-1)
                print("\t", "HeaderTime {}  CalcTime {}".format(header_time, seconds))

    def del_measures(self, start, stop=None):
        '''
        Problem reading Measure.Header.repeatAlternative causes extra measures to be added.
        Delete the extra measures manually here, then rewrite the song for kivy.
        '''
        start -= 1
        if stop is None:
            stop = start + 1
        for track in range(len(self.song_data)):
            for measure in reversed(range(start, stop)):
                del self.song_data[track][measure]
        self._rewrite_song()

    def _rewrite_song(self):
        song = []
        for track_data in self.song_data:
            track = []
            for measure in track_data:
                track.extend(measure[1:])
            song.append(track)
        self.song = song

    def _sum_and_check_song(self):
        for track in self.gp_song.tracks:
            if not self._sum_and_check_track(track):
                return False
        return True

    def _sum_and_check_track(self, track):
        for measure in track.measures:
            if not self._sum_and_check_measure(measure):
                return False
        return True

    def _sum_and_check_measure(self, measure):
        '''Ensure length of each beat in seconds is correct, and that no beats have been missed.

        We need beat lengths in seconds for GUI.  Calculating this may be error-prone due to
        GuitarPro/PyGuitarPro/music theory. Make sure sum of beats in this measure is equal to the
        measure's length. Calculate this a few different ways to catch any logic errors or issues
        with the guitar pro file.

        Return Bool.
        '''
        BPM = measure.header.tempo.value
        beats_this_measure = measure.header.timeSignature.numerator

        seconds_per_beat = (BPM / 60) ** (-1)
        seconds_this_measure = seconds_per_beat * beats_this_measure
        seconds_counted_this_measure_1, seconds_counted_this_measure_2 = 0, 0
        for voice in measure.voices[:-1]:
            for beat in voice.beats:
                # Calculate seconds for rests and notes.
                # Rests == Beat with Beat.Duration but w/o Beat.Note object.
                seconds_counted_this_measure_1 += self._get_beat_length_1(beat)
                seconds_counted_this_measure_2 += self._get_beat_length_2(measure, beat)

            is_length_correct = isclose(seconds_this_measure, seconds_counted_this_measure_1, abs_tol=0.0001) and isclose(seconds_this_measure, seconds_counted_this_measure_2, abs_tol=0.0001)
        return is_length_correct

    def _get_beat_length_1(self, beat):
        # Guitar Pro does the math.
        return beat.duration.time / 960 * (self.gp_song.tempo / 60) ** (-1)

    def _get_beat_length_2(self, measure, beat):
        # Manually do the math.
        BPM = measure.header.tempo.value
        seconds_per_beat = (BPM / 60) ** (-1)
        unit_beat = measure.header.timeSignature.denominator.value
        percentage_beat = unit_beat / beat.duration.value
        tuplet_feel = beat.duration.tuplet.times / beat.duration.tuplet.enters
        seconds = seconds_per_beat * percentage_beat * tuplet_feel
        if beat.duration.isDotted:
            seconds *= (3 / 2)
        elif beat.duration.isDoubleDotted:
            seconds *= (7 / 4)
        return seconds

    ### Music Theory Section ###
    def _detect_song_key_signatures(self):
        song_keys = []
        for track in self.gp_song.tracks:
            track_keys = self._detect_track_key_signatures(track)
            song_keys.append(track_keys)
        return song_keys

    def _detect_track_key_signatures(self, gp_track):
        track_keys = []
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        note_filter = {
            "C":     0b100000000000,
            "C#/Db": 0b010000000000,
            "D":     0b001000000000,
            "D#/Eb": 0b000100000000,
            "E":     0b000010000000,
            "F":     0b000001000000,
            "F#/Gb": 0b000000100000,
            "G":     0b000000010000,
            "G#/Ab": 0b000000001000,
            "A":     0b000000000100,
            "A#/Bb": 0b000000000010,
            "B":     0b000000000001,
        }
        note_to_int = {
            "C": 2048, "C#/Db": 1024, "D": 512, "D#/Eb": 256,
            "E": 128, "F": 64, "F#/Gb": 32, "G": 16,
            "G#/Ab": 8, "A": 4, "A#/Bb": 2, "B": 1,
        }
        maj_filter = {
            'c_maj':  0b101011010101,
            'cs_maj': 0b110101101010,
            'd_maj':  0b011010110101,
            'ds_maj': 0b101101011010,
            'e_maj':  0b010110101101,
            'f_maj':  0b101011010110,
            'fs_maj': 0b010101101011,
            'g_maj':  0b101010110101,
            'gs_maj': 0b110101011010,
            'a_maj':  0b011010101101,
            'as_maj': 0b101101010110,
            'b_maj':  0b010110101011,
        }
        maj_to_int = {
            'c_maj': 2773, 'cs_maj': 3434, 'd_maj': 1717, 'ds_maj': 2906,
            'e_maj': 1453, 'f_maj': 2774, 'fs_maj': 1387, 'g_maj': 2741,
            'gs_maj': 3418, 'a_maj': 1709, 'as_maj': 2902, 'b_maj': 1451,
        }

        this_measure_key = []
        for gp_measure in gp_track.measures:
            key_filter = 0
            for voice in gp_measure.voices[:-1]:
                for gp_beat in voice.beats:
                    for gp_note in gp_beat.notes:
                        octave, semitone = divmod(gp_note.realValue, 12)
                        note = chrom_scale[semitone]
                        key_filter |= note_filter[note]
            this_measure_key.append(key_filter)
            # If we're starting a repeat group, let this_measure build until its closed.
            if gp_measure.header.isRepeatOpen:
                continue
            # Elif we're closing a group, multiply it by number of repeats and clear it.
            elif gp_measure.header.repeatClose > 0:
                this_measure_key[:] = this_measure_key[:] * gp_measure.header.repeatClose
                track_keys.extend(this_measure_key)
                this_measure_key.clear()

            # Otherwise this is just a regular measure. Add it and clear it.
            # So far measure.header.repeatAlternative is always 0.
            else:
                track_keys.extend(this_measure_key)
                this_measure_key.clear()
        return track_keys

    def _note_counter(self):
        chrom_scale = 'C C#/Db D D#/Eb E F F#/Gb G G#/Ab A A#/Bb B'.split()
        note_counts = []
        for track in self.song:
            track_note_counts, track_note_seconds = {n: 0 for n in chrom_scale}, {n: 0 for n in chrom_scale}
            for beat in track:
                for note in beat.notes:
                    track_note_counts[note] += 1
                    track_note_seconds[note] += beat.seconds
            note_counts.append([track_note_counts, track_note_seconds])
        return note_counts


# WORK IN PROGRESS.  Best way to find key signature(s) of song...?
def test_key_sig_eval():
    mode_filters = {
        'c_maj': 2773, 'cs_maj': 3434, 'd_maj': 1717, 'ds_maj': 2906,
        'e_maj': 1453, 'f_maj': 2774, 'fs_maj': 1387, 'g_maj': 2741,
        'gs_maj': 3418, 'a_maj': 1709, 'as_maj': 2902, 'b_maj': 1451,

        'c_harm_min': 2905, 'cs_harm_min': 3500,'d_harm_min': 1750,'ds_harm_min': 875,
        'e_harm_min': 2485, 'f_harm_min': 3290,  'fs_harm_min': 1645, 'g_harm_min': 2870,
        'gs_harm_min': 1435, 'a_harm_min': 2765, 'as_harm_min': 3430, 'b_harm_min': 1715,

        'c_mel_min': 2901, 'cs_mel_min': 3498,'d_mel_min': 1749,'ds_mel_min': 2922,
        'e_mel_min': 1461, 'f_mel_min': 2778,  'fs_mel_min': 1389, 'g_mel_min': 2742,
        'gs_mel_min': 1371, 'a_mel_min': 2733, 'as_mel_min': 3414, 'b_mel_min': 1707,
    }

    def key_sig_DFS(measure_num, path, num_changes, measure_count):
        global min_changes
        if measure_num == measure_count:
            paths.append([num_changes, path[:]])
            min_changes = min(min_changes, num_changes)
            return
        if num_changes > min_changes:
            return

        for key in candidates_per_measure[measure_num]:
            if path[-1] in candidates_per_measure[measure_num] or not candidates_per_measure[
                measure_num]:
                key_sig_DFS(measure_num + 1, path + [path[-1]], num_changes, measure_count)
            else:
                key_sig_DFS(measure_num+1, path+[key], num_changes+1, measure_count)

    def possible_keys(measure_filter):
        candidate_keys = []
        for key, mode_filter in mode_filters.items():
            cur = measure_filter
            candidate_keys += [key]
            while mode_filter and cur:
                # If there's a note in the measure that isn't in the key, remove key from candidates.
                if cur & 1 and not mode_filter & 1:
                    candidate_keys.pop()
                    break
                mode_filter = mode_filter >> 1
                cur = cur >> 1
        return candidate_keys

    def rank_possible_keys(key):
        return key_popularity[key]

    # Print original data for single track.
    for track in song.key_sigs_per_measure:
        print(track)
        break

    # Flatten tracks into one list of key filters.
    song_keys = []
    for track1, track2 in zip(*song.key_sigs_per_measure):
        song_keys.append(track1 | track2)
    print(song_keys)

    # Analyze possible key sigs per measure.
    candidates_per_measure = []
    for i, measure_filter in enumerate(song_keys):
        candidates_per_measure.append(possible_keys(measure_filter))


    key_counter = Counter()
    for group in candidates_per_measure:
        key_counter += Counter(group)
    key_popularity = {key: i for i, (key, val) in enumerate(key_counter.most_common())}
    for candidates in candidates_per_measure:
        candidates.sort(key=rank_possible_keys)
        print(candidates)
    print(list(key_popularity.items()))

    paths = []
    min_changes = float("inf")
    pqueue = [(0, -1, key, [key]) for key in candidates_per_measure[0]]
    heapq.heapify(pqueue)
    while pqueue:
        num_changes, measure_idx, cur_key, path = heapq.heappop(pqueue)
        if -measure_idx == len(candidates_per_measure):
            paths.append(path)
            min_changes = min(min_changes, num_changes)
            break
        elif num_changes < min_changes:
            for key in candidates_per_measure[-measure_idx]:
                if key == cur_key:
                    heapq.heappush(pqueue, (num_changes, -measure_idx+1, key, path + [key]))
                else:
                    heapq.heappush(pqueue, (num_changes + 1, -measure_idx + 1, key, path + [key]))

# TODO: Improve pruning/priority level by using repeat groups.
def test_key_sig_A_star():
    mode_filters = {
        'c_maj': 2773, 'cs_maj': 3434, 'd_maj': 1717, 'ds_maj': 2906,
        'e_maj': 1453, 'f_maj': 2774, 'fs_maj': 1387, 'g_maj': 2741,
        'gs_maj': 3418, 'a_maj': 1709, 'as_maj': 2902, 'b_maj': 1451,

        'c_harm_min': 2905, 'cs_harm_min': 3500, 'd_harm_min': 1750, 'ds_harm_min': 875,
        'e_harm_min': 2485, 'f_harm_min': 3290,  'fs_harm_min': 1645, 'g_harm_min': 2870,
        'gs_harm_min': 1435, 'a_harm_min': 2765, 'as_harm_min': 3430, 'b_harm_min': 1715,

        'c_mel_min': 2901, 'cs_mel_min': 3498,'d_mel_min': 1749,'ds_mel_min': 2922,
        'e_mel_min': 1461, 'f_mel_min': 2778,  'fs_mel_min': 1389, 'g_mel_min': 2742,
        'gs_mel_min': 1371, 'a_mel_min': 2733, 'as_mel_min': 3414, 'b_mel_min': 1707,
    }
    filter_to_mode = {
        2773: 'c_maj',
        3434: 'cs_maj',
        1717: 'd_maj',
        2906: 'ds_maj',
        1453: 'e_maj',
        2774: 'f_maj',
        1387: 'fs_maj',
        2741: 'g_maj',
        3418: 'gs_maj',
        1709: 'a_maj',
        2902: 'as_maj',
        1451: 'b_maj',
        2905: 'c_harm_min',
        3500: 'cs_harm_min',
        1750: 'd_harm_min',
        875: 'ds_harm_min',
        2485: 'e_harm_min',
        3290: 'f_harm_min',
        1645: 'fs_harm_min',
        2870: 'g_harm_min',
        1435: 'gs_harm_min',
        2765: 'a_harm_min',
        3430: 'as_harm_min',
        1715: 'b_harm_min',
        2901: 'c_mel_min',
        3498: 'cs_mel_min',
        1749: 'd_mel_min',
        2922: 'ds_mel_min',
        1461: 'e_mel_min',
        2778: 'f_mel_min',
        1389: 'fs_mel_min',
        2742: 'g_mel_min',
        1371: 'gs_mel_min',
        2733: 'a_mel_min',
        3414: 'as_mel_min',
        1707: 'b_mel_min',
        }


    def flatten_key_sigs_per_measure():
        song_measure_filters = []
        for track1, track2 in zip(*song.key_sigs_per_measure):
            song_measure_filters.append(track1 | track2)
        return song_measure_filters

    def get_measure_candidate_modes(measure):
        candidate_modes = []
        for mode, mode_filter in mode_filters.items():
            measure_filter = measure
            candidate_modes += [mode_filter]
            while mode_filter and measure_filter:
                # If there's a note in the measure that isn't in the key, remove key from candidates
                if measure_filter & 1 and not mode_filter & 1:
                    candidate_modes.pop()
                    break
                mode_filter = mode_filter >> 1
                measure_filter = measure_filter >> 1
        return candidate_modes

    def build_graph(measure_candidate_keys):
        graph = [None] * len(measure_candidate_keys)
        for i, measure in enumerate(measure_candidate_keys):
            node = {mode_filter: float("inf") for mode_filter in measure}
            graph[i] = node
        return graph

    song_measure_filters = flatten_key_sigs_per_measure()
    measure_candidate_modes = [get_measure_candidate_modes(measure) for measure in song_measure_filters]
    graph = build_graph(measure_candidate_modes)
    for mode_filter, cost in graph[0].items():
        graph[0][mode_filter] = 0

    pqueue = [(0, -1, mode_filter, [mode_filter]) for mode_filter in graph[0].keys()]
    heapq.heapify(pqueue)
    result = None
    min_path_cost = float("inf")
    paths = []
    while pqueue:
        # measure_idx is negative so that nodes closer to finishing have priority.
        path_cost, measure_idx, cur_mode, path = heapq.heappop(pqueue)

        # Result.
        if -measure_idx == len(graph)-1:
            paths.append(path[:])
            if path_cost < min_path_cost:
                result = path
                min_path_cost = path_cost
        # Next measure in graph is empty; advance at no cost.
        elif not graph[-measure_idx+1]:
            next_node = (path_cost, measure_idx - 1, cur_mode, path + [cur_mode])
            heapq.heappush(pqueue, next_node)
        # Travel.  No cost to travel when nbr == cur_key modes.
        else:
            for nbr, min_cost_so_far in graph[-measure_idx+1].items():
                edge_cost = bin(cur_mode^nbr).count("1")
                if path_cost + edge_cost < min_cost_so_far:
                    # 9 results without =, 338,000 results with = ...
                    graph[-measure_idx+1][nbr] = path_cost + edge_cost
                    next_node = (path_cost+edge_cost, measure_idx-1, nbr, path+[nbr])
                    heapq.heappush(pqueue, next_node)

    print(result)
    print(len(paths))

    def custom_sort(path):
        return len(set(path))
    paths.sort(key=custom_sort)

    for j, mode in enumerate(paths[0]):
        print("{}: {}".format(j, filter_to_mode[mode]))





# TODO: Clean this up:
# Exports for kivy_app.py (plays track 1).
song = KivySongBuilder()
track = song.song[0]
strings = song.gp_song.tracks[0].strings


