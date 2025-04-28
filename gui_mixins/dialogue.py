import pygame
import re
import config
from config import NikoResponse, TextSpeed, TEXT_SPEED_MAP

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

        # Wrap the text for rendering
        self._wrap_text()

    def _wrap_text(self):
        self.rendered_lines = []
        font_for_wrapping = self.current_font
        # Use getattr to safely access current_text, provide default ""
        current_text_stripped = getattr(self, 'current_text', "").strip()

        if not current_text_stripped or not font_for_wrapping:
            self.total_chars_to_render = 0 # Nothing to wrap? My job here is done.
            return

        max_width_pixels = config.TEXT_WRAP_WIDTH
        # Combined regex for splitting by whitespace OR markers, keeping delimiters
        marker_regex_str = r'(\[face:[a-zA-Z0-9_]+\]|\[sfx:[a-zA-Z0-9_]+\])'
        word_splitter_regex = re.compile(rf'(\s+|{marker_regex_str})')
        parts = word_splitter_regex.split(current_text_stripped)
        parts = [p for p in parts if p] # Remove empty strings from split

        wrapped_paragraphs = []
        current_line = ""
        current_line_width = 0
        # Regexes for checking markers (pre-compiled for efficiency)
        face_marker_regex = getattr(self, 'face_marker_regex', re.compile(r'\[face:([a-zA-Z0-9_]+)\]'))
        sfx_marker_regex = getattr(self, 'sfx_marker_regex', re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]'))


        for part in parts:
            is_face_marker = face_marker_regex.match(part)
            is_sfx_marker = sfx_marker_regex.match(part)
            is_marker = is_face_marker or is_sfx_marker
            is_space = part.isspace()

            if is_marker:
                # Markers don't contribute to width but are kept in the line
                current_line += part
                continue
            elif is_space:
                try:
                    # Only add space width if the line isn't empty
                    space_width = font_for_wrapping.size(" ")[0] if current_line else 0
                except (pygame.error, AttributeError): space_width = 0 # Handle font errors

                # Add space if it fits
                if current_line_width + space_width <= max_width_pixels:
                    current_line += part
                    current_line_width += space_width
                else:
                    # Space doesn't fit, wrap line and start new line with the space
                    wrapped_paragraphs.append(current_line)
                    current_line = part # Start new line with the space
                    current_line_width = space_width
            else: # It's a word (non-marker, non-space)
                word = part
                try:
                    word_surface = font_for_wrapping.render(word, True, (0,0,0)) # Render to get width
                    word_width = word_surface.get_width()
                    space_width = 0
                    # Check if a space is needed before this word
                    if current_line and not current_line.endswith(" ") and not is_marker:
                         # Avoid adding space if the previous part was a marker
                         # Check the end of the current_line for markers to be safer
                         if not face_marker_regex.search(current_line[-20:]) and \
                            not sfx_marker_regex.search(current_line[-20:]):
                              # Also avoid space after certain punctuation if needed (e.g., '(')
                              last_char = current_line[-1] if current_line else ''
                              if last_char not in ['(', '[']: # Example: Don't add space after '('
                                   space_width = font_for_wrapping.size(" ")[0]

                except (pygame.error, AttributeError) as e:
                     print(f"Warning: Error rendering word '{word}' for wrapping: {e}")
                     word_width = 0 # Assume 0 width on error
                     space_width = 0
                     # Continue processing other parts

                # Check if the word (plus potential preceding space) fits
                if current_line_width + space_width + word_width <= max_width_pixels:
                    # Add space if needed
                    if current_line and space_width > 0:
                         current_line += " "
                         current_line_width += space_width
                    # Add the word
                    current_line += word
                    current_line_width += word_width
                else:
                    # Word doesn't fit, wrap the current line
                    wrapped_paragraphs.append(current_line)
                    # Start the new line with the current word
                    current_line = word
                    current_line_width = word_width

        # Add the last accumulated line
        wrapped_paragraphs.append(current_line)

        # --- Post-processing: Clean up lines ---
        final_lines = []
        # Regex to remove space *before* a marker at the start of a wrapped segment
        space_before_marker_regex = re.compile(r'\s+(\[(?:face|sfx):[^\]]+\])')

        for line in wrapped_paragraphs:
            # Remove leading/trailing whitespace and potentially spaces before markers
            cleaned_line = space_before_marker_regex.sub(r'\1', line.strip())
            if cleaned_line: # Only add non-empty lines
                final_lines.append(cleaned_line)

        self.rendered_lines = final_lines

        # --- Calculate total characters accurately (excluding markers) ---
        accurate_plain_char_count = 0
        marker_regex_combined = re.compile(marker_regex_str) # Use the combined marker regex
        for line in self.rendered_lines:
             line_without_markers = marker_regex_combined.sub('', line)
             accurate_plain_char_count += len(line_without_markers)

        self.total_chars_to_render = accurate_plain_char_count


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


    def draw_animated_text(self, target_surface=None):
        if target_surface is None:
            target_surface = self.screen # Assume self.screen exists

        # Use config for offsets
        text_x = self.textbox_x + config.TEXT_OFFSET_X
        text_y = self.textbox_y + config.TEXT_OFFSET_Y
        plain_chars_drawn_total = 0

        # Determine the base font for the current dialogue block
        segment_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE)) # Default fallback
        if self.use_bold and self.use_italic and 'bold_italic' in self.fonts:
            segment_font = self.fonts['bold_italic']
        elif self.use_bold:
            segment_font = self.fonts.get('bold', self.fonts['regular'])
        elif self.use_italic and 'bold_italic' in self.fonts: # Using bold_italic for italic
            segment_font = self.fonts['bold_italic']
        # Ensure segment_font is valid
        if not segment_font: segment_font = pygame.font.Font(None, config.FONT_SIZE)


        # Regex to split line into: face markers, sfx markers, or text segments
        segment_regex = re.compile(
            r'(\[face:([a-zA-Z0-9_]+)\])|'   # Group 1: Full face marker, Group 2: face name
            r'(\[sfx:([a-zA-Z0-9_]+)\])|'    # Group 3: Full sfx marker, Group 4: sfx name
            # Group 5: Text segment (handles brackets not part of known markers)
            r'([^\[]+(?:\[(?![fF][aA][cC][eE]:|[sS][fF][xX]:)[^\[]*)*)'
        )
        # Pre-compile marker regexes if not already done
        face_marker_regex = getattr(self, 'face_marker_regex', re.compile(r'\[face:([a-zA-Z0-9_]+)\]'))
        sfx_marker_regex = getattr(self, 'sfx_marker_regex', re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]'))


        for i, line in enumerate(self.rendered_lines):
            # Stop drawing lines if we've already drawn the required number of characters
            if plain_chars_drawn_total >= self.current_char_index:
                break

            line_y = text_y + i * config.LINE_SPACING
            current_render_x = text_x # Start rendering at the beginning of the line
            marker_idx = 0 # Unique index for SFX markers within this line

            for match in segment_regex.finditer(line):
                # Stop processing segments if we've drawn enough characters
                if plain_chars_drawn_total >= self.current_char_index:
                    break

                # Index where this segment *starts* in terms of plain characters processed so far
                segment_start_plain_char_index = plain_chars_drawn_total

                face_marker_match = match.group(1)
                sfx_marker_match = match.group(3)
                text_segment = match.group(5)

                if face_marker_match:
                    # Process face marker if we've reached or passed its position
                    if segment_start_plain_char_index <= self.current_char_index:
                        face_name = match.group(2)
                        new_face = self.active_face_images.get(face_name)
                        if new_face:
                            self.current_face_image = new_face
                        else:
                            print(f"Warning: Face '{face_name}' referenced in text not found.")
                    # Face markers don't consume render space or plain chars
                    continue

                elif sfx_marker_match:
                    # Process SFX marker if we've reached its position and haven't played it yet
                    marker_key = (i, marker_idx) # Unique key: (line_index, marker_index_in_line)
                    if segment_start_plain_char_index <= self.current_char_index and marker_key not in self._played_sfx_markers:
                        sfx_name = match.group(4)
                        sound = self.other_sfx.get(sfx_name)
                        if sound:
                            # Check if forced quitting prevents sound
                            can_play_sound = not (getattr(self, 'is_forced_quitting', False) and getattr(self, 'forced_quit_timer', 0) >= getattr(self, 'forced_quit_shake_start_delay', 0.2))
                            if can_play_sound:
                                sound.play()
                        else:
                            print(f"Warning: SFX '{sfx_name}' referenced in text not found.")
                        self._played_sfx_markers.add(marker_key) # Mark as played
                    marker_idx += 1 # Increment marker index for the next SFX on this line
                    # SFX markers don't consume render space or plain chars
                    continue

                elif text_segment:
                    # This is a plain text segment
                    plain_sub_segment_len = len(text_segment)
                    # How many more plain characters do we *need* to draw in total?
                    remaining_chars_needed = self.current_char_index - plain_chars_drawn_total
                    # How many characters from *this specific segment* should we draw?
                    chars_to_draw_in_sub_segment = max(0, min(plain_sub_segment_len, remaining_chars_needed))

                    if chars_to_draw_in_sub_segment > 0:
                        text_to_render = text_segment[:chars_to_draw_in_sub_segment]
                        try:
                            # Render the partial (or full) segment text
                            text_surface = segment_font.render(text_to_render, True, config.TEXT_COLOR) # Use config color
                            target_surface.blit(text_surface, (current_render_x, line_y))
                            # Advance the rendering position for the next segment on this line
                            current_render_x += text_surface.get_width()
                        except (pygame.error, AttributeError) as e:
                            print(f"Error rendering text segment: {e}")
                            # Attempt to advance position based on estimated size? Or just skip?
                            # Skipping might be safer to avoid overlapping text.
                            pass # Skip rendering this segment on error

                    # Update the total count of plain characters drawn so far
                    plain_chars_drawn_total += chars_to_draw_in_sub_segment

                    # If we didn't draw the whole sub-segment, it means we've hit the
                    # current_char_index limit, so break from processing further segments.
                    if chars_to_draw_in_sub_segment < plain_sub_segment_len:
                        break # Stop processing segments in this line

            # After processing all segments in a line, check again if we should stop
            if plain_chars_drawn_total >= self.current_char_index:
                break # Stop processing more lines
