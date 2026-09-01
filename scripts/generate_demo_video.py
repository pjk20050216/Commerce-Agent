"""Generate a realistic demo video for mock video display.

Creates a 5-second MP4 with animated product showcase frames.
Uses Pillow to create frames + ffmpeg to encode.

Output: ./output/videos/dev/demo_product_video.mp4
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def create_frame(width, height, frame_num, total_frames, text_lines):
    """Create a single frame with gradient background and text overlay."""
    from PIL import Image, ImageDraw, ImageFont

    # Create gradient background
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Animated gradient colors
    phase = frame_num / total_frames
    r1, g1, b1 = 30, 60, 120  # Dark blue
    r2, g2, b2 = 80, 150, 220  # Light blue

    for y in range(height):
        t = y / height
        r = int(r1 + (r2 - r1) * t + 20 * (1 - abs(2 * phase - 1)))
        g = int(g1 + (g2 - g1) * t + 20 * (1 - abs(2 * phase - 1)))
        b = int(b1 + (b2 - b1) * t)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        for x in range(0, width, 5):
            draw.rectangle([x, y, x + 4, y], fill=(r, g, b))

    # Add text overlay
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32)
        font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw text lines with fade-in effect
    for i, line in enumerate(text_lines):
        # Fade in each line sequentially
        line_phase = (frame_num / total_frames * len(text_lines)) - i
        alpha = max(0, min(255, int(255 * min(1, line_phase))))

        y_pos = 120 + i * 80
        if i == 0:
            font = font_large
        elif i <= 3:
            font = font_medium
        else:
            font = font_small

        # Draw text shadow
        draw.text((width // 2 + 3, y_pos + 3), line, fill=(0, 0, 0, alpha), font=font, anchor="mt")
        # Draw text
        draw.text((width // 2, y_pos), line, fill=(255, 255, 255, alpha), font=font, anchor="mt")

    # Draw progress bar
    bar_width = int(width * 0.6)
    bar_height = 8
    bar_x = (width - bar_width) // 2
    bar_y = height - 100
    progress = frame_num / total_frames

    # Background bar
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                   fill=(100, 100, 100, 128))
    # Progress bar
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height],
                   fill=(0, 200, 100))

    return img


def main():
    output_dir = Path("output/videos/dev")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "demo_product_video.mp4"

    # Video params
    width, height = 1920, 1080
    fps = 30
    duration = 5  # seconds
    total_frames = fps * duration

    # Text content simulating a product showcase
    text_lines = [
        "多智能体跨境电商助手",
        "AI-Powered Product Visual Generator",
        "",
        "Product: Anker PowerCore 26800mAh",
        "Category: Digital / Electronics",
        "",
        "✨ AI Image Generation  ✅",
        "🎬 AI Video Generation  ✅",
        "📝 AI Copywriting       ✅",
        "🌍 Multi-Platform Listing ✅",
    ]

    print(f"Generating {total_frames} frames ({duration}s @ {fps}fps)...")

    # Create temp directory for frames
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(total_frames):
            frame = create_frame(width, height, i, total_frames, text_lines)
            frame_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
            frame.save(frame_path, "PNG")
            if i % 30 == 0:
                print(f"  Frame {i}/{total_frames}")

        print("Encoding with ffmpeg...")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(tmpdir, "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            sys.exit(1)

    file_size = output_path.stat().st_size
    print(f"\n✅ Demo video created: {output_path}")
    print(f"   Resolution: {width}x{height}")
    print(f"   Duration: {duration}s")
    print(f"   FPS: {fps}")
    print(f"   Size: {file_size / 1024:.1f} KB")

    # Also generate a shorter thumbnail version
    thumb_path = output_dir / "demo_thumbnail.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(output_path),
        "-t", "3",
        "-vf", "scale=640:360",
        "-c:v", "libx264",
        "-preset", "fast",
        str(thumb_path),
    ], capture_output=True)
    print(f"\n✅ Thumbnail video: {thumb_path}")
    print(f"   Size: {thumb_path.stat().st_size / 1024:.1f} KB")

    print("\nNotes:")
    print("  - This is a DEMO video for presentation purposes")
    print("  - When mock video is enabled, the system stores videos in:")
    print("    ./output/videos/{tenant_id}/{video_id}.mp4")
    print("  - For real video generation, configure Kling AI API keys in .env")


if __name__ == "__main__":
    main()
