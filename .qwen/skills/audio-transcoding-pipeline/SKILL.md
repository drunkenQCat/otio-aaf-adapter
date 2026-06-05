---
name: audio-transcoding-pipeline
description: Automatic audio file transcoding pipeline that detects format, converts non-conforming files, and updates media references before export
source: auto-skill
extracted_at: '2026-06-02T10:15:00.000Z'
---

# Audio Transcoding Pipeline

An automated pipeline that detects audio file formats, transcodes non-conforming files to a target format, and temporarily updates OTIO media references before export. Useful when downstream tools (e.g., Pro Tools, DaVinci Resolve) require specific audio formats.

## When to Apply

- Exporting timelines where source audio files have mixed or non-standard formats
- Downstream tools require specific sample rates, bit depths, or channel counts
- You want to avoid manual pre-processing of audio files
- The export format embeds audio properties (e.g., AAF WAVEDescriptor.Summary)

## Architecture

### Module Separation

Keep transcoding in its **own module**, separate from the export logic:

```
src/your_adapter/
├── adapters/
│   └── your_format.py      # Export logic — calls transcoder, doesn't implement it
└── audio_transcoder.py      # Standalone transcoding module
```

**Why**: Export logic is already complex. Mixing in format detection, file I/O, and ffmpeg calls creates an unmaintainable monolith.

### Core Functions

```python
def transcode_audio_files(timeline, target_sr=48000, target_bits=24, target_channels=1) -> dict:
    """Returns {original_path: converted_path} mapping."""

def update_media_references(timeline, url_mapping) -> dict:
    """Updates OTIO references, returns {converted_path: original_url} for restoration."""

def restore_media_references(timeline, reverse_mapping):
    """Restores original references after export."""
```

## Implementation Steps

### Step 1: Collect Audio Paths

Walk all audio tracks in the OTIO timeline, collecting `media_reference.target_url` values. Handle URL formats:

```python
for track in timeline.tracks:
    if track.kind != 'Audio':
        continue
    for clip in track:
        if not hasattr(clip, 'media_reference') or not clip.media_reference:
            continue
        target_url = clip.media_reference.target_url
        # Strip file:// prefix for path operations
        if target_url.startswith('file://'):
            target_url = target_url[7:]
            if target_url.startswith('/') and len(target_url) > 2 and target_url[2] == ':':
                target_url = target_url[1:]  # Windows: /C:/ -> C:/
        if target_url.lower().endswith('.wav'):
            audio_paths.append(target_url)
```

### Step 2: Find Common Parent Directory

Use `os.path.commonpath()` to find the shared parent:

```python
try:
    common_parent = os.path.commonpath(audio_paths)
    if os.path.isfile(common_parent):
        common_parent = os.path.dirname(common_parent)
except ValueError:
    # No common path (different drives on Windows)
    common_parent = os.getcwd()
```

### Step 3: Create converted/ Subdirectory

```python
converted_dir = os.path.join(common_parent, 'converted')
os.makedirs(converted_dir, exist_ok=True)
```

**Key rule**: The `converted/` directory lives inside the common parent of the source files. This keeps converted files near their sources for easy debugging and Pro Tools access.

### Step 4: Detect and Transcode

For each audio file:
1. Read format using Python's `wave` module (fast, no ffmpeg dependency)
2. Skip if already converted (check `converted/` directory)
3. If format matches target, copy to `converted/` (consistency)
4. If format doesn't match, transcode with pydub

```python
import wave
from pydub import AudioSegment

def get_wav_format(wav_path):
    with wave.open(wav_path, 'rb') as wf:
        return {
            'sample_rate': wf.getframerate(),
            'sample_width': wf.getsampwidth(),  # bytes, not bits
            'channels': wf.getnchannels()
        }

# Transcode with pydub
audio = AudioSegment.from_wav(audio_path)
audio = audio.set_frame_rate(target_sr)
audio = audio.set_sample_width(target_bytes)  # bytes (24-bit = 3)
audio = audio.set_channels(target_channels)
audio.export(converted_path, format="wav", parameters=["-acodec", "pcm_s24le"])
```

**File naming**: `{original_name}_converted.wav` — preserves the original name for traceability.

### Step 5: Update Media References

Update OTIO's `target_url` to point to converted files. **Use `Path.as_uri()`** from Python's standard library — it handles the `file:///` prefix, forward slashes, and URL encoding of non-ASCII characters automatically:

```python
from pathlib import Path

# CORRECT — one-liner, handles all edge cases:
clip.media_reference.target_url = Path(converted_path).resolve().as_uri()
# Result: file:///C:/path/converted/%E5%8F%B6%E7%BB%8F%E7%90%86/file.wav

# WRONG — manual approaches cause bugs:
clip.media_reference.target_url = f"file:///{converted_path}"  # Missing URL encoding
clip.media_reference.target_url = "file://" + pathname2url(...)  # Double prefix: file://///C:/...
```

**Why this matters**: Downstream tools (Pro Tools, DaVinci Resolve) expect properly formatted `file:///` URLs with encoded non-ASCII characters. Manual string manipulation consistently produces wrong prefixes or unencoded Chinese characters.

Store a reverse mapping for restoration:
```python
reverse_mapping[converted_path] = original_url
```

### Step 6: Restore After Export

After the export completes, restore original references so the OTIO timeline object isn't permanently modified:

```python
for track in timeline.tracks:
    for clip in track:
        current_url = clip.media_reference.target_url
        lookup_url = strip_file_prefix(current_url)
        if lookup_url in reverse_mapping:
            clip.media_reference.target_url = reverse_mapping[lookup_url]
```

**Important**: The `update_media_references` function should store the converted path as a **plain filesystem path** (not a `file://` URL), because the export code's `default_descriptor` will handle URL formatting via `Path.as_uri()`. This avoids double-prefix bugs.

```python
# In update_media_references — store plain path, let export handle URL:
clip.media_reference.target_url = converted_path  # plain path, no file:// prefix
```

## Integration into Export Function

```python
def write_to_file(input_otio, filepath, **kwargs):
    # ... setup ...

    # Transcode audio files to target format
    from your_adapter.audio_transcoder import (
        transcode_audio_files,
        update_media_references,
        restore_media_references
    )

    url_mapping = transcode_audio_files(timeline)
    reverse_mapping = {}
    if url_mapping:
        reverse_mapping = update_media_references(timeline, url_mapping)

    # ... normal export logic ...

    # Restore original references
    if reverse_mapping:
        restore_media_references(timeline, reverse_mapping)
```

## Windows Path Handling

Media references can arrive in multiple formats. The key insight is: **use `Path.as_uri()` for URL generation, and a simple normalization function for file I/O.**

| Format | Example | When to strip |
|--------|---------|-------------|
| `file:///` URL | `file:///C:/path/to/file.wav` | When opening file for reading |
| `file://` URL | `file://C:/path/to/file.wav` | When opening file for reading |
| Windows extended | `\\?\C:\path\to\file.wav` | When opening file for reading |
| Plain path | `C:\path\to\file.wav` | Use as-is |
| Relative path | `test_data/file.wav` | Use as-is |

**For file I/O** (opening WAV files to read headers, transcode, etc.):

```python
def normalize_media_path(target_url):
    """Convert OTIO target_url to a filesystem path for file I/O."""
    wav_path = target_url
    if wav_path.startswith("file:///"):
        wav_path = wav_path[8:]
        if len(wav_path) >= 2 and wav_path[1] == ':':
            wav_path = wav_path.replace("/", os.sep)
    elif wav_path.startswith("file://"):
        wav_path = wav_path[7:]
        if len(wav_path) >= 2 and wav_path[1] == ':':
            wav_path = wav_path.replace("/", os.sep)
    if wav_path.startswith("\\\\?\\"):
        wav_path = wav_path[4:]
    return wav_path
```

**For URL generation** (writing to AAF NetworkLocator):

```python
from pathlib import Path

# Always use Path.as_uri() — it handles file:/// prefix, forward slashes,
# and URL encoding of non-ASCII characters (Chinese, etc.)
url_string = Path(normalized_path).resolve().as_uri()
# Result: file:///C:/path/%E5%8F%B6%E7%BB%8F%E7%90%86/file.wav
```

**⚠️ Never manually concatenate `file://` prefixes** — this causes double-prefix bugs (`file://///C:/...`) or missing URL encoding for non-ASCII characters, both of which make Pro Tools report "files not found."

### Common Bug: Double Path Prefix

If `update_media_references` sets `target_url` to a `file://` URL, and then the export code's `default_descriptor` also adds `file:///`, you get `file:///file:///C:/...`. **Solution**: `update_media_references` should store plain paths; let `default_descriptor` handle URL formatting via `Path.as_uri()`.

## Dependencies

```toml
[project]
dependencies = [
    "pydub>=0.25.1",  # Audio processing (wraps ffmpeg)
]
```

**System requirement**: ffmpeg must be installed and on PATH. pydub wraps ffmpeg for format conversion.

## Common Pitfalls

1. **Don't delete converted files** — they need to exist when Pro Tools/DAW reads the exported AAF
2. **Don't hardcode paths** — always compute from the actual media references
3. **Don't mix path formats** — be consistent: use `file:///` URLs in OTIO, plain paths for file I/O
4. **Don't skip the restore step** — leaving modified references in the OTIO object causes subtle bugs if the timeline is used again
5. **Don't transcode in the export module** — keep it in a separate module for testability
6. **Cache already-converted files** — check if `converted/` file exists before re-transcoding
7. **Handle `\\?\` prefix** — Windows extended-length paths break many string operations

## Verification

After transcoding, verify:
1. All converted files exist in `converted/` directory
2. All converted files have target format (use `wave.open()` to check)
3. Exported file references the converted paths
4. Original OTIO references are restored after export

```python
import wave
w = wave.open(converted_path, 'rb')
assert w.getframerate() == 48000
assert w.getsampwidth() == 3  # 24-bit = 3 bytes
assert w.getnchannels() == 1
w.close()
```

## Related Skills

- `aaf-track-length-synchronization` — Track length padding (uses the same sample rate from WAV files)
- `pyaaf2-diagnostic-workflow` — WAV Summary generation (reads from the same converted files)
- `binary-format-parity-methodology` — Overall parity workflow where transcoding fits in
