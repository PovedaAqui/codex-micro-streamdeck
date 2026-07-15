#!/usr/bin/env python3.12
"""Generate minimalist icons for Stream Deck Codex Micro bridge."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = Path(__file__).parent / "icons"
ICONS_DIR.mkdir(exist_ok=True)

# Icon size: 280x280 (standard Stream Deck resolution)
SIZE = 280

def create_icon(filename: str, color: str, draw_func=None):
    """Create a simple colored icon with optional custom drawing."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw colored background square
    margin = 10
    draw.rectangle([margin, margin, SIZE - margin, SIZE - margin], fill=color)

    # Draw custom icon if provided
    if draw_func:
        draw_func(draw)

    img.save(ICONS_DIR / filename)
    print(f"✓ Created {filename}")

def draw_pause(draw):
    """Draw pause symbol (two vertical bars)."""
    cx, cy = SIZE // 2, SIZE // 2
    bar_width = 30
    bar_height = 80
    gap = 40
    draw.rectangle([cx - gap//2 - bar_width//2 - 5, cy - bar_height//2,
                    cx - gap//2 + bar_width//2 - 5, cy + bar_height//2], fill="white")
    draw.rectangle([cx + gap//2 - bar_width//2 + 5, cy - bar_height//2,
                    cx + gap//2 + bar_width//2 + 5, cy + bar_height//2], fill="white")

def draw_hourglass(draw):
    """Draw hourglass/loading symbol."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 60
    draw.polygon([(cx, cy - r), (cx - r//2, cy), (cx, cy + r//2), (cx + r//2, cy)], fill="white")
    draw.polygon([(cx, cy + r//2), (cx - r//2, cy), (cx, cy - r//2), (cx + r//2, cy)], fill="white")

def draw_play(draw):
    """Draw play triangle."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 70
    draw.polygon([(cx - r//3, cy - r), (cx - r//3, cy + r), (cx + r, cy)], fill="white")

def draw_pause_play(draw):
    """Draw pause/play hybrid."""
    cx, cy = SIZE // 2, SIZE // 2
    bar_width = 25
    bar_height = 60
    gap = 30
    draw.rectangle([cx - gap//2 - bar_width//2, cy - bar_height//2,
                    cx - gap//2 + bar_width//2, cy + bar_height//2], fill="white")
    draw.rectangle([cx + gap//2 - bar_width//2, cy - bar_height//2,
                    cx + gap//2 + bar_width//2, cy + bar_height//2], fill="white")

def draw_check(draw):
    """Draw checkmark."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 60
    draw.polygon([(cx - r, cy), (cx - r//3, cy + r//2), (cx + r, cy - r)], fill="white")

def draw_warning(draw):
    """Draw warning triangle."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 70
    draw.polygon([(cx, cy - r), (cx - r, cy + r//2), (cx + r, cy + r//2)], fill="white")
    draw.rectangle([cx - 5, cy - 20, cx + 5, cy + 10], fill="#808080")
    draw.ellipse([cx - 5, cy + 25, cx + 5, cy + 35], fill="#808080")

def draw_accept(draw):
    """Draw accept/checkmark."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 50
    draw.polygon([(cx - r, cy), (cx - r//3, cy + r//2), (cx + r, cy - r)], fill="white")

def draw_reject(draw):
    """Draw reject/X."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 50
    draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill="white", width=25)
    draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill="white", width=25)

def draw_chat(draw):
    """Draw chat bubble."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 55
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white")
    draw.polygon([(cx - 20, cy + r//2), (cx, cy + r + 20), (cx + 20, cy + r//2)], fill="white")

def draw_reasoning(draw):
    """Draw brain/lightning bolt."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 50
    draw.polygon([(cx + r//3, cy - r), (cx - r//3, cy), (cx + r//3, cy),
                   (cx - r//3, cy + r), (cx + r//3, cy), (cx - r//3, cy),
                   (cx + r//3, cy)], fill="white")

def draw_page(draw):
    """Draw arrow/next page."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 50
    draw.polygon([(cx - r//2, cy - r), (cx + r, cy), (cx - r//2, cy + r)], fill="white")

def draw_pr(draw):
    """Draw PR review (document with lines)."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 45
    draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill="white")
    draw.rectangle([cx - r//2, cy - r//2, cx + r//2, cy - r//4], fill="#808080")
    draw.rectangle([cx - r//2, cy + r//8, cx + r//2, cy + r//4], fill="#808080")

def draw_debug(draw):
    """Draw debug (bug)."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 30
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white")
    # Legs
    for dx, dy in [(-40, -30), (40, -30), (-40, 30), (40, 30)]:
        draw.line([(cx, cy), (cx + dx, cy + dy)], fill="white", width=8)

def draw_refactor(draw):
    """Draw refactor (arrows)."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 40
    draw.polygon([(cx, cy - r), (cx - r, cy + r//2), (cx + r, cy + r//2)], fill="white")
    draw.polygon([(cx, cy + r//2), (cx - r, cy - r//2), (cx + r, cy - r//2)], fill="white")

def draw_test(draw):
    """Draw test (flask)."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 35
    draw.rectangle([cx - r//2, cy - r, cx + r//2, cy - r//3], fill="white")
    draw.polygon([(cx - r, cy - r//3), (cx + r, cy - r//3), (cx, cy + r)], fill="white")

def draw_stop(draw):
    """Draw stop (square)."""
    cx, cy = SIZE // 2, SIZE // 2
    r = 40
    draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill="white")

# Generate all icons
print(f"Generating icons to {ICONS_DIR}...")

# Agent status icons
create_icon("idle.png", "#808080", draw_pause)
create_icon("thinking.png", "#FFD700", draw_hourglass)
create_icon("running.png", "#32CD32", draw_play)
create_icon("waiting.png", "#1E90FF", draw_pause_play)
create_icon("done.png", "#9370DB", draw_check)
create_icon("error.png", "#FF4500", draw_warning)

# Command icons
create_icon("accept.png", "#32CD32", draw_accept)
create_icon("reject.png", "#FF4500", draw_reject)
create_icon("new_chat.png", "#1E90FF", draw_chat)

# Reasoning
create_icon("reasoning.png", "#FFA500", draw_reasoning)

# Page switch
create_icon("next_page.png", "#808080", draw_page)
create_icon("prev_page.png", "#808080", draw_page)

# Workflow icons
create_icon("pr_review.png", "#4169E1", draw_pr)
create_icon("debug.png", "#FF8C00", draw_debug)
create_icon("refactor.png", "#9370DB", draw_refactor)
create_icon("test_deploy.png", "#20B2AA", draw_test)
create_icon("stop_all.png", "#DC143C", draw_stop)

print(f"\nDone! {len(list(ICONS_DIR.glob('*.png')))} icons created.")
