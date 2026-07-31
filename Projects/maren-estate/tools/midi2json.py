#!/usr/bin/env python3
"""Convert a Standard MIDI File into a compact JSON note list for the game's
Web Audio player.  Output: {"name","duration","notes":[[start_s,midi,dur_s,vel01],...]}
Usage: midi2json.py input.mid output.json
"""
import json, math, sys


def read_varlen(data, i):
    v = 0
    while True:
        b = data[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not (b & 0x80):
            return v, i


def parse(path):
    data = open(path, "rb").read()
    assert data[:4] == b"MThd", "not a midi file"
    hlen = int.from_bytes(data[4:8], "big")
    fmt = int.from_bytes(data[8:10], "big")
    ntrks = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    assert not (division & 0x8000), "SMPTE timing unsupported"
    i = 8 + hlen

    tracks = []
    for _ in range(ntrks):
        assert data[i:i + 4] == b"MTrk", "bad track chunk"
        tlen = int.from_bytes(data[i + 4:i + 8], "big")
        start = i + 8
        tracks.append(data[start:start + tlen])
        i = start + tlen

    tempo_map = []  # (tick, microseconds per quarter)
    names = []
    raw_notes = []  # (start_tick, midi, end_tick, velocity)

    for tr in tracks:
        i = 0
        tick = 0
        status = 0
        open_notes = {}
        while i < len(tr):
            dt, i = read_varlen(tr, i)
            tick += dt
            b = tr[i]
            if b == 0xFF:
                mtype = tr[i + 1]
                mlen, j = read_varlen(tr, i + 2)
                payload = tr[j:j + mlen]
                if mtype == 0x51:
                    tempo_map.append((tick, int.from_bytes(payload, "big")))
                elif mtype == 0x03:
                    names.append(payload.decode("latin-1"))
                i = j + mlen
                status = 0
            elif b in (0xF0, 0xF7):
                mlen, j = read_varlen(tr, i + 1)
                i = j + mlen
                status = 0
            else:
                if b & 0x80:
                    status = b
                    i += 1
                ev = status & 0xF0
                if ev in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    d1, d2 = tr[i], tr[i + 1]
                    i += 2
                    if ev == 0x90 and d2 > 0:
                        open_notes.setdefault(d1, []).append((tick, d2))
                    elif ev == 0x80 or (ev == 0x90 and d2 == 0):
                        if open_notes.get(d1):
                            st, vel = open_notes[d1].pop(0)
                            raw_notes.append((st, d1, tick, vel))
                elif ev in (0xC0, 0xD0):
                    i += 1

    tempo_map.sort()
    if not tempo_map:
        tempo_map = [(0, 500000)]

    # piecewise tick -> seconds using the tempo map
    seg_starts = []  # (tick, seconds_at_tick, us_per_quarter)
    sec = 0.0
    prev_tick, prev_us = 0, 500000
    if tempo_map[0][0] == 0:
        prev_us = tempo_map[0][1]
    for t, us in tempo_map:
        sec += (t - prev_tick) * prev_us / (division * 1e6)
        seg_starts.append((t, sec, us))
        prev_tick, prev_us = t, us

    def to_sec(tick):
        lo = 0
        base_t, base_s, us = 0, 0.0, seg_starts[0][2] if seg_starts[0][0] == 0 else 500000
        for t, s, u in seg_starts:
            if t <= tick:
                base_t, base_s, us = t, s, u
            else:
                break
        return base_s + (tick - base_t) * us / (division * 1e6)

    notes = []
    for st, midi, en, vel in raw_notes:
        s0, s1 = to_sec(st), to_sec(en)
        notes.append([round(s0, 3), midi, round(max(0.05, s1 - s0), 3), round(vel / 127, 2)])
    notes.sort(key=lambda n: (n[0], n[1]))

    dur = max((n[0] + n[2]) for n in notes) if notes else 0.0
    tempos_bpm = sorted({round(6e7 / us, 1) for _, us in tempo_map})
    lo = min(n[1] for n in notes)
    hi = max(n[1] for n in notes)
    return {
        "name": names[0] if names else "untitled",
        "format": fmt, "tracks": ntrks, "division": division,
        "duration": round(dur, 2), "note_count": len(notes),
        "pitch_range": [lo, hi],
        "tempo_events": len(tempo_map),
        "bpm_min": tempos_bpm[0], "bpm_max": tempos_bpm[-1],
        "notes": notes,
    }


if __name__ == "__main__":
    result = parse(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump(result, f, separators=(",", ":"))
    NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    pcs = {}
    for n in result["notes"]:
        pcs[n[1] % 12] = pcs.get(n[1] % 12, 0) + 1
    top = sorted(pcs.items(), key=lambda kv: -kv[1])[:7]
    print(json.dumps({k: v for k, v in result.items() if k != "notes"}, indent=2))
    print("pitch classes:", ", ".join(f"{NAMES[p]}:{c}" for p, c in top))
