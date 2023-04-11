from aqt import mw
from aqt import gui_hooks

from anki import hooks
from aqt.operations import QueryOp

import os
import random

from collections import defaultdict
from pathlib import Path
from glob import glob
from collections import defaultdict

from functools import reduce
from pprint import pprint

import kanji_writing.data

ignore = set(data.ignore)
identity = lambda *args: args
kanji_only = lambda x: set(x) - ignore

def hhmmss_to_seconds(hh, mm, ss):
    return hh * 60 * 60 + mm * 60 + ss

MEDIA_EXTENSIONS = ['mkv', 'mp4', 'mp3', 'm4b', 'm4a', 'aac', 'flac']

def get_audio_file(path):
    path = Path(str(path).split('.')[0])
    z = [u for ext in MEDIA_EXTENSIONS if ((u := path.with_suffix('.' + ext)).exists())] + ['/dev/null']
    return z[0]

def srt_to_timings(content, with_indicies=False):
    out = []
    f = 1 if with_indicies else 0
    for i in content:
        n = i.strip().split('\n')
        timings = tuple([hhmmss_to_seconds(*map(float, x.split(":"))) for x in n[f].replace(",", ".").split(" --> ")])
        out.append((timings, ''.join(n[f+1:])))
    return out

class Addon:
    def __init__(self):
        self.subs = defaultdict(set)
        self.kanji_ease = dict({})
        self.ease_max = 0
        self.config = mw.addonManager.getConfig(__name__)
        self.queue = {}

        QueryOp(
            parent=mw,
            op=self.load_ease,
            success=identity
        ).with_progress().run_in_background()
        QueryOp(
            parent=mw,
            op=self.process_subs,
            success=identity
        ).with_progress().run_in_background()

    def process_subs(self, col):
        for i in self.config['paths']:
            for i in map(Path, glob(i + "/**.vtt") + glob(i + "/**.srt")):
                with i.open() as f:
                    content = f.read().strip().split('\n\n')
                    if i.suffix == '.vtt': content = content[1:]
                    audio_path = get_audio_file(i)
                    for timings, line in srt_to_timings(content, with_indicies=(i.suffix == '.srt')):
                        for s in kanji_only(line): self.subs[s].add((timings, audio_path, line))
        print(len(self.subs))
        # return self.subs

    def load_ease(self, col):
        for i in map(col.get_note, col.find_notes(f'deck:"{self.config["deck"]}"')):
            c = i.cards()[0]
            if c.reps == 0: continue
            for k in kanji_only([i for i in i.items() if i[0] == 'Kanji'][0][1]):
                self.kanji_ease[k] = min(self.kanji_ease.get(k, c.due), c.due)
                self.ease_max = max(self.kanji_ease[k], self.ease_max)
        print(len(self.kanji_ease))
        # return (self.kanji_ease, self.ease_max)

    def dynamic(self, field_text, field_name, filter_name, ctx):
        if filter_name != "DynamicKanji": return field_text
        card_id = ctx.card().id
        if card_id in self.queue:
            out = self.queue[card_id]#[1]#card
            del self.queue[card_id]
            return '\n<br>\n'.join(out)

        kanji = sorted(kanji_only(field_text), key=lambda x: self.kanji_ease.get(x, self.ease_max))
        sentences = reduce(set.intersection, [self.subs[i] for i in kanji])

        n = 0 # If we can't find a sentence with both kanji, use the kanji with the lowest ease
        while len(sentences) == 0 and n < len(kanji):
            sentences = self.subs[kanji[n]]
            n += 1
        if n == len(kanji): return ""  # TODO(YM): No sentences exist in the current database, use the sentence provided in the card

        def value(sen):
            senkanji = kanji_only(sen)
            return sum([self.ease_max - self.kanji_ease.get(i, self.ease_max) for i in senkanji]) / len(senkanji) * len(sen)

        timings, file, sentence = random.choice(sorted(sentences, key=value)[:5])
        if os.path.islink('/tmp/whatever'): os.unlink('/tmp/whatever')
        os.symlink(file, '/tmp/whatever')
        # Requires advanced mpv player
        self.queue[card_id] = (sentence, f'[sound:/tmp/whatever --vid=no --start=+{timings[0]-0.1} --end=+{timings[1]+0.1}]')
        # return sentence + '\n' + f'[sound:/tmp/whatever --vid=no --start=+{timings[0]-0.1} --end=+{timings[1]+0.1}]'
        return self.queue[card_id][1]

def init():
    addon = Addon()
    hooks.field_filter.append(addon.dynamic)
gui_hooks.main_window_did_init.append(init)
