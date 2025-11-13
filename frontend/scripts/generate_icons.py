#!/usr/bin/env python3
"""
Generate all favicon and PWA icons for SampleTok
Requires: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFilter
import os
import math

# Icon configurations
ICONS = [
    {"name": "favicon-16x16", "size": 16, "rounded": 3},
    {"name": "favicon-32x32", "size": 32, "rounded": 6},
    {"name": "apple-touch-icon", "size": 180, "rounded": 40},
    {"name": "icon-192x192", "size": 192, "rounded": 42},
    {"name": "icon-512x512", "size": 512, "rounded": 112},
    {"name": "icon-192x192-maskable", "size": 192, "rounded": 42, "maskable": True},
    {"name": "icon-512x512-maskable", "size": 512, "rounded": 112, "maskable": True},
]

# Beautiful gradient colors (pink to rose with vibrant feel)
GRADIENT_TOP = (244, 114, 182)     # Lighter pink #f472b6
GRADIENT_BOTTOM = (190, 24, 93)    # Deeper rose #be185d

def create_gradient(size):
    """Create a smooth radial gradient with depth"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    center_x, center_y = size // 2, size // 2
    max_radius = math.sqrt(2) * size / 2

    for y in range(size):
        for x in range(size):
            # Calculate distance from center
            dx = x - center_x
            dy = y - center_y
            distance = math.sqrt(dx * dx + dy * dy)
            ratio = min(distance / max_radius, 1.0)

            # Smooth easing for more natural gradient
            ratio = ratio * ratio * (3 - 2 * ratio)  # Smoothstep

            r = int(GRADIENT_TOP[0] + (GRADIENT_BOTTOM[0] - GRADIENT_TOP[0]) * ratio)
            g = int(GRADIENT_TOP[1] + (GRADIENT_BOTTOM[1] - GRADIENT_TOP[1]) * ratio)
            b = int(GRADIENT_TOP[2] + (GRADIENT_BOTTOM[2] - GRADIENT_TOP[2]) * ratio)

            img.putpixel((x, y), (r, g, b, 255))

    return img

def draw_music_note(size, maskable=False):
    """Draw a beautiful, well-proportioned music note"""
    # Create a larger canvas for antialiasing
    scale_factor = 4
    canvas_size = size * scale_factor
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scale for maskable icons (need safe zone padding)
    icon_scale = 0.45 if maskable else 0.55
    note_size = int(canvas_size * icon_scale)
    center = canvas_size // 2

    # Note dimensions (scaled up)
    stem_width = max(note_size // 10, scale_factor * 3)
    stem_height = int(note_size * 0.9)

    # Position - slightly off-center for better visual balance
    stem_x = center - note_size // 8
    stem_top = center - stem_height // 2

    # Draw stem first (vertical line going up)
    draw.rounded_rectangle(
        [
            stem_x - stem_width // 2,
            stem_top,
            stem_x + stem_width // 2,
            stem_top + stem_height - stem_width,
        ],
        radius=stem_width // 2,
        fill=(255, 255, 255, 255)
    )

    # Draw note head (filled ellipse at bottom, tilted)
    note_head_width = int(note_size * 0.35)
    note_head_height = int(note_head_width * 0.65)
    note_y = stem_top + stem_height

    # Create separate image for rotated head
    head_img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    head_draw = ImageDraw.Draw(head_img)

    head_draw.ellipse(
        [
            stem_x - note_head_width // 2,
            note_y - note_head_height // 2,
            stem_x + note_head_width // 2,
            note_y + note_head_height // 2,
        ],
        fill=(255, 255, 255, 255)
    )

    # Rotate for musical note tilt (-25 degrees)
    head_img = head_img.rotate(-25, center=(stem_x, note_y), resample=Image.Resampling.BICUBIC)
    img = Image.alpha_composite(img, head_img)

    # Draw elegant flag/beam at top
    flag_width = int(note_size * 0.5)
    flag_height = int(note_size * 0.45)
    flag_x_start = stem_x + stem_width // 2

    # Create curved flag using multiple segments
    num_segments = 30
    for i in range(num_segments):
        t = i / num_segments

        # Smooth curve using easing function
        curve = t * t * (3 - 2 * t)  # Smoothstep

        x1 = flag_x_start + flag_width * t
        y1 = stem_top + flag_height * curve

        # Variable thickness - thicker at base, thinner at end
        thickness = int(stem_width * 1.8 * (1 - t * 0.6))

        if i < num_segments - 1:
            t_next = (i + 1) / num_segments
            curve_next = t_next * t_next * (3 - 2 * t_next)
            x2 = flag_x_start + flag_width * t_next
            y2 = stem_top + flag_height * curve_next

            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 255), width=thickness)

    # Add second beam (for eighth note)
    beam_spacing = int(stem_width * 2.5)
    for i in range(num_segments):
        t = i / num_segments
        curve = t * t * (3 - 2 * t)

        x1 = flag_x_start + flag_width * t * 0.85  # Slightly shorter
        y1 = stem_top + beam_spacing + flag_height * curve * 0.8

        thickness = int(stem_width * 1.5 * (1 - t * 0.6))

        if i < num_segments - 1:
            t_next = (i + 1) / num_segments
            curve_next = t_next * t_next * (3 - 2 * t_next)
            x2 = flag_x_start + flag_width * t_next * 0.85
            y2 = stem_top + beam_spacing + flag_height * curve_next * 0.8

            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 255), width=thickness)

    # Downscale with high-quality antialiasing
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    return img

def create_icon(size, rounded, maskable=False):
    """Create a single icon with the specified size"""
    # Create larger canvas for better quality
    scale = 2
    large_size = size * scale
    large_rounded = rounded * scale

    # Create base gradient
    gradient = create_gradient(large_size)

    # Add subtle inner shadow for depth (larger icons only)
    if size >= 64:
        shadow_overlay = Image.new('RGBA', (large_size, large_size), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay)

        # Draw subtle vignette
        for i in range(large_size // 20):
            alpha = int(15 * (i / (large_size / 20)))
            shadow_draw.ellipse(
                [i, i, large_size - i, large_size - i],
                outline=(0, 0, 0, alpha)
            )

        gradient = Image.alpha_composite(gradient.convert('RGBA'), shadow_overlay)

    # Create mask for rounded corners
    mask = Image.new('L', (large_size, large_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (large_size - 1, large_size - 1)],
        radius=large_rounded,
        fill=255
    )

    # Apply rounded corners
    output = Image.new('RGBA', (large_size, large_size), (0, 0, 0, 0))
    output.paste(gradient, (0, 0))
    output.putalpha(mask)

    # Draw music note
    note = draw_music_note(large_size, maskable)

    # Add subtle shadow to note for depth (larger icons only)
    if size >= 64:
        shadow = note.copy()
        shadow_pixels = shadow.load()
        for y in range(large_size):
            for x in range(large_size):
                _, _, _, a = shadow_pixels[x, y]
                if a > 0:
                    shadow_pixels[x, y] = (0, 0, 0, int(a * 0.3))

        # Blur and offset shadow
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=large_size // 100))
        shadow_offset = large_size // 80

        # Composite shadow then note
        shadow_canvas = Image.new('RGBA', (large_size, large_size), (0, 0, 0, 0))
        shadow_canvas.paste(shadow, (shadow_offset, shadow_offset), shadow)
        output = Image.alpha_composite(output, shadow_canvas)

    # Composite the note
    output = Image.alpha_composite(output, note)

    # Downscale to final size with high-quality resampling
    output = output.resize((size, size), Image.Resampling.LANCZOS)

    return output

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(os.path.dirname(script_dir), 'public', 'icons')

    # Create icons directory if it doesn't exist
    os.makedirs(icons_dir, exist_ok=True)

    print("Generating SampleTok icons...")

    for config in ICONS:
        name = config["name"]
        size = config["size"]
        rounded = config["rounded"]
        maskable = config.get("maskable", False)

        print(f"  Creating {name}.png ({size}x{size}{'maskable' if maskable else ''})")

        icon = create_icon(size, rounded, maskable)
        output_path = os.path.join(icons_dir, f"{name}.png")
        icon.save(output_path, "PNG", optimize=True)

    print(f"\n✅ Successfully generated {len(ICONS)} icons in {icons_dir}")
    print("\nGenerated files:")
    for config in ICONS:
        print(f"  - {config['name']}.png")

if __name__ == "__main__":
    main()
