# Motion preview

The 18-second MP4 animates the selected study’s catalogued note timings over this product’s artwork and uses the opening of its existing simple-synth preview audio. On-screen text and captions identify it as a preview, not a master. See `film/motion-manifest.json` for input and output hashes. This is a visualization, not a filmed performance. The audio has not been independently auditioned.

Rebuild from this repository with Python, Pillow and FFmpeg:

```powershell
python tools/render_motion_preview.py --root . --art film/motion-artwork.jpg --output film --name "Uplifting Trance Leads" --bpm 140 --study ut01
```

Rollback: revert the motion-preview commit on the main branch. Existing MIDI, audio previews, release tags, and earlier video assets are preserved.
