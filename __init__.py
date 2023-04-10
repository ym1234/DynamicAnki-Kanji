from aqt import mw
from aqt import gui_hooks

from anki import hooks
from aqt.operations import QueryOp

import subprocess

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

def hhmmss_to_seconds(hh, mm, ss):
    return hh * 60 * 60 + mm * 60 + ss

subs = defaultdict(set)
def process_subs(col):
    # subs = defaultdict(list)
    dirs = ["/home/ym/SSD/Audiobook Collection Part 1"]
    for i in dirs:
        for i in map(Path, glob(i + "/**.vtt")):
            with i.open() as f:
                content = f.read().split('\n\n')[1:]
                for z in content:
                    n = z.strip().split('\n')
                    start, end = [hhmmss_to_seconds(*map(float, x.split(":"))) for x in n[0].replace(",", ".").split(" --> ")]
                    line = ''.join(n[1:])
                    kanji, audio_path = set(line) - ignore, i.parent / (i.stem + '.m4b')
                    for s in kanji: subs[s].add(((start, end), audio_path, line))
    print(len(subs))
    return subs

process_subs(mw.col)

kanji_ease = None
def init():
    def cal_kanji_ease(col):
        kanji_ease = dict({})
        for i in map(lambda i: col.get_note(i), col.find_notes('deck:"08. 漢字::漢字 Writing"')):
            c = i.cards()[0]
            if c.reps == 0: continue
            for k in set([i for i in i.items() if i[0] == 'Kanji'][0][1]) - ignore:
                due1 = kanji_ease.get(k, c.due)
                if c.due <= due1:
                    kanji_ease[k] = c.due
        print(len(kanji_ease))
        return kanji_ease

    def on_success(x):
        global kanji_ease
        kanji_ease = x
    op = QueryOp(
        parent=mw,
        op=cal_kanji_ease,
        success=on_success,
    ).with_progress().run_in_background()

def dynamic(field_text, field_name, filter_name, ctx):
    if filter_name != "DynamicKanji":
        return field_text
    kanji = sorted(set(field_text) - ignore, key=kanji_ease.__getitem__)
    sentences = reduce(set.intersection, [subs[i] for i in kanji])

    n = 0
    if len(sentences) == 0 and n < len(kanji):
        sentences = subs[kanji[n]]
        n += 1
    if n == len(kanji): # TODO(YM): No sentences exist in the current database, use the sentence provided in the card
        return field_text + "No Sentences!"

    def value(x):
        return random.random() * 100

    sentences = sorted(sentences, key=value)
    temp, file, sentence = sentences[0]
    start, end = temp
    if os.path.exists('/tmp/whatever.m4b'):
        os.unlink('/tmp/whatever.m4b')
    os.symlink(file, '/tmp/whatever.m4b')
    # subprocess.call([
    #     'ffmpeg',
    #     '-hide_banner',
    #     '-loglevel', 'error',
    #     '-y',
    #     '-i', file,
    #     '-preset', 'fast',
    #     '-ss', str(start),
    #     '-t', str(end - start),
    #     # '-codec', 'copy',
    #     '/tmp/whatever.aac',
    # ])
    # Requires advanced mpv player
    return sentence + '\n' + f'[sound:/tmp/whatever.m4b --start=+{start-0.1} --end=+{end+0.1}]'

gui_hooks.main_window_did_init.append(init)
hooks.field_filter.append(dynamic)
