#!/usr/bin/env python3
"""
AAF File Comparison Script

This script compares AAF files exported from different branches to identify
differences and validate improvements.

Usage:
    python compare_aaf_files.py --file1 exports/dev/test.aaf --file2 exports/pt_compat/test.aaf
    python compare_aaf_files.py --dir1 exports/dev --dir2 exports/pt_compat
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
from collections import defaultdict


def get_aaf_info(aaf_file):
    """Extract information from an AAF file using otio."""
    # Use uv run to ensure we use the correct Python environment
    cmd = [
        'uv', 'run', 'python', '-c',
        f"""
import opentimelineio as otio
import json

timeline = otio.adapters.read_from_file(r'{aaf_file}')
info = {{
    'name': timeline.name,
    'tracks': [],
    'global_start_time': str(timeline.global_start_time) if timeline.global_start_time else None
}}

for i, track in enumerate(timeline.tracks):
    track_info = {{
        'name': track.name,
        'kind': str(track.kind),
        'clips': []
    }}
    
    for clip in track.find_clips():
        clip_info = {{
            'name': clip.name,
            'source_range': str(clip.source_range),
            'duration': str(clip.duration()),
            'media_reference': str(clip.media_reference) if clip.media_reference else None
        }}
        track_info['clips'].append(clip_info)
    
    info['tracks'].append(track_info)

print(json.dumps(info, indent=2))
"""
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error reading {aaf_file}:")
        print(result.stderr)
        return None
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {aaf_file}: {e}")
        return None


def compare_tracks(track1, track2, track_idx):
    """Compare two tracks and return differences."""
    differences = []
    
    # Compare track properties
    if track1['name'] != track2['name']:
        differences.append({
            'type': 'track_name',
            'track': track_idx,
            'value1': track1['name'],
            'value2': track2['name']
        })
    
    if track1['kind'] != track2['kind']:
        differences.append({
            'type': 'track_kind',
            'track': track_idx,
            'value1': track1['kind'],
            'value2': track2['kind']
        })
    
    # Compare clip count
    if len(track1['clips']) != len(track2['clips']):
        differences.append({
            'type': 'clip_count',
            'track': track_idx,
            'value1': len(track1['clips']),
            'value2': len(track2['clips'])
        })
    
    # Compare clips
    min_clips = min(len(track1['clips']), len(track2['clips']))
    for clip_idx in range(min_clips):
        clip1 = track1['clips'][clip_idx]
        clip2 = track2['clips'][clip_idx]
        
        # Compare clip properties
        for prop in ['name', 'source_range', 'duration', 'media_reference']:
            if clip1[prop] != clip2[prop]:
                differences.append({
                    'type': f'clip_{prop}',
                    'track': track_idx,
                    'clip': clip_idx,
                    'value1': clip1[prop],
                    'value2': clip2[prop]
                })
    
    return differences


def compare_aaf_files(file1, file2):
    """Compare two AAF files and return a comparison report."""
    print(f"Comparing:")
    print(f"  File 1: {file1}")
    print(f"  File 2: {file2}")
    
    # Get info from both files
    info1 = get_aaf_info(file1)
    info2 = get_aaf_info(file2)
    
    if not info1 or not info2:
        return None
    
    # Compare
    differences = []
    
    # Compare timeline name
    if info1['name'] != info2['name']:
        differences.append({
            'type': 'timeline_name',
            'value1': info1['name'],
            'value2': info2['name']
        })
    
    # Compare global start time
    if info1['global_start_time'] != info2['global_start_time']:
        differences.append({
            'type': 'global_start_time',
            'value1': info1['global_start_time'],
            'value2': info2['global_start_time']
        })
    
    # Compare track count
    if len(info1['tracks']) != len(info2['tracks']):
        differences.append({
            'type': 'track_count',
            'value1': len(info1['tracks']),
            'value2': len(info2['tracks'])
        })
    
    # Compare tracks
    min_tracks = min(len(info1['tracks']), len(info2['tracks']))
    for track_idx in range(min_tracks):
        track_diffs = compare_tracks(
            info1['tracks'][track_idx],
            info2['tracks'][track_idx],
            track_idx
        )
        differences.extend(track_diffs)
    
    # Create report
    report = {
        'file1': str(file1),
        'file2': str(file2),
        'differences': differences,
        'total_differences': len(differences),
        'summary': {
            'tracks': min(len(info1['tracks']), len(info2['tracks'])),
            'clips': sum(min(len(t1['clips']), len(t2['clips'])) 
                        for t1, t2 in zip(info1['tracks'], info2['tracks']))
        }
    }
    
    return report


def compare_directories(dir1, dir2, output_file=None):
    """Compare all AAF files in two directories."""
    dir1 = Path(dir1)
    dir2 = Path(dir2)
    
    if not dir1.exists():
        print(f"Error: Directory {dir1} does not exist")
        return None
    
    if not dir2.exists():
        print(f"Error: Directory {dir2} does not exist")
        return None
    
    # Get all AAF files
    aaf_files1 = {f.name: f for f in dir1.glob('*.aaf')}
    aaf_files2 = {f.name: f for f in dir2.glob('*.aaf')}
    
    # Find common files
    common_files = set(aaf_files1.keys()) & set(aaf_files2.keys())
    
    print(f"\nComparing directories:")
    print(f"  Directory 1: {dir1} ({len(aaf_files1)} files)")
    print(f"  Directory 2: {dir2} ({len(aaf_files2)} files)")
    print(f"  Common files: {len(common_files)}")
    
    # Compare each common file
    all_reports = []
    for filename in sorted(common_files):
        print(f"\n{'='*70}")
        report = compare_aaf_files(aaf_files1[filename], aaf_files2[filename])
        if report:
            all_reports.append(report)
            print(f"  Total differences: {report['total_differences']}")
    
    # Create summary
    total_diffs = sum(r['total_differences'] for r in all_reports)
    files_with_diffs = sum(1 for r in all_reports if r['total_differences'] > 0)
    
    summary = {
        'directory1': str(dir1),
        'directory2': str(dir2),
        'total_files': len(common_files),
        'files_with_differences': files_with_diffs,
        'total_differences': total_diffs,
        'reports': all_reports
    }
    
    # Save summary
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\nComparison summary saved to: {output_file}")
    
    # Print summary
    print(f"\n{'='*70}")
    print("Comparison Summary")
    print(f"{'='*70}")
    print(f"Total files compared: {summary['total_files']}")
    print(f"Files with differences: {summary['files_with_differences']}")
    print(f"Total differences: {summary['total_differences']}")
    
    if all_reports:
        print(f"\nFiles with most differences:")
        sorted_reports = sorted(all_reports, 
                              key=lambda r: r['total_differences'], 
                              reverse=True)
        for report in sorted_reports[:5]:
            filename = Path(report['file1']).name
            print(f"  {filename}: {report['total_differences']} differences")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Compare AAF files from different branches'
    )
    parser.add_argument(
        '--file1',
        type=str,
        help='First AAF file to compare'
    )
    parser.add_argument(
        '--file2',
        type=str,
        help='Second AAF file to compare'
    )
    parser.add_argument(
        '--dir1',
        type=str,
        help='First directory containing AAF files'
    )
    parser.add_argument(
        '--dir2',
        type=str,
        help='Second directory containing AAF files'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='comparison_summary.json',
        help='Output file for comparison summary'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.file1 and args.file2:
        # Compare two files
        report = compare_aaf_files(args.file1, args.file2)
        if report:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nComparison report saved to: {args.output}")
    
    elif args.dir1 and args.dir2:
        # Compare directories
        compare_directories(args.dir1, args.dir2, args.output)
    
    else:
        parser.print_help()
        print("\nError: Please provide either --file1 and --file2, or --dir1 and --dir2")
        sys.exit(1)


if __name__ == '__main__':
    main()
