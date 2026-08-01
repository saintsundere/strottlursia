#!/usr/bin/env python3
"""Assemble game/index.html from game/index.template.html + converted music.
Run from Projects/maren-estate:  python3 tools/build.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKS = {
    'coral':   'music/her_shape_in_coral.json',
    'mist':    'music/wistful_mist.json',
    'widow':   'music/wistful_widow.json',
    'posture': 'music/chapel_posture.json',
    'legs':    'music/chapel_legs.json',
}

payload = {}
for key, path in TRACKS.items():
    full = os.path.join(ROOT, path)
    data = json.load(open(full))
    payload[key] = {k: data[k] for k in ('name', 'duration', 'notes')}

tpl = open(os.path.join(ROOT, 'game/index.template.html')).read()
marker = '/*__MUSIC__*/null'
if marker not in tpl:
    sys.exit('marker not found in template')
out = tpl.replace(marker, json.dumps(payload, separators=(',', ':')))
open(os.path.join(ROOT, 'game/index.html'), 'w').write(out)
print('game/index.html written:', len(out), 'bytes,', len(payload), 'tracks')
