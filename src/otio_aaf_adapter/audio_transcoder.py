"""
Audio file transcoding module for AAF export.

This module provides functionality to automatically detect and transcode
audio files to a target format (48000 Hz, 24-bit, mono) before AAF export.
"""

import os
import wave
from pathlib import Path
from typing import Dict, Optional

import opentimelineio as otio
from pydub import AudioSegment


def get_wav_format(wav_path: str) -> Optional[Dict]:
    """
    Read WAV file format information.
    
    Args:
        wav_path: Path to WAV file
        
    Returns:
        Dictionary with 'sample_rate', 'sample_width' (bytes), 'channels', or None if error
    """
    try:
        with wave.open(wav_path, 'rb') as wf:
            return {
                'sample_rate': wf.getframerate(),
                'sample_width': wf.getsampwidth(),
                'channels': wf.getnchannels()
            }
    except Exception as e:
        print(f"Warning: Could not read WAV format from {wav_path}: {e}")
        return None


def needs_transcoding(
    wav_format: Dict,
    target_sr: int = 48000,
    target_bits: int = 24,
    target_channels: int = 1
) -> bool:
    """
    Check if WAV file needs transcoding.
    
    Args:
        wav_format: Dictionary from get_wav_format()
        target_sr: Target sample rate in Hz
        target_bits: Target bit depth
        target_channels: Target number of channels
        
    Returns:
        True if transcoding is needed
    """
    return (
        wav_format['sample_rate'] != target_sr or
        wav_format['sample_width'] * 8 != target_bits or
        wav_format['channels'] != target_channels
    )


def transcode_audio_files(
    timeline: otio.schema.Timeline,
    target_sr: int = 48000,
    target_bits: int = 24,
    target_channels: int = 1
) -> Dict[str, str]:
    """
    Detect and transcode audio files in timeline to target format.
    
    This function:
    1. Collects all audio file paths from timeline clips
    2. Finds common parent directory
    3. Creates 'converted/' subdirectory
    4. Transcodes files that don't match target format
    5. Returns mapping of original paths to converted paths
    
    Args:
        timeline: OTIO Timeline object
        target_sr: Target sample rate in Hz (default: 48000)
        target_bits: Target bit depth (default: 24)
        target_channels: Target number of channels (default: 1)
        
    Returns:
        Dictionary mapping original target_url to converted file path
    """
    # Step 1: Collect all audio file paths
    audio_paths = []
    for track in timeline.tracks:
        if not hasattr(track, 'kind') or track.kind != 'Audio':
            continue
        for clip in track:
            if not hasattr(clip, 'media_reference') or not clip.media_reference:
                continue
            if not hasattr(clip.media_reference, 'target_url'):
                continue
            
            target_url = clip.media_reference.target_url
            # Handle file:// URLs
            if target_url.startswith('file://'):
                target_url = target_url[7:]
                # Handle Windows file:///C:/... URLs
                if target_url.startswith('/') and len(target_url) > 2 and target_url[2] == ':':
                    target_url = target_url[1:]
            
            # Only process .wav files
            if target_url.lower().endswith('.wav'):
                audio_paths.append(target_url)
    
    if not audio_paths:
        print("No audio files found in timeline")
        return {}
    
    print(f"Found {len(audio_paths)} audio files in timeline")
    
    # Step 2: Find common parent directory
    try:
        common_parent = os.path.commonpath(audio_paths)
        # If common_parent is a file, get its directory
        if os.path.isfile(common_parent):
            common_parent = os.path.dirname(common_parent)
    except ValueError:
        # No common path (different drives on Windows), use current directory
        common_parent = os.getcwd()
    
    # Step 3: Create converted/ subdirectory
    converted_dir = os.path.join(common_parent, 'converted')
    os.makedirs(converted_dir, exist_ok=True)
    print(f"Using converted directory: {converted_dir}")
    
    # Step 4: Detect and transcode
    url_mapping = {}
    target_bytes = target_bits // 8
    
    for audio_path in audio_paths:
        if not os.path.exists(audio_path):
            print(f"Warning: Audio file not found: {audio_path}")
            continue
        
        # Get current format
        wav_format = get_wav_format(audio_path)
        if wav_format is None:
            continue
        
        # Generate output path
        filename = os.path.basename(audio_path)
        name, ext = os.path.splitext(filename)
        converted_filename = f"{name}_converted{ext}"
        converted_path = os.path.join(converted_dir, converted_filename)
        
        # Check if already converted
        if os.path.exists(converted_path):
            print(f"  Using existing converted file: {converted_filename}")
            url_mapping[audio_path] = converted_path
            continue
        
        # Check if transcoding is needed
        if not needs_transcoding(wav_format, target_sr, target_bits, target_channels):
            print(f"  File already matches target format, copying: {filename}")
            # Even if format matches, copy to converted/ for consistency
            import shutil
            shutil.copy2(audio_path, converted_path)
            url_mapping[audio_path] = converted_path
            continue
        
        # Transcode
        print(f"  Transcoding: {filename} ({wav_format['sample_rate']}Hz, {wav_format['sample_width']*8}bit, {wav_format['channels']}ch)")
        print(f"            -> ({target_sr}Hz, {target_bits}bit, {target_channels}ch)")
        
        try:
            # Load audio with pydub
            audio = AudioSegment.from_wav(audio_path)
            
            # Convert to target format
            audio = audio.set_frame_rate(target_sr)
            audio = audio.set_sample_width(target_bytes)
            audio = audio.set_channels(target_channels)
            
            # Export with pcm_s24le codec for 24-bit
            audio.export(
                converted_path,
                format="wav",
                parameters=["-acodec", "pcm_s24le"]
            )
            
            url_mapping[audio_path] = converted_path
            print(f"    -> Saved: {converted_filename}")
            
        except Exception as e:
            print(f"  Error transcoding {filename}: {e}")
            continue
    
    print(f"\nTranscoding complete: {len(url_mapping)} files processed")
    return url_mapping


def update_media_references(
    timeline: otio.schema.Timeline,
    url_mapping: Dict[str, str]
) -> Dict[str, str]:
    """
    Update media references in timeline to use converted files.
    
    Args:
        timeline: OTIO Timeline object
        url_mapping: Dictionary from transcode_audio_files()
        
    Returns:
        Dictionary mapping converted paths back to original paths (for restoration)
    """
    reverse_mapping = {}
    
    for track in timeline.tracks:
        if not hasattr(track, 'kind') or track.kind != 'Audio':
            continue
        for clip in track:
            if not hasattr(clip, 'media_reference') or not clip.media_reference:
                continue
            if not hasattr(clip.media_reference, 'target_url'):
                continue
            
            original_url = clip.media_reference.target_url
            # Handle file:// URLs for lookup
            lookup_url = original_url
            if lookup_url.startswith('file://'):
                lookup_url = lookup_url[7:]
                if lookup_url.startswith('/') and len(lookup_url) > 2 and lookup_url[2] == ':':
                    lookup_url = lookup_url[1:]
            
            if lookup_url in url_mapping:
                converted_path = url_mapping[lookup_url]
                # Store reverse mapping for restoration
                reverse_mapping[converted_path] = original_url
                # Just store the plain path, let aaf_writer handle URL formatting
                clip.media_reference.target_url = converted_path
    
    return reverse_mapping


def restore_media_references(
    timeline: otio.schema.Timeline,
    reverse_mapping: Dict[str, str]
):
    """
    Restore media references to original paths after export.
    
    Args:
        timeline: OTIO Timeline object
        reverse_mapping: Dictionary from update_media_references()
    """
    for track in timeline.tracks:
        if not hasattr(track, 'kind') or track.kind != 'Audio':
            continue
        for clip in track:
            if not hasattr(clip, 'media_reference') or not clip.media_reference:
                continue
            if not hasattr(clip.media_reference, 'target_url'):
                continue
            
            current_url = clip.media_reference.target_url
            # Handle file:// URLs for lookup
            lookup_url = current_url
            if lookup_url.startswith('file://'):
                lookup_url = lookup_url[7:]
                if lookup_url.startswith('/') and len(lookup_url) > 2 and lookup_url[2] == ':':
                    lookup_url = lookup_url[1:]
            
            if lookup_url in reverse_mapping:
                clip.media_reference.target_url = reverse_mapping[lookup_url]
