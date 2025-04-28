import pygame
import config
import os # For background list
import options # Import the options module for saving

class OptionsMenuMixin:
    """Mixin class for handling the dedicated options menu screen."""

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

    def draw_options_menu(self, surface):
        """Draws the entire options menu screen, handling scrolling and pop-ups."""
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
            # Delegate drawing to the ChoicesMixin method
            self.draw_multiple_choice(surface)

    def _draw_input_widget(self, surface, widget, is_focused, draw_rect):
        """Draws the content of an input widget at the specified draw_rect."""
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
        label = widget["label"]
        bg_color = self.options_button_highlight_color if is_focused else self.options_button_color

        pygame.draw.rect(surface, bg_color, draw_rect, border_radius=5)
        label_surf = self.options_font_value.render(label, True, self.options_button_text_color)
        label_rect = label_surf.get_rect(center=draw_rect.center)
        surface.blit(label_surf, label_rect)

    def handle_options_menu_event(self, event) -> str | None:
        """Handles events specifically for the options menu screen, including scrolling and pop-ups."""
        if not self.is_options_menu_active:
            return None

        action = None # Return value: "save", "cancel", or None

        # --- Handle Pop-up Choice Interaction First ---
        if self.is_options_choice_popup_active:
            # --- Intercept Up/Down keys for pop-up ---
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_UP or event.key == pygame.K_DOWN):
                # Explicitly ignore Up/Down keys when the pop-up is active
                return None # Consume the event

            # --- Delegate other relevant events to choice handler ---
            choice_action_result = self.handle_choice_event(event)
            if choice_action_result:
                choice_action, choice_data = choice_action_result
                if choice_action == "choice_made":
                    chosen_index = choice_data
                    # Update the original widget
                    if 0 <= self.editing_choice_widget_index < len(self.options_widgets):
                        widget = self.options_widgets[self.editing_choice_widget_index]
                        widget["current_index"] = chosen_index
                        self.temp_options[widget["key"]] = widget["values"][chosen_index]
                        self._preview_option_change(widget["key"], self.temp_options[widget["key"]])
                    # Close pop-up
                    self.is_options_choice_popup_active = False
                    self.is_choice_active = False
                    self.choice_options = []
                    self.editing_choice_widget_index = -1
                    return None # Consume event
                elif choice_action == "choice_cancel":
                    # Close pop-up without changes
                    self.is_options_choice_popup_active = False
                    self.is_choice_active = False
                    self.choice_options = []
                    self.editing_choice_widget_index = -1
                    self.play_sound("menu_cancel") # Play cancel sound
                    return None # Consume event
            # If choice handler didn't return an action, consume the event anyway if pop-up is active
            return None


        # --- Standard Options Menu Event Handling (if pop-up is not active) ---
        focused_widget = self.options_widgets[self.focused_widget_index]
        max_scroll = max(0, self.total_options_height - self.visible_options_height)

        # --- Scrolling Input ---
        scrolled = False
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y -= event.y * self.scroll_speed
            self.scroll_y = max(0, min(self.scroll_y, max_scroll)) # Clamp
            scrolled = True
        elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_PAGEUP:
                  self.scroll_y -= self.visible_options_height # Scroll up by one page height
                  self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                  scrolled = True
             elif event.key == pygame.K_PAGEDOWN:
                  self.scroll_y += self.visible_options_height # Scroll down by one page height
                  self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                  scrolled = True

        # If scrolling occurred, consume the event and potentially update focus if needed
        if scrolled:
             return None

        # --- Keyboard Navigation (Adjust for Scroll) ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                new_index = (self.focused_widget_index - 1) % len(self.options_widgets)
                self._update_focus_and_scroll(new_index) # Update focus and ensure visibility
            elif event.key == pygame.K_DOWN or event.key == pygame.K_TAB:
                new_index = (self.focused_widget_index + 1) % len(self.options_widgets)
                self._update_focus_and_scroll(new_index) # Update focus and ensure visibility
            elif event.key == pygame.K_ESCAPE:
                action = "cancel" # Escape cancels the options menu
                self.play_sound("menu_cancel")

            # --- Widget Interaction (Keyboard) ---
            elif focused_widget["type"] == "choice":
                # Left/Right keys still cycle through options directly
                num_choices = len(focused_widget["options"])
                if num_choices > 0:
                    if event.key == pygame.K_LEFT:
                        focused_widget["current_index"] = (focused_widget["current_index"] - 1) % num_choices
                        self.temp_options[focused_widget["key"]] = focused_widget["values"][focused_widget["current_index"]]
                        self.play_sound("menu_cursor")
                        self._preview_option_change(focused_widget["key"], self.temp_options[focused_widget["key"]])
                    elif event.key == pygame.K_RIGHT:
                        focused_widget["current_index"] = (focused_widget["current_index"] + 1) % num_choices
                        self.temp_options[focused_widget["key"]] = focused_widget["values"][focused_widget["current_index"]]
                        self.play_sound("menu_cursor")
                        self._preview_option_change(focused_widget["key"], self.temp_options[focused_widget["key"]])
                    # Enter/Space now opens the pop-up
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.is_options_choice_popup_active = True
                        self.editing_choice_widget_index = self.focused_widget_index
                        self.choice_options = focused_widget["options"] # Use options from the widget
                        self.selected_choice_index = focused_widget["current_index"] # Set initial selection
                        self.is_choice_active = True # Activate choice system
                        self.play_confirm_sound() # Sound for opening pop-up
                        return None # Consume event

            elif focused_widget["type"] == "input":
                if event.key == pygame.K_BACKSPACE:
                    if focused_widget["cursor_pos"] > 0:
                        text = focused_widget["text"]
                        focused_widget["text"] = text[:focused_widget["cursor_pos"]-1] + text[focused_widget["cursor_pos"]:]
                        focused_widget["cursor_pos"] -= 1
                        self.temp_options[focused_widget["key"]] = focused_widget["text"]
                elif event.key == pygame.K_DELETE:
                     text = focused_widget["text"]
                     if focused_widget["cursor_pos"] < len(text):
                          focused_widget["text"] = text[:focused_widget["cursor_pos"]] + text[focused_widget["cursor_pos"]+1:]
                          self.temp_options[focused_widget["key"]] = focused_widget["text"]
                elif event.key == pygame.K_LEFT:
                     if focused_widget["cursor_pos"] > 0: focused_widget["cursor_pos"] -= 1
                elif event.key == pygame.K_RIGHT:
                     if focused_widget["cursor_pos"] < len(focused_widget["text"]): focused_widget["cursor_pos"] += 1
                elif event.key == pygame.K_HOME:
                     focused_widget["cursor_pos"] = 0
                elif event.key == pygame.K_END:
                     focused_widget["cursor_pos"] = len(focused_widget["text"])
                elif event.unicode.isprintable(): # Check if it's a printable character
                    text = focused_widget["text"]
                    focused_widget["text"] = text[:focused_widget["cursor_pos"]] + event.unicode + text[focused_widget["cursor_pos"]:]
                    focused_widget["cursor_pos"] += 1
                    self.temp_options[focused_widget["key"]] = focused_widget["text"]
                focused_widget["cursor_visible"] = True
                focused_widget["cursor_timer"] = 0.0

            elif focused_widget["type"] == "button":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    action = focused_widget["action"] # "save" or "cancel"
                    self.play_confirm_sound()

        # --- Mouse Interaction (Adjust for Scroll) ---
        elif event.type == pygame.MOUSEMOTION:
            # Adjust mouse y position by scroll offset for collision checks
            mouse_pos = (event.pos[0], event.pos[1] + self.scroll_y)

            # Check collision with original widget rects (in the scrollable space)
            for i, widget in enumerate(self.options_widgets):
                if widget["rect"].collidepoint(mouse_pos):
                    if self.focused_widget_index != i:
                        self._update_focus_and_scroll(i, scroll_if_needed=False) # Update focus, don't force scroll on hover
                    break # Found focused widget

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                # Adjust mouse y position by scroll offset
                mouse_pos = (event.pos[0], event.pos[1] + self.scroll_y)

                for i, widget in enumerate(self.options_widgets):
                    # Check collision with original widget rects
                    if widget["rect"].collidepoint(mouse_pos):
                        self._update_focus_and_scroll(i, scroll_if_needed=False) # Focus clicked widget
                        focused_widget = self.options_widgets[i] # Get the newly focused widget

                        if focused_widget["type"] == "button":
                            action = focused_widget["action"]
                            self.play_confirm_sound()
                        elif focused_widget["type"] == "choice":
                            # Click on choice widget now opens the pop-up
                            self.is_options_choice_popup_active = True
                            self.editing_choice_widget_index = i
                            self.choice_options = focused_widget["options"]
                            self.selected_choice_index = focused_widget["current_index"]
                            self.is_choice_active = True
                            self.play_confirm_sound()
                            # Don't handle arrow clicks here anymore, pop-up handles selection
                        elif focused_widget["type"] == "input":
                             # Calculate click position relative to text start
                             text_start_x = widget["rect"].left + 5 # padding
                             click_offset_x = mouse_pos[0] - text_start_x
                             # Find closest character index (simplified)
                             text = widget["text"]
                             best_index = 0
                             min_dist = float('inf')
                             for char_i in range(len(text) + 1):
                                  char_offset_x = self.options_font_value.size(text[:char_i])[0]
                                  dist = abs(click_offset_x - char_offset_x)
                                  if dist < min_dist:
                                       min_dist = dist
                                       best_index = char_i
                             widget["cursor_pos"] = best_index
                             widget["cursor_visible"] = True # Make cursor visible on click
                             widget["cursor_timer"] = 0.0
                        break # Click handled

        return action

    def _update_focus_and_scroll(self, new_index, scroll_if_needed=True):
        """Updates the focused widget index and scrolls if necessary to keep it visible."""
        if self.focused_widget_index != new_index:
             old_focused_widget = self.options_widgets[self.focused_widget_index]
             self.focused_widget_index = new_index
             new_focused_widget = self.options_widgets[self.focused_widget_index]
             self.play_sound("menu_cursor") # Play sound on focus change via keys/click

             # Reset cursor blink state for input widgets
             if old_focused_widget["type"] == "input": old_focused_widget["cursor_visible"] = False; old_focused_widget["cursor_timer"] = 0.0
             if new_focused_widget["type"] == "input": new_focused_widget["cursor_visible"] = True; new_focused_widget["cursor_timer"] = 0.0

        if scroll_if_needed:
            # --- Scroll to Keep Focused Widget Visible ---
            widget_rect = self.options_widgets[self.focused_widget_index]["rect"]
            widget_top_on_screen = widget_rect.top - self.scroll_y
            widget_bottom_on_screen = widget_rect.bottom - self.scroll_y
            content_area_y_start = 80 # Match draw logic

            max_scroll = max(0, self.total_options_height - self.visible_options_height)

            # If widget top is above visible area, scroll up
            if widget_top_on_screen < content_area_y_start:
                self.scroll_y = widget_rect.top - content_area_y_start
            # If widget bottom is below visible area, scroll down
            elif widget_bottom_on_screen > content_area_y_start + self.visible_options_height:
                self.scroll_y = widget_rect.bottom - (content_area_y_start + self.visible_options_height)

            # Clamp scroll_y after adjustment
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

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

