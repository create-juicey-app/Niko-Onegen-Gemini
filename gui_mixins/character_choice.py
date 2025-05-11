import pygame
import character_manager
from typing import List, Tuple, Optional
import os  # Added for os.path.join

class CharacterChoiceMixin:
    """Mixin class for handling character selection logic."""

    def _initialize_character_choice_state(self):
        """Initializes state variables for character choice."""
        self._character_choice_display_names: List[str] = []
        self._character_choice_ids: List[str] = []
        self._character_choice_face_surfaces: List[Optional[pygame.Surface]] = []

    def _fetch_character_list(self, player_name: str) -> Tuple[List[str], List[str], List[Optional[pygame.Surface]]]:
        """
        Fetches available characters, their display names, and their default face icons.
        Returns a tuple: (list_of_display_names, list_of_character_ids, list_of_face_surfaces).
        """
        available_char_ids = character_manager.get_available_characters()
        char_display_options: List[str] = []
        char_value_options: List[str] = []
        char_face_surfaces: List[Optional[pygame.Surface]] = []

        if available_char_ids:
            for char_id in available_char_ids:
                effective_player_name = player_name if player_name else "Player"
                temp_char = character_manager.load_character_data(char_id, effective_player_name)
                icon_surface: Optional[pygame.Surface] = None
                if temp_char:
                    char_display_options.append(temp_char.displayName)
                    if hasattr(self, 'load_image'):  # Check if self has load_image (from ResourcesMixin)
                        try:
                            icon_filename = temp_char.facePrefix + temp_char.defaultFace + ".png"  # Assuming .png
                            icon_path = os.path.join(temp_char.actualFaceDir, icon_filename)
                            if os.path.exists(icon_path):
                                # Define a small size for the icon in the list, e.g., 40x40
                                # load_image can take a scale_to argument, or we scale later.
                                # For now, load original and scale in draw_multiple_choice.
                                icon_surface = self.load_image(icon_path)
                                if icon_surface:
                                    icon_surface = icon_surface.convert_alpha()
                            else:
                                print(f"Warning: Icon not found for {temp_char.displayName}: {icon_path}")
                        except Exception as e:
                            print(f"Error loading icon for {temp_char.displayName}: {e}")
                else:
                    char_display_options.append(char_id)  # Fallback to ID if load fails
                
                char_value_options.append(char_id)
                char_face_surfaces.append(icon_surface)
        
        return char_display_options, char_value_options, char_face_surfaces

    def setup_character_selection_ui(self, player_name: str, current_char_id: Optional[str] = None):
        """
        Prepares the GUI's choice system for character selection.
        This method should be called when you want to present a character selection screen
        using the standard ChoicesMixin UI.
        """
        display_names, char_ids, face_surfaces = self._fetch_character_list(player_name)
        
        self._character_choice_display_names = display_names
        self._character_choice_ids = char_ids
        self._character_choice_face_surfaces = face_surfaces

        # self.choice_options will now be a list of (text, surface) tuples
        self.choice_options = list(zip(self._character_choice_display_names, self._character_choice_face_surfaces))

        if current_char_id and self._character_choice_ids:  # Check _character_choice_ids for safety
            try:
                self.selected_choice_index = self._character_choice_ids.index(current_char_id)
            except ValueError:
                self.selected_choice_index = 0 
        else:
            self.selected_choice_index = 0

        self.is_choice_active = True

    def get_selected_character_id_from_choice(self, chosen_index: int) -> Optional[str]:
        """
        Retrieves the character ID based on the index chosen from the UI
        set up by setup_character_selection_ui.
        """
        if 0 <= chosen_index < len(self._character_choice_ids):
            return self._character_choice_ids[chosen_index]
        return None

    def get_character_options_for_dropdown(self, player_name: str) -> Tuple[List[str], List[str]]:
        """
        Provides character display names and IDs, suitable for populating a dropdown
        or similar selection widget in the options menu.
        """
        # This method might also need to return icon surfaces if dropdowns support icons.
        # For now, keeping it as is, as it's used by options menu which doesn't show icons yet.
        display_names, char_ids, _ = self._fetch_character_list(player_name)
        return display_names, char_ids
