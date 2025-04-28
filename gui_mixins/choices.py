import pygame
import config

class ChoicesMixin:
    """Mixin class for handling multiple-choice interactions."""

    def draw_multiple_choice(self, target_surface=None):
        if target_surface is None:
            target_surface = self.screen # Assume self.screen exists

        if not self.choice_options:
            self.choice_rects = [] # Clear rects if no options
            return

        self.choice_rects = [] # Reset rects for redraw
        max_vertical_margin = 40 # Keep some space top/bottom of the window

        # --- Calculate required size with current font ---
        current_font = self.choice_font # Assumes self.choice_font exists
        # Use a fixed padding between lines instead of font height + extra
        current_spacing = 10 # Fixed padding between choice items
        if not current_font:
            print("Error: Choice font not available for drawing.")
            current_font = pygame.font.Font(None, config.FONT_SIZE) # Fallback
            current_spacing = 10 # Ensure spacing is set even on fallback

        max_text_width = 0
        total_text_height = 0
        num_options = len(self.choice_options)

        # Calculate initial dimensions needed based on the font
        line_heights = []
        for option_text in self.choice_options:
            try:
                text_surface = current_font.render(option_text, True, self.choice_color)
                max_text_width = max(max_text_width, text_surface.get_width())
                line_heights.append(text_surface.get_height())
            except (pygame.error, AttributeError):
                # Estimate height if render fails
                print(f"Warning: Could not render choice '{option_text}' to calculate size.")
                line_heights.append(current_font.get_height())

        total_text_height = sum(line_heights) # Sum of actual text heights
        total_text_height += current_spacing * (num_options - 1) if num_options > 1 else 0 # Add spacing between lines
        required_bg_height = total_text_height + self.choice_padding * 2
        required_bg_width = max_text_width + self.choice_padding * 2

        # --- Check if scaling is needed ---
        available_height = self.window_height - max_vertical_margin * 2
        scale_factor = 1.0
        scaled_font = current_font
        # Scale the fixed padding value
        scaled_spacing = current_spacing
        scaled_font_size = config.FONT_SIZE # Start with original size

        if required_bg_height > available_height and available_height > 0:
            scale_factor = available_height / required_bg_height
            # Scale down font size, ensure minimum size (e.g., 10)
            scaled_font_size = max(10, int(config.FONT_SIZE * scale_factor * 0.9)) # Added buffer (0.9)
            # Scale down the fixed spacing, ensure minimum spacing (e.g., 2)
            scaled_spacing = max(2, int(current_spacing * scale_factor * 0.8)) # Added buffer (0.8)

            try:
                # Try loading the scaled font using the configured regular font file
                scaled_font = pygame.font.Font(config.FONT_REGULAR, scaled_font_size)
            except (pygame.error, FileNotFoundError):
                print(f"Warning: Failed to load scaled font '{config.FONT_REGULAR}' at size {scaled_font_size}. Using default.")
                scaled_font = pygame.font.Font(None, scaled_font_size) # Fallback to default system font

            # --- Recalculate size with scaled font ---
            max_text_width = 0
            total_text_height = 0
            line_heights = [] # Recalculate line heights with scaled font
            for option_text in self.choice_options:
                try:
                    text_surface = scaled_font.render(option_text, True, self.choice_color)
                    max_text_width = max(max_text_width, text_surface.get_width())
                    line_heights.append(text_surface.get_height())
                except (pygame.error, AttributeError):
                    print(f"Warning: Could not render choice '{option_text}' with scaled font.")
                    line_heights.append(scaled_font.get_height()) # Use scaled font height

            total_text_height = sum(line_heights) # Sum of scaled text heights
            total_text_height += scaled_spacing * (num_options - 1) if num_options > 1 else 0 # Add scaled spacing
            required_bg_height = total_text_height + self.choice_padding * 2
            required_bg_width = max_text_width + self.choice_padding * 2

            # Ensure scaled height doesn't exceed available height due to rounding/buffers
            required_bg_height = min(required_bg_height, available_height)


        # --- Determine final background size and position ---
        # Use recalculated dimensions (might be original or scaled)
        bg_width = required_bg_width
        # Clamp height just in case scaling logic overshot slightly
        bg_height = min(required_bg_height, self.window_height - max_vertical_margin * 2)
        bg_height = max(bg_height, (line_heights[0] if line_heights else scaled_font.get_height()) + self.choice_padding * 2) # Ensure min height for one line

        bg_x = (self.window_width - bg_width) // 2
        # Center vertically within the available space
        bg_y = max(max_vertical_margin, (self.window_height - bg_height) // 2)


        # --- Draw background ---
        try:
            bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            bg_surface.fill(self.choice_bg_color) # Assumes self.choice_bg_color exists
            target_surface.blit(bg_surface, (bg_x, bg_y))
        except pygame.error as e:
            print(f"Error creating or blitting choice background surface: {e}")
            # Continue without background if it fails

        # --- Draw options with the determined font (scaled or original) ---
        current_y = bg_y + self.choice_padding
        font_to_use = scaled_font # Use the potentially scaled font
        spacing_to_use = scaled_spacing # Use the potentially scaled spacing

        for i, option_text in enumerate(self.choice_options):
            is_selected = (i == self.selected_choice_index)
            # Assumes choice colors exist on self
            color = self.choice_highlight_color if is_selected else self.choice_color

            try:
                final_surface = font_to_use.render(option_text, True, color)
                # Center text horizontally within the background rect
                text_rect = final_surface.get_rect(centerx=bg_x + bg_width // 2, top=current_y)

                # Ensure text doesn't overflow the background vertically (especially if scaled)
                if text_rect.bottom > bg_y + bg_height - self.choice_padding:
                    print("Warning: Choice text rendering exceeds calculated background height.")
                    break # Stop rendering more choices if space runs out

                target_surface.blit(final_surface, text_rect)
                # Store the actual rendered rect for mouse collision detection
                self.choice_rects.append(text_rect)
                # Advance Y position using the rendered height and the calculated spacing
                current_y += final_surface.get_height() # Add height of the current line
                if i < num_options - 1: # Add spacing only if it's not the last item
                     current_y += spacing_to_use

            except (pygame.error, AttributeError) as e:
                 print(f"Error rendering choice text '{option_text}': {e}")
                 # Skip rendering if font fails, but advance position and add placeholder rect
                 placeholder_height = line_heights[i] if i < len(line_heights) else font_to_use.get_height()
                 # Create a placeholder rect for collision detection consistency
                 placeholder_rect = pygame.Rect(bg_x + self.choice_padding, current_y, bg_width - self.choice_padding*2, placeholder_height)
                 self.choice_rects.append(placeholder_rect)
                 # Advance Y position even for placeholders
                 current_y += placeholder_height
                 if i < num_options - 1:
                      current_y += spacing_to_use
                 # Check vertical overflow even for placeholders
                 if current_y > bg_y + bg_height - self.choice_padding:
                     break


    def handle_choice_event(self, event) -> tuple[str, str | int | None] | None:
        """Handles events specifically when multiple choice is active."""
        prev_selected_index = self.selected_choice_index
        action_taken = False # Flag to check if selection changed for sound effect

        if event.type == pygame.KEYDOWN:
            num_options = len(self.choice_options)
            if num_options == 0: return None # No options, nothing to do

            if event.key == pygame.K_UP:
                self.selected_choice_index = (self.selected_choice_index - 1) % num_options
                action_taken = True
            elif event.key == pygame.K_DOWN:
                self.selected_choice_index = (self.selected_choice_index + 1) % num_options
                action_taken = True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self.play_confirm_sound() # Play confirmation sound
                chosen_index = self.selected_choice_index
                # Action: choice_made, Value: the chosen index
                return ("choice_made", chosen_index)
            elif event.key == pygame.K_ESCAPE:
                 # Return a specific cancel action for the caller to handle
                 return ("choice_cancel", None)

        elif event.type == pygame.MOUSEMOTION:
             mouse_pos = event.pos
             # Check collision with rendered choice rects
             for i, rect in enumerate(self.choice_rects):
                  # Inflate rect slightly for easier hovering
                  hover_rect = rect.inflate(4, 4)
                  if hover_rect.collidepoint(mouse_pos):
                       if self.selected_choice_index != i:
                            self.selected_choice_index = i
                            action_taken = True
                       break # Stop checking once a choice is hovered

        elif event.type == pygame.MOUSEBUTTONDOWN:
             if event.button == 1: # Left click
                  mouse_pos = event.pos
                  for i, rect in enumerate(self.choice_rects):
                       if rect.collidepoint(mouse_pos):
                            # Clicked on a choice
                            self.selected_choice_index = i # Select it
                            self.play_confirm_sound() # Play confirmation sound
                            # Action: choice_made, Value: the chosen index
                            return ("choice_made", i)
                  # Clicked outside any choice rect - potentially cancel?
                  # Let's make clicking outside cancel the choice pop-up
                  # Check if the click was outside the estimated background area
                  bg_rect_for_choices = None
                  if self.choice_rects:
                       min_x = min(r.left for r in self.choice_rects) - self.choice_padding
                       min_y = min(r.top for r in self.choice_rects) - self.choice_padding
                       max_x = max(r.right for r in self.choice_rects) + self.choice_padding
                       max_y = max(r.bottom for r in self.choice_rects) + self.choice_padding
                       bg_rect_for_choices = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

                  if bg_rect_for_choices and not bg_rect_for_choices.collidepoint(mouse_pos):
                       # Click was outside the choice area
                       return ("choice_cancel", None)
                  # Otherwise, ignore clicks outside specific choice items but inside the general area

        # Play cursor sound if selection changed via keyboard or mouse hover
        if action_taken and self.selected_choice_index != prev_selected_index:
             self.play_sound("menu_cursor") # Assumes self.play_sound exists

        # Return None if the event was handled within choice mode or irrelevant
        return None
