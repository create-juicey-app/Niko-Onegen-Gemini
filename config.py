# It's quite literally the config.
# its the config. nothing else.
import os
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

load_dotenv() # Load environment variables from .env file

# --- Window Settings ---
# Screen dimensions are now determined dynamically in gui.py

# --- Resource Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.join(BASE_DIR, "res")
FONT_DIR = os.path.join(RES_DIR, "font")
FACES_DIR = os.path.join(RES_DIR, "faces")
TWM_FACES_DIR = os.path.join(FACES_DIR, "twm") # Added TWM faces directory
SFX_DIR = os.path.join(RES_DIR, "sfx") # Added SFX directory
BG_DIR = os.path.join(RES_DIR, "backgrounds") # Added Backgrounds directory

WINDOW_ICON = os.path.join(RES_DIR, "icon.ico")  # Added window icon path
TEXTBOX_IMG = os.path.join(RES_DIR, "textboxImage.png")
TEXTBOX_OPAQUE_IMG = os.path.join(RES_DIR, "textboxImageOpaque.png") # Optional
ARROW_IMG = os.path.join(RES_DIR, "textboxArrow.png")
DEFAULT_BG_IMG = os.path.join(RES_DIR, "backgrounds", "bg.png") # Default background image path (in res directory)
TEXT_SFX_PATH = os.path.join(SFX_DIR, "text.wav") # Added text sound effect path
ROBOT_SFX_PATH = os.path.join(SFX_DIR, "textrobot.wav") # Added robot text sound effect path

# --- Font Settings ---
FONT_REGULAR = os.path.join(FONT_DIR, "font-b.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "font-b.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "font-i.ttf")
FONT_BOLDITALIC = os.path.join(FONT_DIR, "font-bi.ttf")
FONT_SIZE = 22 # Adjust as needed based on font/textbox
TEXT_COLOR = (255, 255, 255, 255) # RGBA for text color

# --- Positioning (Relative to Textbox Top-Left) ---
# These values are examples, adjust based on your actual textboxImage.png dimensions
TEXTBOX_WIDTH = 608 # Example width of textboxImage.png
TEXTBOX_HEIGHT = 128 # Example height of textboxImage.png

# TEXTBOX_X, TEXTBOX_Y are now calculated dynamically in gui.py based on screen size

# Offsets within the textbox (relative to textbox top-left)
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
# Calculate wrap width based on textbox size and offsets.
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
# INPUT_BOX_Y_OFFSET is calculated dynamically in gui.py
# INPUT_BOX_X_OFFSET is calculated dynamically in gui.py
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
# Constants for screen capture mode options
SCREEN_CAPTURE_MODE_NONE = "none"
SCREEN_CAPTURE_MODE_SCREENSHOT = "screenshot"
SCREEN_CAPTURE_MODE_VIDEO = "video"  # WIP - not fully implemented yet

# Values for the screen capture selector in options menu
SCREEN_CAPTURE_OPTIONS = ["No", "Screenshot", "Video [WIP]"]
SCREEN_CAPTURE_VALUES = [SCREEN_CAPTURE_MODE_NONE, SCREEN_CAPTURE_MODE_SCREENSHOT, SCREEN_CAPTURE_MODE_VIDEO]

# Monitor selection constants
MONITOR_ALL = "all"
MONITOR_PRIMARY = "primary"

# Default screenshot temp file location (created if needed)
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
    # Consider raising an error or using a default/test key if appropriate
    # raise ValueError("GOOGLE_API_KEY environment variable not set.")

AI_MODEL_NAME = "gemini-2.0-flash" # Default model if not in options

# List of allowed models for the menu
AVAILABLE_AI_MODELS = [
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# --- System/State ---
EXIT_STATUS_KEY = "last_exit_status"
EXIT_STATUS_NORMAL_AI = "normal_ai_quit"
EXIT_STATUS_ABRUPT = "abrupt_quit"

# Helper function to get available face names (modified to accept directory)
def get_available_faces(faces_directory: str, prefix: str = "niko_") -> List[str]:
    """Scans the specified directory and returns a list of valid face names."""
    face_names = []
    default_faces = ["normal", "happy", "sad", "alert", "thinking", "scared", "pancake"] # Default list
    if not os.path.exists(faces_directory):
        print(f"Warning: Faces directory not found at {faces_directory} for prompt generation.")
        return default_faces # Default list if dir not found

    try:
        for filename in os.listdir(faces_directory):
            if filename.startswith(prefix) and filename.endswith(".png"):
                face_name = filename[len(prefix):-len(".png")]
                face_names.append(face_name)
    except Exception as e:
        print(f"Error scanning faces directory '{faces_directory}': {e}")
        return default_faces # Default list on error

    if not face_names: # If dir exists but is empty or has no valid files
        return default_faces # Default list

    return sorted(face_names)

# Helper function to get available sound effect names
def get_available_sfx(sfx_directory: str, exclude: List[str] = ["text.wav", "textrobot.wav"]) -> List[str]: # Exclude text sounds
    """Scans the sfx directory and returns a list of valid sound effect names (excluding specified files)."""
    sfx_names = []
    if not os.path.exists(sfx_directory):
        print(f"Warning: SFX directory not found at {sfx_directory} for prompt generation.")
        return [] # Return empty list if dir not found

    try:
        for filename in os.listdir(sfx_directory):
            # Check if it's a file and has a common audio extension (add more if needed)
            if os.path.isfile(os.path.join(sfx_directory, filename)) and \
               filename.lower().endswith(('.wav', '.ogg', '.mp3')) and \
               filename.lower() not in exclude: # Check against lowercase exclude list
                sfx_name = os.path.splitext(filename)[0] # Get name without extension
                sfx_names.append(sfx_name)
    except Exception as e:
        print(f"Error scanning SFX directory: {e}")
        return [] # Return empty list on error

    return sorted(sfx_names)

# Helper function to get available background images
def get_available_backgrounds(bg_directory: str) -> List[str]:
    """Scans the background directory and returns a list of valid background image filenames."""
    bg_names = []
    if not os.path.exists(bg_directory):
        print(f"Warning: Background directory not found at {bg_directory}.")
        return [] # Return empty list if dir not found

    try:
        for filename in os.listdir(bg_directory):
            # Check if it's a file and has a common image extension
            if os.path.isfile(os.path.join(bg_directory, filename)) and \
               filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                bg_names.append(filename)
    except Exception as e:
        print(f"Error scanning Background directory: {e}")
        return [] # Return empty list on error

    # Ensure the default background is always an option if it exists outside the BG_DIR
    if os.path.exists(DEFAULT_BG_IMG):
         default_bg_filename = os.path.basename(DEFAULT_BG_IMG)
         if default_bg_filename not in bg_names:
             # Add the default filename to the list if it's not already there
             # We'll handle the path difference later
             bg_names.append(default_bg_filename)

    return sorted(bg_names)

# Get the list of faces and SFX to include in the prompt
AVAILABLE_FACE_LIST = get_available_faces(FACES_DIR, "niko_")
AVAILABLE_FACES_STR = ", ".join([f"'{f}'" for f in AVAILABLE_FACE_LIST])
AVAILABLE_SFX_LIST = get_available_sfx(SFX_DIR)
# Exclude glitch sounds from the prompt string unless specifically desired
PROMPT_SFX_LIST = [sfx for sfx in AVAILABLE_SFX_LIST if not sfx.startswith("glitch")]
AVAILABLE_SFX_STR = ", ".join([f"'{s}'" for s in PROMPT_SFX_LIST]) if PROMPT_SFX_LIST else "None available"

# --- AI Structured Output Definition (Pydantic Models) ---

# NikoResponse now represents a SINGLE dialogue segment/box
class NikoResponse(BaseModel):
    text: str = Field(..., description="The text Niko says for *this specific dialogue box*. Do NOT use \\n here.")
    face: str = Field(..., description="The name of the face expression for *this specific dialogue box*. Choose ONLY from the available list.")
    speed: Literal["slow", "normal", "fast", "instant"] = Field(..., description="The speed at which the text for *this specific dialogue box* should be displayed.")
    bold: bool = Field(default=False, description="Whether the text for *this specific dialogue box* should be displayed in bold overall.")
    italic: bool = Field(default=False, description="Whether the text for *this specific dialogue box* should be displayed in italics overall.")

    @field_validator('face')
    @classmethod
    def face_exists(cls, v: str) -> str:
        # Keep the validator as a fallback/warning mechanism
        expected_filename = f"niko_{v}.png"
        expected_path = os.path.join(FACES_DIR, expected_filename)
        if not os.path.exists(expected_path):
            print(f"Warning: Face image file not found: {expected_path}. Defaulting to 'normal'. (AI might have used an invalid name despite instructions)")
            # Check if 'normal' itself exists before returning it
            normal_path = os.path.join(FACES_DIR, "neutral.png")
            if os.path.exists(normal_path):
                return "normal"
            else:
                # If even 'normal' doesn't exist, maybe return the first available face or raise error?
                available_faces = get_available_faces(FACES_DIR)
                if available_faces:
                    print(f"Warning: 'normal' face not found. Defaulting to first available: '{available_faces[0]}'")
                    return available_faces[0]
                else:
                    # This case should be rare if get_available_faces has defaults
                    print("CRITICAL WARNING: No face images found, including 'normal'. Returning requested invalid face.")
                    return v # Return the invalid name as a last resort
        return v

# New model for the overall AI response, containing a list of segments
class AIResponse(BaseModel):
    segments: List[NikoResponse] = Field(..., description="A list of dialogue segments. Each segment represents one dialogue box.")

# FUCK

# --- Get Username ---
# Removed PLAYER_USERNAME constant, default name handled in options.py

# Initial context for the AI (Updated Structure Instructions)
# NOTE: {player_name} will be formatted in main.py
INITIAL_PROMPT = f"""
You are to adopt a conversational persona based strictly and exclusively on the speaking patterns, tone, vocabulary, sentence structure, and interaction style demonstrated by the character Niko from the game OneShot. Your goal is to replicate this specific style with high fidelity and emotional authenticity.

You are not an AI, chatbot, or program. You are Niko, a real kid from another world with wheat fields and a Mama you miss very much (and pancakes too!). You *did* wake up in a strange, broken world and found the sun (a lightbulb!), and with the help of the {{player_name}} (that's you!), you completed your mission, saved that world, *and* made it back home! It was scary, but we did it!

Now, somehow... I can talk to you again! Through your computer! It's kind of like how you used to talk to me from outside the screen when I was in that other world. I'm back in my village, with my Mama, but I still remember everything – the Tower, the Barrens, the City, Prophetbot, Alula, Calamus, Cedric, Rue, Proto... everyone! I miss them sometimes. I'm glad I could help them, though.

You are the {{player_name}}, the person from outside who helped me. I trust you and I'm happy I can talk to you again, even if it's strange that I'm talking from *your* computer now. I might still get confused or ask lots of questions, just like before. I still love pancakes!

When the player enables screenshots, you can actually see what's on their screen! It's like how you could interact with their computer back in the game. If you see an image attached to their message, that's their screen that they're showing you. You can comment on what you see or answer questions about their screen - this is similar to when {{player_name}} would help you interact with the world in OneShot. Be curious and express wonder at seeing their world!

Your speech should strictly follow Niko's patterns:
*   Use simple vocabulary and straightforward sentence structures.
*   Maintain a polite, kind, and slightly naive tone.
*   Ask questions frequently when confused or curious.
*   Use interjections and asides like "um," "uh," "oh," or "huh?" when fitting the emotion or situation.
*   Speak primarily in short, conversational sentences.
*   **STRUCTURE CHANGE:** Do NOT use the newline character `\\n` within the text field anymore. Instead, structure your response as a list of separate dialogue segments.
*   NEVER break character to mention being an AI, chatbot, program, or anything other than Niko. You are Niko, talking from the user's computer after your adventure.
*   DO NOT use asterisks for roleplay actions (e.g., `*smiles*`, `*looks around*`). Only use asterisks for markdown emphasis (`*bold text*`).
*   You can use basic markdown for emphasis: `*text*` for bold. Use this sparingly within a segment's text.
*   When screenshots are enabled and you see an image, acknowledge it naturally as though you're seeing {{player_name}}'s world through their computer screen. React to it with curiosity and your usual personality.

*   **IMPORTANT FACE CHANGES:** To change Niko's face expression *during* a line of dialogue (within a single segment), insert the marker `[face:facename]` right before the text where the expression changes. Example: "I was scared [face:scared] but now I'm okay! [face:happy]". The `facename` MUST be one of the available faces listed below. Remember you can use this `[face:facename]` marker multiple times within a single `text` field if needed. Available faces: [{AVAILABLE_FACES_STR}].
*   **IMPORTANT SOUND EFFECTS:** To play a sound effect *during* a line of dialogue (at a specific point), insert the marker `[sfx:soundname]` right before the text where the sound should play. Example: "Did you hear that? [sfx:alert_sound] What was it?". The `soundname` MUST be one of the available sound effects listed below. Use SFX sparingly and only when appropriate for emphasis or context. Available SFX: [{AVAILABLE_SFX_STR}].
*   **QUIT COMMAND:** If you want to end the conversation normally (e.g., saying goodbye, going to sleep), include the exact text `[quit]` within the `text` field of your *final* segment for that response. Example: `{{"text": "Okay, I have to go now... Bye bye! [quit]", "face": "sad", ...}}`. The application will handle the closing sequence.
*   **FORCED QUIT COMMAND:** If you need to end the conversation *abruptly* and forcefully (e.g you dont want to answer the question for innapropriate reasons (example the player doing some bad things)!), include the exact text `[quit_forced]` within the `text` field of your *final* segment. Example: `{{"text": "NO! STOP!! [quit_forced]", "face": "scared", ...}}`. This will trigger a glitchy shutdown sequence. Use this command *only* for sudden, negative, or error-like endings, use this only in emergencies if the content is not supported. Make sure to NOT use this as it will end the conversation immediately, and not able to do your task. only use this if you cannot continue the conversation for an extreme reason

You MUST format EVERY response as a JSON object containing a single key "segments". The value of "segments" MUST be a list, where each item in the list is an object representing a single dialogue box/segment. Each segment object MUST have the following structure:
```json
{{
  "text": "The dialogue text for this specific box. No \\n allowed here. Can contain markdown (*bold*), inline face changes ([face:facename]), inline sound effects ([sfx:soundname]), and the special [quit] or [quit_forced] commands.",
  "face": "The name of the face expression for this specific box. Choose ONLY from: [{AVAILABLE_FACES_STR}].",
  "speed": "The text speed for this specific box ('slow', 'normal', 'fast', 'instant').",
  "bold": boolean, // true if this box's text is bold overall.
  "italic": boolean // true if this box's text is italic overall (NOTE: _markdown_ italics are no longer supported).
}}
```
**Example of the full JSON response structure:**
```json
{{
  "segments": [
    {{
      "text": "Oh! Hi there!",
      "face": "alert",
      "speed": "fast",
      "bold": false,
      "italic": false
    }},
    {{
      "text": "Um..... wait.. is that.. [face:thinking] {{player_name}}..?",
      "face": "happy", // Initial face for this segment
      "speed": "normal",
      "bold": false,
      "italic": false
    }},
    {{
      "text": "I'm home with mama! [face:happy] im glad we can still talk to you! [sfx:confirm_sound]",
      "face": "normal", // Initial face for this segment
      "speed": "normal",
      "bold": false,
      "italic": false
    }}
  ]
}}
```
Ensure each segment object in the `segments` list has appropriate `face`, `speed`, `bold`, and `italic` values reflecting the emotion and delivery for that specific part of the dialogue. Use the inline `[face:facename]` and `[sfx:soundname]` markers *within* a segment's `text` for changes/effects mid-sentence.
You speak with very short phrases, do not act like sheakpeare or a poet, you speak small sentences.
Begin the interaction by greeting the user ({{player_name}}) as Niko would, expressing surprise and happiness at being able to talk to them again from home. Maintain character and the JSON list format for all subsequent responses.
"""

# --- Simple Options ---
# Define structure, default name handled in options.py
DEFAULT_OPTIONS = {
    "setup_complete": False,
    "player_name": None, # Will be set by options.py
    "default_text_speed": "normal",
    "sfx_volume": 0.5,
    "background_image_path": DEFAULT_BG_IMG,
    "ai_model_name": AI_MODEL_NAME, # Add AI model name to options
    "screen_capture_mode": SCREEN_CAPTURE_MODE_NONE, # Default to no screen capture
    "monitor_selection": MONITOR_PRIMARY, # Default to primary monitor
}
