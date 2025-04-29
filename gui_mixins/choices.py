import pygame
import config

class ChoicesMixin:
    """Mixin class for handling multiple-choice interactions."""

    def draw_multiple_choice(self, target_surface): # Changed 'surface' to 'target_surface'
        """Draws the multiple choice options centered on the screen, truncating long text."""
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
        pygame.draw.rect(target_surface, self.choice_bg_color, bg_rect, border_radius=8) # Use target_surface

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
                pygame.draw.rect(target_surface, self.choice_highlight_color, item_bg_rect, border_radius=5) # Use target_surface

            # Calculate text position centered within item_bg_rect
            text_rect = display_surf.get_rect(center=item_bg_rect.center)
            target_surface.blit(display_surf, text_rect) # Use target_surface

            # Increment y for the next item's background top
            y += effective_item_spacing

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
            # Check for main Enter, Numpad Enter, or Space
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_KP_ENTER:
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
