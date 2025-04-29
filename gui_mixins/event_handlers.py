import pygame
import config
import os
import options # Import the options module for saving
from .text_utils import wrap_input_text # Import the wrapping utility
import time # For debug timestamp

class EventHandlersMixin:
    """Mixin containing methods for handling events in specific UI states."""

    def handle_input_event(self, event) -> tuple[str, str | int | None] | None:
        """Handles events specifically when text input is active."""
        if event.type == pygame.KEYDOWN:
            # --- DEBUG PRINT ---
            print(f"[{time.time():.2f}] Main Input KeyDown: {pygame.key.name(event.key)}, Unicode: '{event.unicode}'")
            # --- END DEBUG ---

            prev_text = self.user_input_text
            prev_cursor_pos = self.input_cursor_pos
            prev_height = self.input_rect.height
            needs_redraw = False # Flag to indicate if text/cursor changed visually

            # Check for both main Enter and Numpad Enter
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                submitted_text = self.user_input_text
                self.play_confirm_sound() # Play confirmation sound
                return ("submit_input", submitted_text)
            elif event.key == pygame.K_BACKSPACE:
                if self.input_cursor_pos > 0:
                    self.user_input_text = self.user_input_text[:self.input_cursor_pos-1] + self.user_input_text[self.input_cursor_pos:]
                    self.input_cursor_pos -= 1
                    needs_redraw = True
            elif event.key == pygame.K_DELETE:
                 if self.input_cursor_pos < len(self.user_input_text):
                      self.user_input_text = self.user_input_text[:self.input_cursor_pos] + self.user_input_text[self.input_cursor_pos+1:]
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
                return ("input_escape", None) # Allow escaping input mode
            else:
                if event.unicode and event.unicode.isprintable():
                    new_char = event.unicode
                    can_add_char = True
                    try:
                        test_text = self.user_input_text[:self.input_cursor_pos] + new_char + self.user_input_text[self.input_cursor_pos:]
                        max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                        wrapped_lines, _ = wrap_input_text(test_text, self.input_font, max_render_width)
                        num_lines = len(wrapped_lines)
                        required_height = (num_lines * self.input_font.get_height()) + config.INPUT_BOX_PADDING * 2
                        max_input_height = config.TEXTBOX_HEIGHT - 20

                        if self.input_rect.height >= max_input_height and required_height > max_input_height:
                            can_add_char = False

                    except (pygame.error, AttributeError) as e:
                        print(f"Warning: Error checking input box size before adding char: {e}")

                    if can_add_char:
                        self.user_input_text = self.user_input_text[:self.input_cursor_pos] + new_char + self.user_input_text[self.input_cursor_pos:]
                        self.input_cursor_pos += len(new_char)
                        needs_redraw = True

            if needs_redraw and (self.user_input_text != prev_text):
                try:
                    max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                    wrapped_lines, _ = wrap_input_text(self.user_input_text, self.input_font, max_render_width)
                    num_lines = len(wrapped_lines) if wrapped_lines else 1
                    required_height = (num_lines * self.input_font.get_height()) + config.INPUT_BOX_PADDING * 2

                    min_height = config.INPUT_BOX_HEIGHT
                    max_input_height = config.TEXTBOX_HEIGHT - 20

                    new_height = max(min_height, min(required_height, max_input_height))

                    if new_height != self.input_rect.height:
                        self.input_rect.height = new_height
                        needs_redraw = True

                except (pygame.error, AttributeError) as e:
                    print(f"Warning: Error calculating input box size after modification: {e}")
                    self.input_rect.height = prev_height

            if needs_redraw:
                self.input_cursor_visible = True
                self.input_cursor_timer = 0.0
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN:
             if self.input_rect.collidepoint(event.pos):
                  return None
             else:
                  pass

        return None


    def handle_choice_event(self, event) -> tuple[str, str | int | None] | None:
        """Handles events specifically when multiple choice is active."""
        prev_selected_index = self.selected_choice_index
        action_taken = False

        if event.type == pygame.KEYDOWN:
            num_options = len(self.choice_options)
            if num_options == 0: return None

            if event.key == pygame.K_UP:
                self.selected_choice_index = (self.selected_choice_index - 1) % num_options
                action_taken = True
            elif event.key == pygame.K_DOWN:
                self.selected_choice_index = (self.selected_choice_index + 1) % num_options
                action_taken = True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_KP_ENTER:
                self.play_confirm_sound()
                chosen_index = self.selected_choice_index
                return ("choice_made", chosen_index)
            elif event.key == pygame.K_ESCAPE:
                 return ("choice_cancel", None)

        elif event.type == pygame.MOUSEMOTION:
             mouse_pos = event.pos
             for i, rect in enumerate(self.choice_rects):
                  hover_rect = rect.inflate(4, 4)
                  if hover_rect.collidepoint(mouse_pos):
                       if self.selected_choice_index != i:
                            self.selected_choice_index = i
                            action_taken = True
                       break

        elif event.type == pygame.MOUSEBUTTONDOWN:
             if event.button == 1:
                  mouse_pos = event.pos
                  for i, rect in enumerate(self.choice_rects):
                       if rect.collidepoint(mouse_pos):
                            self.selected_choice_index = i
                            self.play_confirm_sound()
                            return ("choice_made", i)
                  bg_rect_for_choices = None
                  if self.choice_rects:
                       min_x = min(r.left for r in self.choice_rects) - self.choice_padding
                       min_y = min(r.top for r in self.choice_rects) - self.choice_padding
                       max_x = max(r.right for r in self.choice_rects) + self.choice_padding
                       max_y = max(r.bottom for r in self.choice_rects) + self.choice_padding
                       bg_rect_for_choices = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

                  if bg_rect_for_choices and not bg_rect_for_choices.collidepoint(mouse_pos):
                       return ("choice_cancel", None)

        if action_taken and self.selected_choice_index != prev_selected_index:
             self.play_sound("menu_cursor")

        return None


    def handle_options_menu_event(self, event) -> str | None:
        """Handles events specifically for the options menu screen, including scrolling and pop-ups."""
        if not self.is_options_menu_active:
            return None

        action = None

        if self.is_options_choice_popup_active:
            choice_action_result = self.handle_choice_event(event)
            if choice_action_result:
                choice_action, choice_data = choice_action_result
                if choice_action == "choice_made":
                    chosen_index = choice_data
                    if 0 <= self.editing_choice_widget_index < len(self.options_widgets):
                        widget = self.options_widgets[self.editing_choice_widget_index]
                        widget["current_index"] = chosen_index
                        self.temp_options[widget["key"]] = widget["values"][chosen_index]
                        self._preview_option_change(widget["key"], self.temp_options[widget["key"]])
                    self.is_options_choice_popup_active = False
                    self.is_choice_active = False
                    self.choice_options = []
                    self.editing_choice_widget_index = -1
                    return None
                elif choice_action == "choice_cancel":
                    self.is_options_choice_popup_active = False
                    self.is_choice_active = False
                    self.choice_options = []
                    self.editing_choice_widget_index = -1
                    self.play_sound("menu_cancel")
                    return None
            return None

        focused_widget = self.options_widgets[self.focused_widget_index]
        max_scroll = max(0, self.total_options_height - self.visible_options_height)
        num_widgets = len(self.options_widgets)
        save_button_index = num_widgets - 2
        cancel_button_index = num_widgets - 1

        scrolled = False
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y -= event.y * self.scroll_speed
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))
            scrolled = True
        elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_PAGEUP:
                  self.scroll_y -= self.visible_options_height
                  self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                  scrolled = True
             elif event.key == pygame.K_PAGEDOWN:
                  self.scroll_y += self.visible_options_height
                  self.scroll_y = max(0, min(self.scroll_y, max_scroll))
                  scrolled = True

        if scrolled:
             return None

        if event.type == pygame.KEYDOWN:
            # --- DEBUG PRINT ---
            if not self.is_options_choice_popup_active:
                print(f"[{time.time():.2f}] Options KeyDown: {pygame.key.name(event.key)}, Unicode: '{event.unicode}'")
            # --- END DEBUG ---

            if event.key == pygame.K_LEFT:
                if self.focused_widget_index == cancel_button_index:
                    self._update_focus_and_scroll(save_button_index)
                    return None
            elif event.key == pygame.K_RIGHT:
                if self.focused_widget_index == save_button_index:
                    self._update_focus_and_scroll(cancel_button_index)
                    return None

            if event.key == pygame.K_UP:
                new_index = (self.focused_widget_index - 1) % num_widgets
                self._update_focus_and_scroll(new_index)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_TAB:
                new_index = (self.focused_widget_index + 1) % num_widgets
                self._update_focus_and_scroll(new_index)
            elif event.key == pygame.K_ESCAPE:
                action = "cancel"
                self.play_sound("menu_cancel")

            elif focused_widget["type"] == "choice":
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
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_KP_ENTER:
                        self.is_options_choice_popup_active = True
                        self.editing_choice_widget_index = self.focused_widget_index
                        self.choice_options = focused_widget["options"]
                        self.selected_choice_index = focused_widget["current_index"]
                        self.is_choice_active = True
                        self.play_confirm_sound()
                        return None

            elif focused_widget["type"] == "input":
                # --- DEBUG PRINT ---
                print(f"    -> Options Input Widget Handling Key: {pygame.key.name(event.key)}")
                # --- END DEBUG ---
                text = focused_widget["text"]
                cursor_pos = focused_widget["cursor_pos"]
                text_changed = False

                if event.key == pygame.K_BACKSPACE:
                    if cursor_pos > 0:
                        focused_widget["text"] = text[:cursor_pos-1] + text[cursor_pos:]
                        focused_widget["cursor_pos"] -= 1
                        text_changed = True
                elif event.key == pygame.K_DELETE:
                     if cursor_pos < len(text):
                          focused_widget["text"] = text[:cursor_pos] + text[cursor_pos+1:]
                          text_changed = True
                elif event.key == pygame.K_LEFT:
                     if cursor_pos > 0: focused_widget["cursor_pos"] -= 1
                elif event.key == pygame.K_RIGHT:
                     if cursor_pos < len(text): focused_widget["cursor_pos"] += 1
                elif event.key == pygame.K_HOME:
                     focused_widget["cursor_pos"] = 0
                elif event.key == pygame.K_END:
                     focused_widget["cursor_pos"] = len(text)
                elif event.unicode and event.unicode.isprintable():
                    focused_widget["text"] = text[:cursor_pos] + event.unicode + text[cursor_pos:]
                    focused_widget["cursor_pos"] += len(event.unicode)
                    text_changed = True

                if text_changed:
                    self.temp_options[focused_widget["key"]] = focused_widget["text"]

                focused_widget["cursor_visible"] = True
                focused_widget["cursor_timer"] = 0.0
                return None

            elif focused_widget["type"] == "button":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_KP_ENTER:
                    action = focused_widget["action"]
                    self.play_confirm_sound()

        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = (event.pos[0], event.pos[1] + self.scroll_y)

            for i, widget in enumerate(self.options_widgets):
                if widget["rect"].collidepoint(mouse_pos):
                    if self.focused_widget_index != i:
                        self._update_focus_and_scroll(i, scroll_if_needed=False)
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_pos = (event.pos[0], event.pos[1] + self.scroll_y)

                for i, widget in enumerate(self.options_widgets):
                    if widget["rect"].collidepoint(mouse_pos):
                        self._update_focus_and_scroll(i, scroll_if_needed=False)
                        focused_widget = self.options_widgets[i]

                        if focused_widget["type"] == "button":
                            action = focused_widget["action"]
                            self.play_confirm_sound()
                        elif focused_widget["type"] == "choice":
                            self.is_options_choice_popup_active = True
                            self.editing_choice_widget_index = i
                            self.choice_options = focused_widget["options"]
                            self.selected_choice_index = focused_widget["current_index"]
                            self.is_choice_active = True
                            self.play_confirm_sound()
                        elif focused_widget["type"] == "input":
                             text_start_x = widget["rect"].left + 5
                             click_offset_x = mouse_pos[0] - text_start_x
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
                             widget["cursor_visible"] = True
                             widget["cursor_timer"] = 0.0
                        break

        return action


    def _update_focus_and_scroll(self, new_index, scroll_if_needed=True):
        """Updates the focused widget index and scrolls if necessary to keep it visible."""
        if self.focused_widget_index != new_index:
             old_focused_widget = self.options_widgets[self.focused_widget_index]
             self.focused_widget_index = new_index
             new_focused_widget = self.options_widgets[self.focused_widget_index]
             self.play_sound("menu_cursor")

             if old_focused_widget["type"] == "input": old_focused_widget["cursor_visible"] = False; old_focused_widget["cursor_timer"] = 0.0
             if new_focused_widget["type"] == "input": new_focused_widget["cursor_visible"] = True; new_focused_widget["cursor_timer"] = 0.0

        if scroll_if_needed:
            widget_rect = self.options_widgets[self.focused_widget_index]["rect"]
            widget_top_on_screen = widget_rect.top - self.scroll_y
            widget_bottom_on_screen = widget_rect.bottom - self.scroll_y
            content_area_y_start = 80

            max_scroll = max(0, self.total_options_height - self.visible_options_height)

            if widget_top_on_screen < content_area_y_start:
                self.scroll_y = widget_rect.top - content_area_y_start
            elif widget_bottom_on_screen > content_area_y_start + self.visible_options_height:
                self.scroll_y = widget_rect.bottom - (content_area_y_start + self.visible_options_height)

            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

