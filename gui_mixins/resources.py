import pygame
import os
import config
from config import get_available_sfx, get_available_faces

class ResourcesMixin:
    """Mixin class for loading GUI resources like images, sounds, and fonts."""

    def load_image(self, path, scale_to=None):
        if not path or not os.path.exists(path):
             # Use self.options if available, otherwise directly use config
             default_bg = getattr(self, 'options', {}).get("background_image_path", config.DEFAULT_BG_IMG)
             if path != default_bg and os.path.exists(default_bg):
                 try:
                     image = pygame.image.load(default_bg).convert_alpha()
                     # Ensure image is scaled if scale_to is provided
                     if scale_to:
                         image = pygame.transform.smoothscale(image, scale_to)
                     return image
                 except pygame.error as e:
                     print(f"Warning: Failed to load fallback image '{default_bg}': {e}")
                     pass # Failed to load the fallback? Double fail.

             # Create placeholder if primary and fallback fail
             placeholder_size = scale_to if scale_to else (50, 50)
             placeholder = pygame.Surface(placeholder_size)
             placeholder.fill((128, 0, 128)) # The majestic purple square of failure.
             print(f"Warning: Image not found at '{path}', using placeholder.")
             return placeholder
        try:
            image = pygame.image.load(path).convert_alpha()
            if scale_to:
                image = pygame.transform.smoothscale(image, scale_to)
            return image
        except pygame.error as e:
            print(f"Error loading image '{path}': {e}. Using placeholder.")
            placeholder_size = scale_to if scale_to else (50, 50)
            placeholder = pygame.Surface(placeholder_size)
            placeholder.fill((128, 0, 128)) # The majestic purple square of failure.
            return placeholder

    def load_sound(self, path):
        if not path or not os.path.exists(path):
            print(f"Warning: Sound file not found: {path}")
            return None # Can't play silence... or can I?
        if not pygame.mixer or not pygame.mixer.get_init():
            print("Warning: Pygame mixer not initialized, cannot load sound.")
            return None
        try:
            sound = pygame.mixer.Sound(path)
            # Access sfx_volume from self (the GUI instance)
            sound.set_volume(getattr(self, 'sfx_volume', 0.5))
            return sound
        except pygame.error as e:
            print(f"Error loading sound '{path}': {e}")
            return None

    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        # Ensure these attributes exist on self before setting volume
        if hasattr(self, 'default_text_sfx') and self.default_text_sfx:
            self.default_text_sfx.set_volume(self.sfx_volume)
        if hasattr(self, 'robot_text_sfx') and self.robot_text_sfx:
            self.robot_text_sfx.set_volume(self.sfx_volume)
        if hasattr(self, 'other_sfx'):
            for sound in self.other_sfx.values():
                if sound: sound.set_volume(self.sfx_volume)
        # Also update confirm_sfx and glitch_sfx if they exist
        if hasattr(self, 'confirm_sfx') and self.confirm_sfx:
            self.confirm_sfx.set_volume(self.sfx_volume)
        if hasattr(self, 'glitch_sfx'):
             for sound in self.glitch_sfx:
                 if sound: sound.set_volume(self.sfx_volume)


    def _load_fonts(self):
        fonts = {}
        try:
            fonts['regular'] = pygame.font.Font(config.FONT_REGULAR, config.FONT_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Regular font '{config.FONT_REGULAR}' not found or failed to load: {e}. Using default.")
            fonts['regular'] = pygame.font.Font(None, config.FONT_SIZE)

        try:
            fonts['bold'] = pygame.font.Font(config.FONT_BOLD, config.FONT_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Bold font '{config.FONT_BOLD}' not found or failed to load: {e}. Using regular.")
            fonts['bold'] = fonts['regular'] # Fallback to regular

        # Load bold italic, fallback to bold if unavailable or fails
        try:
            if os.path.exists(config.FONT_BOLDITALIC):
                fonts['bold_italic'] = pygame.font.Font(config.FONT_BOLDITALIC, config.FONT_SIZE)
            else:
                print(f"Warning: Bold Italic font '{config.FONT_BOLDITALIC}' not found. Using bold.")
                fonts['bold_italic'] = fonts['bold']
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Bold Italic font '{config.FONT_BOLDITALIC}' failed to load: {e}. Using bold.")
            fonts['bold_italic'] = fonts['bold']

        # Remove 'italic' key if it exists from previous logic (no separate italic font used)
        if 'italic' in fonts:
            del fonts['italic']

        return fonts

    def _load_face_images(self, directory: str, prefix: str):
        faces = {}
        # Create a default placeholder surface first
        placeholder_surface = pygame.Surface((config.FACE_WIDTH, config.FACE_HEIGHT)) # Use config size
        placeholder_surface.fill((255, 0, 255)) # Use Magenta for placeholder

        if not os.path.exists(directory):
            print(f"Warning: Face directory not found: {directory}")
            # Ensure 'normal' key exists even if directory is missing
            faces['normal'] = placeholder_surface
            return faces
        try:
            face_list = get_available_faces(directory, prefix)
            for face_name in face_list:
                # Strip prefix if get_available_faces includes it (ensure consistency)
                clean_face_name = face_name.replace(prefix, '', 1) if face_name.startswith(prefix) else face_name
                filename = f"{prefix}{clean_face_name}.png" # Reconstruct filename
                path = os.path.join(directory, filename)
                # Load image without scaling here, scaling happens during rendering if needed
                loaded_image = self.load_image(path, scale_to=(config.FACE_WIDTH, config.FACE_HEIGHT))
                # Use the clean name (without prefix) as the key
                faces[clean_face_name] = loaded_image
        except Exception as e:
            print(f"Error loading faces from {directory}: {e}")
            pass # Continue even if some faces fail to load

        # Check if 'normal' face was loaded, if not, add the placeholder
        if 'normal' not in faces:
             print(f"Warning: '{prefix}normal.png' face not found or failed to load in {directory}. Using placeholder.")
             faces['normal'] = placeholder_surface

        # If after all that, faces dict is STILL empty, add at least 'normal' placeholder
        if not faces:
             faces['normal'] = placeholder_surface

        return faces

    def _load_other_sfx(self):
        sfx_dict = {}
        required_sfx = ["menu_decision", "menu_cursor", "menu_cancel", "menu_buzzer", "glitch1", "glitch2", "glitch3"]
        sfx_names = get_available_sfx(config.SFX_DIR)

        found_required = {name: False for name in required_sfx}

        for name in sfx_names:
            found_path = None
            # Check common audio extensions
            for ext in ['.wav', '.ogg', '.mp3']:
                path = os.path.join(config.SFX_DIR, f"{name}{ext}")
                if os.path.exists(path):
                    found_path = path
                    break

            if found_path:
                sound = self.load_sound(found_path)
                if sound:
                    sfx_dict[name] = sound
                    if name in found_required:
                        found_required[name] = True
                else:
                    print(f"Warning: Failed to load sound file '{found_path}' for SFX '{name}'.")
            else:
                 print(f"Warning: SFX file for '{name}' not found in '{config.SFX_DIR}' with supported extensions.")

        for name, found in found_required.items():
            if not found:
                print(f"Warning: Required SFX '{name}' was not found or failed to load.")

        return sfx_dict

    def play_confirm_sound(self):
        # Access confirm_sfx from self
        confirm_sfx = getattr(self, 'confirm_sfx', None)
        if confirm_sfx:
            confirm_sfx.play()
        else:
            print("Debug: Confirm SFX not available or not loaded.")
            pass # Sound not loaded or available

    def play_sound(self, name: str):
        # Access other_sfx from self
        other_sfx = getattr(self, 'other_sfx', {})
        sound = other_sfx.get(name)
        if sound:
            sound.play()
        else:
            print(f"Debug: SFX '{name}' not found in other_sfx.")
            pass # Sound not found
