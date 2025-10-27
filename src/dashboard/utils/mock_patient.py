"""
Patient photo/avatar generation utilities
"""
import io
from PIL import Image, ImageDraw, ImageFont
import random

def generate_avatar(initials="P", size=(200, 200), bg_color="#1E64C8"):
    """
    Generate a simple avatar with initials
    
    Args:
        initials: Patient initials (e.g., "JD" for John Doe)
        size: Tuple of (width, height)
        bg_color: Background color (default UGent Blue)
    
    Returns:
        PIL Image object
    """
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw initials
    try:
        # Try to use a nice font
        font_size = size[0] // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    draw.text(position, initials, fill='white', font=font)
    
    return img

def get_patient_initials(first_name="", last_name=""):
    """Extract initials from patient name"""
    initials = ""
    if first_name:
        initials += first_name[0].upper()
    if last_name:
        initials += last_name[0].upper()
    return initials if initials else "P"

def save_avatar_to_bytes(img):
    """Convert PIL Image to bytes for Streamlit display"""
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

