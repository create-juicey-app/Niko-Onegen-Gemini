# This module defines the main GUI class, inheriting functionalities
# from various mixins for organization. It manages the overall state,
# initialization, and the main update loop.

import pygame
import os
import config
import textwrap # Keep for potential use outside mixins? Or remove if unused.
import re
import time
import math
import random
from typing import Literal
from config import NikoResponse, TextSpeed, TEXT_SPEED_MAP, get_available_sfx, get_available_faces
import platform

# Import Mixins
from gui_mixins.resources import ResourcesMixin
from gui_mixins.dialogue import DialogueMixin
from gui_mixins.input import InputMixin
from gui_mixins.choices import ChoicesMixin
from gui_mixins.effects import EffectsMixin
from gui_mixins.rendering import RenderingMixin
from gui_mixins.events import EventsMixin
from gui_mixins.options_menu import OptionsMenuMixin
from gui_mixins.rendering_components import RenderingComponentsMixin
from gui_mixins.event_handlers import EventHandlersMixin

if platform.system() == "Windows":
    import ctypes
    # Note: ctypes usage is now within EventsMixin and EffectsMixin

# Inherit from all mixins including the new ones
class GUI(ResourcesMixin, DialogueMixin, InputMixin, ChoicesMixin, EffectsMixin,
          RenderingMixin, EventsMixin, OptionsMenuMixin,
          RenderingComponentsMixin, EventHandlersMixin):
    """
    Handles the graphical user interface, rendering, and events by combining
    functionality from various specialized mixin classes.
    """

    def __init__(self, initial_options):
        # Let the variable hoarding begin! (Kept in main class for shared state)
        self.options = initial_options
        self.sfx_volume = initial_options.get("sfx_volume", 0.5) # Initial volume

        pygame.init()
        pygame.font.init()
        # Initialize mixer only if not disabled
        if not pygame.mixer.get_init():
             try:
                 pygame.mixer.init() # Gotta make some noise
             except pygame.error as e:
                 print(f"Warning: Failed to initialize pygame.mixer: {e}. Sound disabled.")
                 # Handle case where mixer fails entirely if needed

        # --- Enable Key Repeat ---
        pygame.key.set_repeat(config.KEY_REPEAT_DELAY, config.KEY_REPEAT_INTERVAL)

        # --- Screen and Window Setup ---
        try:
            # Try to get primary display info for centering
            pygame.display.init() # Ensure display is initialized
            info = pygame.display.Info()
            screen_width = info.current_w
            screen_height = info.current_h
        except pygame.error as e:
            print(f"Warning: Could not get display info ({e}). Using default 800x600 for positioning.")
            screen_width = 800
            screen_height = 600

        # Define window dimensions based on config
        self.window_width = config.TEXTBOX_WIDTH + 40 # Add padding around textbox
        self.window_height = config.TEXTBOX_HEIGHT + config.INPUT_BOX_HEIGHT + 150 # Approx height for textbox, input, face, padding

        # Calculate initial window position (centered horizontally, near bottom)
        pos_x = (screen_width - self.window_width) // 2
        pos_y = screen_height - self.window_height - 80 # Offset from bottom
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_x},{pos_y}" # Set position before creating window

        # Create the display surface
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.SHOWN) # Use SHOWN flag
        pygame.display.set_caption("Niko-Onegen") # Window title
        self.window_x = pos_x # Store initial position
        self.window_y = pos_y

        # --- UI Element Positioning ---
        self.textbox_x = (self.window_width - config.TEXTBOX_WIDTH) // 2 # Center textbox
        self.textbox_y = 20 # Padding from top

        # Initial input box dimensions and position (relative to textbox)
        initial_input_box_width = config.TEXTBOX_WIDTH - 40 # Slightly narrower than textbox
        self.input_box_x = self.textbox_x + (config.TEXTBOX_WIDTH - initial_input_box_width) // 2
        self.input_box_y = self.textbox_y + config.TEXTBOX_HEIGHT + 10 # Below textbox
        initial_input_box_height = config.INPUT_BOX_HEIGHT

        # --- State Variables ---
        self.clock = pygame.time.Clock()
        self.running = True # Main loop flag

        # --- Load Resources using Methods from ResourcesMixin ---
        # Fonts
        self.fonts = self._load_fonts() # From ResourcesMixin
        # Images (Background, Textbox, Arrow)
        self.bg_img_original = self.load_image(self.options.get("background_image_path", config.DEFAULT_BG_IMG)) # From ResourcesMixin
        self.textbox_img = self.load_image(config.TEXTBOX_IMG, scale_to=(config.TEXTBOX_WIDTH, config.TEXTBOX_HEIGHT)) # Scale textbox img
        self.arrow_img = self.load_image(config.ARROW_IMG) # From ResourcesMixin
        # Face Images
        self.niko_face_images = self._load_face_images(config.FACES_DIR, "niko_") # From ResourcesMixin
        self.twm_face_images = self._load_face_images(config.TWM_FACES_DIR, "en_") # From ResourcesMixin
        # Sounds (Text SFX, Other SFX)
        self.default_text_sfx = self.load_sound(config.TEXT_SFX_PATH) # From ResourcesMixin
        self.robot_text_sfx = self.load_sound(config.ROBOT_SFX_PATH) # From ResourcesMixin
        self.other_sfx = self._load_other_sfx() # From ResourcesMixin
        # Assign specific SFX for easier access
        self.confirm_sfx = self.other_sfx.get("menu_decision")
        self.glitch_sfx = [
            self.other_sfx.get("glitch1"),
            self.other_sfx.get("glitch2"),
            self.other_sfx.get("glitch3")
        ]
        self.glitch_sfx = [sfx for sfx in self.glitch_sfx if sfx] # Filter out None values

        # --- Initialize Mixin States ---
        # (Call initializers for mixins that require them)
        self._initialize_options_menu_state() # Initialize options menu state

        # --- Dialogue State ---
        self.active_text_sfx = self.default_text_sfx # Start with default text sound
        self.active_face_images = self.niko_face_images # Start with Niko faces
        self.current_face_image = self.active_face_images.get("normal") # Start with normal face
        self.last_face_image = self.current_face_image # Track previous face for AI thinking pulse

        self._sfx_play_toggle = False # Used for alternating text SFX
        self._played_sfx_markers = set() # Track played inline [sfx:] tags

        self.current_text = "" # Current dialogue text being displayed
        self.current_char_index = 0 # Current character index for animation
        self.text_animation_timer = 0.0 # Timer for text animation speed
        # Default speed from options or fallback
        default_speed_key = self.options.get("default_text_speed", "normal")
        self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(default_speed_key, config.TEXT_SPEED_MAP["normal"])
        # Font style state
        self.current_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE)) # Fallback font
        self.use_bold = False
        self.use_italic = False

        self.is_animating = False # Is text currently animating?
        self.draw_arrow = False # Should the advance arrow be drawn?
        self.arrow_blink_timer = 0.0 # Timer for arrow blinking
        self.arrow_visible = True # Is the arrow currently visible (during blink)?
        self.arrow_base_y = self.textbox_y + config.ARROW_OFFSET_Y # Base Y position for arrow
        self.arrow_offset_y = 0 # Vertical offset for arrow bobbing

        self.rendered_lines = [] # Stores wrapped text lines
        self.total_chars_to_render = 0 # Total non-marker characters in current text

        # Pause State
        self.is_paused = False # Is dialogue paused (e.g., after punctuation)?
        self.pause_timer = 0.0 # Timer for current pause duration
        self.current_pause_duration = 0.0 # Duration of the current pause

        # --- Input State ---
        self.is_input_active = False # Is the text input box active?
        self.user_input_text = "" # Current text entered by the user
        self.input_cursor_pos = 0 # Cursor position within user_input_text
        # Input box rectangle (dynamic height)
        self.input_rect = pygame.Rect(
            self.input_box_x,
            self.input_box_y,
            initial_input_box_width,
            initial_input_box_height
        )
        self.input_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE)) # Font for input
        self.input_cursor_visible = False # Is the input cursor currently visible (blinking)?
        self.input_cursor_timer = 0.0 # Timer for input cursor blinking

        # --- AI Thinking State ---
        self.ai_is_thinking = False # Is the AI currently "thinking"? (Affects face display)

        # --- Choice State (Main choices, not options menu widgets) ---
        self.is_choice_active = False # Is the multiple-choice interface active?
        self.choice_options = [] # List of choice strings
        self.choice_rects = [] # List of pygame.Rect for each rendered choice (for mouse collision)
        self.selected_choice_index = 0 # Index of the currently highlighted choice
        self.choice_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE)) # Font for choices
        # Choice colors and layout
        self.choice_color = config.CHOICE_TEXT_COLOR # Defined in config
        self.choice_highlight_color = config.CHOICE_HIGHLIGHT_COLOR # Defined in config
        self.choice_bg_color = config.CHOICE_BG_COLOR # Defined in config
        self.choice_padding = config.CHOICE_PADDING # Defined in config
        self.choice_spacing = self.choice_font.get_height() + config.CHOICE_SPACING_EXTRA # Dynamic spacing

        # --- Menu / History State ---
        self.is_menu_active = False # Is the *main* pause menu overlay active?
        self.menu_overlay_color = (0, 0, 0, 150) # Semi-transparent black overlay
        self.is_history_active = False # Is the dialogue history view active?

        # --- Window Interaction State ---
        self.dragging = False # Is the window currently being dragged?
        self.drag_offset_x = 0 # Offset for dragging calculation
        self.drag_offset_y = 0

        # --- Text Parsing Regex (Compile once) ---
        self.face_marker_regex = re.compile(r'\[face:([a-zA-Z0-9_]+)\]')
        self.sfx_marker_regex = re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]')

        # --- Forced Quit State (Initialized by EffectsMixin.start_forced_quit) ---
        self.is_forced_quitting = False
        self.forced_quit_timer = 0.0
        # Other forced quit variables (glitch_index, shake_timer, etc.) are initialized in start_forced_quit

        # --- Fade Effect Surface ---
        self.fade_surface = pygame.Surface((self.window_width, self.window_height))
        self.fade_surface.fill((0, 0, 0)) # Initialize as black

        # --- Windows Specific Handle (for dragging/positioning) ---
        self.hwnd = None
        if platform.system() == "Windows":
            try:
                # Ensure display is initialized before getting wm_info
                if not pygame.display.get_init(): pygame.display.init()
                self.hwnd = pygame.display.get_wm_info()["window"]
            except (pygame.error, KeyError) as e:
                print(f"Warning: Could not get window handle (HWND) for dragging: {e}")
                pass # Dragging might not work smoothly

        # --- Initial Dialogue ---
        # Set an initial state, maybe an empty dialogue or a loading message
        # self.set_dialogue(NikoResponse(text="Loading...", face="normal", speed="normal"))
        # Or leave it blank until the first message arrives


    def update(self, dt):
        """Main update loop called every frame."""
        # Ignore updates if history view or options menu is active
        if self.is_history_active or self.is_options_menu_active:
             # Still update input cursor blink if options menu input is focused
             if self.is_options_menu_active:
                  try: # Defensive check
                       focused_widget = self.options_widgets[self.focused_widget_index]
                       if focused_widget["type"] == "input":
                            focused_widget["cursor_timer"] += dt
                            if focused_widget["cursor_timer"] >= config.CURSOR_BLINK_INTERVAL:
                                 focused_widget["cursor_visible"] = not focused_widget["cursor_visible"]
                                 focused_widget["cursor_timer"] %= config.CURSOR_BLINK_INTERVAL
                  except (IndexError, KeyError, AttributeError):
                       pass # Ignore errors if widget structure is unexpected
             return

        # --- Forced Quit Update ---
        if self.is_forced_quitting:
            # Delegate update logic to EffectsMixin
            self.update_forced_quit(dt)
            # No further updates needed if forced quitting
            return

        # --- Pause Update ---
        if self.is_paused:
            self.pause_timer += dt
            if self.pause_timer >= self.current_pause_duration:
                self.is_paused = False # Pause over
                self.pause_timer = 0.0
                self.current_pause_duration = 0.0
            else:
                # Stop text sound during pause
                if self.active_text_sfx and self.active_text_sfx.get_num_channels() > 0:
                    self.active_text_sfx.stop()
                return # Don't process animation while paused

        # --- Text Animation Update ---
        if self.is_animating:
            # Instant Text Speed
            if self.current_text_speed_ms == config.TextSpeed.INSTANT.value:
                # Play sound once at the beginning if instant speed
                if self.total_chars_to_render > 0 and self.current_char_index == 0 and self.active_text_sfx:
                     self.active_text_sfx.play()
                # Complete animation instantly
                self.current_char_index = self.total_chars_to_render
                self.is_animating = False
                self.draw_arrow = True # Show arrow immediately
            # Normal Animation Speed
            elif self.current_char_index < self.total_chars_to_render:
                self.text_animation_timer += dt * 1000 # Convert dt (seconds) to milliseconds
                # Calculate how many characters *should* be visible by now
                target_char_index = int(self.text_animation_timer / self.current_text_speed_ms)

                if target_char_index > self.current_char_index:
                    new_char_index = min(target_char_index, self.total_chars_to_render)
                    num_new_chars = new_char_index - self.current_char_index

                    # Play sound based on toggle for newly revealed characters
                    play_sound_this_frame = False
                    if num_new_chars > 0:
                        for _ in range(num_new_chars): # Toggle for each new char
                            self._sfx_play_toggle = not self._sfx_play_toggle
                            if self._sfx_play_toggle:
                                play_sound_this_frame = True
                                break # Only need one toggle=True to play sound once
                    if play_sound_this_frame and self.active_text_sfx:
                        self.active_text_sfx.play()

                    # Update the actual character index
                    self.current_char_index = new_char_index

                    # Check for pause triggers *after* updating index
                    pause_duration = self._check_pause_trigger_at_index(self.current_char_index) # From DialogueMixin
                    if pause_duration > 0:
                        self.is_paused = True
                        self.current_pause_duration = pause_duration
                        self.pause_timer = 0.0
                        # Stop sound when pausing
                        if self.active_text_sfx and self.active_text_sfx.get_num_channels() > 0:
                            self.active_text_sfx.stop()
                        # Don't return here, let the pause check handle the next frame

            else: # Animation finished (current_char_index >= total_chars_to_render)
                self.is_animating = False
                self.draw_arrow = True # Show arrow
                self.text_animation_timer = 0.0 # Reset timer

        # --- Arrow Blinking and Bobbing Update ---
        # Only update arrow if it should be drawn and not in other modes
        should_update_arrow = (self.draw_arrow and
                              not self.is_input_active and
                              not self.is_paused and
                              not self.is_choice_active)

        if should_update_arrow:
            # Blinking
            self.arrow_blink_timer += dt
            if self.arrow_blink_timer > config.ARROW_BLINK_INTERVAL: # Use config value
                self.arrow_visible = not self.arrow_visible
                self.arrow_blink_timer = 0.0
            # Bobbing (using sine wave)
            bob_offset = (math.sin(pygame.time.get_ticks() * config.ARROW_BOB_SPEED) * config.ARROW_BOB_AMOUNT)
            self.arrow_offset_y = bob_offset
        else:
            self.arrow_visible = False # Ensure arrow is hidden if conditions not met

        # --- Input Cursor Blinking Update (Main Input) ---
        if self.is_input_active:
            self.input_cursor_timer += dt
            if self.input_cursor_timer >= config.CURSOR_BLINK_INTERVAL: # Use config value
                self.input_cursor_visible = not self.input_cursor_visible
                self.input_cursor_timer = 0.0
        else:
            self.input_cursor_visible = False # Ensure cursor is hidden if input not active

    # Methods moved to mixins:
    # - load_image, load_sound, set_sfx_volume, _load_fonts, _load_face_images, _load_other_sfx
    # - set_active_sfx, set_active_face_set, set_dialogue, _wrap_text, _check_pause_trigger_at_index, draw_animated_text
    # - clear_input, _wrap_input_text, handle_input_event (logic moved to EventsMixin)
    # - draw_multiple_choice, handle_choice_event (logic moved to EventsMixin)
    # - fade_out, fade_in, start_forced_quit, update_forced_quit, render_forced_quit_effects
    # - render_background_and_overlay, render, render_input_box
    # - handle_event
    # - play_confirm_sound, play_sound (moved to ResourcesMixin for consistency)
    # - draw_options_menu, handle_options_menu_event, enter_options_menu, exit_options_menu (now in OptionsMenuMixin)

    # Kept methods:
    # - __init__
    # - update
