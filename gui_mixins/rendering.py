import pygame
import config
import math # For pulsing alpha

class RenderingMixin:
    """Mixin class for handling the main rendering loop and drawing components."""

    def render_background_and_overlay(self, target_surface):
        """Renders the background image and menu overlay if active."""
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


    def render(self):
        """Main rendering function to draw all GUI elements."""
        # Check if history view is active, if so, skip normal rendering
        if getattr(self, 'is_history_active', False):
            # Assume history rendering is handled elsewhere or simply does nothing here
            # pygame.display.flip() # Flip required if history draws something
            return # Don't render the normal UI

        # Get delta time for effects that might need it (like pixel effect rate)
        dt = 0
        if hasattr(self, 'clock'):
             dt = self.clock.get_time() / 1000.0
        else:
             # Estimate dt if clock is unavailable, less accurate
             # This might not be ideal for frame-rate dependent effects
             pass # dt remains 0 or could be estimated differently


        is_forced_quitting = getattr(self, 'is_forced_quitting', False)

        if is_forced_quitting:
            # --- Forced Quit Rendering ---
            self.screen.fill((0, 0, 0)) # Start with a black void

            # Create a temporary surface for all UI elements that will be shaken
            # Ensure SRCALPHA for transparency if needed (e.g., if background has alpha)
            ui_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
            ui_surface.fill((0, 0, 0, 0)) # Make it transparent initially

            # 1. Render background onto the UI surface
            self.render_background_and_overlay(ui_surface) # Render background normally first

            # 2. Render Textbox onto the UI surface
            if hasattr(self, 'textbox_img'):
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                ui_surface.blit(self.textbox_img, textbox_rect)

            # 3. Render Face onto the UI surface (use current face)
            if hasattr(self, 'current_face_image') and self.current_face_image:
                face_x = self.textbox_x + config.FACE_OFFSET_X
                face_y = self.textbox_y + config.FACE_OFFSET_Y
                ui_surface.blit(self.current_face_image, (face_x, face_y))

            # 4. Render Text onto the UI surface (use the dialogue drawing method)
            # Ensure the method exists and pass the UI surface as the target
            if hasattr(self, 'draw_animated_text'):
                # Draw the *entire* text instantly during forced quit, not animated
                # We might need a separate draw_static_text or modify draw_animated_text
                # For simplicity, let's assume draw_animated_text can draw fully if index is max
                original_char_index = getattr(self, 'current_char_index', 0)
                original_is_animating = getattr(self, 'is_animating', False)
                self.current_char_index = getattr(self, 'total_chars_to_render', 0) # Force full render
                self.is_animating = False # Ensure it draws statically
                self.draw_animated_text(target_surface=ui_surface)
                # Restore original state if needed, though likely irrelevant during quit
                self.current_char_index = original_char_index
                self.is_animating = original_is_animating


            # 5. Blit the combined UI surface onto the main screen with shake offset
            shake_x = getattr(self, 'shake_offset_x', 0)
            shake_y = getattr(self, 'shake_offset_y', 0)
            self.screen.blit(ui_surface, (shake_x, shake_y))

            # 6. Render forced quit specific effects (pixels) on top
            # Ensure the effect rendering method exists
            if hasattr(self, 'render_forced_quit_effects'):
                self.render_forced_quit_effects(dt) # Pass dt if needed
                # This method should handle drawing the random_pixel_overlay if it exists
                if hasattr(self, 'random_pixel_overlay') and self.random_pixel_overlay:
                    self.screen.blit(self.random_pixel_overlay, (0,0))


        else:
            # --- Normal Rendering ---
            render_surface = self.screen # Render directly to the screen

            # 1. Render Background and Menu Overlay
            self.render_background_and_overlay(render_surface)

            # 2. Render Textbox
            if hasattr(self, 'textbox_img'):
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                render_surface.blit(self.textbox_img, textbox_rect)

            # 3. Render Face (potentially pulsing if AI is thinking)
            face_x = self.textbox_x + config.FACE_OFFSET_X
            face_y = self.textbox_y + config.FACE_OFFSET_Y
            face_to_draw = None
            apply_alpha_pulse = False

            ai_is_thinking = getattr(self, 'ai_is_thinking', False)
            last_face = getattr(self, 'last_face_image', None)
            current_face = getattr(self, 'current_face_image', None)

            if ai_is_thinking:
                if last_face: # Prefer last face when thinking
                    face_to_draw = last_face
                    apply_alpha_pulse = True
                elif current_face: # Fallback to current if last doesn't exist
                     face_to_draw = current_face
                     # Maybe don't pulse if falling back to current? Optional.
                     # apply_alpha_pulse = True
            elif current_face: # Not thinking, use current face
                face_to_draw = current_face

            if face_to_draw:
                if apply_alpha_pulse:
                    # Calculate pulsing alpha
                    pulse_speed = 4.0 # Speed of the pulse
                    min_alpha = 80
                    max_alpha = 200
                    alpha_range = max_alpha - min_alpha
                    # Use pygame ticks for smooth animation independent of frame rate
                    alpha = min_alpha + (alpha_range / 2) * (1 + math.sin(pygame.time.get_ticks() * 0.001 * pulse_speed))
                    alpha = int(max(0, min(255, alpha))) # Clamp alpha value

                    try:
                        # Create a copy to apply alpha without modifying original
                        face_copy = face_to_draw.copy()
                        face_copy.set_alpha(alpha)
                        render_surface.blit(face_copy, (face_x, face_y))
                    except pygame.error as e:
                        print(f"Error applying alpha to face: {e}. Drawing opaque.")
                        # Fallback: draw the original face without alpha
                        render_surface.blit(face_to_draw, (face_x, face_y))
                else:
                    # Draw face normally (opaque)
                    render_surface.blit(face_to_draw, (face_x, face_y))

            # 4. Render Dialogue Text (Animated)
            # Only draw dialogue if AI is not thinking
            if not ai_is_thinking:
                # Ensure the method exists
                if hasattr(self, 'draw_animated_text'):
                    self.draw_animated_text(target_surface=render_surface)

            # 5. Render Advance Arrow (if applicable)
            # Check flags: draw_arrow is True, arrow is visible (blinking), not input/choice/pause
            should_draw_arrow = (getattr(self, 'draw_arrow', False) and
                                 getattr(self, 'arrow_visible', False) and
                                 not getattr(self, 'is_input_active', False) and
                                 not getattr(self, 'is_choice_active', False) and
                                 not getattr(self, 'is_paused', False))

            if should_draw_arrow and hasattr(self, 'arrow_img'):
                arrow_x = self.textbox_x + config.ARROW_OFFSET_X
                # Use base Y + calculated bobbing offset
                arrow_y = getattr(self, 'arrow_base_y', self.textbox_y + config.ARROW_OFFSET_Y) + \
                          getattr(self, 'arrow_offset_y', 0)
                arrow_rect = self.arrow_img.get_rect(centerx=arrow_x, top=arrow_y)
                render_surface.blit(self.arrow_img, arrow_rect)

            # 6. Render Input Box (if active)
            if getattr(self, 'is_input_active', False):
                self.render_input_box(render_surface) # Delegate to helper method

            # 7. Render Multiple Choice Box (if active)
            if getattr(self, 'is_choice_active', False):
                 # Ensure the method exists
                 if hasattr(self, 'draw_multiple_choice'):
                     self.draw_multiple_choice(target_surface=render_surface)

        # --- Final Flip ---
        pygame.display.flip() # Update the full display


    def render_input_box(self, target_surface):
        """Renders the text input box, text, and cursor."""
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

        # Ensure wrapping method exists
        if not hasattr(self, '_wrap_input_text'):
             print("Error: _wrap_input_text method missing.")
             return

        wrapped_text_lines, line_start_indices = self._wrap_input_text(self.user_input_text, max_text_width)

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
