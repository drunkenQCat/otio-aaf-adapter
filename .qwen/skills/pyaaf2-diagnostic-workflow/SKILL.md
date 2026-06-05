---
name: pyaaf2-diagnostic-workflow
description: Patterns for working with pyaaf2 API, MobID manipulation, AAF diagnostic comparisons, and iterative parity fix workflow
source: auto-skill
extracted_at: '2026-06-02T04:11:52.167Z'
---

# pyaaf2 API Patterns and AAF Diagnostic Workflow

## pyaaf2 API Gotchas

The pyaaf2 API has several non-obvious patterns that differ from what scripts might assume:

### Property Access
- **Wrong**: `obj.attr` (AttributeError for most properties)
- **Correct**: `obj[key].value` for property values
- **Safe wrapper**: 
```python
def safe_get(obj, key, default=None):
    try:
        return obj[key].value
    except Exception:
        return default
```

### Header Properties
```python
# IdentificationList (not 'identifications')
idents = list(f.header['IdentificationList'].value)

# ⚠️ CRITICAL: .get() returns Property OBJECTS, NOT values!
# This is a common source of bugs. Always use .value or safe_val().
#
# WRONG (returns Property object like <CompanyName <aafString TypeDefString>>):
#   company = ident.get('CompanyName', 'N/A')
#
# CORRECT patterns:
company = ident['CompanyName'].value          # raises if missing
version = f.header['Version'].value           # Returns dict like {'major': 1, 'minor': 1}
product_version = ident['ProductVersion'].value  # Returns dict or None

# Safe wrapper — always use this instead of .get():
def safe_val(obj, key, default=None):
    try:
        v = obj[key].value
        if isinstance(v, list):
            return list(v)
        return v
    except (KeyError, AttributeError):
        try:
            return getattr(obj, key, default)
        except Exception:
            return default
```

### CompositionMob Slot Alignment

When comparing CompositionMob slots between two AAF files with different slot counts
(e.g., one has an extra video slot), **do not align by index** — this causes cascade false
failures as all subsequent slots get misaligned. Instead, **align by SlotID**:

```python
# For CompositionMob: align by SlotID
slot_map_c = {s.slot_id: s for s in slots_c}
slot_map_t = {s.slot_id: s for s in slots_t}
for sid in sorted(set(slot_map_c) | set(slot_map_t)):
    sc = slot_map_c.get(sid)
    st = slot_map_t.get(sid)
    # Check existence, then compare properties...

# For other mobs (MasterMob, SourceMob): index alignment is fine
# since slot counts should match.
```

### Dictionary Enumeration
```python
# No class_defs() or type_defs() methods
# Use dictionary properties instead:
container_defs = list(f.dictionary['ContainerDefinitions'].value)
data_defs = list(f.dictionary['DataDefinitions'].value)

# Available dictionary keys:
# ContainerDefinitions, DataDefinitions, OperationDefinitions,
# ParameterDefinitions, PluginDefinitions, CodecDefinitions,
# InterpolationDefinitions, KLVDataDefinitions, TaggedValueDefinitions
```

### Mob and Slot Access
```python
# Mobs are accessed via content.mobs
mobs = list(f.content.mobs)

# Slot properties
slot_id = slot.slot_id  # Direct attribute works
edit_rate = slot.edit_rate  # Direct attribute works
physical_track = slot['PhysicalTrackNumber'].value  # Dict-style for this

# Segment access
segment = slot.segment  # Direct attribute
```

### MobID Manipulation (⚠️ CRITICAL: property returns COPY)

The `mob_id` property returns a **copy** of the MobID object, not a reference.
In-place modifications do NOT persist to the AAF file.

```python
# WRONG — modification is lost on save:
mob.mob_id.bytes_le[10] = 0x0d  # silently discarded!

# CORRECT — read, modify, reassign:
mid = mob.mob_id
mid.bytes_le[8] = 0x01
mid.bytes_le[9] = 0x01
mid.bytes_le[10] = 0x0d
mid.bytes_le[11] = 0x43
mob.mob_id = mid  # MUST reassign to persist

# MobID byte layout (32 bytes, bytes_le is little-endian):
# [0:4]   SMPTE label start: 06 0a 2b 34
# [4:8]   Label details:     01 01 01 05
# [8:12]  Material type:     01 01 0f 20  (pyaaf2 default)
#                             01 01 0d 43  (DaVinci Resolve)
# [12:16] Length + instance:  13 00 00 00
# [16:32] UUID material:      (random, unique per mob)
```

### pyaaf2 Installation on Windows (editable mode)

When using `uv pip install -e ./pyaaf2`, editable mode may not work correctly
on Windows — the `.venv\Lib\site-packages\aaf2\` copy may still be a non-editable
install. Always verify:

```python
# Check which file Python actually loads:
import aaf2
print(aaf2.__file__)
# If this points to .venv\Lib\site-packages\ (not pyaaf2/src/),
# you must edit BOTH files or reinstall properly.
```

**Quick fix**: If you need to modify pyaaf2 code (e.g., change Version from 1.2 to 1.1), edit the file in `.venv\Lib\site-packages\aaf2\` directly, since that's what Python actually loads on Windows.

**But first test if the modification is necessary**: For example, AAF Version 1.1 vs 1.2 — test both versions with your downstream tool (e.g., Pro Tools) before committing to a fork. If both work, you don't need to maintain a fork.

### Iterative Fix-Verify Workflow

When fixing AAF parity differences one at a time:
1. Pick one tracker item
2. Make the minimal code change
3. Re-export (`test_export.py` or `parity_gate.py`)
4. Run `parity_gate.py --skip-export` to verify
5. Confirm: target item fixed, no new FAILs introduced
6. If regression test fails, check if it was pre-existing (run `git stash` + test)
7. Only proceed to next item after verification

### Descriptor Properties
```python
# WAVEDescriptor properties
descriptor = mob.descriptor
sample_rate = descriptor['SampleRate'].value
summary = descriptor['Summary'].value  # Returns bytes

# Enumerate all properties
for prop in descriptor.properties():
    name = prop.name
    value = prop.value
```

## Diagnostic Comparison Workflow

When comparing AAF files for parity analysis:

### 1. Run Multiple Scripts in Parallel
Where scripts are independent, run them concurrently to save time:
- Binary comparison (compare_binary.py)
- Semantic comparison (deep_compare_aaf.py)
- Property enumeration (enumerate_properties.py)
- Dictionary comparison (compare_dictionary.py)

### 2. Handle Script Failures Gracefully
Scripts may fail due to API changes. When they do:
- Introspect the actual API: `print(dir(obj))`, `print(obj.keys())`
- Fix the script paths and API calls
- Record both the error and the fix for future reference

### 3. Structured Output Collection
For each diagnostic script, collect:
- Full output (for appendices)
- Key differences found
- Error messages if any
- Map findings to a structured tracker format

### 4. Binary vs Semantic Differences
- Binary differences (byte-level) often cascade from structural differences
- A single semantic difference (e.g., SectorSize) can cause thousands of binary differences
- Focus on semantic layer first, then trace binary differences back to root causes
- **Critical**: When container-level differences dominate (e.g., CFB SectorSize 512 vs 1024 causing 36000+ diff groups out of 36333 total), binary comparison is **useless as a PASS/FAIL criterion**. Use it only as an info/trend metric until container-level parity is achieved.

### 5. Parity Tracker Structure
Organize findings by:
- **Layer**: L0 (CFB container), L1 (Header), L2 (Mob structure), L3 (Descriptors)
- **Controllability**: controllable, pyaaf2-dependent, or whitelisted (uncontrollable)
- **Status**: OPEN, WHITELIST, BLOCKED, FIXED
- **Priority**: Impact on compatibility (e.g., Pro Tools)

## Mob Ordering in AAF Files

### DaVinci Resolve Pattern: Interleaved Per-Clip

DaVinci Resolve outputs mobs **interleaved per clip**, not grouped by type:

```
Correct:  Comp, Master, Tape, File, Master, Tape, File, Master, Tape, File, ...
```

**NOT** (common mistake):
```
Wrong:    Comp, Master, Master, Master, ..., Tape, Tape, ..., File, File, ...
```

### Implementation: Deferred Append with Insertion Order Tracking

The fix is to **not append mobs in the `_unique_*` factory methods**, but instead
track which mobs are new and append them in the correct order in `aaf_sourceclip`:

```python
def aaf_sourceclip(self, otio_clip):
    # Track which mobs are new BEFORE creating them
    mob_id = self.root_file_transcriber._clip_mob_ids_map.get(otio_clip)
    mastermob_is_new = mob_id not in self.root_file_transcriber._unique_mastermobs
    tapemob_is_new = mob_id not in self.root_file_transcriber._unique_tapemobs
    filemob_is_new = mob_id not in self.root_file_transcriber._filemobs

    # Create mobs (but don't append yet)
    tapemob, tapemob_slot = self._create_tapemob(otio_clip)
    filemob, filemob_slot = self._create_filemob(otio_clip, tapemob, tapemob_slot)
    mastermob, mastermob_slot = self._create_mastermob(otio_clip, filemob, filemob_slot)

    # Append in correct order: MasterMob first, then TapeMob, then FileMob
    if mastermob_is_new:
        self.root_file_transcriber._mobs_to_append.append(('master', mastermob))
    if tapemob_is_new:
        self.root_file_transcriber._mobs_to_append.append(('tape', tapemob))
    if filemob_is_new:
        self.root_file_transcriber._mobs_to_append.append(('file', filemob))
```

And `append_all_mobs` simply iterates in insertion order:

```python
def append_all_mobs(self):
    self.aaf_file.content.mobs.append(self.compositionmob)
    for mob_type, mob in self._mobs_to_append:
        self.aaf_file.content.mobs.append(mob)
```

**Key**: The `_unique_mastermob`, `_unique_tapemob`, and `_create_filemob` methods must
**NOT** append to `_mobs_to_append` themselves. The appending is centralized in
`aaf_sourceclip` to control the order.

## OperationDef / ParameterDef UUID Diagnosis

When two AAF files use different UUIDs for the same logical operation (e.g., Audio Gain), the root cause is often **writer code constants**, not pyaaf2 built-ins.

### Diagnostic Pattern

```python
import aaf2

def inspect_opdefs(path):
    """Extract OperationDef and ParameterDef details from an AAF file."""
    results = {'opdefs': [], 'paramdefs': [], 'og_usage': []}
    with aaf2.open(path) as f:
        # Dictionary-level definitions
        for od in f.dictionary['OperationDefinitions'].values():
            results['opdefs'].append({'name': od.name, 'uuid': str(od.uuid)})
        for pd in f.dictionary['ParameterDefinitions'].values():
            results['paramdefs'].append({'name': pd.name, 'uuid': str(pd.uuid)})

        # Actual usage in CompositionMob OperationGroups
        for mob in f.content.mobs:
            if type(mob).__name__ != 'CompositionMob':
                continue
            for slot in mob.slots:
                seg = slot.segment
                if type(seg).__name__ == 'Sequence' and hasattr(seg, 'components'):
                    for i, comp in enumerate(seg.components):
                        if type(comp).__name__ == 'OperationGroup':
                            og = {
                                'slot_id': slot.slot_id,
                                'comp_index': i,
                                'op_name': comp.operation.name if comp.operation else None,
                                'op_uuid': str(comp.operation.uuid) if comp.operation else None,
                                'params': [],
                            }
                            for p in comp.parameters:
                                pi = {
                                    'name': p.name,
                                    'type': type(p).__name__,
                                    'value': str(p.value)[:80],
                                }
                                if hasattr(p, 'parameterdef') and p.parameterdef:
                                    pi['paramdef_name'] = p.parameterdef.name
                                    pi['paramdef_uuid'] = str(p.parameterdef.uuid)
                                og['params'].append(pi)
                            results['og_usage'].append(og)
    return results
```

### Key Insight: UUID Source Priority

1. **pyaaf2 does NOT hardcode Audio Gain UUIDs** — `datadefs.py` does not contain `9d2ea894` or `e4962321` patterns
2. UUIDs come from **writer code constants** (e.g., `aaf_writer.py` L29/L33)
3. When diagnosing mismatches, check in this order:
   - Writer code constants (most likely cause)
   - Writer code string parameters (e.g., `"ParameterDef_Level"` vs `"Amplitude"`)
   - pyaaf2 `dictionary.py` lookup logic (rare)
   - pyaaf2 `datadefs.py` built-ins (rare — grep first to confirm)

### Common UUID Confusion Bug

Writer code may swap OperationDef UUID and ParameterDef UUID by mistake:

```python
# WRONG — UUIDs swapped:
AAF_PARAMETERDEF_LEVEL = uuid.UUID("e4962320-...")  # Actually OpDef UUID
AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("e4962321-...")  # Actually ParamDef UUID

# CORRECT (matching DaVinci Resolve):
AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("9d2ea894-0968-11d3-8a38-0050040ef7d2")
# ParameterDef: name="Amplitude", uuid="e4962321-2267-11d3-8a4c-0050040ef7d2"
```

**Symptom**: Exported file has correct structure but wrong UUIDs. Downstream tools (Pro Tools) may reject it.

### Verifying After Fix

```python
# Quick check: does the exported file now have correct UUIDs?
import aaf2
with aaf2.open('exported.aaf') as f:
    for od in f.dictionary['OperationDefinitions'].values():
        print(f"OpDef: {od.name} = {od.uuid}")
    for pd in f.dictionary['ParameterDefinitions'].values():
        print(f"ParamDef: {pd.name} = {pd.uuid}")
```

## Common Diagnostic Scripts

### Property Enumeration
Use `enumerate_properties.py` to discover all properties in both files, not just known ones. This catches unexpected attributes that DaVinci Resolve sets.

### WAV Summary Analysis
The Summary field contains an embedded WAV header. Parse it byte-by-byte:
- Bytes 4-7: RIFF chunk size (little-endian uint32)
- Bytes 24-27: Sample rate
- Bytes 28-29: Block align
- Bytes 30-31: Bits per sample
- Bytes 40-43: data chunk size

### WAV Summary Generation from Actual Files

AAF WAVEDescriptor Summary is a **standardized 44-byte PCM WAV header** — not a copy
of the actual file's header. DaVinci Resolve reads the actual WAV file and normalizes it.
Common pitfalls:

1. **Never hardcode values** (bits_per_sample=16, channels=1) — the actual WAV may be
   24-bit, multi-channel, etc.
2. **WAV files may have non-standard chunks before `fmt`** — JUNK, bext, LIST chunks
   can push `fmt` past the first 128 bytes. Read at least 4KB to find all chunks.
3. **Extensible WAV format** (audio_format=0xFFFE) must be **standardized to PCM**
   (audio_format=1, fmt_chunk_size=16) in the Summary — DaVinci Resolve does this.
4. **RIFF size and data size must be real values**, not zero placeholders.

```python
def build_wav_summary(media_ref, fallback_sample_rate):
    """Read actual WAV file and build standardized 44-byte Summary."""
    import struct, os

    wav_path = media_ref.target_url.replace("file:///", "").replace("/", os.sep)
    with open(wav_path, 'rb') as f:
        raw = f.read(4096)  # 4KB to find fmt+data chunks past JUNK/bext

    if len(raw) < 44 or raw[0:4] != b'RIFF' or raw[8:12] != b'WAVE':
        return None

    riff_size = struct.unpack_from('<I', raw, 4)[0]

    # Walk chunks — don't assume fmt is at offset 12
    pos = 12
    channels = sample_rate = byte_rate = block_align = bits_per_sample = data_size = 0
    while pos + 8 <= len(raw):
        chunk_id = raw[pos:pos + 4]
        chunk_size = struct.unpack_from('<I', raw, pos + 4)[0]
        if chunk_id == b'fmt ':
            channels = struct.unpack_from('<H', raw, pos + 10)[0]
            sample_rate = struct.unpack_from('<I', raw, pos + 12)[0]
            byte_rate = struct.unpack_from('<I', raw, pos + 16)[0]
            block_align = struct.unpack_from('<H', raw, pos + 20)[0]
            bits_per_sample = struct.unpack_from('<H', raw, pos + 22)[0]
        elif chunk_id == b'data':
            data_size = chunk_size
        pos += 8 + chunk_size

    # Standardize to PCM (audio_format=1, fmt_size=16)
    summary = bytearray(44)
    struct.pack_into('<4s', summary, 0, b'RIFF')
    struct.pack_into('<I', summary, 4, riff_size)
    struct.pack_into('<4s', summary, 8, b'WAVE')
    struct.pack_into('<4s', summary, 12, b'fmt ')
    struct.pack_into('<I', summary, 16, 16)
    struct.pack_into('<H', summary, 20, 1)  # PCM (standardized)
    struct.pack_into('<H', summary, 22, channels)
    struct.pack_into('<I', summary, 24, sample_rate)
    struct.pack_into('<I', summary, 28, byte_rate)
    struct.pack_into('<H', summary, 32, block_align)
    struct.pack_into('<H', summary, 34, bits_per_sample)
    struct.pack_into('<4s', summary, 36, b'data')
    struct.pack_into('<I', summary, 40, data_size)
    return summary
```

### Dictionary Comparison
Compare all Definition lists, not just ClassDefinitions. pyaaf2 may register extra definitions that DaVinci Resolve doesn't include.

### CFB Structure Analysis (L0 Layer)

When investigating binary-level differences that don't map to semantic differences, analyze the Compound File Binary (CFB) container structure:

```python
import aaf2
from aaf2 import cfb
import os

def analyze_cfb_structure(path):
    """Analyze CFB container structure for L0 layer investigation."""
    with open(path, 'rb') as f:
        cfb_file = cfb.CompoundFileBinary(f, 'rb')

        # CFB header properties
        print(f"Sector Size: {cfb_file.sector_size} bytes")
        print(f"Mini Sector Size: {cfb_file.mini_stream_sector_size} bytes")
        print(f"Major Version: {cfb_file.major_version}")
        print(f"Minor Version: {cfb_file.minor_version}")

        # List all streams with sizes
        def list_streams(path_prefix="/"):
            streams = []
            try:
                entries = cfb_file.listdir(path_prefix)
                for entry in entries:
                    full_path = f"{path_prefix}{entry}" if path_prefix.endswith('/') else f"{path_prefix}/{entry}"
                    try:
                        # Try to open as stream
                        size = cfb_file.root.openstream(full_path).size
                        streams.append((full_path, size))
                    except:
                        # It's a storage, recurse
                        streams.extend(list_streams(full_path))
            except:
                pass
            return streams

        streams = list_streams()
        return {
            'sector_size': cfb_file.sector_size,
            'streams': streams
        }

# Compare two files
correct = analyze_cfb_structure("correct_timeline.aaf")
test = analyze_cfb_structure("test_output.aaf")

# Key comparison points:
# 1. SectorSize - pyaaf2 default is 4096 bytes
# 2. Stream count and sizes
# 3. Stream layout (same data at different sector offsets)
```

**Key insights from CFB analysis:**
- **SectorSize differences** (e.g., 512 vs 1024 vs 4096) are structural, not semantic
- **Stream layout differences** (same data at different offsets) are implementation details
- **CFB metadata differences** (FAT tables, Directory Entries) don't affect AAF semantics
- When L1/L2/L3 all PASS but binary diffs remain, they're almost always CFB structural differences

## OTIO Media Reference Path Handling

OTIO's `media_reference.target_url` can arrive in multiple path formats, causing subtle bugs when the export code assumes a specific format:

### Path Format Variants

| Format | Example | Source |
|--------|---------|--------|
| `file:///` URL | `file:///C:/path/to/file.wav` | Standard OTIO export |
| `file://` URL | `file://C:/path/to/file.wav` | Some OTIO versions |
| Windows extended | `\\?\C:\path\to\file.wav` | DaVinci Resolve OTIO export |
| Plain path | `C:\path\to\file.wav` | Manual creation |
| Relative path | `test_data/file.wav` | Test fixtures |

### Robust Path Normalization

Always use this pattern when reading WAV files from OTIO references:

```python
def normalize_media_path(target_url):
    """Convert OTIO target_url to a filesystem path."""
    wav_path = target_url
    # Strip file:/// prefix (3 slashes)
    if wav_path.startswith("file:///"):
        wav_path = wav_path[8:]
        # Windows: /C:/path -> C:\path
        if len(wav_path) >= 2 and wav_path[1] == ':':
            wav_path = wav_path.replace("/", os.sep)
    # Strip file:// prefix (2 slashes)
    elif wav_path.startswith("file://"):
        wav_path = wav_path[7:]
        if len(wav_path) >= 2 and wav_path[1] == ':':
            wav_path = wav_path.replace("/", os.sep)
    # Strip Windows extended-length prefix
    if wav_path.startswith("\\\\?\\"):
        wav_path = wav_path[4:]
    return wav_path
```

### Generating file:// URLs — Use Path.as_uri()

**Always use `pathlib.Path.as_uri()`** instead of manual string concatenation. It handles everything in one call: `file:///` prefix, forward slashes, and URL encoding of non-ASCII characters (Chinese, etc.).

```python
from pathlib import Path

# CORRECT — one-liner, handles all edge cases:
url_string = Path(wav_path).resolve().as_uri()
# Result: file:///C:/TechProjects/path/%E5%8F%B6%E7%BB%8F%E7%90%86/file.wav

# WRONG — manual string manipulation causes endless bugs:
url_string = "file:///" + wav_path.replace("\\", "/")  # Missing URL encoding!
url_string = "file://" + pathname2url(str(Path(p).resolve()))  # Double prefix: file://///C:/...
```

**Why this matters**: DaVinci Resolve's AAF files use `file:///C:/path/%E5%8F%B6...wav` format. Manual approaches produce wrong prefixes (`file://///?/`, `file://///`) or unencoded Chinese characters, causing Pro Tools to report "files not found."

**Path.as_uri() handles**:
- Correct `file:///` prefix (exactly 3 slashes)
- Windows backslash → forward slash conversion
- URL encoding of non-ASCII characters (Chinese → `%E5%8F%B6...`)
- Path normalization via `.resolve()`

**For building URLs from OTIO target_url that may already have prefixes**:

```python
from pathlib import Path

target_url = media.target_url

# Strip any existing file:// prefix first
if target_url.startswith("file:///"):
    target_url = target_url[8:]
elif target_url.startswith("file://"):
    target_url = target_url[7:]

# Strip Windows extended-length prefix \\?\
if target_url.startswith("\\\\?\\"):
    target_url = target_url[4:]

# Path.as_uri() does the rest
url_string = Path(target_url).resolve().as_uri()
```

## Programmatic Markdown Updates

When scripts need to append rows to markdown tables (e.g., convergence logs), use an anchor comment rather than fragile string matching:

```markdown
| 2026-06-02 | 27 | 36333 | 370548 | 初始基线 |
<!-- convergence-log-end -->
```

```python
anchor = "<!-- convergence-log-end -->"
content = open("tracker.md", encoding="utf-8").read()
content = content.replace(anchor, f"{new_row}\n{anchor}")
```

This avoids breakage when the table structure changes.
