import pygame
import config
import os # For background list
import options # Import the options module for saving
# Add tkinter import for file dialogs
import tkinter as tk
from tkinter import filedialog
import character_manager # Import the new manager

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

        # Tkinter root for file dialogs
        self.tk_root = None

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
        bg_options_display = ["Select from file..."] + [os.path.basename(p) for p in config.get_available_backgrounds(config.BG_DIR)]
        bg_values = [config.SELECT_BACKGROUND_FROM_FILE] + [os.path.join(config.BG_DIR, name) for name in bg_options_display[1:]] # Skip "Select..."

        # Ensure default is present if it's not in BG_DIR
        default_bg_name = os.path.basename(config.DEFAULT_BG_IMG)
        if config.DEFAULT_BG_IMG not in bg_values:
             # Insert default after "Select..."
             bg_options_display.insert(1, default_bg_name)
             bg_values.insert(1, config.DEFAULT_BG_IMG)

        self.options_widgets.append({
            "key": "background_image_path",
            "label": "Background:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": bg_options_display, # Display names including "Select..."
            "values": bg_values, # Actual values/paths + placeholder
            "current_index": 0, # Will be updated in enter_options_menu
            "current_display_value": "" # Store the actual path if custom
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
        y_offset += widget_height + spacing

        # 6. Screen Capture Mode (Choice Selector)
        capture_options = config.SCREEN_CAPTURE_OPTIONS
        capture_values = config.SCREEN_CAPTURE_VALUES
        self.options_widgets.append({
            "key": "screen_capture_mode",
            "label": "Able to See Screen:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": capture_options,
            "values": capture_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 7. Monitor Selection (Choice Selector) - Only if screen capture is enabled
        monitor_options = ["Primary Monitor", "All Monitors"]
        monitor_values = [config.MONITOR_PRIMARY, config.MONITOR_ALL]
        self.options_widgets.append({
            "key": "monitor_selection",
            "label": "Monitor to Capture:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": monitor_options,
            "values": monitor_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 8. AI Speech Frequency (Choice Selector)
        speech_options = config.AI_SPEAK_FREQUENCY_OPTIONS
        speech_values = config.AI_SPEAK_FREQUENCY_VALUES
        self.options_widgets.append({
            "key": "ai_speak_frequency",
            "label": "Niko speaks by itself:",
            "type": "choice",
            "rect": pygame.Rect(x_margin + label_width, y_offset, widget_width, widget_height),
            "options": speech_options,
            "values": speech_values,
            "current_index": 0
        })
        y_offset += widget_height + spacing

        # 9. hard erased cuz i don't like it, but you can add it back if you want, just good luck x3
        # Extra space before buttons, applied to the current y_offset
        # (which will be higher if char dropdown was added)
        y_offset += 20

        # 10. Save Button
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

        # 11. Cancel Button
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
                        # Handle background separately due to custom paths
                        if key == "background_image_path":
                            if value == config.SELECT_BACKGROUND_FROM_FILE: # Should not happen in saved options
                                widget["current_index"] = 0
                                widget["current_display_value"] = ""
                            elif value in widget["values"]:
                                widget["current_index"] = widget["values"].index(value)
                                widget["current_display_value"] = widget["options"][widget["current_index"]]
                            else:
                                # Custom path saved, find "Select..." and store path
                                widget["current_index"] = widget["values"].index(config.SELECT_BACKGROUND_FROM_FILE)
                                widget["current_display_value"] = os.path.basename(value) # Show filename
                        else:
                             widget["current_index"] = widget["values"].index(value)
                    except ValueError:
                        # Handle case where saved value is no longer valid
                        print(f"Warning: Saved value '{value}' for option '{key}' not found in current choices. Resetting.")
                        widget["current_index"] = 0
                        self.temp_options[key] = widget["values"][0] # Update temp option
                        if key == "background_image_path":
                             widget["current_display_value"] = widget["options"][0]
                elif widget["type"] == "dropdown":
                    current_value = widget.get("current_value", widget["values"][0] if widget["values"] else None)
                    try:
                        current_index = widget["values"].index(current_value)
                        widget["display_text"] = widget["options"][current_index]
                    except (ValueError, IndexError):
                        # Fallback if current_value is not in values or options/values mismatch
                        widget["display_text"] = widget["options"][0] if widget["options"] else "N/A"
                        current_index = 0

        # Store current active face and sfx before switching
        self._stored_face_set = getattr(self, 'active_face_set', None) 
        self._stored_sfx_set = getattr(self, 'active_sfx_set', None)
        
        # Try to use TWM resources if available, otherwise keep current
        try:
            # Check if we have TWM faces
            if hasattr(self, 'twm_face_images'):
                self.set_active_face_set("twm")
            # Check if we have robot sfx 
            if hasattr(self, 'robot_sfx'):
                self.set_active_sfx("robot")
        except Exception as e:
            print(f"Warning: Could not set TWM resources for options menu: {e}")
            
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
        saved_bg_path = self.temp_options.get("background_image_path")

        if save_changes:
            # Ensure SELECT_BACKGROUND_FROM_FILE isn't saved
            if saved_bg_path == config.SELECT_BACKGROUND_FROM_FILE:
                 # This should only happen if the user selected "Select..." but cancelled the dialog
                 # Revert to the original path before saving
                 self.temp_options["background_image_path"] = original_bg_path
                 print("Warning: 'Select from file...' was chosen but no file selected. Reverting background.")

            self.options.update(self.temp_options)
            options.save_options(self.options) # Use imported options module
            print("Options saved.")
            # Apply changes immediately
            self.set_sfx_volume(self.options["sfx_volume"])
            self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(self.options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
            # Reload background if it changed
            new_bg_path = self.options.get("background_image_path")
            if new_bg_path != original_bg_path:
                 self.bg_img_original = self.load_image(new_bg_path)
                 if self.bg_img_original:
                      self.bg_img = pygame.transform.smoothscale(self.bg_img_original, (self.window_width, self.window_height))
                 else: # Handle load failure
                      print(f"Error loading saved background: {new_bg_path}. Reverting to default.")
                      self.options["background_image_path"] = config.DEFAULT_BG_IMG # Correct the saved option
                      options.save_options(self.options) # Save the correction
                      self.bg_img_original = self.load_image(config.DEFAULT_BG_IMG)
                      if self.bg_img_original:
                           self.bg_img = pygame.transform.smoothscale(self.bg_img_original, (self.window_width, self.window_height))
                      else:
                           self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))

        else:
            print("Options cancelled.")
            # Revert any previewed changes (e.g., background)
            # Check if the temp path is different AND not the placeholder
            if saved_bg_path != original_bg_path and saved_bg_path != config.SELECT_BACKGROUND_FROM_FILE:
                 self.bg_img_original = self.load_image(original_bg_path)
                 if self.bg_img_original:
                      self.bg_img = pygame.transform.smoothscale(self.bg_img_original, (self.window_width, self.window_height))
                 else:
                      self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))
            # Revert volume preview if any was done
            self.set_sfx_volume(self.options["sfx_volume"])

        # Restore original face/sfx set
        try:
            if self._stored_face_set:
                self.set_active_face_set(self._stored_face_set)
            if self._stored_sfx_set:
                self.set_active_sfx(self._stored_sfx_set)
        except Exception as e:
            print(f"Warning: Could not restore original face/sfx: {e}")
            # Fallback to default character resources
            try:
                if hasattr(self, 'character_data'):
                    face_set = getattr(self.character_data, 'faceSet', 'niko')
                    sfx_set = getattr(self.character_data, 'sfxSet', 'default')
                    self.set_active_face_set(face_set)
                    self.set_active_sfx(sfx_set)
            except Exception as e2:
                print(f"Warning: Fallback to character defaults also failed: {e2}")

    def _preview_option_change(self, key, value):
        """Applies a preview effect for certain options when changed."""
        if key == "sfx_volume":
            self.set_sfx_volume(value)
            # Play sound again with new volume for preview
            self.play_sound("menu_cursor")
        elif key == "background_image_path":
            # Handle the placeholder value - don't try to load it
            if value == config.SELECT_BACKGROUND_FROM_FILE:
                return # Do nothing for the placeholder itself

            # Load and apply the new background immediately for preview
            try:
                preview_bg = self.load_image(value)
                if preview_bg:
                     self.bg_img = pygame.transform.smoothscale(preview_bg, (self.window_width, self.window_height))
                else: # Handle load failure
                     print(f"Warning: Could not load background preview for: {value}")
                     # Optionally revert to a default or keep the old one
                     # self.bg_img = pygame.Surface((self.window_width, self.window_height)); self.bg_img.fill((50,50,50))
            except Exception as e:
                print(f"Error loading background preview: {e}")

    def _init_tk_root(self):
        """Initialize the tkinter root window for dialogs."""
        # Make sure we don't already have a root
        if self.tk_root:
            try:
                self.tk_root.destroy()
            except tk.TclError: # Handle case where it might already be destroyed
                pass
            self.tk_root = None

        # Create a new root window
        self.tk_root = tk.Tk()
        # Hide the root window
        self.tk_root.withdraw()
        # Bring it to the front (especially important on macOS)
        self.tk_root.attributes('-topmost', True)
        # Ensure it's shown over pygame window
        self.tk_root.update()

    def _select_background_from_file(self, widget_index):
        """Opens a file dialog to select a background image."""
        if not (0 <= widget_index < len(self.options_widgets)):
            return

        widget = self.options_widgets[widget_index]
        if widget["key"] != "background_image_path":
            return

        self._init_tk_root()
        try:
            filepath = filedialog.askopenfilename(
                parent=self.tk_root,
                title="Select Background Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
            )

            if filepath:
                # Normalize path separators
                filepath = os.path.normpath(filepath)
                print(f"Selected background file: {filepath}")
                # Update the temporary option value
                self.temp_options[widget["key"]] = filepath
                # Update the display value in the widget
                widget["current_display_value"] = os.path.basename(filepath)
                # Keep the index pointing to "Select from file..." visually
                widget["current_index"] = widget["values"].index(config.SELECT_BACKGROUND_FROM_FILE)
                # Trigger preview
                self._preview_option_change(widget["key"], filepath)
            else:
                print("Background file selection cancelled.")
                # If cancelled, revert the widget's display to the *actual* current background
                current_saved_path = self.temp_options.get(widget["key"], config.DEFAULT_BG_IMG)
                if current_saved_path == config.SELECT_BACKGROUND_FROM_FILE: # Should not happen, but safety check
                    current_saved_path = config.DEFAULT_BG_IMG

                if current_saved_path in widget["values"]:
                    widget["current_index"] = widget["values"].index(current_saved_path)
                    widget["current_display_value"] = widget["options"][widget["current_index"]]
                else: # Custom path was active before cancelling
                    widget["current_index"] = widget["values"].index(config.SELECT_BACKGROUND_FROM_FILE)
                    widget["current_display_value"] = os.path.basename(current_saved_path)


        except Exception as e:
            print(f"Error opening file dialog: {e}")
        finally:
            if self.tk_root:
                self.tk_root.destroy()
                self.tk_root = None

