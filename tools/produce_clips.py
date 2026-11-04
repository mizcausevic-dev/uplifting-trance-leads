#!/usr/bin/env python3
"""Produce and verify focused four-bar clips for the approved ten-pack batch."""
import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import build_release as release
import build_footwork as engine

MODES = {
    "dark-edm-chord-vault": ("chords",),
    "nineties-trance-chords-melodies": ("chords", "principal_motif"),
    "bass-house-hooks": ("sub_bass",),
    "tech-house-groove-builder": ("sub_bass",),
    "melodic-house-chord-journeys": ("chords",),
    "house-techno-crossover": ("sub_bass",),
    "hardstyle-anthem-toolkit": ("principal_motif",),
    "disco-funk-chords": ("chords",),
    "progressive-rock-writing-kit": ("principal_motif",),
    "afro-house-inspired-melodies": ("principal_motif",),
    "hip-hop-chord-melody-sketches": ("chords", "principal_motif"),
    "ambientcore-textures": ("chords",),
    "soulful-house-chords": ("chords",),
    "piano-house-hooks": ("principal_motif",),
    "garage-house-grooves": ("sub_bass",),
    "melodic-techno-sequences": ("principal_motif",),
    "dark-techno-melodies": ("principal_motif",),
    "uplifting-trance-leads": ("principal_motif",),
    "afrobeats-inspired-melodies": ("principal_motif",),
    "trap-melody-toolkit": ("principal_motif",),
}
END = 4 * release.BAR_TICKS

def make_clip(notes, name):
    raw = engine.common_meta(name)
    for start, duration, pitch, velocity in notes:
        raw.extend([(start, 3, bytes([0x90, pitch, velocity])), (start+duration, 2, bytes([0x80, pitch, 0]))])
    return engine.midi(0, [engine.track(raw, end_tick=END)])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--pack", choices=MODES, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    pack = dict(release.PACKS[args.pack])
    pack["slug"] = args.pack
    studies = release.configure(root, pack)
    folder = root / "clips"
    folder.mkdir(exist_ok=False)
    records = []
    for study_index, study in enumerate(studies):
        score = release.compose(study, study_index, pack["pattern"])
        for kind in MODES[args.pack]:
            for variation in range(4):
                notes = []
                if kind == "chords":
                    for bar in range(4):
                        pitches = study["chords"][(bar + variation) % 4][:]
                        if variation % 2:
                            pitches = [pitches[1], pitches[2], pitches[0]+12]
                        if variation == 2:
                            pitches = [pitches[0]-12, pitches[1], pitches[2]]
                        for pitch in sorted(pitches):
                            notes.append((bar*release.BAR_TICKS, 1440, pitch, 72 + (bar%2)*8))
                else:
                    start = (8 + variation*4) * release.BAR_TICKS
                    for event in score[kind]:
                        if start <= event["start"] < start + END:
                            local = event["start"] - start
                            # Reserve a different bar of space in each bass study.
                            if kind == "sub_bass" and study_index and local // release.BAR_TICKS == study_index and local % release.BAR_TICKS == 0:
                                continue
                            notes.append((local, min(event["duration"], END-local), event["pitch"], event["velocity"]))
                if not notes:
                    raise ValueError(f"Empty clip: {study['id']} {kind} {variation}")
                label = "chord-progression" if kind == "chords" else ("bass-hook" if kind == "sub_bass" else "melody")
                path = folder / f"{study['id']}-{label}-{variation+1:02d}.mid"
                path.write_bytes(make_clip(notes, f"{study['id']}-{label}-{variation+1:02d}"))
                parsed = engine.parse_midi(path)
                actual = parsed["tracks"][0]["events"]
                if parsed["format"] != 0 or parsed["division"] != 480 or parsed["tracks"][0]["eot"] != END or len(actual) != len(notes) or any(e["duration"] <= 0 for e in actual):
                    raise ValueError(f"Clip validation failed: {path.name}")
                records.append({"path":path.relative_to(root).as_posix(),"study":study["id"],"kind":label,"bars":4,"tempo_bpm":pack["bpm"],"notes":len(notes),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    with (root/"catalog"/"clip-index.csv").open("w",encoding="utf-8",newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    report = {"status":"PASS","files_checked":len(records),"checks":["Reopened each MIDI file","Format 0, 480 PPQ, four-bar end tick","Paired positive-duration notes","Nonempty note events","SHA-256"],"limitations":["Technical validation does not establish listening quality."]}
    (root/"checks"/"clip-validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
    archive = root/"downloads"/f"{args.pack}-midi.zip"
    with zipfile.ZipFile(archive,"a",compression=zipfile.ZIP_DEFLATED) as bundle:
        for record in records:
            bundle.write(root/record["path"],record["path"])
        bundle.write(root/"catalog"/"clip-index.csv","catalog/clip-index.csv")
    with zipfile.ZipFile(archive) as bundle:
        for record in records:
            if hashlib.sha256(bundle.read(record["path"])).hexdigest() != record["sha256"]:
                raise ValueError("Archive clip hash mismatch")
    count = 28 + len(records)
    readme = root/"README.md"
    readme.write_text(readme.read_text(encoding="utf-8")+f"\n## Focused clips\n\nThis pack also includes {len(records)} four-bar standalone MIDI clips in `clips/`, indexed in `catalog/clip-index.csv` and included in the main ZIP. These are derived from the pack's harmonic and melodic material. The download contains {count} MIDI files in total. Clip integrity results are in `checks/clip-validation.json`.\n",encoding="utf-8",newline="\n")
    site = root/"index.html"
    html = site.read_text(encoding="utf-8").replace("Download 28-MIDI archive", f"Download {count}-MIDI archive")
    html = html.replace("</main><footer>", f'<section><h2>Focused MIDI clips</h2><p>{len(records)} four-bar clips are included in the download. <a href="catalog/clip-index.csv">Browse the clip index</a> · <a href="checks/clip-validation.json">Clip validation</a></p></section></main><footer>')
    site.write_text(html,encoding="utf-8",newline="\n")
    release.write_checksums(root)
    print(json.dumps({"pack":args.pack,"clips":len(records),"total_midi":count,"status":"PASS"}))

if __name__ == "__main__":
    main()
