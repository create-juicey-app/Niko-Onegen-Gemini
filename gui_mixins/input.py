import pygame
import re
import config

class InputMixin:
    """Mixin class for handling user text input."""

    def clear_input(self):
        """Clears the user input text and resets related state."""
        self.user_input_text = ""
        self.input_cursor_pos = 0
        # Reset input box height to default only if it exists
        if hasattr(self, 'input_rect'):
            self.input_rect.height = config.INPUT_BOX_HEIGHT
        # Reset cursor visibility timer
        self.input_cursor_visible = True
        self.input_cursor_timer = 0.0
        # Ensure the input box is rendered immediately with the cleared state
        if hasattr(self, 'input_rect') and hasattr(self, 'input_font'):
            try:
                max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                self._wrap_input_text(self.user_input_text, max_render_width)  # Recalculate layout
            except Exception as e:
                print(f"Warning: Error recalculating input box layout: {e}")

    def _wrap_input_text(self, text: str, max_width: int) -> tuple[list[str], list[int]]:
        """Wraps input text based on font size and max width, returning lines and start indices."""
        wrapped_lines = []
        line_start_indices = [0] # Start index of the first line is always 0
        current_wrap_line = ""
        original_text_ptr = 0 # Tracks position in the original unwrapped text

        # Use raw string for regex to avoid potential SyntaxWarning
        # Split by whitespace, keeping the whitespace as separate elements
        words = re.split(r'(\s+)', text)
        words = [w for w in words if w] # Remove empty strings potentially created by split

        font = self.input_font # Assumes self.input_font is set

        if not font:
            print("Error: Input font not available for wrapping.")
            return [text], [0] # Fallback: return original text as single line

        current_line_char_count = 0 # Track characters added to the current line

        for word in words:
            is_space = word.isspace()
            test_line = current_wrap_line + word # Tentative line with the new word/space

            try:
                line_width = font.size(test_line)[0]

                # --- Case 1: Word/Space fits on the current line ---
                if line_width <= max_width:
                    current_wrap_line += word
                    current_line_char_count += len(word)
                    # original_text_ptr is implicitly advanced by len(word) later

                # --- Case 2: Word/Space does NOT fit on the current line ---
                else:
                    # First, add the completed line (if not empty) to wrapped_lines
                    if current_wrap_line:
                        wrapped_lines.append(current_wrap_line)
                        # The start index of the *next* line is the current pointer position
                        line_start_indices.append(original_text_ptr)

                    # Now, handle the word/space that didn't fit
                    word_width = font.size(word)[0]

                    # --- Subcase 2a: The word itself is longer than the max width ---
                    if not is_space and word_width > max_width:
                        # Break the long word character by character
                        temp_long_word_line = ""
                        for char_idx, char in enumerate(word):
                            char_width = font.size(char)[0]
                            # Check if adding the char exceeds max width
                            if font.size(temp_long_word_line + char)[0] <= max_width:
                                temp_long_word_line += char
                            else:
                                # Char doesn't fit, wrap the line built so far
                                wrapped_lines.append(temp_long_word_line)
                                original_text_ptr += len(temp_long_word_line)
                                line_start_indices.append(original_text_ptr)
                                # Start the new line with the current char
                                temp_long_word_line = char
                        # The remainder of the long word becomes the start of the next line
                        current_wrap_line = temp_long_word_line
                        current_line_char_count = len(current_wrap_line)
                        # original_text_ptr advanced within the loop

                    # --- Subcase 2b: It's a space that doesn't fit (or a normal word) ---
                    # Start the new line with this word/space (trim leading space if it was the cause of wrap)
                    else:
                        # If the word is just a space, and the previous line wasn't empty,
                        # we might just discard this leading space on the new line.
                        # However, the regex split keeps spaces, so handle them.
                        # If the word itself fits on a new line, start with it.
                        if word_width <= max_width:
                            current_wrap_line = word.lstrip() if wrapped_lines else word # Avoid leading space on new line unless it's the very first word
                            current_line_char_count = len(current_wrap_line)
                            # original_text_ptr advanced later
                        else:
                             # This case should be covered by 2a (word longer than max_width)
                             # If somehow reached, treat as error or simple wrap
                             current_wrap_line = word
                             current_line_char_count = len(word)
            except pygame.error as e:
                print(f"Error calculating text size for wrapping: {e}")
                # Fallback: treat the word as a single line
                wrapped_lines.append(current_wrap_line)
                line_start_indices.append(original_text_ptr)
                current_wrap_line = word
                current_line_char_count = len(word)
                # No need to check width, just add it

            # Advance the original text pointer *after* processing the word/space
            original_text_ptr += len(word)


        # Add the last remaining line
        if current_wrap_line:
            wrapped_lines.append(current_wrap_line)
            # No need to add a start index here, as it's the end of the text

        # Ensure the number of lines and start indices match up (should be len(lines) == len(indices))
        # If text is empty, wrapped_lines is [], indices is [0]. Correct.
        # If text has one line, wrapped_lines is [line], indices is [0]. Correct.
        # If text has N lines, wrapped_lines is [l1..lN], indices is [0, start2..startN]. Correct.

        # Handle completely empty input text case
        if not text:
            return [], [0]

        return wrapped_lines, line_start_indices

    def handle_input_event(self, event) -> tuple[str, str | int | None] | None:
        """Handles events specifically when text input is active."""
        if event.type == pygame.KEYDOWN:
            prev_text = self.user_input_text
            prev_cursor_pos = self.input_cursor_pos
            prev_height = self.input_rect.height
            needs_redraw = False # Flag to indicate if text/cursor changed visually

            if event.key == pygame.K_RETURN:
                # Don't submit if input is empty (optional)
                # if not self.user_input_text.strip():
                #     self.play_sound("menu_buzzer") # Or some other feedback
                #     return None
                submitted_text = self.user_input_text
                self.play_confirm_sound() # Play confirmation sound
                # Action: submit_input, Value: the text
                return ("submit_input", submitted_text)
            elif event.key == pygame.K_BACKSPACE:
                if self.input_cursor_pos > 0:
                    # Remove character before cursor
                    self.user_input_text = self.user_input_text[:self.input_cursor_pos-1] + self.user_input_text[self.input_cursor_pos:]
                    self.input_cursor_pos -= 1
                    needs_redraw = True
            elif event.key == pygame.K_DELETE:
                 if self.input_cursor_pos < len(self.user_input_text):
                      # Remove character after cursor
                      self.user_input_text = self.user_input_text[:self.input_cursor_pos] + self.user_input_text[self.input_cursor_pos+1:]
                      # Cursor position doesn't change, but text does
                      needs_redraw = True
            elif event.key == pygame.K_LEFT:
                if self.input_cursor_pos > 0:
                    self.input_cursor_pos = max(0, self.input_cursor_pos - 1)
                    needs_redraw = True # Cursor moved
            elif event.key == pygame.K_RIGHT:
                if self.input_cursor_pos < len(self.user_input_text):
                    self.input_cursor_pos = min(len(self.user_input_text), self.input_cursor_pos + 1)
                    needs_redraw = True # Cursor moved
            elif event.key == pygame.K_HOME:
                 if self.input_cursor_pos > 0:
                     self.input_cursor_pos = 0
                     needs_redraw = True # Cursor moved
            elif event.key == pygame.K_END:
                 if self.input_cursor_pos < len(self.user_input_text):
                     self.input_cursor_pos = len(self.user_input_text)
                     needs_redraw = True # Cursor moved
            elif event.key == pygame.K_ESCAPE:
                # Action: input_escape, Value: None
                return ("input_escape", None) # Allow escaping input mode
            else:
                # Handle printable characters
                if event.unicode.isprintable():
                    new_char = event.unicode
                    # --- Check if adding character would exceed max height ---
                    can_add_char = True
                    try:
                        # Simulate adding the character
                        test_text = self.user_input_text[:self.input_cursor_pos] + new_char + self.user_input_text[self.input_cursor_pos:]
                        max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                        wrapped_lines, _ = self._wrap_input_text(test_text, max_render_width)
                        num_lines = len(wrapped_lines)
                        required_height = (num_lines * self.input_font.get_height()) + config.INPUT_BOX_PADDING * 2
                        max_input_height = config.TEXTBOX_HEIGHT - 20 # Max height constraint

                        # If current height is already max, and required height is still greater, prevent adding char
                        if self.input_rect.height >= max_input_height and required_height > max_input_height:
                            self.play_sound("menu_buzzer") # Play sound indicating limit reached
                            can_add_char = False

                    except (pygame.error, AttributeError) as e:
                        print(f"Warning: Error checking input box size before adding char: {e}")
                        # Proceed cautiously, allow adding char but don't resize later if error occurs

                    # --- Add character if allowed ---
                    if can_add_char:
                        self.user_input_text = self.user_input_text[:self.input_cursor_pos] + new_char + self.user_input_text[self.input_cursor_pos:]
                        self.input_cursor_pos += len(new_char) # Use len(new_char) for potential multi-byte chars
                        needs_redraw = True

            # --- Recalculate height after modification (if text changed) ---
            if needs_redraw and (self.user_input_text != prev_text): # Only recalc if text actually changed
                try:
                    max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                    wrapped_lines, _ = self._wrap_input_text(self.user_input_text, max_render_width)
                    num_lines = len(wrapped_lines) if wrapped_lines else 1 # At least one line high
                    required_height = (num_lines * self.input_font.get_height()) + config.INPUT_BOX_PADDING * 2

                    min_height = config.INPUT_BOX_HEIGHT # Min height constraint
                    max_input_height = config.TEXTBOX_HEIGHT - 20 # Max height constraint

                    # Clamp the new height between min and max
                    new_height = max(min_height, min(required_height, max_input_height))

                    # Update rect height if it changed
                    if new_height != self.input_rect.height:
                        self.input_rect.height = new_height
                        # Maybe redraw needed flag already set, but ensure it if height changes
                        needs_redraw = True

                except (pygame.error, AttributeError) as e:
                    print(f"Warning: Error calculating input box size after modification: {e}")
                    # Keep previous height if calculation fails
                    self.input_rect.height = prev_height


            # Reset cursor blink timer if text or cursor position changed
            if needs_redraw:
                self.input_cursor_visible = True # Make cursor visible immediately
                self.input_cursor_timer = 0.0 # Reset blink timer
            return None # Event handled within input mode

        elif event.type == pygame.MOUSEBUTTONDOWN:
             # Allow clicking inside the input box without exiting input mode
             if self.input_rect.collidepoint(event.pos):
                  # Optional: Implement cursor positioning based on click
                  # This requires mapping click coordinates back to text index, complex!
                  # For now, just consume the click event.
                  return None # Stay in input mode
             else:
                  # Clicked outside the input box - maybe treat as submit or escape?
                  # For now, let the main event handler decide (e.g., dragging)
                  pass # Don't consume, let main handler process it

        # Return None if the event was consumed or irrelevant to input logic here
        return None
