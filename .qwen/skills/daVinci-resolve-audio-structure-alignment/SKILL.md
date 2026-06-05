---
name: daVinci-resolve-audio-structure-alignment
description: Align AAF audio track structure with DaVinci Resolve for Pro Tools compatibility - OperationGroup wrapping and length rounding rules
source: auto-skill
extracted_at: '2026-06-03T04:47:42.580Z'
---

# DaVinci Resolve Audio Structure Alignment

## Problem

When exporting AAF files from otio-aaf-adapter, Pro Tools may reject or misinterpret the file because the audio track structure differs from DaVinci Resolve's output:

1. **Missing OperationGroup wrapper**: Audio clips are bare `SourceClip` objects instead of wrapped in `OperationGroup` with Audio Gain effect
2. **Inconsistent length rounding**: Using `round()` or `int()` uniformly causes cumulative length mismatches with DaVinci Resolve

## Discovery: DaVinci Resolve's Length Rounding Rules

Through comparison analysis, DaVinci Resolve uses **different rounding strategies for different component types**:

| Component Type | Rounding Method | Example |
|----------------|-----------------|---------|
| **Clip durations** | `floor()` (向下取整) | 238.511 → 238 frames → 476000 samples |
| **Gap/Filler durations** | `ceil()` (向上取整) | 512.488 → 513 frames → 1026000 samples |

**Why this works**: When OTIO clip durations have fractional frames (e.g., 238.511), `floor` clips truncate the fractional part while `ceil` fillers expand to compensate. The cumulative sum equals the target timeline duration exactly.

### Verification Example

From 飞驰人生测试 data:

```
Correct (DaVinci Resolve):
- Filler[0]: 28524000 = 14262 × 2000 (14262.0 ceil = 14262)
- OperationGroup[1]: 476000 = 238 × 2000 (238.511 floor = 238)
- Filler[2]: 1026000 = 513 × 2000 (512.488 ceil = 513)

Test (After fix):
- Filler[0]: 28524000 ✅
- OperationGroup[1]: 476000 ✅
- Filler[2]: 1026000 ✅
```

## Solution

### 1. Add Audio Gain OperationDefinition AUID

```python
# Audio Gain OperationDefinition (AAF standard MonoAudioGain, matching DaVinci Resolve)
AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("9d2ea894-0968-11d3-8a38-0050040ef7d2")
# Audio Gain uses "Amplitude" ParameterDef (matching DaVinci Resolve)
AAF_PARAMETERDEF_AMPLITUDE = uuid.UUID("e4962321-2267-11d3-8a4c-0050040ef7d2")
```

**CRITICAL UUID CORRECTIONS (discovered 2026-06-03)**:
- OperationDef UUID: `9d2ea894-0968-11d3-8a38-0050040ef7d2` (NOT `e4962321-...`)
- ParameterDef name: `Amplitude` (NOT `ParameterDef_Level`)
- ParameterDef UUID: `e4962321-2267-11d3-8a4c-0050040ef7d2` (NOT `e4962320-...`)

**File identity clarification**:
- `飞驰人生测试_20260515.20260602163810.aaf` = **DaVinci** (golden standard)
- `飞驰人生测试_testdata_new.aaf` = **OTIO export**
- `correct_timeline.aaf` = Simple DaVinci file, no OperationGroup (NOT suitable for UUID reference)

### 2. Modify `aaf_filler()` for Audio — Use ceil

```python
def aaf_filler(self, otio_gap):
    """Convert an otio Gap into an aaf Filler"""
    import math
    gap_duration = otio_gap.visible_range().duration
    if self.media_kind == "sound":
        # DaVinci Resolve uses ceil for Gap/Filler durations
        # This compensates for floor-truncated clip durations
        frame_count = math.ceil(gap_duration.value)
        length = int(frame_count * (self.audio_sampling_rate / gap_duration.rate))
    else:
        length = int(gap_duration.value)
    filler = self.aaf_file.create.Filler(self.media_kind, length)
    return filler
```

### 3. Modify `aaf_sourceclip()` for Audio — Use floor + Wrap in OperationGroup

```python
def aaf_sourceclip(self, otio_clip):
    # ... (create mobs, clips, etc.)
    
    visible_duration = otio_clip.visible_range().duration
    if self.media_kind == "sound":
        # DaVinci Resolve uses floor for Clip durations
        frame_count = int(visible_duration.value)  # floor
        length = int(frame_count * (self.audio_sampling_rate / visible_duration.rate))
    else:
        length = int(visible_duration.value)

    compmob_clip = self.compositionmob.create_source_clip(...)
    
    # Wrap in Audio Gain OperationGroup
    op_group = self._create_audio_gain_opgroup(compmob_clip, length)
    return op_group
```

### 4. Create `_create_audio_gain_opgroup()` Helper

```python
def _create_audio_gain_opgroup(self, source_clip, length):
    """
    Create an Audio Gain OperationGroup wrapping a SourceClip.
    Matches DaVinci Resolve's output structure.
    """
    import aaf2.rational

    # Create OperationDefinition
    op_def = self.aaf_file.create.OperationDef(
        AAF_OPERATIONDEF_AUDIOGAIN, "Audio Gain"
    )
    self.aaf_file.dictionary.register_def(op_def)
    op_def.media_kind = self.media_kind
    datadef = self.aaf_file.dictionary.lookup_datadef(self.media_kind)

    # Required properties
    op_def["IsTimeWarp"].value = False
    op_def["Bypass"].value = 0
    op_def["NumberInputs"].value = 1
    op_def["OperationCategory"].value = "OperationCategory_Effect"
    op_def["DataDefinition"].value = datadef

    # Create Amplitude ParameterDef (NOT ParameterDef_Level!)
    try:
        param_def_level = self.aaf_file.dictionary.lookup_parameterdef("Amplitude")
    except Exception:  # pyaaf2 raises Exception, not KeyError
        def_level_typedef = self.aaf_file.dictionary.lookup_typedef("Rational")
        param_def_level = self.aaf_file.create.ParameterDef(
            AAF_PARAMETERDEF_AMPLITUDE, "Amplitude", "", def_level_typedef
        )
        self.aaf_file.dictionary.register_def(param_def_level)

    # Create ConstantValue with 1.0 gain (no attenuation)
    # 536870912/536870912 = 1.0 in AAFRational representation
    const_value = self.aaf_file.create.ConstantValue()
    const_value.parameterdef = param_def_level
    const_value["Value"].value = aaf2.rational.AAFRational(536870912, 536870912)

    # Create OperationGroup
    op_group = self.aaf_file.create.OperationGroup(op_def, length)
    op_group.media_kind = self.media_kind
    op_group["DataDefinition"].value = datadef
    op_group.segments.append(source_clip)
    op_group["Parameters"].append(const_value)

    return op_group
```

### 5. CRITICAL: SourceClip StartTime Inside OperationGroup Must Be 0

**Discovery (2026-06-03)**: When a SourceClip is wrapped inside an OperationGroup, its StartTime must be **0**, not the timeline offset. The OperationGroup itself handles timeline positioning.

```python
# WRONG - causes Pro Tools to fail:
compmob_clip = self.compositionmob.create_source_clip(
    slot_id=self.timeline_mobslot.slot_id,
    start=int(start),  # ❌ Timeline offset
    length=int(length),
    media_kind=self.media_kind,
)

# CORRECT - matches DaVinci Resolve:
compmob_clip = self.compositionmob.create_source_clip(
    slot_id=self.timeline_mobslot.slot_id,
    start=0,  # ✅ Zero offset
    length=int(length),
    media_kind=self.media_kind,
)
```

**Why**: The OperationGroup is placed in the Sequence with the correct timeline offset. The inner SourceClip references the MasterMob from position 0 (the beginning of the source material). Using a non-zero start causes Pro Tools to read from invalid positions.

### 6. WAVEDescriptor Summary Fallback

WAVEDescriptor requires a Summary property. When the actual WAV file cannot be read, provide a default:

```python
def default_descriptor(self, otio_clip):
    # ... (create descriptor, set SampleRate, Length, etc.)
    
    # Add Summary (WAV header bytes) — read from actual WAV file
    summary = self._build_wav_summary(media, length_samples)
    if summary:
        descriptor["Summary"].value = summary
    else:
        # Provide default Summary if WAV file can't be read
        descriptor["Summary"].value = self._build_default_wav_summary(length_samples)
    
    return descriptor
```

## Structure Comparison

| Property | DaVinci Resolve | Before Fix | After Fix |
|----------|-----------------|------------|-----------|
| Component type | `OperationGroup` | `SourceClip` | `OperationGroup` ✅ |
| Operation name | "Audio Gain" | N/A | "Audio Gain" ✅ |
| Parameter type | `ConstantValue` | N/A | `ConstantValue` ✅ |
| Parameter value | 536870912/536870912 | N/A | 536870912/536870912 ✅ |
| Clip length | floor (e.g., 476000) | round (e.g., 477023) | floor (476000) ✅ |
| Filler length | ceil (e.g., 1026000) | floor (e.g., 1024000) | ceil (1026000) ✅ |

## Verification Checklist

1. Export test AAF with multi-track audio timeline
2. Compare with DaVinci Resolve reference:
   - Check Sequence contains `OperationGroup` (not `SourceClip`)
   - Check OperationGroup.operation.name == "Audio Gain"
   - Check OperationGroup has `ConstantValue` parameter
   - Check all component lengths match exactly
3. Verify parity gate passes for L2 structure checks

## Common Pitfalls

1. **Using `round()` uniformly**: DaVinci Resolve uses different rounding for clips vs fillers
2. **Missing OperationGroup wrapper**: Pro Tools may expect this structure
3. **Wrong exception type**: pyaaf2's `lookup_parameterdef` raises `Exception`, not `KeyError`
4. **Not registering OperationDef**: Must register before creating OperationGroup

## Related Skills

- `aaf-track-length-synchronization` — Related length synchronization issue
- `binary-format-parity-methodology` — Overall parity methodology
- `pyaaf2-diagnostic-workflow` — For debugging AAF structure