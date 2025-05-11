import pygame
import pygame.surfarray
import config
import math
import os
import re
from .text_utils import wrap_input_text # Import the wrapping utility

CHOICE_ICON_SIZE = (40, 40)  # Example size, adjust as needed
CHOICE_ICON_PADDING = 5     # Padding between icon and text

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
                        new_face = self.face_images.get(face_name) # Use self.face_images
                        if new_face:
                            self.current_face_image = new_face
                        else:
                            # Modified: Get default face from character data and use it as fallback
                            default_face = None
                            if hasattr(self, 'character_data') and self.character_data:
                                default_face_name = self.character_data.defaultFace
                                default_face = self.face_images.get(default_face_name)
                                print(f"Warning: Face '{face_name}' referenced in text not found. Using default face '{default_face_name}'.")
                            else:
                                print(f"Warning: Face '{face_name}' referenced in text not found. Character data unavailable.")
                            
                            if default_face:
                                self.current_face_image = default_face
                            elif self.face_images:  # Last resort: use any available face
                                self.current_face_image = next(iter(self.face_images.values()))
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


    def render_input_box(self, surface):
        """Renders the text input box, including text and cursor."""
        if not self.is_input_active:
            return

        # Draw background and border
        pygame.draw.rect(surface, config.INPUT_BOX_BG_COLOR, self.input_rect)
        pygame.draw.rect(surface, config.INPUT_BOX_BORDER_COLOR, self.input_rect, config.INPUT_BOX_BORDER_WIDTH)

        try:
            max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
            wrapped_lines, cursor_line_char_pos = wrap_input_text(
                self.user_input_text, self.input_font, max_render_width, self.input_cursor_pos
            )

            line_height = self.input_font.get_height()
            start_x = self.input_rect.left + config.INPUT_BOX_PADDING
            start_y = self.input_rect.top + config.INPUT_BOX_PADDING

            # --- Render Text Lines ---
            for i, line in enumerate(wrapped_lines):
                text_surface = self.input_font.render(line, True, config.INPUT_BOX_TEXT_COLOR)
                text_rect = text_surface.get_rect(topleft=(start_x, start_y + i * line_height))
                surface.blit(text_surface, text_rect)

            # --- Render Cursor ---
            if self.input_cursor_visible:
                if cursor_line_char_pos is not None: # Explicit check
                    cursor_line_index = cursor_line_char_pos[0]
                    cursor_char_index = cursor_line_char_pos[1]

                    # Calculate cursor position based on wrapped lines and character index
                    if 0 <= cursor_line_index < len(wrapped_lines):
                        line_text_before_cursor = wrapped_lines[cursor_line_index][:cursor_char_index]
                        try:
                            cursor_offset_x = self.input_font.size(line_text_before_cursor)[0]
                        except (pygame.error, AttributeError):
                            cursor_offset_x = cursor_char_index * (self.input_font.get_height() // 2) # Estimate

                        cursor_x = start_x + cursor_offset_x
                        cursor_y = start_y + cursor_line_index * line_height

                        # Draw cursor (vertical line)
                        pygame.draw.line(surface, config.INPUT_BOX_TEXT_COLOR, (cursor_x, cursor_y), (cursor_x, cursor_y + line_height), 2)
                    else:
                        print(f"Warning: Invalid cursor_line_index ({cursor_line_index}) from wrap_input_text.")

                else: # Handle case where cursor_line_char_pos is None
                    print("Warning: cursor_line_char_pos is None in render_input_box. Skipping cursor render.")

        except Exception as e:
            print(f"Error rendering input text/cursor: {e}")
            try:
                error_font = pygame.font.Font(None, 18)
                error_surf = error_font.render("Render Error", True, (255, 0, 0))
                error_rect = error_surf.get_rect(center=self.input_rect.center)
                surface.blit(error_surf, error_rect)
            except Exception as e2:
                print(f"Error rendering error indicator: {e2}")


    def draw_multiple_choice(self, screen: pygame.Surface):
        """Draws the multiple choice options on the screen."""
        if not self.is_choice_active or not self.choice_options:
            return

        self.choice_rects = []  # Clear previous rects

        # grid layout for icon+text entries
        if self.choice_options and isinstance(self.choice_options[0], tuple):
            cols   = 4
            total  = len(self.choice_options)
            rows   = (total + cols - 1) // cols

            # spacing
            h_gap  = 20
            v_gap  = 20

            # measure icon/text
            icon_h = CHOICE_ICON_SIZE[1]
            text_h = self.choice_font.get_height()
            cell_h = icon_h + CHOICE_ICON_PADDING + text_h + self.choice_padding

            # compute total grid height
            total_h = rows * cell_h + (rows - 1) * v_gap

            # base top below textbox
            base_top = self.textbox_y + self.textbox_img.get_height() + 20

            # move grid up by half of extra height
            top = base_top - max(0, (total_h - cell_h) / 2)

            left   = self.choice_padding
            cell_w = (self.window_width - 2*self.choice_padding - (cols-1)*h_gap) / cols

            self.choice_rects = []
            for idx, (text, icon) in enumerate(self.choice_options):
                r, c = divmod(idx, cols)
                x    = left + c * (cell_w + h_gap)
                y    = top  + r * (cell_h + v_gap)
                rect = pygame.Rect(x, y, cell_w, cell_h)

                # derive bg color by averaging all pixels of icon, fallback to menu_bg_color
                if icon:
                    try:
                        arr = pygame.surfarray.array3d(icon)
                        avg = arr.mean(axis=(0,1))
                        def _adj(c: float) -> int:
                            return min(255, max(0, int(((int(c)-128)*1.2 + 128)*0.9)))
                        cell_color = (_adj(avg[0]), _adj(avg[1]), _adj(avg[2]))
                    except Exception:
                        cell_color = getattr(self, 'menu_bg_color', (50,50,50))
                else:
                    cell_color = getattr(self, 'menu_bg_color', (50,50,50))

                pygame.draw.rect(screen, cell_color, rect, border_radius=8)

                # icon
                if icon:
                    icon_s = pygame.transform.smoothscale(icon, CHOICE_ICON_SIZE)
                    ix = x + (cell_w - CHOICE_ICON_SIZE[0])//2
                    iy = y
                    screen.blit(icon_s, (ix, iy))

                # label
                color = (self.choice_highlight_color if idx == self.selected_choice_index
                         else self.choice_color)
                ts    = self.choice_font.render(text, True, color)
                tx    = x + (cell_w - ts.get_width())//2
                ty    = y + icon_h + CHOICE_ICON_PADDING
                screen.blit(ts, (tx, ty))

                self.choice_rects.append(rect)
            return

        base_y = self.textbox_y + self.textbox_img.get_height() + 20 # Below textbox
        if hasattr(self, 'input_rect') and self.is_input_active: # If input is active, draw above it
             base_y = self.input_rect.y - (len(self.choice_options) * (self.choice_font.get_height() + self.choice_spacing) + 20)
        elif hasattr(self, 'input_rect') and not self.is_input_active and not self.current_text: # if input not active and no dialogue, position near where input would be
             base_y = self.input_box_y - (len(self.choice_options) * (self.choice_font.get_height() + self.choice_spacing) + 20)

        min_y_for_choices = self.textbox_y # Don't overlap with textbox top
        calculated_total_height = len(self.choice_options) * (max(self.choice_font.get_height(), CHOICE_ICON_SIZE[1]) + self.choice_spacing) - self.choice_spacing
        
        if hasattr(self, 'input_rect') and self.is_input_active:
            base_y = self.input_rect.y - calculated_total_height - 10 # 10px padding above input
        elif hasattr(self, 'input_rect') and not self.is_input_active and not self.current_text and not self.is_menu_active:
             base_y = self.input_box_y - calculated_total_height - 10
        elif self.is_menu_active:
            menu_items_total_height = len(self.choice_options) * (max(self.choice_font.get_height(), CHOICE_ICON_SIZE[1] if any(isinstance(opt, tuple) and opt[1] for opt in self.choice_options) else 0) + self.choice_spacing) - self.choice_spacing
            base_y = (self.window_height - menu_items_total_height) // 2
        else:
            base_y = self.textbox_y + self.textbox_img.get_height() + 15

        base_y = max(base_y, min_y_for_choices)

        for i, option_data in enumerate(self.choice_options):
            text_content: str
            icon_surface: pygame.Surface | None = None

            if isinstance(option_data, tuple) and len(option_data) == 2:
                text_content, icon_surface = option_data
            elif isinstance(option_data, str): # Fallback for simple string options
                text_content = option_data
            else:
                text_content = "Error: Invalid choice format" # Should not happen

            color = self.choice_highlight_color if i == self.selected_choice_index else self.choice_color
            
            effective_line_height = max(self.choice_font.get_height(), CHOICE_ICON_SIZE[1] if icon_surface else 0)
            y_pos = base_y + i * (effective_line_height + self.choice_spacing)

            current_x_offset = 0
            icon_render_width = 0
            if icon_surface:
                try:
                    scaled_icon = pygame.transform.smoothscale(icon_surface, CHOICE_ICON_SIZE)
                    icon_rect = scaled_icon.get_rect()
                    icon_y = y_pos + (effective_line_height - CHOICE_ICON_SIZE[1]) // 2
                    screen.blit(scaled_icon, (self.textbox_x + self.choice_padding + current_x_offset, icon_y))
                    current_x_offset += CHOICE_ICON_SIZE[0] + CHOICE_ICON_PADDING
                    icon_render_width = CHOICE_ICON_SIZE[0] + CHOICE_ICON_PADDING
                except Exception as e:
                    print(f"Error rendering choice icon: {e}")

            text_surface = self.choice_font.render(text_content, True, color)
            text_rect = text_surface.get_rect()
            text_x = self.textbox_x + self.choice_padding + current_x_offset
            text_y = y_pos + (effective_line_height - text_rect.height) // 2
            screen.blit(text_surface, (text_x, text_y))

            content_width = icon_render_width + text_rect.width
            choice_item_width = max(content_width + self.choice_padding * 2, config.TEXTBOX_WIDTH // 2)
            if self.is_menu_active:
                 choice_item_width = config.TEXTBOX_WIDTH - self.choice_padding * 2

            rect_x = self.textbox_x + self.choice_padding
            rect_x = (self.window_width - choice_item_width) // 2

            choice_rect = pygame.Rect(
                rect_x,
                y_pos - self.choice_padding // 2,
                choice_item_width,
                effective_line_height + self.choice_padding
            )
            pygame.draw.rect(screen, self.menu_bg_color, choice_rect, border_radius=8)
            self.choice_rects.append(choice_rect)


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

