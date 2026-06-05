---
name: exhaustive-binary-comparison
description: Systematic methodology for exhaustive multi-dimensional comparison of complex binary files to identify all structural differences
source: auto-skill
extracted_at: '2026-06-03T04:40:00.000Z'
---

# Exhaustive Binary File Comparison Methodology

When you need to find **all** differences between two complex binary files (e.g., AAF, MXF, MOV containers), use a systematic multi-dimensional approach with structured JSON output.

## When to Apply

- Two implementations produce the same binary format but behave differently
- You need to find **every** difference, not just obvious ones
- The format has hierarchical structure (container → header → objects → properties)
- Simple property comparison isn't enough — you need recursive deep inspection
- You're preparing for Pro Tools / downstream tool compatibility testing

## The Three-Layer Comparison Strategy

### Layer 1: Binary Structure Analysis

**Goal**: Compare container-level structure (CFB headers, sectors, hashes)

**Script pattern**: `binary_analysis.py`

```python
import struct
import hashlib

def analyze_binary_structure(file_path):
    """Analyze CFB container structure."""
    with open(file_path, 'rb') as f:
        header = f.read(512)
        
        # CFB signature
        signature = header[0:8]
        is_valid = signature == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        
        # Version info
        minor_version = struct.unpack('<H', header[24:26])[0]
        major_version = struct.unpack('<H', header[26:28])[0]
        
        # Sector size (power of 2)
        sector_shift = struct.unpack('<H', header[30:32])[0]
        sector_size = 1 << sector_shift
        
        # File size
        f.seek(0, 2)
        file_size = f.tell()
        
        # MD5 hash
        f.seek(0)
        file_md5 = hashlib.md5(f.read()).hexdigest()
        
        return {
            'signature_valid': is_valid,
            'major_version': major_version,
            'minor_version': minor_version,
            'sector_size': sector_size,
            'file_size': file_size,
            'md5': file_md5
        }
```

**Key comparisons**:
- Signature validity
- Version numbers (major, minor)
- Sector size (4096 vs 512 vs 1024)
- File size difference
- MD5 hash (to detect any difference)

### Layer 2: Dictionary and Definition Analysis

**Goal**: Compare all definition types (OperationDefs, ParameterDefs, DataDefs, etc.)

**Script pattern**: `audio_structure_analysis.py`

```python
import aaf2

def analyze_dictionary(path):
    """Extract all dictionary definitions."""
    results = {}
    
    with aaf2.open(path) as f:
        # OperationDefinitions
        results['operationdefs'] = []
        for opdef in f.dictionary['OperationDefinitions'].values():
            results['operationdefs'].append({
                'name': opdef.name,
                'uuid': str(opdef.uuid)
            })
        
        # ParameterDefinitions
        results['parameterdefs'] = []
        for paramdef in f.dictionary['ParameterDefinitions'].values():
            results['parameterdefs'].append({
                'name': paramdef.name,
                'uuid': str(paramdef.uuid)
            })
        
        # DataDefinitions
        results['datadefs'] = []
        for datadef in f.dictionary['DataDefinitions'].values():
            results['datadefs'].append({
                'name': datadef.name,
                'uuid': str(datadef.uuid)
            })
        
        # ContainerDefinitions (often many)
        results['containerdefs'] = []
        for cdef in f.dictionary['ContainerDefinitions'].values():
            results['containerdefs'].append({
                'name': cdef.name,
                'uuid': str(cdef.uuid)
            })
    
    return results
```

**Critical finding pattern**: UUID mismatches between files often indicate:
- Different library versions
- Wrong constants in writer code
- Missing definition registrations

### Layer 3: Object Structure Deep Dive

**Goal**: Recursively compare all objects (Mobs, Slots, Segments, Components)

**Script pattern**: `exhaustive_compare.py`

```python
import aaf2
import json

def extract_all_properties(path):
    """Recursively extract all properties from all objects."""
    results = {
        'header': {},
        'mobs': [],
        'essence_data': []
    }
    
    with aaf2.open(path) as f:
        # Header properties
        results['header'] = {
            'version': str(f.header['Version'].value),
            'creation_date': str(f.header['CreationDate'].value)
        }
        
        # Walk all mobs
        for mob in f.content.mobs:
            mob_info = {
                'type': type(mob).__name__,
                'name': mob.name if hasattr(mob, 'name') else 'N/A',
                'mob_id': str(mob.mob_id),
                'slots': []
            }
            
            # Walk all slots
            for slot in mob.slots:
                slot_info = {
                    'slot_id': slot.slot_id,
                    'edit_rate': str(slot.edit_rate),
                    'segment': describe_segment_recursive(slot.segment)
                }
                mob_info['slots'].append(slot_info)
            
            results['mobs'].append(mob_info)
    
    return results

def describe_segment_recursive(segment, depth=0):
    """Recursively describe a segment and all its children."""
    if depth > 10:  # Prevent infinite recursion
        return {'type': type(segment).__name__, 'truncated': True}
    
    info = {
        'type': type(segment).__name__,
        'length': getattr(segment, 'length', None),
        'start': getattr(segment, 'start', None)
    }
    
    # OperationGroup specific properties
    if type(segment).__name__ == 'OperationGroup':
        if hasattr(segment, 'operation') and segment.operation:
            info['operation'] = {
                'name': segment.operation.name,
                'uuid': str(segment.operation.uuid)
            }
        
        # Parameters
        info['parameters'] = []
        for param in segment.parameters:
            param_info = {
                'type': type(param).__name__,
                'name': param.name if hasattr(param, 'name') else 'N/A'
            }
            if hasattr(param, 'parameterdef') and param.parameterdef:
                param_info['paramdef_name'] = param.parameterdef.name
                param_info['paramdef_uuid'] = str(param.parameterdef.uuid)
            info['parameters'].append(param_info)
        
        # Input segments (recursive)
        info['input_segments'] = []
        for inp in segment.segments:
            info['input_segments'].append(
                describe_segment_recursive(inp, depth + 1)
            )
    
    # SourceClip specific properties
    elif type(segment).__name__ == 'SourceClip':
        if segment.get('StartTime'):
            info['start_time'] = segment['StartTime'].value
        if segment.get('SourceID'):
            info['source_id'] = str(segment['SourceID'].value)
    
    # Sequence components (recursive)
    elif type(segment).__name__ == 'Sequence':
        if hasattr(segment, 'components'):
            info['components'] = []
            for comp in segment.components:
                info['components'].append(
                    describe_segment_recursive(comp, depth + 1)
                )
    
    return info
```

## Comparison and Categorization

### Recursive Comparison Function

```python
from collections import defaultdict

def compare_recursive(obj1, obj2, path=""):
    """Recursively compare two objects, return categorized differences."""
    diffs = []
    
    # Handle dictionaries
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            
            if key not in obj1:
                diffs.append({
                    'type': 'missing_in_file1',
                    'path': new_path,
                    'value': obj2[key]
                })
            elif key not in obj2:
                diffs.append({
                    'type': 'missing_in_file2',
                    'path': new_path,
                    'value': obj1[key]
                })
            else:
                diffs.extend(compare_recursive(obj1[key], obj2[key], new_path))
    
    # Handle lists
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            diffs.append({
                'type': 'length_mismatch',
                'path': path,
                'file1_length': len(obj1),
                'file2_length': len(obj2)
            })
        
        for i, (item1, item2) in enumerate(zip(obj1, obj2)):
            diffs.extend(
                compare_recursive(item1, item2, f"{path}[{i}]")
            )
    
    # Handle scalar values
    else:
        if obj1 != obj2:
            diffs.append({
                'type': 'value_diff',
                'path': path,
                'file1_value': obj1,
                'file2_value': obj2
            })
    
    return diffs
```

### Severity Categorization

```python
def categorize_differences(diffs):
    """Categorize differences by severity and type."""
    categories = {
        'CRITICAL': [],  # Pro Tools will reject
        'HIGH': [],      # May cause issues
        'MEDIUM': [],    # Cosmetic or minor
        'LOW': []        # Ignorable
    }
    
    for diff in diffs:
        path = diff['path']
        
        # CRITICAL: UUID mismatches, missing OperationGroups
        if 'uuid' in path.lower() and 'operationdef' in path.lower():
            categories['CRITICAL'].append(diff)
        elif 'operationgroup' in path.lower() and diff['type'] == 'missing_in_file2':
            categories['CRITICAL'].append(diff)
        elif 'start_time' in path and diff.get('file1_value', 0) != 0:
            categories['CRITICAL'].append(diff)
        
        # HIGH: Parameter name mismatches, length differences
        elif 'parameter' in path.lower() and 'name' in path.lower():
            categories['HIGH'].append(diff)
        elif 'length' in path.lower() and diff['type'] == 'value_diff':
            categories['HIGH'].append(diff)
        
        # MEDIUM: Mob name differences, ordering
        elif '.name' in path and 'mob' in path.lower():
            categories['MEDIUM'].append(diff)
        elif diff['type'] == 'length_mismatch' and 'mobs' in path:
            categories['MEDIUM'].append(diff)
        
        # LOW: Timestamps, container definitions
        elif 'creation_date' in path or 'timestamp' in path:
            categories['LOW'].append(diff)
        elif 'containerdef' in path.lower():
            categories['LOW'].append(diff)
        
        # Default to MEDIUM
        else:
            categories['MEDIUM'].append(diff)
    
    return categories
```

## Report Generation

### JSON Output Structure

```python
import json

def generate_comparison_report(file1, file2, output_path):
    """Generate comprehensive comparison report."""
    
    # Extract all data
    data1 = extract_all_properties(file1)
    data2 = extract_all_properties(file2)
    
    # Compare recursively
    all_diffs = compare_recursive(data1, data2)
    
    # Categorize
    categories = categorize_differences(all_diffs)
    
    # Build report
    report = {
        'files': {
            'file1': str(file1),
            'file2': str(file2)
        },
        'summary': {
            'total_differences': len(all_diffs),
            'critical': len(categories['CRITICAL']),
            'high': len(categories['HIGH']),
            'medium': len(categories['MEDIUM']),
            'low': len(categories['LOW'])
        },
        'differences': all_diffs,
        'categories': categories
    }
    
    # Write JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report
```

## Script Organization Pattern

Create these scripts in a `diagnostics/` directory:

1. **binary_analysis.py** - Layer 1: CFB structure
2. **audio_structure_analysis.py** - Layer 2: Dictionary definitions
3. **exhaustive_compare.py** - Layer 3: Recursive object comparison
4. **verify_operationdef_uuid.py** - Specific UUID verification
5. **length_compare.py** - Component length analysis
6. **investigate_start_times.py** - SourceClip start time analysis

Each script should:
- Take file paths as command-line arguments or constants
- Output structured JSON to `diagnostics/*.json`
- Print human-readable summary to console
- Be runnable independently

## Common Patterns

### Safe Property Access

```python
def safe_get(obj, key, default=None):
    """Safely get property value from pyaaf2 objects."""
    try:
        return obj[key].value
    except (KeyError, AttributeError):
        return default
```

### Mob Type Grouping

```python
def group_mobs_by_type(mobs):
    """Group mobs by type for organized comparison."""
    groups = defaultdict(list)
    for mob in mobs:
        mob_type = type(mob).__name__
        groups[mob_type].append(mob)
    return dict(groups)
```

### Length Precision Check

```python
def check_length_precision(length):
    """Check if length is integer or has floating-point residue."""
    if isinstance(length, (int, float)):
        return {
            'value': length,
            'is_integer': length == int(length),
            'integer_part': int(length),
            'fractional_part': length - int(length)
        }
    return {'value': length, 'is_integer': False}
```

## Success Metrics

A successful exhaustive comparison:

1. **Finds ALL differences** - not just obvious ones
2. **Categorizes by severity** - CRITICAL > HIGH > MEDIUM > LOW
3. **Provides actionable paths** - exact property paths to fix
4. **Outputs structured data** - JSON for programmatic analysis
5. **Includes human-readable summary** - console output for quick review

## Common Pitfalls

1. **Shallow comparison**: Only comparing top-level properties misses nested differences
2. **Index-based alignment**: Using list indices instead of object IDs causes cascade errors
3. **Ignoring missing keys**: Not checking for keys present in one file but absent in another
4. **No recursion limit**: Infinite loops in circular references (use depth counter)
5. **Poor categorization**: Treating all differences as equal priority
6. **No JSON output**: Console-only output makes programmatic analysis impossible

## Related Skills

- `binary-format-parity-methodology` - Overall 5-phase parity approach
- `daVinci-resolve-audio-structure-alignment` - Specific audio structure fixes
- `pyaaf2-diagnostic-workflow` - pyaaf2 API patterns and gotchas
