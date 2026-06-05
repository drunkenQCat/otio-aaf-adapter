---
name: aaf-track-length-synchronization
description: Fix AAF export track length inconsistency by reading actual audio properties and padding to uniform duration
source: auto-skill
extracted_at: '2026-06-02T09:16:03.182Z'
---

# AAF Track Length Synchronization

## Problem

When exporting multi-track audio timelines to AAF format, different audio tracks may end up with different total lengths due to:

1. **Hardcoded sample rate** (e.g., always 48000 Hz) ignoring actual WAV file properties
2. **Frame truncation errors** accumulating differently per track (each clip/gap uses `int()` conversion)
3. **No global duration target** - each track independently sums its components

This causes Pro Tools and other DAWs to reject the AAF file or display incorrect timeline lengths.

## Solution

### 1. Read Actual Audio Properties from WAV Files

Never hardcode sample rate or bit depth. Read from the first available WAV file in the timeline:

```python
@property
def audio_sampling_rate(self):
    """Get the audio sampling rate from the first audio clip's WAV file."""
    self._ensure_wav_info()
    return self._cached_sample_rate

@property
def audio_bits_per_sample(self):
    """Get the audio bit depth from the first audio clip's WAV file."""
    self._ensure_wav_info()
    return self._cached_bits_per_sample

def _ensure_wav_info(self):
    """Read sample rate and bit depth from the first available WAV file."""
    if hasattr(self, '_cached_sample_rate'):
        return

    import struct
    import os
    for child in self.otio_track:
        if not hasattr(child, 'media_reference') or not child.media_reference:
            continue
        mr = child.media_reference
        if not hasattr(mr, 'target_url') or not mr.target_url:
            continue
        wav_path = mr.target_url.replace("file:///", "").replace("/", os.sep)
        try:
            with open(wav_path, 'rb') as wf:
                header = wf.read(4096)
            if len(header) >= 44 and header[0:4] == b'RIFF' and header[8:12] == b'WAVE':
                pos = 12
                while pos + 8 <= len(header):
                    chunk_id = header[pos:pos + 4]
                    chunk_size = struct.unpack_from('<I', header, pos + 4)[0]
                    if chunk_id == b'fmt ':
                        self._cached_sample_rate = struct.unpack_from('<I', header, pos + 12)[0]
                        self._cached_bits_per_sample = struct.unpack_from('<H', header, pos + 22)[0]
                        return
                    pos += 8 + chunk_size
        except (OSError, FileNotFoundError):
            continue

    self._cached_sample_rate = 48000
    self._cached_bits_per_sample = 16
```

### 2. Calculate Target Duration Based on Timeline + 1 Frame

The target audio duration should match the timecode length. **Use `int()` + 1, NOT `math.ceil()` + 1** — the latter adds an extra frame when the duration has a fractional part.

```python
# Get audio sampling rate from the first audio track's WAV file
audio_sampling_rate = 48000  # Default
for otio_track in timeline.tracks:
    if otio_track.kind == "Audio" and len(otio_track) > 0:
        transcriber = otio2aaf.track_transcriber(otio_track)
        audio_sampling_rate = transcriber.audio_sampling_rate
        break

# Calculate target audio duration in samples for all tracks
target_audio_duration_samples = None
timeline_duration = timeline.duration()
if timeline_duration:
    # ⚠️ CRITICAL: Use int() + 1, NOT math.ceil() + 1
    # For 16931.5 frames:
    #   int(16931.5) + 1 = 16932 ✅ (matches DaVinci Resolve)
    #   ceil(16931.5) + 1 = 16933 ❌ (extra frame = 2000 samples at 48kHz)
    #
    # The timecode length formula in add_timecode_first() uses int() + 1,
    # so the audio target must use the SAME formula to stay in sync.
    frames = int(timeline_duration.value) + 1
    duration_seconds = frames / timeline_duration.rate
    target_audio_duration_samples = int(duration_seconds * audio_sampling_rate)
```

**Why `int()` + 1, not `ceil()` + 1**:
- `int(16931.5) + 1 = 16932` — correct, matches timecode track length
- `ceil(16931.5) + 1 = 16933` — wrong, adds 1 extra frame
- The extra frame = 2000 samples at 48kHz = ~42ms of audio drift
- DaVinci Resolve uses `ceil(16931.5) = 16932` (no +1), which equals `int() + 1` for half-frame values

### 3. Pad All Audio Tracks to Target Duration

After transcribing each audio track, add a Filler component to reach the target length:

```python
# For audio tracks, pad to target timeline duration
# This ensures all audio tracks have exactly the same length
if transcriber.media_kind == "sound" and target_audio_duration_samples:
    current_length = transcriber.sequence.length
    filler_length = target_audio_duration_samples - current_length

    # Add filler if track is shorter than target duration
    if filler_length > 0:
        filler = f.create.Filler("sound", filler_length)
        transcriber.sequence.components.append(filler)
        transcriber.sequence.length = target_audio_duration_samples
```

### 4. Cache Transcriber Instances

Prevent duplicate mobslot creation by caching transcribers:

```python
def track_transcriber(self, otio_track):
    """Return an appropriate _TrackTranscriber given an otio track.
    Results are cached to avoid duplicate mobslot creation."""
    if not hasattr(self, '_transcriber_cache'):
        self._transcriber_cache = {}
    
    track_id = id(otio_track)
    if track_id in self._transcriber_cache:
        return self._transcriber_cache[track_id]
    
    if otio_track.kind == otio.schema.TrackKind.Video:
        transcriber = VideoTrackTranscriber(self, otio_track)
    elif otio_track.kind == otio.schema.TrackKind.Audio:
        transcriber = AudioTrackTranscriber(self, otio_track)
    else:
        raise otio.exceptions.NotSupportedError(
            f"Unsupported track kind: {otio_track.kind}"
        )
    
    self._transcriber_cache[track_id] = transcriber
    return transcriber
```

## Verification

After implementing these fixes:

1. **All audio tracks must have identical length** (in samples)
2. **Length should match timecode** (timeline frames + 1) × audio_sampling_rate / frame_rate
3. **Parity gate should pass** (no L2/L3 failures related to track length)

Example verification:
```
Correct: Slot[3] edit_rate=48000 name='叶经理_1' seg=Sequence len=33864000
Test:    Slot[3] edit_rate=44100 name='叶经理_1' seg=Sequence len=31114387
```

Note: Different sample rates (48000 vs 44100) produce different sample counts, but **all tracks within the same file must be identical**.

## Common Pitfalls

1. **Hardcoding 48000 Hz** - Always read from WAV files, never assume
2. **Using timeline duration directly** - Must add +1 frame to match timecode
3. **Creating multiple transcribers** - Cache to avoid duplicate mobslots
4. **Forgetting bit depth** - WAVEDescriptor.Summary also needs bits_per_sample from WAV

## Related Skills

- `audio-transcoding-pipeline` — **Prerequisite**: Transcode audio files to target format before export. The sample rate read here must match the transcoded files' format.
- `pyaaf2-diagnostic-workflow` - For debugging AAF structure issues and OTIO path handling
- `binary-format-parity-methodology` - For comparing AAF files at binary level
