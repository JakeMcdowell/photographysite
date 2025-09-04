from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os

WATERMARK_TEXT = "Rogers Photography"

# --- Font: Snell Roundhand Bold ---
# On macOS, Snell Roundhand is a .ttc (font collection). Bold is typically face index 1 (Black may be 2).
# If you have a dedicated .ttf/.otf for Bold, set FONT_PATH_BOLD to that and keep FONT_INDEX=0.
FONT_PATH_BOLD = "/Library/Fonts/SnellRoundhand.ttc"  # update if your path differs
FONT_INDEX = 1  # 0=Regular, 1=Bold, 2=Black (varies by system)

INPUT_FOLDER = "static/images/original"
OUTPUT_FOLDER = "static/images/watermarked"

# --- Shadow settings (as requested) ---
SHADOW_OPACITY = 80          # 0..255
SHADOW_OFFSET_DISTANCE = 10  # pixels
SHADOW_ANGLE_DEGREES = -90   # degrees; -90 is straight up in image coords
SHADOW_BLUR_RADIUS = 20      # Gaussian blur radius

TEXT_FILL = (255, 255, 255, 160)  # same semi-transparent white as before

def load_snell_font(size: int) -> ImageFont.FreeTypeFont:
    # Handles .ttc face selection; falls back to index 0 if needed.
    try:
        return ImageFont.truetype(FONT_PATH_BOLD, size=size, index=FONT_INDEX)
    except Exception:
        # Fallback: try index 0, then raise
        try:
            return ImageFont.truetype(FONT_PATH_BOLD, size=size, index=0)
        except Exception as e:
            print(f"Cannot load Snell Roundhand from {FONT_PATH_BOLD} (index {FONT_INDEX}).")
            raise e

def find_max_font_size(text, image_width):
    size = 50  # start big
    while size > 1:
        font = load_snell_font(size)
        dummy_img = Image.new("RGBA", (100, 100))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= image_width - 20:  # 10px padding each side
            return font
        size -= 1
    return load_snell_font(10)

def apply_watermark(input_path, output_path):
    image = Image.open(input_path).convert("RGBA")
    base = image.copy()

    # Text font sized to width
    font = find_max_font_size(WATERMARK_TEXT, image.width)

    # Measure and center
    # Measure text
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", image.size))
    bbox = tmp_draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Bottom-right position with padding
    PADDING = 20
    x = image.width - text_w - PADDING
    y = image.height - text_h - PADDING

    # Compute shadow offset
    theta = math.radians(SHADOW_ANGLE_DEGREES)
    dx = int(round(SHADOW_OFFSET_DISTANCE * math.cos(theta)))
    dy = int(round(SHADOW_OFFSET_DISTANCE * math.sin(theta)))

    # Draw shadow on its own layer, then blur
    shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.text((x + dx, y + dy), WATERMARK_TEXT, font=font, fill=(0, 0, 0, SHADOW_OPACITY))
    shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))

    # Composite: base + shadow + text
    composed = Image.alpha_composite(base, shadow_blurred)

    text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((x, y), WATERMARK_TEXT, font=font, fill=TEXT_FILL)
    composed = Image.alpha_composite(composed, text_layer)

    composed.convert("RGB").save(output_path, "JPEG", quality=95)

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    for filename in os.listdir(INPUT_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            input_path = os.path.join(INPUT_FOLDER, filename)
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            apply_watermark(input_path, output_path)
            print(f"Watermarked: {filename}")
