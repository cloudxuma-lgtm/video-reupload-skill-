---
name: video-reupload
description: Process authorized English videos into Chinese-subtitled projects, including download, Whisper transcription, manual or automatic translation, bilingual SRT generation, validation, and archival. Use for the user's video-subtitling/reupload workspace; do not bypass platform restrictions or process content without authorization.
metadata:
  short-description: English video to Chinese bilingual subtitles
---

# Video Reupload

Use this skill for the user's video-subtitling workflow at `D:\codex-workspace\TTS`.

## Operating rules

- Treat each video as an independent project under `D:\codex-workspace\TTS\projects`.
- Preserve `manifest.json` and update the workflow through the provided CLI instead of manually changing stage state.
- Prefer manual or AI-assisted translation with human review for academic, economic, mathematical, and technical content. Automatic MyMemory translation is only a draft.
- Do not overwrite existing transcript, translation, or output files unless the user explicitly requests regeneration; use `--force` only when needed.
- Before archiving, verify that the bilingual SRT exists and the project status is `completed`.
- Only download or process videos the user is authorized to use, and do not bypass DRM, access controls, or platform restrictions.

## Standard workflow

Run commands from `D:\codex-workspace\TTS`:

```powershell
python tools\workflow.py init "VIDEO_URL" --title "TITLE" --download
python tools\workflow.py transcribe VIDEO_ID
python tools\workflow.py translate VIDEO_ID
# Edit projects\VIDEO_ID\translation.zh.tsv and complete the translations.
python tools\workflow.py build VIDEO_ID
python tools\workflow.py status VIDEO_ID
python tools\workflow.py archive VIDEO_ID
```

For a fast draft workflow:

```powershell
python tools\workflow.py run VIDEO_ID --auto-translate
```

Use `python tools\workflow.py list` for active projects and `python tools\workflow.py list --archived` for archived projects.

## Translation requirements

`translation.zh.tsv` must use one cue per line:

```text
cue_id<TAB>Chinese translation
```

Keep cue IDs aligned with `transcript.en.srt`. Preserve names, equations, technical terms, and uncertainty rather than inventing content. For long videos, translate in numbered chunks and merge them only after checking for duplicate or missing cue IDs.

## Validation and recovery

- Use `status VIDEO_ID` after each stage.
- If a command fails, inspect the manifest and existing files before retrying; resume from the first incomplete stage.
- Verify subtitle continuity and translation coverage before publishing.
- Use `transcribe VIDEO_ID --force` only to intentionally regenerate the transcript.
- Consult `D:\codex-workspace\TTS\SKILL.md` or the bundled `references/workspace-SKILL.md` for detailed commands and troubleshooting.

## Available tools

- `tools\workflow.py`: project orchestration, download, transcription, translation, build, status, list, archive, and run.
- `tools\transcribe_to_srt.py`: faster-whisper transcription.
- `tools\build_srt.py`: SRT parsing and bilingual subtitle assembly.
- `tools\make_bilingual_srt.py`: automatic translation draft generation.
