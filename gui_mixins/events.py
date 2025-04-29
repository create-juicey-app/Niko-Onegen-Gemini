import pygame
import platform
if platform.system() == "Windows":
    import ctypes # Keep windows specific import here
import config # Needed for key checks maybe

class EventsMixin:
    """Mixin class for handling Pygame events and window interactions."""

    def handle_event(self, event) -> tuple[str, str | int | None] | None:
        """Processes a single Pygame event and returns an action tuple or None."""

        # --- Forced Quit Check ---
        # During forced quit, only allow QUIT event or essential window events
        if getattr(self, 'is_forced_quitting', False):
            if event.type == pygame.QUIT:
                self.running = False # Allow quitting immediately
                return ("quit", None) # Return quit action
            # Potentially allow window events like move/resize if needed, but generally block input
            return None # Ignore all other input during forced quit

        # --- Standard Event Handling ---

        # 1. QUIT Event (Window Close Button)
        if event.type == pygame.QUIT:
            # Don't set self.running = False directly here.
            # Return an action that the main loop can use to initiate fade-out or quit.
            return ("initiate_quit", None)

        # 2. History View Active Check
        if getattr(self, 'is_history_active', False):
            # Only handle Escape key or essential window events in history view
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Let the caller handle closing the history view
                return ("history_escape", None)
            # Allow dragging/quit events even in history view (fall through)
            elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.QUIT]:
                 pass # Let these events be handled below
            else:
                 return None # Ignore other input (like clicks, typing) in history view

        # 3. Menu Toggle (Tab Key)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            # Only toggle menu if not in input mode or choice mode (unless menu allows it)
            if not getattr(self, 'is_input_active', False) and \
               not getattr(self, 'is_choice_active', False):
                # Action: toggle_menu, Value: None
                return ("toggle_menu", None)

        # 4. Escape Key Handling (Context Dependent)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if getattr(self, 'is_options_menu_active', False): # Check options menu first
                 # Delegate Escape in options menu to its handler
                 if hasattr(self, 'handle_options_menu_event'):
                      action = self.handle_options_menu_event(event)
                      if action == "cancel":
                           return ("exit_options", False) # Signal to exit options without saving
                 return None # Consume escape if options menu handled it (or should have)
            elif getattr(self, 'is_menu_active', False):
                self.play_sound("menu_cancel") # Play cancel sound if available
                # Action: toggle_menu (used to close the menu), Value: None
                return ("toggle_menu", None)
            # Note: Escape handling within input/choice modes is done in their specific handlers

        # 5. Window Dragging Logic
        # --- Start Drag ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
            mouse_pos = event.pos
            # Check if click is outside interactive elements (textbox, input, choice)
            is_on_interactive = False
            if hasattr(self, 'textbox_img'):
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                if textbox_rect.collidepoint(mouse_pos):
                    is_on_interactive = True

            if not is_on_interactive and getattr(self, 'is_input_active', False) and hasattr(self, 'input_rect'):
                # Slightly larger rect for input interaction check
                input_interaction_rect = self.input_rect.inflate(10, 10)
                if input_interaction_rect.collidepoint(mouse_pos):
                    is_on_interactive = True

            if not is_on_interactive and getattr(self, 'is_choice_active', False) and hasattr(self, 'choice_rects'):
                 # Check if click is on any choice rect
                 bg_rect_for_choices = None
                 if self.choice_rects:
                      # Estimate background area based on choice rects
                      min_x = min(r.left for r in self.choice_rects) - self.choice_padding
                      min_y = min(r.top for r in self.choice_rects) - self.choice_padding
                      max_x = max(r.right for r in self.choice_rects) + self.choice_padding
                      max_y = max(r.bottom for r in self.choice_rects) + self.choice_padding
                      bg_rect_for_choices = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

                 if bg_rect_for_choices and bg_rect_for_choices.collidepoint(mouse_pos):
                      is_on_interactive = True


            # If click is not on any interactive element, start dragging
            if not is_on_interactive:
                self.dragging = True
                # Get current window position accurately (using OS specific methods if possible)
                current_window_x, current_window_y = self.window_x, self.window_y # Use stored pos as fallback
                if platform.system() == "Windows" and getattr(self, 'hwnd', None):
                     try:
                         rect = ctypes.wintypes.RECT()
                         ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
                         current_window_x = rect.left
                         current_window_y = rect.top
                         # Update stored position as well
                         self.window_x, self.window_y = current_window_x, current_window_y
                     except Exception as e:
                         print(f"Warning: Failed to get window rect via ctypes: {e}")
                         pass # Use fallback position

                # Calculate offset from window top-left to mouse click position
                self.drag_offset_x = current_window_x - mouse_pos[0]
                self.drag_offset_y = current_window_y - mouse_pos[1]
                # Action: drag_start, Value: None
                return ("drag_start", None) # Consume the click event

        # --- Stop Drag ---
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if getattr(self, 'dragging', False):
                self.dragging = False
                # Action: drag_end, Value: None
                return ("drag_end", None) # Consume the event

        # --- Dragging Motion ---
        elif event.type == pygame.MOUSEMOTION:
            if getattr(self, 'dragging', False):
                mouse_pos = event.pos
                # Calculate new window top-left position
                new_x = mouse_pos[0] + self.drag_offset_x
                new_y = mouse_pos[1] + self.drag_offset_y

                # Try to move the window using OS-specific methods
                moved_successfully = False
                if platform.system() == "Windows" and getattr(self, 'hwnd', None):
                    try:
                        # Flags for SetWindowPos: NO_SIZE, NO_ZORDER, SHOW_WINDOW (maybe NO_ACTIVATE?)
                        # SWP_NOSIZE (0x0001), SWP_NOZORDER (0x0004), SWP_SHOWWINDOW (0x0040)
                        # Using 0x0005 = SWP_NOSIZE | SWP_NOZORDER
                        flags = 0x0001 | 0x0004 # NOSIZE | NOZORDER
                        ctypes.windll.user32.SetWindowPos(self.hwnd, 0, new_x, new_y, 0, 0, flags)
                        # Update stored position if successful
                        self.window_x = new_x
                        self.window_y = new_y
                        moved_successfully = True
                    except Exception as e:
                        print(f"Warning: Failed to set window pos via ctypes: {e}")
                        self.dragging = False # Stop dragging if OS call fails
                # Add elif for Linux/X11 or macOS if implementing platform-specific dragging there

                # If OS move failed or not implemented, dragging stops (or does nothing)
                if not moved_successfully:
                     # On unsupported platforms, dragging flag remains True but window doesn't move
                     # Or uncomment below to stop dragging if OS move fails:
                     # self.dragging = False
                     pass


                # Action: dragging, Value: new calculated position (optional)
                return ("dragging", (new_x, new_y)) # Consume the event

        # --- Consume mouse events if dragging started outside interactive elements ---
        if getattr(self, 'dragging', False) and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
             return None


        # 6. Context-Specific Input Handling (Options Menu, Choices, Text Input, Dialogue)
        # Process these modes exclusively.

        # --- Options Menu Mode ---
        if getattr(self, 'is_options_menu_active', False):
            if hasattr(self, 'handle_options_menu_event'):
                action_result = self.handle_options_menu_event(event) # Get result first
                # Check if the options handler returned an action ("save" or "cancel")
                if isinstance(action_result, str): # handle_options_menu_event returns "save" or "cancel"
                    if action_result == "save":
                        return ("exit_options", True)
                    elif action_result == "cancel":
                        return ("exit_options", False)
                # If handle_options_menu_event returned None, it means the event was
                # handled internally (like navigation), so consume the event.
                return None # Consume event, preventing fall-through
            else:
                print("Warning: is_options_menu_active is True, but handle_options_menu_event method missing.")
                return None # Consume event anyway

        # --- Choice Mode ---
        if getattr(self, 'is_choice_active', False):
            # Ensure the choice event handler method exists (now in EventHandlersMixin)
            if hasattr(self, 'handle_choice_event'):
                return self.handle_choice_event(event)
            else:
                print("Warning: is_choice_active is True, but handle_choice_event method missing.")
                return None # Consume event anyway if state is inconsistent

        # --- Input Mode ---
        if getattr(self, 'is_input_active', False):
            # Ensure the input event handler method exists (now in EventHandlersMixin)
            if hasattr(self, 'handle_input_event'):
                return self.handle_input_event(event)
            else:
                print("Warning: is_input_active is True, but handle_input_event method missing.")
                return None # Consume event anyway if state is inconsistent

        # --- Normal Dialogue Mode (Only if not in other modes) ---
        # This block should now only be reached if Options, Choice, and Input modes are inactive.
        # Handle advance/skip actions for dialogue
        if event.type == pygame.KEYDOWN:
            # Check for Space or Enter keys
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Check current dialogue state to determine action
                if getattr(self, 'is_paused', False):
                    return ("skip_pause", None)
                elif getattr(self, 'is_animating', False):
                    return ("skip_anim", None)
                elif getattr(self, 'draw_arrow', False):
                    return ("advance", None)

        elif event.type == pygame.MOUSEBUTTONDOWN:
             if event.button == 1: # Left click
                mouse_pos = event.pos
                # Check if click is within the textbox area
                if hasattr(self, 'textbox_img'):
                    textbox_clickable_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                    if textbox_clickable_rect.collidepoint(mouse_pos):
                        # Same logic as keydown for skipping/advancing
                        if getattr(self, 'is_paused', False):
                            return ("skip_pause", None)
                        elif getattr(self, 'is_animating', False):
                            return ("skip_anim", None)
                        elif getattr(self, 'draw_arrow', False):
                            return ("advance", None)
                        # Consume the click on the textbox even if no action is taken
                        return None


        # 7. Default: No specific action taken for this event in this context
        return None
