import pygame
import config
import os # For background list
import options # Import the options module for saving

class OptionsMenuMixin:
    """Mixin class for handling the dedicated options menu screen state."""

    def _initialize_options_menu_state(self):
        """Initializes variables specific to the options menu."""
        self.is_options_menu_active = False
        self.temp_options = {} # Temporary storage while menu is open
        self.options_widgets = [] # List to store widget definitions and rects
        self.focused_widget_index = 0
        self.options_font_label = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        self.options_font_value = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        # Define colors (consider moving to config)
        self.options_label_color = (200, 200, 200)
        self.options_value_color = (255, 255, 255)
        self.options_highlight_color = config.CHOICE_HIGHLIGHT_COLOR
        self.options_widget_bg_color = (40, 40, 50, 200) # Semi-transparent dark bg
        self.options_button_color = (70, 70, 90)
        self.options_button_highlight_color = (100, 100, 120)
        self.options_button_text_color = (220, 220, 220)
        self.scrollbar_color = (100, 100, 100)
        self.scrollbar_handle_color = (150, 150, 150)

        # Scroll state
        self.scroll_y = 0
        self.total_options_height = 0 # Calculated in _build_options_widgets
        self.visible_options_height = self.window_height # Area available for options content
        self.scroll_speed = 40 # Pixels per mouse wheel tick

        # Pop-up choice state
        self.is_options_choice_popup_active = False
        self.editing_choice_widget_index = -1

        # Define widget structure dynamically
        self._build_options_widgets()

    def _build_options_widgets(self):
        """Defines the widgets for the options menu and calculates total height."""
        self.options_widgets = []
        y_offset = 80 # Starting Y position (relative to top of the virtual scroll area)
        x_margin = 50
        label_width = 200
        widget_width = 300
        widget_height = 40
        spacing = 15
        content_start_y = y_offset # Store starting Y for height calculation

        # 1. Player Name (Input)
        self.options_widgets.append({
            "key": "player_name",
            "label": "Player Name:",
            "type": "input",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "text": "", # Current input text
            "cursor_pos": 0,
            "cursor_visible": False,
            "cursor_timer": 0.0
        })
        y_offset += widget_height + spacing

        # 2. SFX Volume (Choice Selector)
        volume_options = ["Mute", "Quiet", "Medium", "Loud"]
        volume_values = [0.0, 0.25, 0.5, 0.8]
        self.options_widgets.append({
            "key": "sfx_volume",
            "label": "SFX Volume:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": volume_options,
            "values": volume_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 3. Text Speed (Choice Selector)
        speed_options = ["Slow", "Normal", "Fast", "Instant"]
        speed_values = ["slow", "normal", "fast", "instant"]
        self.options_widgets.append({
            "key": "default_text_speed",
            "label": "Text Speed:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": speed_options,
            "values": speed_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 4. Background Image (Choice Selector)
        bg_options = [os.path.basename(p) for p in config.get_available_backgrounds(config.BG_DIR)]
        bg_values = [os.path.join(config.BG_DIR, name) for name in bg_options]
        # Add default if not already listed? Ensure it's present.
        default_bg_name = os.path.basename(config.DEFAULT_BG_IMG)
        if default_bg_name not in bg_options:
             bg_options.insert(0, default_bg_name)
             bg_values.insert(0, config.DEFAULT_BG_IMG)

        self.options_widgets.append({
            "key": "background_image_path",
            "label": "Background:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": bg_options,
            "values": bg_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 5. AI Model (Choice Selector)
        model_options = config.AVAILABLE_AI_MODELS
        model_values = config.AVAILABLE_AI_MODELS
        self.options_widgets.append({
            "key": "ai_model_name",
            "label": "AI Model:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": model_options,
            "values": model_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing + 20 # Extra space before buttons

        # 6. Save Button
        button_width = 100
        button_height = 40
        save_x = self.window_width // 2 - button_width - 10
        self.options_widgets.append({
            "key": "save_button",
            "label": "Save",
            "type": "button",
            "rect": pygame.Rect(save_x, y_offset, button_width, button_height),
            "action": "save"
        })

        # 7. Cancel Button
        cancel_x = self.window_width // 2 + 10
        self.options_widgets.append({
            "key": "cancel_button",
            "label": "Cancel",
            "type": "button",
            "rect": pygame.Rect(cancel_x, y_offset, button_width, button_height),
            "action": "cancel"
        })

        # Calculate total height needed for all widgets + final padding
        self.total_options_height = y_offset + button_height + 40 # Add padding at the bottom

    def enter_options_menu(self):
        """Prepares the GUI state for showing the options menu."""
        if not hasattr(self, 'options_widgets'): # Initialize if first time
             self._initialize_options_menu_state()
        else: # Ensure widgets are up-to-date (e.g., background list)
             self._build_options_widgets() # Rebuild to refresh dynamic lists like backgrounds

        self.is_options_menu_active = True
        self.temp_options = self.options.copy() # Work on a copy
        self.scroll_y = 0 # Reset scroll position when entering
        self.focused_widget_index = 0 # Start focus at the top

        # Set initial widget states based on temp_options
        for i, widget in enumerate(self.options_widgets):
            key = widget.get("key")
            if key in self.temp_options:
                value = self.temp_options[key]
                if widget["type"] == "input":
                    widget["text"] = str(value)
                    widget["cursor_pos"] = len(widget["text"])
                elif widget["type"] == "choice":
                    try:
                        widget["current_index"] = widget["values"].index(value)
                    except ValueError:
                        # Handle case where saved value is no longer valid
                        print(f"Warning: Saved value '{value}' for option '{key}' not found in current choices. Resetting.")
                        widget["current_index"] = 0
                        self.temp_options[key] = widget["values"][0] # Update temp option

        # Set TWM face/sfx for the options menu itself
        self.set_active_face_set("twm")
        self.set_active_sfx("robot")
        # Ensure no dialogue is displayed
        self.current_text = ""
        self.is_animating = False
        self.draw_arrow = False
        self.is_input_active = False # Deactivate main input
        self.is_choice_active = False # Deactivate main choice

    def exit_options_menu(self, save_changes: bool):
        """Cleans up state after exiting the options menu and applies changes if requested."""
        self.is_options_menu_active = False
        # Reset pop-up state on exit as well
        self.is_options_choice_popup_active = False
        self.is_choice_active = False
        self.choice_options = []
        self.editing_choice_widget_index = -1

        original_bg_path = self.options.get("background_image_path") # Get original before potential save

        if save_changes:
            self.options.update(self.temp_options)
            options.save_options(self.options) # Use imported options module
            print("Options saved.")
            # Apply changes immediately
            self.set_sfx_volume(self.options["sfx_volume"])
            self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(self.options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
            # Reload background if it changed
            if self.options.get("background_image_path") != original_bg_path:
                 self.bg_img_original = self.load_image(self.options["background_image_path"])
                 if self.bg_img_original:
                      self.bg_img = pygame.transform.smoothscale(self.bg_img_original, (self.window_width, self.window_height))
                 else: # Handle load failure
                      self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))
            # Update AI model in the AI instance (requires access to niko_ai)
            # This might need to be handled in main.py after this function returns,
            # or niko_ai needs to be passed or made accessible here.
            # For now, print a message.
            print(f"AI Model changed to: {self.options.get('ai_model_name')}")
            # Let main.py handle the actual AI instance update after the menu closes.

        else:
            print("Options cancelled.")
            # Revert any previewed changes (e.g., background)
            if self.temp_options.get("background_image_path") != original_bg_path:
                 self.bg_img_original = self.load_image(original_bg_path)
                 if self.bg_img_original:
                      self.bg_img = pygame.transform.smoothscale(self.bg_img_original, (self.window_width, self.window_height))
                 else:
                      self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))
            # Revert volume preview if any was done
            self.set_sfx_volume(self.options["sfx_volume"])


        # Restore original face/sfx set (assuming it was Niko before entering options)
        # TODO: Make this smarter - store the state before entering options
        self.set_active_face_set("niko")
        self.set_active_sfx("default")

    def _preview_option_change(self, key, value):
        """Applies a preview effect for certain options when changed."""
        if key == "sfx_volume":
            self.set_sfx_volume(value)
            # Play sound again with new volume for preview
            self.play_sound("menu_cursor")
        elif key == "background_image_path":
            # Load and apply the new background immediately for preview
            try:
                preview_bg = self.load_image(value)
                if preview_bg:
                     self.bg_img = pygame.transform.smoothscale(preview_bg, (self.window_width, self.window_height))
                else: # Handle load failure
                     self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))
            except Exception as e:
                print(f"Error loading background preview: {e}")

