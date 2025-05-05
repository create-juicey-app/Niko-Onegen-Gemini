import pygame
import textwrap
import re
import json
import os
from datetime import datetime
from typing import List, Dict, Tuple, Any, Callable
from pydantic import ValidationError
import config 
# Add tkinter import for file dialogs
import tkinter as tk
from tkinter import filedialog
import pickle
import zlib

class HistoryMixin:
    """Mixin class for displaying chat history in a modern messaging style interface."""

    def _initialize_history_state(self):
        """Initialize state variables for the history view."""
        # History view state
        self.is_history_active = False
        self.history_scroll_y = 0
        self.history_max_scroll_y = 0
        
        # Styling constants - use colors from the main theme
        self.HISTORY_BG_COLOR = (25, 25, 35)  # Same dark background as main
        # Use colors from config where available
        self.HISTORY_USER_BUBBLE_COLOR = config.CHOICE_HIGHLIGHT_COLOR  # Use the highlight color for user bubbles
        self.HISTORY_AI_BUBBLE_COLOR = (50, 50, 60)  # Similar to dialogue box
        self.HISTORY_TEXT_COLOR = config.TEXT_COLOR  # Use the same text color as dialogue
        self.HISTORY_BUBBLE_PADDING = 10
        self.HISTORY_BUBBLE_MARGIN_Y = 5
        self.HISTORY_BUBBLE_MARGIN_X = 15
        self.HISTORY_MAX_BUBBLE_WIDTH_RATIO = 0.65
        self.HISTORY_FACE_SIZE = 64
        self.HISTORY_SCROLL_SPEED = 30
        
        # Scrollbar colors - match with options menu scrollbar
        self.HISTORY_SCROLLBAR_COLOR = getattr(self, 'scrollbar_color', (100, 100, 100))
        self.HISTORY_SCROLLBAR_HANDLE_COLOR = getattr(self, 'scrollbar_handle_color', (150, 150, 150))
        self.HISTORY_SCROLLBAR_ACTIVE_COLOR = (180, 180, 180)
        
        # Pre-render common elements - use the same fonts
        self.history_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE - 2))
        self.history_line_height = self.history_font.get_height() + 2
        
        # Keep track of rendered bubbles (cache)
        self.history_rendered_bubbles = []
        self.history_total_content_height = 0
        self.history_cached_for_history = None
        
        # Mouse scrolling state
        self.scrollbar_dragging = False
        self.scrollbar_rect = None
        self.scrollbar_handle_rect = None
        
        # Action buttons
        self.history_buttons = []
        self.create_history_buttons()
        
        # Button navigation state
        self.selected_button_index = 0  # Track which button is currently selected
        self.using_keyboard_navigation = False  # Track if we're using keyboard or mouse
        
        # History save/load directory
        self.history_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_histories')
        os.makedirs(self.history_dir, exist_ok=True)
        
        # Initialize tkinter for file dialogs but hide the root window
        self.tk_root = None
        
        # State for confirmation dialogs
        self.showing_confirmation = False
        self.confirmation_message = ""
        self.confirmation_callback = None
        self.confirmation_buttons = []
        self.selected_confirmation_button = 0  # Track which confirmation button is selected
        
        # Message navigation state
        self.user_turn_indices = []  # Indices of user message turns for navigation
        self.current_nav_index = -1   # Current navigation position
        
        # Callback for when history is deleted to reset AI
        self.history_delete_callback = None

    def create_history_buttons(self):
        """Create floating action buttons for history view."""
        button_width = 80
        button_height = 35
        button_margin = 10
        button_y = self.window_height - button_height - button_margin
        
        # Save button
        save_rect = pygame.Rect(
            button_margin, 
            button_y, 
            button_width, 
            button_height
        )
        self.history_buttons.append({
            'rect': save_rect,
            'text': 'Save',
            'action': 'save_history',
            'hover': False
        })
        
        # Load button
        load_rect = pygame.Rect(
            button_margin + button_width + 10, 
            button_y, 
            button_width, 
            button_height
        )
        self.history_buttons.append({
            'rect': load_rect,
            'text': 'Load',
            'action': 'load_history',
            'hover': False
        })
        
        # Delete button
        delete_rect = pygame.Rect(
            button_margin + (button_width + 10) * 2, 
            button_y, 
            button_width, 
            button_height
        )
        self.history_buttons.append({
            'rect': delete_rect,
            'text': 'Delete',
            'action': 'delete_history',
            'hover': False
        })

    def display_chat_history(self, history: List[Dict], delete_callback: Callable = None):
        """Displays the chat history in a simulated messaging app window."""
        # Initialize history state if not already done
        if not hasattr(self, 'history_rendered_bubbles'):
            self._initialize_history_state()
            
        self.is_history_active = True
        
        # Store the delete callback for resetting AI
        self.history_delete_callback = delete_callback
        
        # Reset button navigation state
        self.selected_button_index = 0
        self.using_keyboard_navigation = False
        
        # Only regenerate bubbles if history has changed
        if self.history_cached_for_history != history:
            self._generate_history_bubbles(history)
            self.history_cached_for_history = history
            
            # Set scroll position to bottom by default
            self.history_max_scroll_y = max(0, self.history_total_content_height - self.window_height)
            self.history_scroll_y = self.history_max_scroll_y  # Start at bottom
        else:
            # Recalculate max scroll in case window size changed
            self.history_max_scroll_y = max(0, self.history_total_content_height - self.window_height)

        history_active = True
        while history_active and self.running:
            dt = self.clock.tick(60) / 1000.0

            # Only update hover from mouse if not using keyboard
            mouse_pos = pygame.mouse.get_pos()
            if not self.using_keyboard_navigation:
                self._update_button_hover_states(mouse_pos)

            for event in pygame.event.get():
                result = self.handle_event(event)
                if result:
                    action, _ = result
                    if action == "initiate_quit":
                        self.running = False
                        history_active = False
                        break
                    elif action == "history_escape" or action == "toggle_menu":
                        history_active = False
                        break
                        
                # Handle scroll and mouse events
                self._handle_history_scroll_event(event)
                self._handle_history_mouse_event(event)
                
                # Set keyboard navigation flag if arrow keys are used
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.using_keyboard_navigation = True

            if not self.running: 
                break

            self._render_history_view()

        self.is_history_active = False
        # Reset dragging state when exiting
        self.scrollbar_dragging = False
        # Clear delete callback reference
        self.history_delete_callback = None

    def _update_button_hover_states(self, mouse_pos):
        """Update hover states for all buttons based on mouse position."""
        if self.using_keyboard_navigation:
            return
            
        # Check if mouse is over any button
        mouse_over_button = False
        for i, button in enumerate(self.history_buttons):
            is_hover = button['rect'].collidepoint(mouse_pos)
            button['hover'] = is_hover
            if is_hover:
                self.selected_button_index = i
                mouse_over_button = True
        
        # If mouse moved away from buttons, stop using keyboard navigation
        if not mouse_over_button:
            # Keep the current selected button highlighted if using keyboard
            if self.using_keyboard_navigation and self.history_buttons:
                self.history_buttons[self.selected_button_index]['hover'] = True

    def _handle_history_mouse_event(self, event):
        """Handle mouse interactions with the history view."""
        # If showing a confirmation dialog, handle its events first
        if self.showing_confirmation:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                for i, button in enumerate(self.confirmation_buttons):
                    if button['rect'].collidepoint(event.pos):
                        self.selected_confirmation_button = i
                        if button['action'] == 'confirm':
                            self.showing_confirmation = False
                            if self.confirmation_callback:
                                self.confirmation_callback()
                        else:  # 'cancel'
                            self.showing_confirmation = False
                        return
            return
            
        # Any mouse movement or click should disable keyboard navigation
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and event.pos:
            self.using_keyboard_navigation = False
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            # Check for button clicks
            for i, button in enumerate(self.history_buttons):
                if button['hover']:
                    self.selected_button_index = i
                    if button['action'] == 'save_history':
                        self._save_current_history()
                    elif button['action'] == 'load_history':
                        self._load_history()
                    elif button['action'] == 'delete_history':
                        self._delete_current_history()
                    return
                    
            # Check if scrollbar handle is clicked
            if self.scrollbar_handle_rect and self.scrollbar_handle_rect.collidepoint(event.pos):
                self.scrollbar_dragging = True
                return
                
            # Check if scrollbar track is clicked (jump to position)
            if self.scrollbar_rect and self.scrollbar_rect.collidepoint(event.pos):
                # Calculate new scroll position based on click position relative to the track
                relative_y = event.pos[1] - self.scrollbar_rect.top
                click_y_ratio = relative_y / self.scrollbar_rect.height
                click_y_ratio = max(0, min(1, click_y_ratio))  # Clamp between 0 and 1
                self.history_scroll_y = int(click_y_ratio * self.history_max_scroll_y)
                return
                
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click released
                self.scrollbar_dragging = False
                
        elif event.type == pygame.MOUSEMOTION:
            if self.scrollbar_dragging and self.history_max_scroll_y > 0:
                # Calculate new scroll position based on drag relative to the track
                relative_y = event.pos[1] - self.scrollbar_rect.top
                drag_y_ratio = relative_y / self.scrollbar_rect.height
                drag_y_ratio = max(0, min(1, drag_y_ratio))  # Clamp between 0 and 1
                self.history_scroll_y = int(drag_y_ratio * self.history_max_scroll_y)

    def _handle_history_scroll_event(self, event: pygame.event.Event):
        """Handle scroll events in the history view."""
        if event.type == pygame.KEYDOWN:
            # Handle navigation within confirmation dialog if active
            if self.showing_confirmation:
                if event.key == pygame.K_LEFT:
                    self.selected_confirmation_button = 0  # Yes
                    self.confirmation_buttons[0]['hover'] = True
                    self.confirmation_buttons[1]['hover'] = False
                elif event.key == pygame.K_RIGHT:
                    self.selected_confirmation_button = 1  # No
                    self.confirmation_buttons[0]['hover'] = False
                    self.confirmation_buttons[1]['hover'] = True
                elif event.key == pygame.K_RETURN:
                    # Activate the selected confirmation button
                    if self.selected_confirmation_button == 0:  # Yes
                        self.showing_confirmation = False
                        if self.confirmation_callback:
                            self.confirmation_callback()
                    else:  # No
                        self.showing_confirmation = False
                return
            
            # Regular keyboard navigation
            if event.key == pygame.K_UP:
                self.history_scroll_y = max(0, self.history_scroll_y - self.HISTORY_SCROLL_SPEED)
            elif event.key == pygame.K_DOWN:
                self.history_scroll_y = min(self.history_max_scroll_y, self.history_scroll_y + self.HISTORY_SCROLL_SPEED)
            elif event.key == pygame.K_PAGEUP:
                self.history_scroll_y = max(0, self.history_scroll_y - self.window_height)
            elif event.key == pygame.K_PAGEDOWN:
                self.history_scroll_y = min(self.history_max_scroll_y, self.history_scroll_y + self.window_height)
            elif event.key == pygame.K_HOME:
                self.history_scroll_y = 0
            elif event.key == pygame.K_END:
                self.history_scroll_y = self.history_max_scroll_y
            # Button navigation with left/right arrows
            elif event.key == pygame.K_LEFT:
                self._navigate_previous_button()
            elif event.key == pygame.K_RIGHT:
                self._navigate_next_button()
            # User message navigation
            elif event.key == pygame.K_COMMA or event.key == pygame.K_PERIOD:  # Use comma/period as alternatives
                if event.key == pygame.K_COMMA:
                    self._navigate_to_previous_user_message()
                else:
                    self._navigate_to_next_user_message()
            # Activate buttons with Enter
            elif event.key == pygame.K_RETURN:
                self._activate_selected_button()
            # Add Delete key as shortcut for deleting history
            elif event.key == pygame.K_DELETE:
                self._delete_current_history()
        elif event.type == pygame.MOUSEWHEEL:
            self.history_scroll_y = max(0, min(self.history_max_scroll_y, 
                                             self.history_scroll_y - event.y * self.HISTORY_SCROLL_SPEED))

    def _navigate_previous_button(self):
        """Navigate to the previous button."""
        if not self.history_buttons:
            return
            
        self.using_keyboard_navigation = True
        # Reset all buttons' hover state
        for button in self.history_buttons:
            button['hover'] = False
            
        # Move selection to previous button
        self.selected_button_index = (self.selected_button_index - 1) % len(self.history_buttons)
        # Set hover state for selected button
        self.history_buttons[self.selected_button_index]['hover'] = True
        
    def _navigate_next_button(self):
        """Navigate to the next button."""
        if not self.history_buttons:
            return
            
        self.using_keyboard_navigation = True
        # Reset all buttons' hover state
        for button in self.history_buttons:
            button['hover'] = False
            
        # Move selection to next button
        self.selected_button_index = (self.selected_button_index + 1) % len(self.history_buttons)
        # Set hover state for selected button
        self.history_buttons[self.selected_button_index]['hover'] = True
        
    def _activate_selected_button(self):
        """Activate the currently selected button."""
        if not self.history_buttons:
            return
            
        button = self.history_buttons[self.selected_button_index]
        if button['action'] == 'save_history':
            self._save_current_history()
        elif button['action'] == 'load_history':
            self._load_history()
        elif button['action'] == 'delete_history':
            self._delete_current_history()

    def _navigate_to_previous_user_message(self):
        """Navigate to the previous user message in history."""
        if not self.user_turn_indices:
            return
            
        # If we haven't started navigation yet, start at the most recent message
        if self.current_nav_index == -1:
            self.current_nav_index = len(self.user_turn_indices) - 1
        else:
            # Move to previous message
            self.current_nav_index = max(0, self.current_nav_index - 1)
            
        # Scroll to the message
        self._scroll_to_message_index(self.user_turn_indices[self.current_nav_index])
        
    def _navigate_to_next_user_message(self):
        """Navigate to the next user message in history."""
        if not self.user_turn_indices:
            return
            
        # If we haven't started navigation yet, start at the first message
        if self.current_nav_index == -1:
            self.current_nav_index = 0
        else:
            # Move to next message
            self.current_nav_index = min(len(self.user_turn_indices) - 1, self.current_nav_index + 1)
            
        # Scroll to the message
        self._scroll_to_message_index(self.user_turn_indices[self.current_nav_index])
        
    def _scroll_to_message_index(self, index):
        """Scroll the view to make the message at the given index visible."""
        if index < 0 or index >= len(self.history_rendered_bubbles):
            return
            
        # Get the bubble rect for this message
        _, bubble_rect, _ = self.history_rendered_bubbles[index]
        
        # Calculate scroll position to make this message visible
        # Aim to position the message 1/3 of the way down the screen
        target_scroll_y = bubble_rect.top - (self.window_height // 3)
        
        # Clamp to valid scroll range
        self.history_scroll_y = max(0, min(self.history_max_scroll_y, target_scroll_y))
        
    def _delete_current_history(self):
        """Delete the current chat history."""
        if not self.history_cached_for_history:
            self._show_notification("No history to delete")
            return
            
        self._show_confirmation(
            "Are you sure you want to delete the current history?",
            self._confirm_delete_history
        )
        
    def _confirm_delete_history(self):
        """Actually delete the history after confirmation."""
        # Clear the history
        self.history_cached_for_history = []
        self.history_rendered_bubbles = []
        self.history_total_content_height = 0
        self.history_max_scroll_y = 0
        self.history_scroll_y = 0
        self.user_turn_indices = []
        self.current_nav_index = -1
        
        # Force regeneration of empty history view
        self._generate_history_bubbles([])
        
        # Call the delete callback to reset the AI's history if provided
        if self.history_delete_callback:
            self.history_delete_callback()
            
        # Also delete the history.dat file if it exists
        history_file_path = config.HISTORY_FILE
        file_deleted = False
        
        if os.path.exists(history_file_path):
            try:
                os.remove(history_file_path)
                file_deleted = True
                print(f"Deleted history file: {history_file_path}")
            except (IOError, PermissionError) as e:
                print(f"Error deleting history file {history_file_path}: {e}")
        
        # Show appropriate notification
        if file_deleted:
            self._show_notification("History deleted from memory and disk")
        else:
            self._show_notification("History deleted from memory")
        
    def _show_confirmation(self, message, callback):
        """Show a confirmation dialog with Yes/No buttons."""
        self.showing_confirmation = True
        self.confirmation_message = message
        self.confirmation_callback = callback
        self.selected_confirmation_button = 1  # Default to "No" for safety
        
        # Create Yes/No buttons
        button_width = 60
        button_height = 30
        button_spacing = 20
        total_width = (button_width * 2) + button_spacing
        
        # Center the buttons horizontally
        start_x = (self.window_width - total_width) // 2
        button_y = (self.window_height // 2) + 20
        
        # Yes button
        yes_rect = pygame.Rect(
            start_x, 
            button_y, 
            button_width, 
            button_height
        )
        
        # No button
        no_rect = pygame.Rect(
            start_x + button_width + button_spacing, 
            button_y, 
            button_width, 
            button_height
        )
        
        self.confirmation_buttons = [
            {
                'rect': yes_rect,
                'text': 'Yes',
                'action': 'confirm',
                'hover': False
            },
            {
                'rect': no_rect,
                'text': 'No',
                'action': 'cancel',
                'hover': True  # Default No to highlighted
            }
        ]

    def _render_history_view(self):
        """Render the chat history view."""
        # Reuse the background rendering function for consistent look
        if hasattr(self, 'render_background_and_overlay'):
            self.render_background_and_overlay(self.screen)
        else:
            self.screen.fill(self.HISTORY_BG_COLOR)

        # Draw message bubbles
        visible_area = pygame.Rect(0, self.history_scroll_y, self.window_width, self.window_height)
        for bubble_surf, bubble_rect, role in self.history_rendered_bubbles:
            if bubble_rect.colliderect(visible_area):
                draw_pos = bubble_rect.move(0, -self.history_scroll_y)
                self.screen.blit(bubble_surf, draw_pos)

        # Draw title at the top
        title_font = self.fonts.get('bold', self.history_font)
        title_surf = title_font.render("Chat History", True, config.TEXT_COLOR)
        title_rect = title_surf.get_rect(centerx=self.window_width // 2, top=20)
        
        # Add a semi-transparent background behind the title for better readability
        title_bg = pygame.Surface((title_surf.get_width() + 20, title_surf.get_height() + 10), pygame.SRCALPHA)
        title_bg.fill((0, 0, 0, 128))
        self.screen.blit(title_bg, (title_rect.left - 10, title_rect.top - 5))
        self.screen.blit(title_surf, title_rect)

        # Draw scrollbar if needed
        if self.history_max_scroll_y > 0:
            self._draw_history_scrollbar()
            
        # Draw action buttons
        self._draw_history_buttons()
        
        # Draw confirmation dialog if active
        if self.showing_confirmation:
            self._draw_confirmation_dialog()

        pygame.display.flip()

    def _draw_history_scrollbar(self):
        """Draw a scrollbar for the history view using the same style as options menu."""
        # Calculate 90% of window height for the scrollbar
        scrollbar_area_height = int(self.window_height * 0.9)
        # Calculate y position to center it vertically
        scrollbar_area_y = int(self.window_height * 0.05)  # 5% from top
        
        # Calculate handle height proportionally
        scrollbar_height_ratio = min(1.0, self.window_height / self.history_total_content_height)
        scrollbar_height = max(20, int(scrollbar_area_height * scrollbar_height_ratio))
        
        # Calculate handle position relative to the scrollable area
        scrollbar_y_ratio = self.history_scroll_y / self.history_max_scroll_y if self.history_max_scroll_y > 0 else 0
        # Position handle within the scrollbar track (not the full window)
        scrollbar_y = scrollbar_area_y + int(scrollbar_y_ratio * (scrollbar_area_height - scrollbar_height))

        # Draw scrollbar track - use the same style as options menu scrollbar
        scrollbar_x = self.window_width - 15
        track_rect = pygame.Rect(scrollbar_x, scrollbar_area_y, 8, scrollbar_area_height)
        self.scrollbar_rect = track_rect  # Store for mouse interaction
        pygame.draw.rect(self.screen, self.HISTORY_SCROLLBAR_COLOR, track_rect, border_radius=4)
        
        # Draw scrollbar handle
        handle_rect = pygame.Rect(scrollbar_x, scrollbar_y, 8, scrollbar_height)
        self.scrollbar_handle_rect = handle_rect  # Store for mouse interaction
        
        # Use active color if being dragged
        handle_color = self.HISTORY_SCROLLBAR_ACTIVE_COLOR if self.scrollbar_dragging else self.HISTORY_SCROLLBAR_HANDLE_COLOR
        pygame.draw.rect(self.screen, handle_color, handle_rect, border_radius=4)
        
        # Add subtle navigation indicators
        if self.history_scroll_y > 0:
            # Draw up indicator
            pygame.draw.polygon(self.screen, self.HISTORY_SCROLLBAR_HANDLE_COLOR, 
                              [(self.window_width - 11, scrollbar_area_y + 5), 
                               (self.window_width - 15, scrollbar_area_y + 10), 
                               (self.window_width - 7, scrollbar_area_y + 10)])
            
        if self.history_scroll_y < self.history_max_scroll_y:
            # Draw down indicator
            bottom_y = scrollbar_area_y + scrollbar_area_height
            pygame.draw.polygon(self.screen, self.HISTORY_SCROLLBAR_HANDLE_COLOR,
                              [(self.window_width - 11, bottom_y - 5), 
                               (self.window_width - 15, bottom_y - 10),
                               (self.window_width - 7, bottom_y - 10)])

    def _draw_history_buttons(self):
        """Draw floating action buttons for Save/Load/Delete history."""
        button_font = self.fonts.get('bold', pygame.font.Font(None, config.FONT_SIZE - 4))
        
        for button in self.history_buttons:
            # Draw button background
            color = config.CHOICE_HIGHLIGHT_COLOR if button['hover'] else self.HISTORY_USER_BUBBLE_COLOR
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            
            # Draw button border
            border_color = (255, 255, 255) if button['hover'] else (150, 150, 150)
            pygame.draw.rect(self.screen, border_color, button['rect'], width=1, border_radius=5)
            
            # Draw button text
            text_surf = button_font.render(button['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)

    def _draw_confirmation_dialog(self):
        """Draw the confirmation dialog overlay."""
        # Darken the background
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))
        
        # Draw the dialog box
        dialog_width = self.window_width * 0.6
        dialog_height = 150
        dialog_x = (self.window_width - dialog_width) // 2
        dialog_y = (self.window_height - dialog_height) // 2
        
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(self.screen, (40, 40, 60), dialog_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 100), dialog_rect, width=2, border_radius=8)
        
        # Draw the message
        font = self.fonts.get('bold', pygame.font.Font(None, config.FONT_SIZE))
        message_lines = textwrap.wrap(self.confirmation_message, width=40)
        
        line_y = dialog_y + 30
        for line in message_lines:
            text_surf = font.render(line, True, (255, 255, 255))
            text_rect = text_surf.get_rect(centerx=self.window_width // 2, y=line_y)
            self.screen.blit(text_surf, text_rect)
            line_y += font.get_height()
        
        # Draw the buttons
        button_font = self.fonts.get('bold', pygame.font.Font(None, config.FONT_SIZE - 4))
        
        # Draw navigation hint
        hint_text = "Use Left/Right arrows to navigate, Enter to select"
        hint_surf = self.history_font.render(hint_text, True, (180, 180, 180))
        hint_rect = hint_surf.get_rect(centerx=self.window_width // 2, bottom=dialog_y + dialog_height - 10)
        self.screen.blit(hint_surf, hint_rect)
        
        # Draw each button
        for i, button in enumerate(self.confirmation_buttons):
            # Highlight button if selected
            button['hover'] = (i == self.selected_confirmation_button)
            
            # Draw button
            color = config.CHOICE_HIGHLIGHT_COLOR if button['hover'] else (60, 60, 80)
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            pygame.draw.rect(self.screen, (150, 150, 150), button['rect'], width=1, border_radius=5)
            
            # Draw text
            text_surf = button_font.render(button['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)

    def _save_current_history(self):
        """Save the current chat history to a file using the system file dialog."""
        if not self.history_cached_for_history:
            self._show_notification("No history to save")
            return
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"history-{timestamp}.dat"
        
        # Create and hide tkinter root window for dialog
        self._init_tk_root()
        
        try:
            # Open file save dialog
            filepath = filedialog.asksaveasfilename(
                parent=self.tk_root,
                initialdir=self.history_dir,
                initialfile=default_filename,
                defaultextension=".dat",
                filetypes=[("History Files", "*.dat"), ("All Files", "*.*")]
            )
            
            # User cancelled
            if not filepath:
                self._show_notification("Save cancelled")
                return
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # Compress and save the data
            with open(filepath, 'wb') as f:
                serialized_data = pickle.dumps(self.history_cached_for_history)
                compressed_data = zlib.compress(serialized_data, level=9)
                f.write(compressed_data)
                
            self._show_notification(f"History saved to {os.path.basename(filepath)}")
        except Exception as e:
            self._show_notification(f"Error saving history: {e}")
        finally:
            # Clean up tkinter
            if self.tk_root:
                self.tk_root.destroy()
                self.tk_root = None

    def _load_history(self):
        """Load chat history from a file using the system file dialog."""
        # Create and hide tkinter root window for dialog
        self._init_tk_root()
        
        try:
            # Open file open dialog
            filepath = filedialog.askopenfilename(
                parent=self.tk_root,
                initialdir=self.history_dir,
                defaultextension=".dat",
                filetypes=[("History Files", "*.dat"), ("All Files", "*.*")]
            )
            
            # User cancelled
            if not filepath:
                self._show_notification("Load cancelled")
                return
                
            # Load and decompress the data
            with open(filepath, 'rb') as f:
                compressed_data = f.read()
                serialized_data = zlib.decompress(compressed_data)
                loaded_history = pickle.loads(serialized_data)
                
            # Update the history and regenerate bubbles
            self.history_cached_for_history = None  # Reset to force regeneration
            self._generate_history_bubbles(loaded_history)
            self.history_cached_for_history = loaded_history
            
            # Set scroll position to bottom
            self.history_max_scroll_y = max(0, self.history_total_content_height - self.window_height)
            self.history_scroll_y = self.history_max_scroll_y
            
            self._show_notification(f"Loaded history from {os.path.basename(filepath)}")
        except zlib.error:
            self._show_notification("Error: Not a valid compressed history file")
        except pickle.UnpicklingError:
            self._show_notification("Error: File format not recognized")
        except (IOError, EOFError) as e:
            self._show_notification(f"Error reading file: {e}")
        except Exception as e:
            self._show_notification(f"Error loading history: {e}")
        finally:
            # Clean up tkinter
            if self.tk_root:
                self.tk_root.destroy()
                self.tk_root = None
    
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

    def _show_notification(self, message):
        """Show a temporary notification in the history view."""
        # This is a simple implementation - in the future could be enhanced with animation
        notification_font = self.fonts.get('bold', pygame.font.Font(None, config.FONT_SIZE - 2))
        notification_surf = notification_font.render(message, True, (255, 255, 255))
        
        # Create background for notification
        padding = 10
        bg_width = notification_surf.get_width() + padding * 2
        bg_height = notification_surf.get_height() + padding * 2
        bg_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 180))
        
        # Position at center bottom
        x = (self.window_width - bg_width) // 2
        y = self.window_height - bg_height - 50
        
        # Draw on screen
        self.screen.blit(bg_surf, (x, y))
        self.screen.blit(notification_surf, (x + padding, y + padding))
        pygame.display.update()
        
        # Keep notification visible for a moment
        pygame.time.delay(1500)

    def _generate_history_bubbles(self, history: List[Dict]):
        """Generate and cache the message bubbles for the chat history."""
        self.history_rendered_bubbles = []
        self.history_total_content_height = self.HISTORY_BUBBLE_MARGIN_Y
        self.user_turn_indices = []  # Reset navigation indices
        
        bubble_index = 0
        for turn_index, turn in enumerate(history):
            role = turn.get('role')
            parts = turn.get('parts', [])
            if not isinstance(parts, list): 
                parts = [parts]

            full_text = ""
            face_name = "normal"

            # Track user message positions for keyboard navigation
            if role == 'user':
                self.user_turn_indices.append(bubble_index)

            if role == 'user':
                text = parts[0] if parts else "(Empty Input)"
                full_text = f"{text}"
            elif role == 'model':
                try:
                    ai_response_json = parts[0]
                    if not isinstance(ai_response_json, str): 
                        ai_response_json = str(ai_response_json)

                    ai_response_data = json.loads(ai_response_json)
                    if 'segments' in ai_response_data and ai_response_data['segments']:
                        full_text = " ".join([seg.get('text', '') for seg in ai_response_data['segments']])
                        face_name = ai_response_data['segments'][0].get('face', 'normal')
                    elif isinstance(ai_response_data, list) and ai_response_data:
                        full_text = " ".join([seg.get('text', '') for seg in ai_response_data])
                        face_name = ai_response_data[0].get('face', 'normal')
                    else:
                        full_text = "(Error: Unexpected model response format)"

                    # Clean up marker tags
                    full_text = re.sub(r'\[(?:face|sfx):[^\]]+\]', '', full_text).strip()
                except (json.JSONDecodeError, ValidationError, IndexError, KeyError, TypeError) as e:
                    full_text = f"(Error parsing response: {e})"

            if not full_text: 
                continue

            message_lines = full_text.split('\n')
            is_first_line_of_turn = True

            for line_text in message_lines:
                line_text = line_text.strip()
                if not line_text: 
                    continue

                self._create_message_bubble(line_text, role, face_name, is_first_line_of_turn)
                is_first_line_of_turn = False
                bubble_index += 1

        self.history_total_content_height += self.HISTORY_BUBBLE_MARGIN_Y
        # Reset navigation index after rebuilding
        self.current_nav_index = -1

    def _create_message_bubble(self, line_text: str, role: str, face_name: str, is_first_line_of_turn: bool):
        """Create a single message bubble for the history view."""
        max_bubble_width_pixels = int(self.window_width * self.HISTORY_MAX_BUBBLE_WIDTH_RATIO)
        font_char_width = self._get_font_char_width()

        wrap_width_chars = int(max_bubble_width_pixels / font_char_width)
        if wrap_width_chars <= 0: 
            wrap_width_chars = 10

        wrapped_lines = textwrap.wrap(line_text, width=wrap_width_chars,
                                    replace_whitespace=True, drop_whitespace=True)

        if not wrapped_lines:
            return

        text_block_height = len(wrapped_lines) * self.history_line_height
        bubble_height = text_block_height + self.HISTORY_BUBBLE_PADDING * 2

        # Render text and calculate bubble dimensions
        actual_max_line_width, rendered_line_surfaces = self._render_bubble_text_lines(wrapped_lines)
        bubble_width = actual_max_line_width + self.HISTORY_BUBBLE_PADDING * 2

        # Add space for face if needed
        show_face = role == 'model' and is_first_line_of_turn
        bubble_x_offset = 0
        if show_face:
            bubble_width += self.HISTORY_FACE_SIZE + self.HISTORY_BUBBLE_PADDING
            bubble_x_offset = self.HISTORY_FACE_SIZE + self.HISTORY_BUBBLE_PADDING

        # Create bubble surface
        bubble_surf = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
        bubble_color = self.HISTORY_AI_BUBBLE_COLOR if role == 'model' else self.HISTORY_USER_BUBBLE_COLOR
        bubble_surf.fill(bubble_color)

        # Add face if needed
        if show_face:
            self._add_face_to_bubble(bubble_surf, face_name)

        # Add text to bubble
        text_y = self.HISTORY_BUBBLE_PADDING
        text_x = self.HISTORY_BUBBLE_PADDING + bubble_x_offset
        for line_surf in rendered_line_surfaces:
            if line_surf:
                bubble_surf.blit(line_surf, (text_x, text_y))
            text_y += self.history_line_height

        # Position bubble in chat flow
        bubble_rect = bubble_surf.get_rect()
        current_margin = self.HISTORY_BUBBLE_MARGIN_Y * 2 if is_first_line_of_turn else self.HISTORY_BUBBLE_MARGIN_Y
        bubble_rect.top = self.history_total_content_height + current_margin

        # Align bubble based on sender
        if role == 'model':
            bubble_rect.left = self.HISTORY_BUBBLE_MARGIN_X
        else:
            bubble_rect.right = self.window_width - self.HISTORY_BUBBLE_MARGIN_X

        # Store rendered bubble
        self.history_rendered_bubbles.append((bubble_surf, bubble_rect, role))
        self.history_total_content_height = bubble_rect.bottom

    def _get_font_char_width(self) -> float:
        """Get the approximate character width for the history font."""
        try:
            font_char_width = self.history_font.size("A")[0] * 1.2
            if font_char_width <= 0: 
                font_char_width = 10
            return font_char_width
        except (pygame.error, AttributeError):
            return 10

    def _render_bubble_text_lines(self, wrapped_lines: List[str]) -> Tuple[int, List[pygame.Surface]]:
        """Render text lines for a message bubble and return max width and surfaces."""
        actual_max_line_width = 0
        rendered_line_surfaces = []
        for line in wrapped_lines:
            try:
                line_surf = self.history_font.render(line, True, self.HISTORY_TEXT_COLOR)
                rendered_line_surfaces.append(line_surf)
                actual_max_line_width = max(actual_max_line_width, line_surf.get_width())
            except (pygame.error, AttributeError):
                rendered_line_surfaces.append(None)
        return actual_max_line_width, rendered_line_surfaces

    def _add_face_to_bubble(self, bubble_surf: pygame.Surface, face_name: str):
        """Add a character face to the message bubble."""
        face_image = self.active_face_images.get(face_name)
        if not face_image: 
            face_image = self.active_face_images.get("normal")
        if face_image:
            try:
                scaled_face = pygame.transform.smoothscale(face_image, (self.HISTORY_FACE_SIZE, self.HISTORY_FACE_SIZE))
                bubble_surf.blit(scaled_face, (self.HISTORY_BUBBLE_PADDING // 2, self.HISTORY_BUBBLE_PADDING // 2))
            except pygame.error:
                pass  # Skip face if scaling fails
