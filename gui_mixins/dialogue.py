import pygame
import re
import config
from config import NikoResponse, TextSpeed, TEXT_SPEED_MAP
from .text_utils import wrap_text # Import the wrapping utility

class DialogueMixin:
    """Mixin class for handling dialogue display, animation, and parsing."""

    def set_active_sfx(self, sfx_type: config.Literal["default", "robot"]):
        if sfx_type == "robot" and self.robot_text_sfx:
            self.active_text_sfx = self.robot_text_sfx
        else:
            self.active_text_sfx = self.default_text_sfx

    def set_active_face_set(self, face_set_type: config.Literal["niko", "twm"]):
        if face_set_type == "twm":
            self.active_face_images = self.twm_face_images
        else:
            self.active_face_images = self.niko_face_images

        # Ensure 'normal' exists in the chosen set, fallback to placeholder if needed
        if 'normal' not in self.active_face_images:
             print(f"Warning: 'normal' face missing from active set '{face_set_type}'. Creating placeholder.")
             # Create placeholder dynamically if needed
             placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT))
             placeholder_surface.fill((255, 0, 255)) # Magenta placeholder
             self.active_face_images['normal'] = placeholder_surface

        # Attempt to set current face to 'normal' from the active set
        self.current_face_image = self.active_face_images.get("normal")

        # Final fallback if even 'normal' failed somehow (e.g., loading error)
        if not self.current_face_image:
             print(f"Critical Warning: Could not set 'normal' face for set '{face_set_type}'. Trying first available.")
             if self.active_face_images:
                 # Get the first available face as a last resort
                 self.current_face_image = next(iter(self.active_face_images.values()), None)
                 if self.current_face_image is None: # If dict was empty after all attempts
                      print("Critical Error: No faces available in active set. Using final placeholder.")
                      placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT))
                      placeholder_surface.fill((255, 0, 255))
                      self.current_face_image = placeholder_surface
             else: # Should not happen if _load_face_images ensures 'normal'
                 print("Critical Error: Active face images dictionary is empty. Using final placeholder.")
                 placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT))
                 placeholder_surface.fill((255, 0, 255))
                 self.current_face_image = placeholder_surface


    def set_dialogue(self, dialogue_data: NikoResponse):
        # Store the current face before potentially changing it
        if hasattr(self, 'current_face_image') and self.current_face_image:
            self.last_face_image = self.current_face_image
        else:
            # Ensure last_face_image is initialized if current_face_image isn't set yet
            self.last_face_image = self.active_face_images.get("normal")


        # Reset flags and states
        self.is_input_active = False
        self.is_choice_active = False
        self.user_input_text = ""
        self.input_cursor_pos = 0
        self.ai_is_thinking = False # Ensure AI thinking state is reset

        if not dialogue_data:
            self.current_text = "..." # Default text for empty data
            # Try to set face to sad, fallback to normal, then last resort placeholder
            self.current_face_image = self.active_face_images.get("sad", self.active_face_images.get("normal"))
            if not self.current_face_image: # Final fallback
                 placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT)); placeholder_surface.fill((255,0,255))
                 self.current_face_image = placeholder_surface
            # Use default speed calculation for empty data
            default_speed_key = getattr(self, 'options', {}).get("default_text_speed", "normal")
            self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(default_speed_key, config.TEXT_SPEED_MAP["normal"])
            self.use_bold = False
            self.use_italic = False
        else:
            self.current_text = dialogue_data.text
            face_name = dialogue_data.face
            # Try to get the specified face, fallback to normal, then placeholder
            self.current_face_image = self.active_face_images.get(face_name)
            if not self.current_face_image:
                 print(f"Warning: Face '{face_name}' not found. Falling back to 'normal'.")
                 self.current_face_image = self.active_face_images.get("normal")
                 if not self.current_face_image: # Final fallback
                      print(f"Critical Warning: Face 'normal' also not found. Using placeholder.")
                      placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT)); placeholder_surface.fill((255,0,255))
                      self.current_face_image = placeholder_surface

            # --- Text Speed Calculation ---
            # Define speed modifiers (Ideally, this map should be in config.py)
            SPEED_MODIFIER_MAP = {
                "slow": 1.5,
                "normal": 1.0,
                "fast": 0.5,
                "instant": 0.0
            }
            # Get user's base speed setting
            user_base_speed_key = getattr(self, 'options', {}).get("default_text_speed", "normal")
            # Get base speed value (ms/char)
            base_speed_ms = config.TEXT_SPEED_MAP.get(user_base_speed_key, config.TEXT_SPEED_MAP["normal"])

            # Get AI's requested speed modifier key
            ai_speed_key = dialogue_data.speed
            # Get the modifier value, default to 1.0 (normal) if invalid/missing
            speed_modifier = SPEED_MODIFIER_MAP.get(ai_speed_key, 1.0)

            # Calculate final speed
            if speed_modifier == 0.0: # Handle "instant" explicitly
                self.current_text_speed_ms = 0.0
            else:
                self.current_text_speed_ms = base_speed_ms * speed_modifier
                # Optional: Add a minimum speed to prevent excessively fast text if needed
                # self.current_text_speed_ms = max(1, self.current_text_speed_ms) # Example: minimum 1ms/char

            # --- End Text Speed Calculation ---


            # Set font style flags
            self.use_bold = dialogue_data.bold
            self.use_italic = dialogue_data.italic

        # Select the appropriate font based on flags
        if self.use_bold and self.use_italic and 'bold_italic' in self.fonts:
            self.current_font = self.fonts['bold_italic']
        elif self.use_bold:
            self.current_font = self.fonts.get('bold', self.fonts['regular'])
        # Italic uses bold_italic font if available, otherwise regular
        elif self.use_italic and 'bold_italic' in self.fonts:
             # Note: This assumes you want bold_italic for italic-only.
             # If you had a dedicated italic font, you'd load and use it here.
            self.current_font = self.fonts['bold_italic']
        else:
            self.current_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE)) # Fallback font

        # Reset animation state
        self.current_char_index = 0
        self.text_animation_timer = 0.0
        self.is_animating = True
        self.draw_arrow = False
        self._sfx_play_toggle = False # Reset sfx toggle for character sounds
        self.is_paused = False
        self.pause_timer = 0.0
        self.current_pause_duration = 0.0
        self._played_sfx_markers.clear() # Clear markers for inline SFX

        # Wrap the text for rendering using the utility function
        self.rendered_lines, self.total_chars_to_render = wrap_text(
            self.current_text,
            self.current_font,
            config.TEXT_WRAP_WIDTH
        )

    def _check_pause_trigger_at_index(self, current_plain_index: int) -> float:
        """Checks if the character at the given plain index triggers a pause."""
        if current_plain_index <= 0:
            return 0.0 # No pause at the very beginning

        cumulative_plain_chars = 0
        # Regex to find markers, punctuation groups, or text segments
        # Handles markers, specific punctuation, and general text chunks
        segment_regex = re.compile(
            r'(\[face:[a-zA-Z0-9_]+\])|'   # Group 1: Face marker
            r'(\[sfx:[a-zA-Z0-9_]+\])|'    # Group 2: SFX marker
            r'(\.\.\.|[.,!?])|'            # Group 3: Punctuation (..., . , ! ?)
            r'([^\[.,!?]+(?:\[(?![fF][aA][cC][eE]:|[sS][fF][xX]:)[^\[]*)*)' # Group 4: Text segment (handles brackets not part of markers)
        )
        # Pre-compile marker regexes if not already done
        face_marker_regex = getattr(self, 'face_marker_regex', re.compile(r'\[face:([a-zA-Z0-9_]+)\]'))
        sfx_marker_regex = getattr(self, 'sfx_marker_regex', re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]'))


        for line in self.rendered_lines:
            for match in segment_regex.finditer(line):
                face_marker_match = match.group(1)
                sfx_marker_match = match.group(2)
                punctuation_segment = match.group(3)
                text_segment = match.group(4) # This captures plain text

                if face_marker_match:
                    # Face markers have no duration and don't trigger pauses themselves
                    continue

                elif sfx_marker_match:
                    # SFX markers *might* trigger a short pause *after* they are processed
                    # Check if the *end* of this marker corresponds to the current index
                    # Since markers have zero plain char length, check if the index matches the *start*
                    if cumulative_plain_chars == current_plain_index:
                         # Check if this specific marker should pause (optional config)
                         # sfx_name = sfx_marker_regex.match(sfx_marker_match).group(1) # Extract name if needed
                         return config.SFX_PAUSE_DURATION # Apply standard SFX pause
                    # No plain chars added by SFX marker itself

                elif punctuation_segment:
                    segment_len = len(punctuation_segment)
                    start_plain_index = cumulative_plain_chars
                    end_plain_index = cumulative_plain_chars + segment_len

                    # Check if the *end* of this punctuation segment matches the target index
                    if current_plain_index == end_plain_index:
                        if punctuation_segment == "...":
                            return config.ELLIPSIS_PAUSE_DURATION
                        elif punctuation_segment == ",":
                            return config.COMMA_PAUSE_DURATION
                        elif punctuation_segment == ".":
                            return config.PERIOD_PAUSE_DURATION
                        elif punctuation_segment == "?":
                            return config.QUESTION_PAUSE_DURATION
                        elif punctuation_segment == "!":
                            return config.EXCLAMATION_PAUSE_DURATION
                        # Add other punctuation pauses here if needed

                    # If the target index falls *within* the punctuation, no pause yet
                    if start_plain_index < current_plain_index < end_plain_index:
                         return 0.0 # Still processing the punctuation itself

                    cumulative_plain_chars += segment_len # Advance count by punctuation length

                elif text_segment:
                    # This is a plain text segment
                    plain_text_segment = text_segment # Already plain text
                    segment_len = len(plain_text_segment)
                    start_plain_index = cumulative_plain_chars
                    end_plain_index = cumulative_plain_chars + segment_len

                    # If the target index falls within this text segment, no pause needed
                    if start_plain_index < current_plain_index <= end_plain_index:
                        return 0.0 # Still processing plain text

                    cumulative_plain_chars += segment_len # Advance count by text length

            # If we finished processing a line and the target index is beyond it, continue to next line
            if cumulative_plain_chars >= current_plain_index:
                 # We've processed enough characters to cover the target index
                 # If no pause was triggered exactly at the index, return 0.0
                 # (This handles cases where the index lands between segments)
                 # The check inside the loops should have returned a duration if needed.
                 # If we reach here, it means the index didn't land exactly at a pause point.
                 # However, the logic inside the loop should correctly return 0.0 if the index
                 # falls *within* a segment. This final return handles cases after the loop.
                 # Let's refine: if the index was *exactly* matched for a pause, it returned > 0.
                 # If it fell *within* a segment, it returned 0.0.
                 # If we exit the loop because cumulative >= current, and no pause was triggered,
                 # it means the character *at* current_plain_index doesn't trigger a pause itself.
                 return 0.0


        # Should ideally not be reached if current_plain_index <= total_chars_to_render
        # But return 0.0 as a safeguard
        return 0.0
