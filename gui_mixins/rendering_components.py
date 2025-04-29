import pygame
import config
import math
import os
import re
from .text_utils import wrap_input_text # Import the wrapping utility

class RenderingComponentsMixin:
    """Mixin containing methods for drawing specific UI components."""

    def render_background_and_overlay(self, target_surface):
        """Renders the background image and menu overlay if active."""
        # fuck
        # Check if forced quitting to potentially alter background
        is_forced_quitting = getattr(self, 'is_forced_quitting', False)

        if is_forced_quitting:
            # During forced quit, the background might be part of the shaken surface
            # Or we might want a specific static background like black
            # For now, assume the main render handles the background as part of the UI surface
            pass # Let the main render logic handle background during quit
        elif hasattr(self, 'bg_img_original') and self.bg_img_original:
            # Draw the normal background
            target_surface.fill((0, 0, 0)) # Clear surface first
            # Center the background image
            bg_rect = self.bg_img_original.get_rect(center=(self.window_width // 2, self.window_height // 2))
            target_surface.blit(self.bg_img_original, bg_rect)
        else:
            # Fallback: Fill with black if no background image
            target_surface.fill((0, 0, 0))

        # Draw menu overlay if menu is active and not forced quitting
        if getattr(self, 'is_menu_active', False) and not is_forced_quitting:
            # Ensure overlay color is defined
            overlay_color = getattr(self, 'menu_overlay_color', (0, 0, 0, 150))
            try:
                overlay_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay_surface.fill(overlay_color)
                target_surface.blit(overlay_surface, (0, 0))
            except pygame.error as e:
                print(f"Error creating or blitting menu overlay: {e}")


    def draw_animated_text(self, target_surface=None):
        """Draws the dialogue text with animation and marker processing."""
        # ... existing code from dialogue.py ...
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


    def render_input_box(self, target_surface):
        """Renders the text input box, text, and cursor."""
        # ... existing code from rendering.py ...
        # Check required attributes exist
        if not all(hasattr(self, attr) for attr in ['input_rect', 'input_font', 'user_input_text', 'input_cursor_pos']):
            print("Error: Missing attributes required for render_input_box.")
            return

        # Draw background and border
        try:
            # Background (slightly transparent)
            input_bg_surface = pygame.Surface(self.input_rect.size, pygame.SRCALPHA)
            input_bg_surface.fill(config.INPUT_BOX_BG_COLOR) # Assumes format (R, G, B, A)
            target_surface.blit(input_bg_surface, self.input_rect.topleft)
            # Border
            pygame.draw.rect(target_surface, config.INPUT_BOX_BORDER_COLOR, self.input_rect, config.INPUT_BOX_BORDER_WIDTH)
        except pygame.error as e:
            print(f"Error drawing input box background/border: {e}")
            # Continue to draw text if possible

        # Wrap the text to fit the box width
        max_text_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
        if max_text_width <= 0: return # Cannot render text if padding exceeds width

        # Use the imported wrap_input_text function
        wrapped_text_lines, line_start_indices = wrap_input_text(self.user_input_text, self.input_font, max_text_width)

        # Render wrapped text lines
        cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING # Default cursor X
        cursor_render_y = self.input_rect.top + config.INPUT_BOX_PADDING # Default cursor Y
        found_cursor_line = False
        line_y = self.input_rect.top + config.INPUT_BOX_PADDING

        for i, line_text in enumerate(wrapped_text_lines):
            line_start_char_index = line_start_indices[i]
            # Determine end index carefully (index of start of *next* line, or total length)
            line_end_char_index = line_start_indices[i+1] if i + 1 < len(line_start_indices) else len(self.user_input_text)

            # Stop rendering lines if they exceed the box height
            if line_y + self.input_font.get_height() > self.input_rect.bottom - config.INPUT_BOX_PADDING:
                break # Don't draw lines outside the box

            try:
                # Render the line surface
                line_surface = self.input_font.render(line_text, True, config.INPUT_BOX_TEXT_COLOR[:3]) # Use RGB for color
                line_rect = line_surface.get_rect(topleft=(self.input_rect.left + config.INPUT_BOX_PADDING, line_y))
                target_surface.blit(line_surface, line_rect)

                # --- Calculate cursor position for this line ---
                # Check if the logical cursor position falls within this line's character range
                # Note: cursor can be AT line_end_char_index (meaning at the end of the line)
                if not found_cursor_line and line_start_char_index <= self.input_cursor_pos <= line_end_char_index:
                    # Calculate cursor's character position relative to the start of this *rendered* line
                    # This needs to account for potential stripping of leading spaces during wrapping
                    # For simplicity, assume line_text corresponds directly for now
                    cursor_char_pos_in_line = self.input_cursor_pos - line_start_char_index
                    text_before_cursor_on_line = line_text[:cursor_char_pos_in_line]

                    # Calculate the pixel offset based on the text before the cursor on this line
                    cursor_offset_x = self.input_font.size(text_before_cursor_on_line)[0]

                    # Set the render coordinates for the cursor
                    cursor_render_x = line_rect.left + cursor_offset_x + 1 # Add 1 pixel offset for visibility
                    cursor_render_y = line_rect.top
                    found_cursor_line = True # Found the line where the cursor should be drawn

            except (pygame.error, AttributeError) as e:
                print(f"Error rendering input line: {e}")
                # Skip rendering this line, but advance position

            # Move to the next line position
            line_y += self.input_font.get_height() # Advance by font height (no extra spacing needed)


        # --- Handle cursor position if it's after all rendered text ---
        # This happens if the cursor is at the very end of the input text
        if not found_cursor_line and self.input_cursor_pos == len(self.user_input_text):
             if wrapped_text_lines:
                 # Place cursor at the end of the last rendered line
                 last_line_text = wrapped_text_lines[-1]
                 last_line_y = self.input_rect.top + config.INPUT_BOX_PADDING + (len(wrapped_text_lines) - 1) * self.input_font.get_height()
                 # Check if last line was actually rendered (didn't exceed box height)
                 if last_line_y + self.input_font.get_height() <= self.input_rect.bottom - config.INPUT_BOX_PADDING:
                     cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING + self.input_font.size(last_line_text)[0] + 1
                     cursor_render_y = last_line_y
                 else:
                     # Last line wasn't fully rendered, cursor position is uncertain.
                     # Default to top-left? Or try to estimate based on last visible line?
                     # Fallback to default position for safety.
                     cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING + 1
                     cursor_render_y = self.input_rect.top + config.INPUT_BOX_PADDING

             else:
                 # No lines rendered (empty text), place cursor at the start
                 cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING + 1
                 cursor_render_y = self.input_rect.top + config.INPUT_BOX_PADDING

        # --- Draw the cursor if it's visible (blinking) ---
        if getattr(self, 'input_cursor_visible', False):
            cursor_height = self.input_font.get_height()
            # Ensure cursor doesn't draw outside the right edge of the input box padding area
            cursor_rect = pygame.Rect(cursor_render_x, cursor_render_y, 2, cursor_height) # Simple vertical line cursor
            max_cursor_x = self.input_rect.right - config.INPUT_BOX_PADDING - cursor_rect.width
            cursor_rect.left = min(cursor_rect.left, max_cursor_x)
            cursor_rect.left = max(cursor_rect.left, self.input_rect.left + config.INPUT_BOX_PADDING) # Ensure not left of padding

            # Ensure cursor doesn't draw outside the bottom edge
            cursor_rect.bottom = min(cursor_rect.bottom, self.input_rect.bottom - config.INPUT_BOX_PADDING)

            # Only draw if height is positive (didn't get clipped entirely)
            if cursor_rect.height > 0:
                try:
                    pygame.draw.rect(target_surface, config.INPUT_BOX_TEXT_COLOR[:3], cursor_rect) # Use RGB
                except pygame.error as e:
                    print(f"Error drawing input cursor: {e}")


    def draw_multiple_choice(self, surface):
        """Draws the multiple choice options centered on the screen, truncating long text."""
        # ... existing code from choices.py ...
        if not self.is_choice_active or not self.choice_options:
            return

        # Calculate dimensions and positioning
        max_width = 0
        initial_rendered_surfaces = [] # Store initial renders to get max width
        for option_text in self.choice_options:
            text_surf = self.choice_font.render(option_text, True, self.choice_color)
            initial_rendered_surfaces.append(text_surf)
            max_width = max(max_width, text_surf.get_width())

        # Define item height and gap
        item_height = self.choice_font.get_height() + self.choice_padding # Height of one item's background
        gap = config.CHOICE_SPACING_EXTRA # Gap between items
        effective_item_spacing = item_height + gap # Total vertical space allocated per item

        # Calculate total height of the choice block
        total_height = (len(self.choice_options) * effective_item_spacing) - gap + (self.choice_padding * 2)
        start_y = (self.window_height - total_height) // 2 # Center the block vertically

        # Calculate width of the main background block based on the widest *original* text
        block_width = max_width + self.choice_padding * 4 # Add padding around the widest text
        # Ensure block width doesn't exceed screen width minus margins
        max_allowed_block_width = self.window_width - 40 # Example margin
        block_width = min(block_width, max_allowed_block_width)
        block_x = (self.window_width - block_width) // 2

        # Draw main background for the whole block
        bg_rect = pygame.Rect(block_x, start_y, block_width, total_height)
        pygame.draw.rect(surface, self.choice_bg_color, bg_rect, border_radius=8)

        # Starting y for the first item's background rect, inside the main block padding
        y = start_y + self.choice_padding
        self.choice_rects = [] # Reset rects for collision detection

        # Calculate max width available for text *inside* the block's padding
        max_text_width = block_width - (self.choice_padding * 2)

        for i, option_text in enumerate(self.choice_options):
            # Initial render to check width
            text_surf = self.choice_font.render(option_text, True, self.choice_color)
            display_surf = text_surf # Surface to actually draw
            current_text = option_text

            # --- Truncation Logic ---
            while display_surf.get_width() > max_text_width and len(current_text) > 1:
                # Remove last character before ellipsis (if adding one)
                current_text = current_text[:-1]
                # Render with ellipsis
                display_surf = self.choice_font.render(current_text + "...", True, self.choice_color)
                # If even "..." is too wide, break (shouldn't happen with reasonable fonts/padding)
                if len(current_text) <= 1 and display_surf.get_width() > max_text_width:
                     # As a fallback, render just "..." if it fits, otherwise empty
                     ellipsis_surf = self.choice_font.render("...", True, self.choice_color)
                     if ellipsis_surf.get_width() <= max_text_width:
                          display_surf = ellipsis_surf
                     else: # Render nothing if even ellipsis doesn't fit
                          display_surf = pygame.Surface((0,0))
                     break
            # --- End Truncation ---

            # Calculate the background rect for this specific item
            # Use the width of the *displayed* (potentially truncated) text for item bg width
            item_bg_width = display_surf.get_width() + self.choice_padding * 2
            # Center item_bg horizontally *within* the main bg_rect
            item_bg_x = bg_rect.centerx - (item_bg_width // 2)
            item_bg_rect = pygame.Rect(
                item_bg_x, # Use calculated centered x
                y,
                item_bg_width,
                item_height # Use calculated item height
            )
            self.choice_rects.append(item_bg_rect) # Store this rect for collision

            # Draw highlight if selected (using item_bg_rect)
            if i == self.selected_choice_index:
                pygame.draw.rect(surface, self.choice_highlight_color, item_bg_rect, border_radius=5)

            # Calculate text position centered within item_bg_rect
            text_rect = display_surf.get_rect(center=item_bg_rect.center)
            surface.blit(display_surf, text_rect) # Blit the potentially truncated text

            # Increment y for the next item's background top
            y += effective_item_spacing


    def draw_options_menu(self, surface):
        """Draws the entire options menu screen, handling scrolling and pop-ups."""
        # ... existing code from options_menu.py ...
        if not self.is_options_menu_active:
            return

        # Draw background overlay
        self.render_background_and_overlay(surface)

        # Define the visible content area (excluding potential header/footer fixed areas)
        content_area_y_start = 80 # Match initial y_offset in build
        content_area_height = self.window_height - content_area_y_start # Available space for scrollable content
        self.visible_options_height = content_area_height # Update visible height

        # Draw Title (Fixed position)
        title_font = self.fonts.get('bold', self.options_font_label)
        title_surf = title_font.render("Options", True, self.options_value_color)
        title_rect = title_surf.get_rect(centerx=self.window_width // 2, top=30)
        surface.blit(title_surf, title_rect)

        # --- Draw Scrollable Widgets ---
        max_scroll = max(0, self.total_options_height - self.visible_options_height)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll)) # Clamp scroll_y

        for i, widget in enumerate(self.options_widgets):
            is_focused = (i == self.focused_widget_index)
            # Original rect defines position within the *total* scrollable area
            original_rect = widget["rect"]
            # Calculate draw rect based on scroll offset
            draw_rect = original_rect.move(0, -self.scroll_y)

            # --- Visibility Check ---
            # Check if the widget is vertically within the visible content area
            visible_rect = pygame.Rect(0, content_area_y_start, self.window_width, content_area_height)
            if not visible_rect.colliderect(draw_rect):
                 continue # Skip drawing if not visible

            # --- Draw Label (Skip for buttons, handled internally) ---
            if widget["type"] != "button":
                label_text = widget["label"]
                label_surf = self.options_font_label.render(label_text, True, self.options_label_color)
                label_rect = label_surf.get_rect(midright=(draw_rect.left - 10, draw_rect.centery))
                surface.blit(label_surf, label_rect)

            # Draw Widget Background (at draw_rect position)
            pygame.draw.rect(surface, self.options_widget_bg_color, draw_rect, border_radius=5)

            # Draw Widget Content (pass draw_rect for positioning)
            if widget["type"] == "input":
                self._draw_input_widget(surface, widget, is_focused, draw_rect)
            elif widget["type"] == "choice":
                self._draw_choice_widget(surface, widget, is_focused, draw_rect)
            elif widget["type"] == "button":
                self._draw_button_widget(surface, widget, is_focused, draw_rect)

            # Draw Focus Highlight (at draw_rect position)
            if is_focused and not self.is_options_choice_popup_active: # Don't show main focus if pop-up is active
                pygame.draw.rect(surface, self.options_highlight_color, draw_rect, width=2, border_radius=5)

        # --- Draw Scrollbar ---
        if max_scroll > 0:
            scrollbar_area_height = self.visible_options_height
            scrollbar_x = self.window_width - 15 # Position on the right
            scrollbar_y = content_area_y_start # Align with content area

            # Scrollbar background track
            track_rect = pygame.Rect(scrollbar_x, scrollbar_y, 8, scrollbar_area_height)
            pygame.draw.rect(surface, self.scrollbar_color, track_rect, border_radius=4)

            # Scrollbar handle
            handle_height_ratio = min(1.0, scrollbar_area_height / self.total_options_height)
            handle_height = max(20, int(scrollbar_area_height * handle_height_ratio))
            handle_y_ratio = self.scroll_y / max_scroll
            handle_y = scrollbar_y + int(handle_y_ratio * (scrollbar_area_height - handle_height))

            handle_rect = pygame.Rect(scrollbar_x, handle_y, 8, handle_height)
            pygame.draw.rect(surface, self.scrollbar_handle_color, handle_rect, border_radius=4)

        # --- Draw Choice Pop-up (if active) ---
        if self.is_options_choice_popup_active:
            # Delegate drawing to the ChoicesMixin method (which is now also in this mixin)
            self.draw_multiple_choice(target_surface=surface) # Pass the main surface as target_surface


    def _draw_input_widget(self, surface, widget, is_focused, draw_rect):
        """Draws the content of an input widget at the specified draw_rect."""
        # ... existing code from options_menu.py ...
        text = widget["text"]
        padding = 5

        # Render text
        text_surf = self.options_font_value.render(text, True, self.options_value_color)
        text_rect = text_surf.get_rect(midleft=(draw_rect.left + padding, draw_rect.centery))
        # Clip text rendering to the widget's draw_rect bounds
        surface.set_clip(draw_rect)
        surface.blit(text_surf, text_rect)
        surface.set_clip(None) # Reset clip

        # Draw cursor if focused
        if is_focused:
            widget["cursor_timer"] += self.clock.get_time() / 1000.0 # Use clock from GUI
            if widget["cursor_timer"] >= config.CURSOR_BLINK_INTERVAL:
                widget["cursor_visible"] = not widget["cursor_visible"]
                widget["cursor_timer"] %= config.CURSOR_BLINK_INTERVAL

            if widget["cursor_visible"]:
                # Calculate cursor position relative to draw_rect
                cursor_x_offset = self.options_font_value.size(text[:widget["cursor_pos"]])[0]
                cursor_x = draw_rect.left + padding + cursor_x_offset
                # Ensure cursor stays within bounds
                if cursor_x < draw_rect.right - padding:
                    cursor_y = draw_rect.top + padding
                    cursor_height = draw_rect.height - 2 * padding
                    pygame.draw.line(surface, self.options_value_color, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)


    def _draw_choice_widget(self, surface, widget, is_focused, draw_rect):
        """Draws the content of a choice selector widget at the specified draw_rect, truncating long text."""
        # ... existing code from options_menu.py ...
        options = widget["options"]
        current_index = widget["current_index"]
        padding = 10
        arrow_space = 15 # Approx space needed for each arrow + padding

        if not options: return

        # Draw Left Arrow relative to draw_rect
        left_arrow_points = [(draw_rect.left + padding, draw_rect.centery),
                             (draw_rect.left + padding + 10, draw_rect.centery - 7),
                             (draw_rect.left + padding + 10, draw_rect.centery + 7)]
        pygame.draw.polygon(surface, self.options_label_color, left_arrow_points)

        # Draw Right Arrow relative to draw_rect
        right_arrow_points = [(draw_rect.right - padding, draw_rect.centery),
                              (draw_rect.right - padding - 10, draw_rect.centery - 7),
                              (draw_rect.right - padding - 10, draw_rect.centery + 7)]
        pygame.draw.polygon(surface, self.options_label_color, right_arrow_points)

        # --- Text Truncation Logic ---
        value_text = options[current_index]
        # Calculate max width available for text between the arrows
        max_text_width = draw_rect.width - (arrow_space * 2) - (padding * 2)

        # Initial render
        value_surf = self.options_font_value.render(value_text, True, self.options_value_color)
        display_surf = value_surf
        current_text = value_text

        # Truncate if necessary
        while display_surf.get_width() > max_text_width and len(current_text) > 1:
            current_text = current_text[:-1]
            display_surf = self.options_font_value.render(current_text + "...", True, self.options_value_color)
            # Fallback for very narrow space
            if len(current_text) <= 1 and display_surf.get_width() > max_text_width:
                 ellipsis_surf = self.options_font_value.render("...", True, self.options_value_color)
                 if ellipsis_surf.get_width() <= max_text_width: display_surf = ellipsis_surf
                 else: display_surf = pygame.Surface((0,0))
                 break
        # --- End Truncation ---

        # Draw Current Value Text centered in draw_rect
        value_rect = display_surf.get_rect(center=draw_rect.center)
        # Clip text rendering to the widget's draw_rect bounds (optional, but safe)
        surface.set_clip(draw_rect)
        surface.blit(display_surf, value_rect) # Blit potentially truncated text
        surface.set_clip(None) # Reset clip


    def _draw_button_widget(self, surface, widget, is_focused, draw_rect):
        """Draws the content of a button widget at the specified draw_rect."""
        # ... existing code from options_menu.py ...
        label = widget["label"]
        bg_color = self.options_button_highlight_color if is_focused else self.options_button_color

        pygame.draw.rect(surface, bg_color, draw_rect, border_radius=5)
        label_surf = self.options_font_value.render(label, True, self.options_button_text_color)
        label_rect = label_surf.get_rect(center=draw_rect.center)
        surface.blit(label_surf, label_rect)

