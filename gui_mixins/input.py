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
                # No need to call _wrap_input_text here, rendering will handle it
            except Exception as e:
                print(f"Warning: Error recalculating input box layout: {e}")
