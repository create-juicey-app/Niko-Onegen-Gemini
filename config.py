# It's quite literally the config.
# its the config. nothing else.
import os
import sys  # Added import
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Literal

load_dotenv() # Load environment variables from .env file

# --- Resource Paths ---
# Function to determine the base directory for resources
def get_base_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running in a normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir() # Updated BASE_DIR definition
RES_DIR = os.path.join(BASE_DIR, "res")
FONT_DIR = os.path.join(RES_DIR, "font")
SFX_DIR = os.path.join(RES_DIR, "sfx") # Kept for global SFX
BG_DIR = os.path.join(RES_DIR, "backgrounds") # Kept for backgrounds
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters") # New directory for character JSONs

WINDOW_ICON = os.path.join(RES_DIR, "icon.ico")
TEXTBOX_IMG = os.path.join(RES_DIR, "textboxImage.png")
TEXTBOX_OPAQUE_IMG = os.path.join(RES_DIR, "textboxImageOpaque.png") # Optional
ARROW_IMG = os.path.join(RES_DIR, "textboxArrow.png")
DEFAULT_BG_IMG = os.path.join(BG_DIR, "bg.png") # Default background image path (now explicitly in BG_DIR)

# --- Font Settings ---
FONT_REGULAR = os.path.join(FONT_DIR, "font-b.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "font-b.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "font-i.ttf")
FONT_BOLDITALIC = os.path.join(FONT_DIR, "font-bi.ttf")
FONT_SIZE = 22 # Adjust as needed based on font/textbox
TEXT_COLOR = (255, 255, 255, 255) # RGBA for text color

# --- Positioning (Relative to Textbox Top-Left) ---
TEXTBOX_WIDTH = 608 # Example width of textboxImage.png
TEXTBOX_HEIGHT = 128 # Example height of textboxImage.png

TEXT_OFFSET_X = 20
TEXT_OFFSET_Y = 15
FACE_OFFSET_X = 496 # Example: Adjust based on textbox layout
FACE_OFFSET_Y = 16  # Example: Adjust based on textbox layout
FACE_WIDTH = 96
FACE_HEIGHT = 96
ARROW_OFFSET_X = TEXTBOX_WIDTH // 2 # Center of textbox width
ARROW_OFFSET_Y = 118 # Example: Bottom edge of text area

# --- Text Rendering Parameters ---
LINE_SPACING = FONT_SIZE + 3 # A bit more than font height
TEXT_WRAP_WIDTH = FACE_OFFSET_X - TEXT_OFFSET_X - 15 # Adjust padding (e.g., 15px) as needed

# --- Text Animation Pauses ---
SFX_PAUSE_DURATION = 0.5  # seconds pause after an inline [sfx:] marker
ELLIPSIS_PAUSE_DURATION = 0.3 # seconds pause after '...'
COMMA_PAUSE_DURATION = 0.15 # seconds pause after ','
PERIOD_PAUSE_DURATION = 0.25 # seconds pause after '.'
QUESTION_PAUSE_DURATION = 0.3 # seconds pause after '?'
EXCLAMATION_PAUSE_DURATION = 0.2 # seconds pause after '!'
ARROW_BLINK_INTERVAL = 500 # seconds for the arrow blink interval
ARROW_BOB_SPEED = 5 # seconds for the arrow bobbing speed
ARROW_BOB_AMOUNT = 3 # pixels for the arrow bobbing amount

# --- Input Box Settings ---
INPUT_BOX_HEIGHT = 35
INPUT_BOX_WIDTH = TEXTBOX_WIDTH # Match textbox width (can be adjusted)
INPUT_BOX_BG_COLOR = (30, 30, 30, 230) # RGBA, slightly transparent background
INPUT_BOX_TEXT_COLOR = (220, 220, 220, 255) # RGBA
INPUT_BOX_BORDER_COLOR = (80, 80, 80, 255) # RGBA for border
INPUT_BOX_BORDER_WIDTH = 1 # Border thickness
INPUT_BOX_PADDING = 10 # Padding inside the box for text
CURSOR_BLINK_INTERVAL = 0.5 # seconds for cursor blink interval

# Key Repeat Settings (milliseconds)
KEY_REPEAT_DELAY = 400  # Initial delay before repeat starts
KEY_REPEAT_INTERVAL = 40 # Interval between repeated keydown events

CHOICE_TEXT_COLOR = (255, 255, 255, 255) # RGBA for choice text
CHOICE_HIGHLIGHT_COLOR = (68, 36, 158, 255) # RGBA for highlighted choice text
CHOICE_BG_COLOR = (40, 20, 70, 255) # RGBA for choice background
CHOICE_PADDING = 5
CHOICE_SPACING_EXTRA = 10

HISTORY_FILE = os.path.join("history.dat")  # File to save conversation history

# --- Screen Capture Settings ---
SCREEN_CAPTURE_MODE_NONE = "none"
SCREEN_CAPTURE_MODE_SCREENSHOT = "screenshot"
SCREEN_CAPTURE_MODE_VIDEO = "video"  # WIP - not fully implemented yet

SCREEN_CAPTURE_OPTIONS = ["No", "Screenshot", "Video [WIP]"]
SCREEN_CAPTURE_VALUES = [SCREEN_CAPTURE_MODE_NONE, SCREEN_CAPTURE_MODE_SCREENSHOT, SCREEN_CAPTURE_MODE_VIDEO]

MONITOR_ALL = "all"
MONITOR_PRIMARY = "primary"

SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
TEMP_SCREENSHOT = os.path.join(SCREENSHOT_DIR, "temp_screenshot.jpg")

# --- Text Speed ---
class TextSpeed(Enum):
    SLOW = 100  # milliseconds per character
    NORMAL = 35 # Make normal speed faster (was 50)
    FAST = 20 # Adjust fast accordingly (was 25)
    INSTANT = 1

TEXT_SPEED_MAP = {
    "slow": TextSpeed.SLOW.value,
    "normal": TextSpeed.NORMAL.value,
    "fast": TextSpeed.FAST.value,
    "instant": TextSpeed.INSTANT.value,
}

# --- AI Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not found in environment variables.")

AI_MODEL_NAME = "gemini-2.0-flash" # Default model if not in options

AVAILABLE_AI_MODELS = [
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

EXIT_STATUS_KEY = "last_exit_status"
EXIT_STATUS_NORMAL_AI = "normal_ai_quit"
EXIT_STATUS_ABRUPT = "abrupt_quit"

# Helper function to get available face names
def get_available_faces(faces_directory: str, prefix: str = "") -> List[str]:
    """Scans the specified directory and returns a list of valid face names."""
    face_names = []
    if not os.path.exists(faces_directory):
        print(f"Warning: Faces directory not found at {faces_directory} for face detection.")
        return [] 

    try:
        print(f"Scanning faces directory: {faces_directory} with prefix '{prefix}'")
        for filename in os.listdir(faces_directory):
            file_path = os.path.join(faces_directory, filename)
            # Only consider files (not directories) that start with prefix and have image extensions
            if (os.path.isfile(file_path) and 
                filename.startswith(prefix) and 
                filename.lower().endswith((".png", ".jpg", ".jpeg"))):
                face_name = filename[len(prefix):-len(os.path.splitext(filename)[1])]
                face_names.append(face_name)
                print(f"  Found face: '{face_name}' from file: {filename}")
    except Exception as e:
        print(f"Error scanning faces directory '{faces_directory}': {e}")
        return [] 

    if not face_names:
        print(f"Warning: No face files found in '{faces_directory}' with prefix '{prefix}'.")
        all_files = []
        try:
            if os.path.exists(faces_directory):
                all_files = os.listdir(faces_directory)
                print(f"  Contents of directory: {all_files}")
        except Exception:
            pass
    else:
        print(f"Found {len(face_names)} faces: {', '.join(face_names)}")

    return sorted(face_names)

# Helper function to get available sound effect names
def get_available_sfx(sfx_directory: str, exclude: List[str] = []) -> List[str]:
    """Scans the sfx directory and returns a list of valid sound effect names (excluding specified files)."""
    sfx_names = []
    if not os.path.exists(sfx_directory):
        print(f"Warning: SFX directory not found at {sfx_directory} for SFX detection.")
        return [] 

    try:
        for filename in os.listdir(sfx_directory):
            if os.path.isfile(os.path.join(sfx_directory, filename)) and \
               filename.lower().endswith(('.wav', '.ogg', '.mp3')) and \
               filename.lower() not in exclude:
                sfx_name = os.path.splitext(filename)[0]
                sfx_names.append(sfx_name)
    except Exception as e:
        print(f"Error scanning SFX directory: {e}")
        return [] 

    return sorted(sfx_names)

# Helper function to get available background images
def get_available_backgrounds(bg_directory: str) -> List[str]:
    """Scans the background directory and returns a list of valid background image filenames."""
    bg_names = []
    if not os.path.exists(bg_directory):
        print(f"Warning: Background directory not found at {bg_directory}.")
        return [] 

    try:
        for filename in os.listdir(bg_directory):
            if os.path.isfile(os.path.join(bg_directory, filename)) and \
               filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                bg_names.append(filename)
    except Exception as e:
        print(f"Error scanning Background directory: {e}")
        return [] 

    default_bg_filename = os.path.basename(DEFAULT_BG_IMG)
    if default_bg_filename not in bg_names and os.path.exists(DEFAULT_BG_IMG):
        pass 

    return sorted(list(set(bg_names)))

# --- AI Structured Output Definition (Pydantic Models) ---

class NikoResponse(BaseModel):
    text: str = Field(..., description="The text Niko says for *this specific dialogue box*. Do NOT use \\n here.")
    face: str = Field(..., description="The name of the face expression for *this specific dialogue box*. Choose ONLY from the available list for the current character.")
    speed: Literal["slow", "normal", "fast", "instant"] = Field(..., description="The speed at which the text for *this specific dialogue box* should be displayed.")
    bold: bool = Field(default=False, description="Whether the text for *this specific dialogue box* should be displayed in bold overall.")
    italic: bool = Field(default=False, description="Whether the text for *this specific dialogue box* should be displayed in italics overall.")

# New model for the overall AI response, containing a list of segments
class AIResponse(BaseModel):
    segments: List[NikoResponse] = Field(..., description="A list of dialogue segments. Each segment represents one dialogue box.")

# --- AI Self-Speaking Settings ---
AI_SPEAK_FREQUENCY_NEVER = "never"
AI_SPEAK_FREQUENCY_RARELY = "rarely"
AI_SPEAK_FREQUENCY_SOMETIMES = "sometimes"
AI_SPEAK_FREQUENCY_OFTEN = "often"

AI_SPEAK_FREQUENCY_OPTIONS = ["Never", "Rarely", "Sometimes", "Often"]
AI_SPEAK_FREQUENCY_VALUES = [AI_SPEAK_FREQUENCY_NEVER, AI_SPEAK_FREQUENCY_RARELY, 
                           AI_SPEAK_FREQUENCY_SOMETIMES, AI_SPEAK_FREQUENCY_OFTEN]

AI_SPEAK_FREQUENCY_TIMES = {
    AI_SPEAK_FREQUENCY_NEVER: None,
    AI_SPEAK_FREQUENCY_RARELY: (300, 900),
    AI_SPEAK_FREQUENCY_SOMETIMES: (120, 300),
    AI_SPEAK_FREQUENCY_OFTEN: (30, 120)
}

# --- Simple Options ---
DEFAULT_OPTIONS = {
    "setup_complete": False,
    "player_name": None,
    "active_character_id": "niko",
    "default_text_speed": "normal",
    "sfx_volume": 0.5,
    "background_image_path": DEFAULT_BG_IMG,
    "ai_model_name": AI_MODEL_NAME,
    "screen_capture_mode": SCREEN_CAPTURE_MODE_NONE,
    "monitor_selection": MONITOR_PRIMARY,
    "ai_speak_frequency": AI_SPEAK_FREQUENCY_NEVER,
}

SELECT_BACKGROUND_FROM_FILE = "SELECT_FROM_FILE"
