"""
FFmpeg Automated Converter

This snippet demonstrates how post-processing is automated once the GridMarkets Cloud
Farm finishes rendering an image sequence layout and synchronizes it to Google Drive.
It detects the sequence pattern dynamically and triggers an automated encode to ProRes 
and H.264 without manual user input.
"""

import re
import subprocess
from pathlib import Path

def detect_sequence(directory: Path) -> dict | None:
    """
    Auto-detect image sequences (EXR or PNG) in a directory and calculate padding.
    E.g., logo.0001.exr -> detects pattern 'logo.%04d.exr'
    """
    files = list(directory.glob("*.exr")) + list(directory.glob("*.png"))
    if not files: return None

    # Regex: everything before the frame, the frame itself, and the extension
    pattern_re = re.compile(r"^(.+?)[._](\d+)\.(\w+)$")
    sequences = {}

    for f in files:
        match = pattern_re.match(f.name)
        if match:
            base, frame_str, ext = match.groups()
            key = (base, ext)
            sequences.setdefault(key, []).append((int(frame_str), len(frame_str)))

    if not sequences: return None

    # Find the sequence with the most frames
    longest_key = max(sequences, key=lambda k: len(sequences[k]))
    seq_files = sorted(sequences[longest_key], key=lambda x: x[0])

    base, ext = longest_key
    start = seq_files[0][0]
    padding = seq_files[0][1]

    # Convert to FFmpeg ingest pattern
    ffmpeg_pattern = f"{base}.%0{padding}d.{ext}"

    return {
        "pattern": ffmpeg_pattern,
        "base": base,
        "start": start,
        "count": len(seq_files)
    }

def encode_to_prores_alpha(input_dir: Path, seq_info: dict, fps: int = 24):
    """Encodes the EXR/PNG sequence directly into a transparent 4444 MOV."""
    output_path = input_dir / f"{seq_info['base']}_alpha.mov"
    
    cmd = [
        "ffmpeg", "-y", 
        "-framerate", str(fps),
        "-start_number", str(seq_info['start']),
        "-i", str(input_dir / seq_info['pattern']),
        "-frames:v", str(seq_info['count']),
        "-c:v", "prores_ks",
        "-profile:v", "4",            # ProRes 4444 Profile
        "-pix_fmt", "yuva444p10le",   # Retain Alpha + 10bit
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path

def encode_to_h264(input_dir: Path, seq_info: dict, fps: int = 24):
    """Encodes the EXR/PNG sequence into a lightweight MP4 for web review."""
    output_path = input_dir / f"{seq_info['base']}.mp4"
    
    cmd = [
        "ffmpeg", "-y", 
        "-framerate", str(fps),
        "-start_number", str(seq_info['start']),
        "-i", str(input_dir / seq_info['pattern']),
        "-frames:v", str(seq_info['count']),
        "-c:v", "libx264",
        "-crf", "18",                 # High quality
        "-preset", "slow",
        "-pix_fmt", "yuv420p",        # Standardize colorspace
        str(output_path),
    ]
    subprocess.run(cmd, check=True)
    return output_path

if __name__ == "__main__":
    render_dir = Path("/path/to/downloaded/cloud/renders")
    seq = detect_sequence(render_dir)
    if seq:
        print(f"Found {seq['count']} frames. Packaging Video...")
        encode_to_prores_alpha(render_dir, seq)
        encode_to_h264(render_dir, seq)
