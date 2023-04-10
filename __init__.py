from aqt import mw
from aqt import gui_hooks

from anki import hooks
from aqt.operations import QueryOp

from collections import defaultdict
from pathlib import Path
from glob import glob
from collections import defaultdict

import kanji_writing.data
ignore = set(data.ignore)

def hhmmss_to_seconds(hh, mm, ss):
    return hh * 60 * 60 + mm * 60 + ss

subs = defaultdict(list)
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
                    for s in kanji: subs[s].append(((start, end), audio_path, line))
    print(len(subs))
    return subs

process_subs(mw.col)

def dynamic(field_text, field_name, filter_name, ctx):
    if filter_name != "DynamicKanji":
        return field_text
    return field_text + "Works!"

kanji_ease = None
def init():
    def cal_kanji_ease(col):
        kanji_ease = dict({})
        for i in map(lambda i: col.get_note(i), col.find_notes('deck:"08. 漢字::漢字 Writing"')):
            c = i.cards()[0]
            if c.reps == 0: continue
            kanji = set([i for i in i.items() if i[0] == 'Kanji'][0][1]) - ignore
            for k in kanji:
                due1 = kanji_ease.get(k, c.due)
                if c.due <= due1:
                    kanji_ease[k] = c.due
        print(len(kanji_ease))
        return kanji_ease

    def on_success(x): kanji_ease = x
    op = QueryOp(
        parent=mw,
        op=cal_kanji_ease,
        success=on_success,
    ).with_progress().run_in_background()

gui_hooks.main_window_did_init.append(init)
hooks.field_filter.append(dynamic)
