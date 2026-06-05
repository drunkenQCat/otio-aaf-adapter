#!/usr/bin/env python3
"""
Unified Export Script for AAF Branch Comparison

This script exports OTIO files to AAF format from different branches
for comparison purposes.

Usage:
    python verify_exports.py --branch dev --output exports/dev/
    python verify_exports.py --branch pt_compat --output exports/pt_compat/
    python verify_exports.py --branch all --output exports/
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import tempfile
import shutil


def get_current_branch():
    """Get the current git branch name."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def checkout_branch(branch_name):
    """Checkout a specific git branch."""
    print(f"Checking out branch: {branch_name}")
    subprocess.run(
        ['git', 'checkout', branch_name],
        check=True
    )


def get_test_files():
    """Get all OTIO test files from tests/sample_data/ that are expected to succeed."""
    test_dir = Path('tests/sample_data')
    if not test_dir.exists():
        print(f"Error: Test directory {test_dir} does not exist")
        sys.exit(1)
    
    # These files are expected to fail during export
    expected_failures = {
        'no_metadata.otio',
        'not_aaf.otio',
        'precheckfail.otio'
    }
    
    otio_files = [f for f in test_dir.glob('*.otio') 
                  if f.name not in expected_failures]
    
    if not otio_files:
        print(f"Error: No exportable .otio files found in {test_dir}")
        sys.exit(1)
    
    return sorted(otio_files)


def export_otio_to_aaf(otio_file, output_file):
    """Export an OTIO file to AAF format."""
    print(f"  Exporting: {otio_file.name} -> {output_file.name}")
    
    # Use otioconvert command instead of python -m
    cmd = [
        'uv', 'run', 'otioconvert',
        '-i', str(otio_file),
        '-o', str(output_file)
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  Error exporting {otio_file.name}:")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        return False
    
    return True


def run_tests():
    """Run the test suite and return results."""
    print("\nRunning test suite...")
    # Use uv run to ensure pytest-cov is available
    cmd = [
        'uv', 'run', 'pytest',
        'tests/test_aaf_adapter.py',
        '-v',
        '--tb=no',
        '-q'
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    # Parse test results from pytest output
    passed = 0
    failed = 0
    total = 0
    
    # Look for the summary line like "66 passed in 135.97s"
    for line in result.stdout.split('\n'):
        if 'passed' in line:
            # Extract numbers from the line
            import re
            match = re.search(r'(\d+)\s+passed', line)
            if match:
                passed = int(match.group(1))
            
            match = re.search(r'(\d+)\s+failed', line)
            if match:
                failed = int(match.group(1))
            
            # Total is passed + failed
            total = passed + failed
            break
    
    return passed, failed, total, result.stdout


def export_branch(branch_name, output_dir):
    """Export all test files from a specific branch."""
    print(f"\n{'='*70}")
    print(f"Exporting from branch: {branch_name}")
    print(f"{'='*70}")
    
    # Save current branch
    original_branch = get_current_branch()
    
    # Checkout target branch
    try:
        checkout_branch(branch_name)
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not checkout branch {branch_name}")
        print(f"  {e}")
        return None
    
    # Create output directory
    branch_output_dir = Path(output_dir) / branch_name
    branch_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get test files
    test_files = get_test_files()
    print(f"\nFound {len(test_files)} test files")
    
    # Export each file
    exported_files = []
    failed_exports = []
    
    for otio_file in test_files:
        aaf_file = branch_output_dir / (otio_file.stem + '.aaf')
        success = export_otio_to_aaf(otio_file, aaf_file)
        
        if success:
            exported_files.append({
                'otio': otio_file,
                'aaf': aaf_file
            })
        else:
            failed_exports.append(otio_file)
    
    # Run tests
    passed, failed, total, test_output = run_tests()
    
    # Save test results
    test_results_file = branch_output_dir / 'test_results.txt'
    with open(test_results_file, 'w') as f:
        f.write(test_output)
    
    # Create summary
    summary = {
        'branch': branch_name,
        'total_files': len(test_files),
        'exported': len(exported_files),
        'failed': len(failed_exports),
        'tests_passed': passed,
        'tests_failed': failed,
        'tests_total': total,
        'test_rate': f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
    }
    
    # Save summary
    summary_file = branch_output_dir / 'summary.json'
    import json
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Restore original branch
    try:
        checkout_branch(original_branch)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not restore original branch {original_branch}")
    
    print(f"\nSummary for {branch_name}:")
    print(f"  Files exported: {summary['exported']}/{summary['total_files']}")
    print(f"  Tests passed: {summary['tests_passed']}/{summary['tests_total']} ({summary['test_rate']})")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Export OTIO files to AAF from different branches'
    )
    parser.add_argument(
        '--branch',
        type=str,
        default='all',
        help='Branch to export from (dev, pt_compat, or all)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='exports',
        help='Output directory for exports'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine which branches to export
    if args.branch == 'all':
        branches = ['dev', 'pt_compat']
    else:
        branches = [args.branch]
    
    # Export from each branch
    summaries = []
    for branch in branches:
        summary = export_branch(branch, output_dir)
        if summary:
            summaries.append(summary)
    
    # Print comparison
    if len(summaries) > 1:
        print(f"\n{'='*70}")
        print("Branch Comparison")
        print(f"{'='*70}")
        print(f"{'Branch':<15} {'Files':<10} {'Tests':<15} {'Pass Rate':<10}")
        print('-' * 70)
        for summary in summaries:
            print(f"{summary['branch']:<15} "
                  f"{summary['exported']}/{summary['total_files']:<8} "
                  f"{summary['tests_passed']}/{summary['tests_total']:<12} "
                  f"{summary['test_rate']:<10}")


if __name__ == '__main__':
    main()
