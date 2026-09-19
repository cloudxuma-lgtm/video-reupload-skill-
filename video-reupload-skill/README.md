# Video Reupload Skill

Codex skill and local CLI workflow for turning authorized English videos into Chinese bilingual subtitles.

## Features

- Project-based workflow with `manifest.json`
- Optional YouTube/Bilibili download through `yt-dlp`
- English transcription through `faster-whisper`
- Manual or automatic Chinese translation
- Bilingual SRT generation
- Status tracking, resumable stages, and project archival

## Repository contents

```text
SKILL.md                 # Codex skill instructions
agents/openai.yaml       # Codex display metadata
tools/workflow.py        # Main workflow CLI
tools/transcribe_to_srt.py
tools/build_srt.py
tools/make_bilingual_srt.py
references/full-workflow.md
```

Runtime directories such as `projects/`, `models/`, `archive/`, `output/`, and local media are intentionally excluded from this repository.

## Requirements

- Python 3.10+
- FFmpeg available on `PATH`
- `faster-whisper`
- `yt-dlp` (optional, for downloading videos)

```powershell
pip install faster-whisper yt-dlp
```

## Quick start

Run commands from the repository root:

```powershell
python tools\workflow.py init "VIDEO_URL" --title "TITLE" --download
python tools\workflow.py transcribe VIDEO_ID
python tools\workflow.py translate VIDEO_ID
# Edit projects\VIDEO_ID\translation.zh.tsv
python tools\workflow.py build VIDEO_ID
python tools\workflow.py status VIDEO_ID
python tools\workflow.py archive VIDEO_ID
```

For a fast automatic draft:

```powershell
python tools\workflow.py run VIDEO_ID --auto-translate
```

Automatic translation is a draft and should be reviewed before publication, especially for academic or technical material.

## Translation format

`translation.zh.tsv` uses one cue per line:

```text
cue_id<TAB>Chinese translation
```

Keep cue IDs aligned with the source SRT. For long videos, translate in numbered chunks and check for missing or duplicate IDs before building the final subtitle file.

## Authorization and platform safety

Use this workflow only for content you are authorized to download, translate, and redistribute. It does not bypass DRM, access controls, or platform restrictions.

## Skill installation

Copy this repository folder into:

```text
%USERPROFILE%\.codex\skills\video-reupload
```

Then restart or refresh Codex so the skill is discovered.
