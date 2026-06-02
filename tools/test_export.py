#!/usr/bin/env python
"""Test script to export OTIO timeline to AAF."""

import opentimelineio as otio
from otio_aaf_adapter.adapters.aaf_adapter import aaf_writer
import aaf2

# Load the test timeline
timeline = otio.adapters.read_from_file("SimpleTimeline.otio")

print("Loaded timeline:")
print(f"  Name: {timeline.name}")
print(f"  Global start time: {timeline.global_start_time}")
print(f"  Duration: {timeline.duration()}")
print(f"  Tracks: {len(timeline.tracks)}")

for i, track in enumerate(timeline.tracks):
    print(f"  Track {i}: {track.name} ({track.kind})")
    for j, child in enumerate(track):
        print(f"    Child {j}: {type(child).__name__} - {getattr(child, 'name', 'N/A')}")
        if hasattr(child, 'media_reference'):
            print(f"      Media: {child.media_reference}")
            if hasattr(child.media_reference, 'available_range'):
                print(f"      Available range: {child.media_reference.available_range}")

# Export to AAF
output_path = "test_output.aaf"
print(f"\nExporting to {output_path}...")

# Use the write_to_file function which has all the fixes
otio.adapters.write_to_file(timeline, output_path)

print(f"Export completed: {output_path}")

# Verify the output
print("\nVerifying output file...")
with aaf2.open(output_path) as f:
    mobs = list(f.content.mobs)
    print(f"  Mobs: {len(mobs)}")
    for mob in mobs:
        mob_type = mob.__class__.__name__
        print(f"    {mob_type}: {mob.name} (Slots: {len(list(mob.slots))})")
        for slot in mob.slots:
            segment = slot.segment
            segment_info = f"{segment.__class__.__name__}"
            if hasattr(segment, 'length'):
                segment_info += f" (Length: {segment.length})"
            if hasattr(slot, 'edit_rate'):
                segment_info += f" (EditRate: {slot.edit_rate})"
            print(f"      Slot {slot.slot_id}: {segment_info}")

print("\nExport test completed!")
