# ///////////////////////////////////////////////////////
# No copyright! Open Source!
# Created by JuiceyDev (create-juicey-dev)
# ///////////////////////////////////////////////////////
# This module defines the GUI class responsible for rendering the visual interface,
# handling user input (keyboard, mouse), managing dialogue display (text animation,
# faces, sounds), choices, input fields, and visual effects like window dragging
# and a forced quit sequence using Pygame.

import pygame
import os
import config
import textwrap
import re
import time
import math
import random
from typing import Literal
from config import NikoResponse, TextSpeed, TEXT_SPEED_MAP, get_available_sfx, get_available_faces
import platform
if platform.system() == "Windows":
    import ctypes

class GUI:
    """Handles the graphical user interface, rendering, and events."""

    def __init__(self, initial_options):
        # Let the variable hoarding begin!
        self.options = initial_options
        self.sfx_volume = initial_options.get("sfx_volume", 0.5)

        pygame.init()
        pygame.font.init()
        pygame.mixer.init() # Gotta make some noise

        try:
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
        except pygame.error as e:
            # Fine, be that way. 800x600 it is.
            self.width = 800
            self.height = 600

        try:
            pygame.display.init()
            info = pygame.display.Info()
            screen_width = info.current_w
            screen_height = info.current_h
        except pygame.error as e:
            screen_width = 800
            screen_height = 600

        self.window_width = config.TEXTBOX_WIDTH + 40
        self.window_height = config.TEXTBOX_HEIGHT + config.INPUT_BOX_HEIGHT + 150

        pos_x = (screen_width - self.window_width) // 2
        pos_y = screen_height - self.window_height - 80
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_x},{pos_y}" # Magic window positioning spell

        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.NOFRAME)
        pygame.display.set_caption("Chat with Niko")
        self.window_x = pos_x
        self.window_y = pos_y

        self.textbox_x = (self.window_width - config.TEXTBOX_WIDTH) // 2
        self.textbox_y = 20

        initial_input_box_width = config.TEXTBOX_WIDTH - 40
        self.input_box_x = self.textbox_x + (config.TEXTBOX_WIDTH - initial_input_box_width) // 2
        self.input_box_y = self.textbox_y + config.TEXTBOX_HEIGHT + 10
        initial_input_box_height = config.INPUT_BOX_HEIGHT

        self.choice_bg_color = (0, 0, 0, 180)
        self.choice_padding = 15

        self.clock = pygame.time.Clock()
        self.running = True

        self.bg_img_original = self.load_image(self.options.get("background_image_path", config.DEFAULT_BG_IMG))
        self.textbox_img = self.load_image(config.TEXTBOX_IMG)
        self.arrow_img = self.load_image(config.ARROW_IMG)
        self.fonts = self._load_fonts()

        self.niko_face_images = self._load_face_images(config.FACES_DIR, "niko_")
        self.twm_face_images = self._load_face_images(config.TWM_FACES_DIR, "en_")

        self.default_text_sfx = self.load_sound(config.TEXT_SFX_PATH)
        self.robot_text_sfx = self.load_sound(config.ROBOT_SFX_PATH)
        self.other_sfx = self._load_other_sfx()
        self.confirm_sfx = self.other_sfx.get("menu_decision")
        self.glitch_sfx = [
            self.other_sfx.get("glitch1"),
            self.other_sfx.get("glitch2"),
            self.other_sfx.get("glitch3")
        ]
        self.glitch_sfx = [sfx for sfx in self.glitch_sfx if sfx]

        self.active_text_sfx = self.default_text_sfx
        self.active_face_images = self.niko_face_images
        self.current_face_image = self.active_face_images.get("normal")

        self._sfx_play_toggle = False
        self._played_sfx_markers = set()

        self.current_text = ""
        self.current_char_index = 0
        self.text_animation_timer = 0.0
        self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(self.options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
        self.current_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        self.use_bold = False
        self.use_italic = False

        self.is_animating = False
        self.draw_arrow = False
        self.arrow_blink_timer = 0.0
        self.arrow_visible = True
        self.arrow_base_y = self.textbox_y + config.ARROW_OFFSET_Y
        self.arrow_offset_y = 0

        self.rendered_lines = []
        self.total_chars_to_render = 0

        self.is_paused = False
        self.pause_timer = 0.0
        self.current_pause_duration = 0.0 # Shhh, quiet time.

        self.is_input_active = False
        self.user_input_text = ""
        self.input_cursor_pos = 0
        self.input_rect = pygame.Rect(
            self.input_box_x,
            self.input_box_y,
            initial_input_box_width,
            initial_input_box_height
        )
        self.input_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        self.input_cursor_visible = False
        self.input_cursor_timer = 0.0 # Blink... blink... blink...

        self.is_choice_active = False
        self.choice_options = []
        self.choice_rects = []
        self.selected_choice_index = 0 
        self.choice_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        self.choice_color = (230, 230, 230)
        self.choice_highlight_color = (255, 255, 100)
        self.choice_spacing = self.choice_font.get_height() + 10

        self.is_menu_active = False
        self.menu_overlay_color = (0, 0, 0, 150)
        self.is_history_active = False

        self.dragging = False 
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.face_marker_regex = re.compile(r'\[face:([a-zA-Z0-9_]+)\]') # Regex my beloved nemesis
        self.sfx_marker_regex = re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]')

        self.is_forced_quitting = False # if you ever trigger that fuck you
        self.forced_quit_timer = 0.0
        self.forced_quit_glitch_index = 0
        self.forced_quit_glitch_delay = 0.6
        self.forced_quit_shake_start_delay = 0.2
        self.forced_quit_duration = self.forced_quit_glitch_delay * len(self.glitch_sfx) + 1.0

        self.shake_timer = 0.0
        self.shake_intensity = 0.0
        self.max_shake_intensity = 15
        self.shake_offset_x = 0
        self.shake_offset_y = 0
        self.shake_ramp_up_time = self.forced_quit_duration * 0.7

        self.random_pixel_overlay = None # Sprinkle some chaos pixels
        self.current_random_pixel_rate = 0.0
        self.max_random_pixel_rate = (self.window_width * self.window_height) / (self.forced_quit_duration * 0.8)
        self.random_pixel_ramp_up_time = self.forced_quit_duration * 0.6
        # that was a lot right? 
        self.hwnd = None
        if platform.system() == "Windows":
            try:
                pygame.display.init()
                self.hwnd = pygame.display.get_wm_info()["window"] # Windows witchcraft
            except (pygame.error, KeyError) as e:
                pass # Oh well, no magic today.

    def start_forced_quit(self):
        if self.is_forced_quitting: return # Already panicking, can't panic more!

        self.is_forced_quitting = True
        self.forced_quit_timer = 0.0
        self.forced_quit_glitch_index = 0
        self.shake_timer = 0.0
        self.shake_intensity = 0.0
        self.shake_offset_x = 0
        self.shake_offset_y = 0

        self.current_random_pixel_rate = 0.0
        self.random_pixel_overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        self.random_pixel_overlay.fill((0, 0, 0, 0))

    def load_image(self, path, scale_to=None):
        if not path or not os.path.exists(path):
             if path != config.DEFAULT_BG_IMG and os.path.exists(config.DEFAULT_BG_IMG):
                 try:
                     image = pygame.image.load(config.DEFAULT_BG_IMG).convert_alpha()
                     return image
                 except pygame.error as e:
                     pass # Failed to load the fallback? Double fail.

             placeholder = pygame.Surface(scale_to if scale_to else (50, 50))
             placeholder.fill((128, 0, 128)) # The majestic purple square of failure.
             return placeholder
        try:
            image = pygame.image.load(path).convert_alpha()
            return image
        except pygame.error as e:
            placeholder = pygame.Surface(scale_to if scale_to else (50, 50))
            placeholder.fill((128, 0, 128)) # The majestic purple square of failure.
            return placeholder

    def load_sound(self, path):
        if not path or not os.path.exists(path):
            return None # Can't play silence... or can I?
        if not pygame.mixer or not pygame.mixer.get_init():
            return None
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.sfx_volume)
            return sound
        except pygame.error as e:
            return None

    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        if self.default_text_sfx: self.default_text_sfx.set_volume(self.sfx_volume)
        if self.robot_text_sfx: self.robot_text_sfx.set_volume(self.sfx_volume)
        for sound in self.other_sfx.values():
            if sound: sound.set_volume(self.sfx_volume)

    def _load_fonts(self):
        fonts = {}
        try:
            fonts['regular'] = pygame.font.Font(config.FONT_REGULAR, config.FONT_SIZE)
            fonts['bold'] = pygame.font.Font(config.FONT_BOLD, config.FONT_SIZE)
            if os.path.exists(config.FONT_BOLDITALIC):
                fonts['bold_italic'] = pygame.font.Font(config.FONT_BOLDITALIC, config.FONT_SIZE)
            else:
                fonts['bold_italic'] = fonts['bold'] 
        except pygame.error as e:
            # Font loading failed?
            default_font = pygame.font.Font(None, config.FONT_SIZE)
            fonts['regular'] = fonts.get('regular', default_font)
            fonts['bold'] = fonts.get('bold', default_font)
            fonts['bold_italic'] = fonts.get('bold_italic', fonts.get('bold', default_font))
        if 'italic' in fonts:
            del fonts['italic']
        return fonts

    def _load_face_images(self, directory: str, prefix: str):
        faces = {}
        # Create a default placeholder surface first
        placeholder_surface = pygame.Surface((50, 50))
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
                clean_face_name = face_name.replace(prefix, '', 1)
                filename = f"{prefix}{clean_face_name}.png" # Reconstruct filename
                path = os.path.join(directory, filename)
                loaded_image = self.load_image(path)
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
            for ext in ['.wav', '.ogg', '.mp3']: # Gotta catch 'em all 
                path = os.path.join(config.SFX_DIR, f"{name}{ext}")
                if os.path.exists(path):
                    found_path = path
                    break
            # wanted this to be really customizable so i did this godawful code 
            if found_path:
                sound = self.load_sound(found_path)
                if sound:
                    sfx_dict[name] = sound
                    if name in found_required:
                        found_required[name] = True
            else:
                 pass # File not found

        for name, found in found_required.items():
            if not found:
                pass # Missing required sounds? Eh, it'll probably be fine.

        return sfx_dict

    def set_active_sfx(self, sfx_type: Literal["default", "robot"]):
        if sfx_type == "robot" and self.robot_text_sfx:
            self.active_text_sfx = self.robot_text_sfx
        else:
            self.active_text_sfx = self.default_text_sfx

    def set_active_face_set(self, face_set_type: Literal["niko", "twm"]):
        if face_set_type == "twm":
            self.active_face_images = self.twm_face_images
        else:
            self.active_face_images = self.niko_face_images

        # Ensure 'normal' exists in the chosen set, fallback to placeholder if needed
        if 'normal' not in self.active_face_images:
             print(f"Warning: 'normal' face missing from active set '{face_set_type}'. Creating placeholder.")
             placeholder_surface = pygame.Surface((50, 50))
             placeholder_surface.fill((255, 0, 255)) # Magenta placeholder
             self.active_face_images['normal'] = placeholder_surface

        self.current_face_image = self.active_face_images.get("normal")

        # Final fallback if even 'normal' failed somehow
        if not self.current_face_image:
             if self.active_face_images:
                 # Get the first available face as a last resort
                 self.current_face_image = next(iter(self.active_face_images.values()), None)
                 if self.current_face_image is None: # If dict was empty after all
                      placeholder_surface = pygame.Surface((50, 50))
                      placeholder_surface.fill((255, 0, 255))
                      self.current_face_image = placeholder_surface
             else: # Should not happen if load_face_images ensures 'normal'
                 placeholder_surface = pygame.Surface((50, 50))
                 placeholder_surface.fill((255, 0, 255))
                 self.current_face_image = placeholder_surface

    def set_dialogue(self, dialogue_data: NikoResponse):
        self.is_input_active = False
        self.is_choice_active = False
        self.user_input_text = ""
        self.input_cursor_pos = 0

        if not dialogue_data:
            self.current_text = "..."
            self.current_face_image = self.active_face_images.get("sad", self.active_face_images.get("normal"))
            self.current_text_speed_ms = config.TEXT_SPEED_MAP["normal"]
            self.use_bold = False
            self.use_italic = False
        else:
            self.current_text = dialogue_data.text
            face_name = dialogue_data.face
            self.current_face_image = self.active_face_images.get(face_name)
            if not self.current_face_image:
                 self.current_face_image = self.active_face_images.get("normal")
                 if not self.current_face_image:
                      pass

            ai_speed = dialogue_data.speed
            default_speed_key = self.options.get("default_text_speed", "normal")
            self.current_text_speed_ms = config.TEXT_SPEED_MAP.get(ai_speed, config.TEXT_SPEED_MAP[default_speed_key])

            self.use_bold = dialogue_data.bold
            self.use_italic = dialogue_data.italic

        if self.use_bold and self.use_italic and 'bold_italic' in self.fonts:
            self.current_font = self.fonts['bold_italic']
        elif self.use_bold:
            self.current_font = self.fonts.get('bold', self.fonts['regular'])
        elif self.use_italic and 'bold_italic' in self.fonts:
            self.current_font = self.fonts['bold_italic']
        else:
            self.current_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))

        self.current_char_index = 0
        self.text_animation_timer = 0.0
        self.is_animating = True
        self.draw_arrow = False
        self._sfx_play_toggle = False
        self.is_paused = False
        self.pause_timer = 0.0
        self.current_pause_duration = 0.0
        self._played_sfx_markers.clear()

        self._wrap_text()

    def _wrap_text(self):
        self.rendered_lines = []
        font_for_wrapping = self.current_font
        current_text_stripped = self.current_text.strip()
        if not current_text_stripped or not font_for_wrapping:
            self.total_chars_to_render = 0 # Nothing to wrap? My job here is done.
            return

        max_width_pixels = config.TEXT_WRAP_WIDTH
        marker_regex_str = r'(\[face:[a-zA-Z0-9_]+\]|\[sfx:[a-zA-Z0-9_]+\\])' # Regex more like regex less 
        marker_regex = re.compile(marker_regex_str)
        word_splitter_regex = re.compile(rf'(\s+|{marker_regex_str})') # Split ALL the things!
        parts = word_splitter_regex.split(current_text_stripped)
        parts = [p for p in parts if p] # Clean up the mess.

        wrapped_paragraphs = []
        current_line = ""
        current_line_width = 0
        plain_char_count = 0

        for part in parts:
            is_face_marker = self.face_marker_regex.match(part)
            is_sfx_marker = self.sfx_marker_regex.match(part)
            is_marker = is_face_marker or is_sfx_marker
            is_space = part.isspace()

            if is_marker:
                current_line += part
                continue
            elif is_space:
                try:
                    space_width = font_for_wrapping.size(" ")[0] if current_line else 0
                except (pygame.error, AttributeError): space_width = 0

                if current_line_width + space_width <= max_width_pixels:
                    current_line += part
                    current_line_width += space_width
                    plain_char_count += len(part)
                else:
                    wrapped_paragraphs.append(current_line)
                    current_line = part
                    current_line_width = space_width
                    plain_char_count += len(part)
            else:
                word = part
                plain_word = word
                try:
                    word_surface = font_for_wrapping.render(plain_word, True, (0,0,0))
                    word_width = word_surface.get_width()
                    space_width = 0
                    if current_line and not current_line.endswith(" ") and not is_marker:
                         last_char = current_line[-1] if current_line else ''
                         if not self.face_marker_regex.search(current_line[-20:]) and not self.sfx_marker_regex.search(current_line[-20:]):
                              if last_char not in ['(', '[']:
                                   space_width = font_for_wrapping.size(" ")[0]

                except (pygame.error, AttributeError) as e:
                     continue

                if current_line_width + space_width + word_width <= max_width_pixels:
                    if current_line and space_width > 0:
                         current_line += " "
                         current_line_width += space_width
                         plain_char_count += 1
                    current_line += word
                    current_line_width += word_width
                    plain_char_count += len(plain_word)
                else:
                    wrapped_paragraphs.append(current_line)
                    current_line = word
                    current_line_width = word_width
                    plain_char_count_in_word = len(plain_word)
                    plain_char_count += plain_char_count_in_word


        wrapped_paragraphs.append(current_line)

        final_lines = []
        space_before_marker_regex = re.compile(r'\s+(\[(?:face|sfx):[^\]]+\])')
        # HATE. LET ME TELL YOU HOW I HATE. # I feel you. Regex is pain. But also power? Maybe?

        for line in wrapped_paragraphs:
            cleaned_line = space_before_marker_regex.sub(r'\1', line) # More cleaning! So much cleaning.
            stripped_line = cleaned_line.strip()
            if stripped_line:
                final_lines.append(stripped_line)

        self.rendered_lines = final_lines

        accurate_plain_char_count = 0
        for line in self.rendered_lines:
             line_without_markers = marker_regex.sub('', line)
             accurate_plain_char_count += len(line_without_markers)

        self.total_chars_to_render = accurate_plain_char_count

    def _check_pause_trigger_at_index(self, current_plain_index: int) -> float:
        if current_plain_index <= 0:
            return 0.0

        cumulative_plain_chars = 0
        segment_regex = re.compile(r'(\[face:[a-zA-Z0-9_]+\])|(\[sfx:[a-zA-Z0-9_]+\])|(\.\.\.|[.,!?])|([^\[.,!?]+(?:\[(?![fF][aA][cC][eE]:|sS][fF][xX]:)[^\[]*)*)')
        # ITS REGEXXXXXXXXXXXXXXXXXXXXXXXXXX AHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH YOUUUUUUUUUUUU FUCKING BIIIIIIIIITCCCCCCCCCCCCHHHHHHHHHHHH
        # RAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH 
        for line in self.rendered_lines:
            for match in segment_regex.finditer(line):
                face_marker_match = match.group(1)
                sfx_marker_match = match.group(2)
                punctuation_segment = match.group(3)
                text_segment = match.group(4)

                if face_marker_match:
                    continue

                elif sfx_marker_match:
                    if cumulative_plain_chars == current_plain_index:
                        return config.SFX_PAUSE_DURATION

                elif punctuation_segment:
                    segment_len = len(punctuation_segment)
                    start_plain_index = cumulative_plain_chars
                    end_plain_index = cumulative_plain_chars + segment_len

                    if current_plain_index == end_plain_index:
                        if punctuation_segment == "...":
                            return config.ELLIPSIS_PAUSE_DURATION
                        elif punctuation_segment == ",":
                            return config.COMMA_PAUSE_DURATION
                        elif punctuation_segment == ".":
                            return config.PERIOD_PAUSE_DURATION
                        elif punctuation_segment == "?":
                            return config.QUESTION_PAUSE_DURATION
                        elif punctuation_segment == "!":
                            return config.EXCLAMATION_PAUSE_DURATION

                    if start_plain_index < current_plain_index < end_plain_index:
                         return 0.0

                    cumulative_plain_chars += segment_len

                elif text_segment:
                    plain_text_segment = text_segment
                    segment_len = len(plain_text_segment)
                    start_plain_index = cumulative_plain_chars
                    end_plain_index = cumulative_plain_chars + segment_len

                    if start_plain_index < current_plain_index <= end_plain_index:
                        return 0.0

                    cumulative_plain_chars += segment_len

            if cumulative_plain_chars >= current_plain_index:
                 break

        return 0.0
        # why not 

    def update(self, dt):
        if self.is_history_active:
            return # History is boring, let's stay in the present.

        if self.is_forced_quitting:
            self.forced_quit_timer += dt

            random_pixel_ramp_progress = min(1.0, self.forced_quit_timer / self.random_pixel_ramp_up_time)
            self.current_random_pixel_rate = self.max_random_pixel_rate * random_pixel_ramp_progress

            next_glitch_time = self.forced_quit_glitch_index * self.forced_quit_glitch_delay
            if self.glitch_sfx and self.forced_quit_glitch_index < len(self.glitch_sfx) and self.forced_quit_timer >= next_glitch_time:
                self.glitch_sfx[self.forced_quit_glitch_index].play() # Play the scary noises!
                self.forced_quit_glitch_index += 1

            if self.forced_quit_timer >= self.forced_quit_shake_start_delay:
                self.shake_timer += dt
                ramp_progress = min(1.0, self.shake_timer / self.shake_ramp_up_time)
                self.shake_intensity = self.max_shake_intensity * ramp_progress

                self.shake_offset_x = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
                self.shake_offset_y = random.randint(-int(self.shake_intensity), int(self.shake_intensity))

                if self.is_animating:
                    self.is_animating = False
                    self.draw_arrow = False
                    if self.active_text_sfx and self.active_text_sfx.get_num_channels() > 0:
                        self.active_text_sfx.stop()
            else:
                self.shake_offset_x = 0
                self.shake_offset_y = 0

            if self.forced_quit_timer >= self.forced_quit_duration:
                self.running = False # Time to go home
                return

        if self.is_paused and not self.is_forced_quitting:
            self.pause_timer += dt
            if self.pause_timer >= self.current_pause_duration:
                self.is_paused = False # Pause over! Back to the chaos.
                self.pause_timer = 0.0
                self.current_pause_duration = 0.0
            else:
                if self.active_text_sfx and self.active_text_sfx.get_num_channels() > 0:
                    self.active_text_sfx.stop() # Silence the text! It's pause time.
                return

        if self.is_animating:
            if self.current_text_speed_ms == config.TextSpeed.INSTANT.value:
                if self.total_chars_to_render > 0 and self.current_char_index == 0 and self.active_text_sfx:
                     if not (self.is_forced_quitting and self.forced_quit_timer >= self.forced_quit_shake_start_delay):
                          self.active_text_sfx.play()
                self.current_char_index = self.total_chars_to_render
                self.is_animating = False
                if not self.is_forced_quitting:
                    self.draw_arrow = True
            elif self.current_char_index < self.total_chars_to_render:
                self.text_animation_timer += dt * 1000 # Time marches on... character by character.
                target_char_index = int(self.text_animation_timer / self.current_text_speed_ms)

                if target_char_index > self.current_char_index:
                    new_char_index = min(target_char_index, self.total_chars_to_render)
                    num_new_chars = new_char_index - self.current_char_index

                    play_sound_this_frame = False
                    can_play_sound = not (self.is_forced_quitting and self.forced_quit_timer >= self.forced_quit_shake_start_delay)

                    if num_new_chars > 0 and can_play_sound:
                        for i in range(num_new_chars):
                            self._sfx_play_toggle = not self._sfx_play_toggle
                            if self._sfx_play_toggle:
                                play_sound_this_frame = True
                                break
                    if play_sound_this_frame and self.active_text_sfx:
                        self.active_text_sfx.play() # Blip blop, text go brrr.

                    self.current_char_index = new_char_index

                    if not self.is_forced_quitting:
                        pause_duration = self._check_pause_trigger_at_index(self.current_char_index)
                        if pause_duration > 0:
                            self.is_paused = True
                            self.current_pause_duration = pause_duration
                            self.pause_timer = 0.0
                            if self.active_text_sfx and self.active_text_sfx.get_num_channels() > 0:
                                self.active_text_sfx.stop()

            else:
                self.is_animating = False # Animation complete. 
                if not self.is_forced_quitting:
                    self.draw_arrow = True # Show arrow!
                self.text_animation_timer = 0.0

        if self.draw_arrow and not self.is_input_active and not self.is_paused and not self.is_choice_active and not self.is_forced_quitting:
            self.arrow_blink_timer += dt
            if self.arrow_blink_timer > 0.25:
                self.arrow_visible = not self.arrow_visible
                self.arrow_blink_timer = 0.0
            bob_offset = (math.sin(pygame.time.get_ticks() * 0.005) * 2)
            self.arrow_offset_y = bob_offset
        else:
            self.arrow_visible = False # No arrow for you!

        if self.is_input_active and not self.is_forced_quitting:
            self.input_cursor_timer += dt
            if self.input_cursor_timer >= 0.5:
                self.input_cursor_visible = not self.input_cursor_visible
                self.input_cursor_timer = 0.0
        else:
            self.input_cursor_visible = False # Stop blinking!


    def render_background_and_overlay(self):
        target_surface = self.screen

        if self.is_forced_quitting:
            pass
        elif self.bg_img_original:
            target_surface.fill((0, 0, 0))
            bg_rect = self.bg_img_original.get_rect(center=(self.window_width // 2, self.window_height // 2))
            target_surface.blit(self.bg_img_original, bg_rect)
        else:
            target_surface.fill((0, 0, 0))

        if self.is_menu_active and not self.is_forced_quitting:
            overlay_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
            overlay_surface.fill(self.menu_overlay_color)
            target_surface.blit(overlay_surface, (0, 0))

    def render(self):
        if self.is_history_active:
            return # Still boring.

        dt = self.clock.get_time() / 1000.0 # she Deltas my time till i-

        if self.is_forced_quitting:
            self.screen.fill((0, 0, 0)) # The void consumes all.

            ui_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
            ui_surface.fill((0, 0, 0, 0)) # this doesn't work i tried 

            if self.bg_img_original:
                bg_rect = self.bg_img_original.get_rect(center=(self.window_width // 2, self.window_height // 2))
                ui_surface.blit(self.bg_img_original, bg_rect)
            else:
                ui_surface.fill((0, 0, 0))

            textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
            ui_surface.blit(self.textbox_img, textbox_rect)

            if self.current_face_image:
                face_x = self.textbox_x + config.FACE_OFFSET_X
                face_y = self.textbox_y + config.FACE_OFFSET_Y
                ui_surface.blit(self.current_face_image, (face_x, face_y))

            self.draw_animated_text(target_surface=ui_surface) # Draw the text, even amidst the chaos.

            self.screen.blit(ui_surface, (self.shake_offset_x, self.shake_offset_y)) # Shake shake shake!

            if self.random_pixel_overlay:
                num_random_pixels = int(self.current_random_pixel_rate * dt)
                for _ in range(num_random_pixels): # Pixel party!
                    try:
                        x = random.randint(0, self.window_width - 1)
                        y = random.randint(0, self.window_height - 1)
                        random_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                        self.random_pixel_overlay.set_at((x, y), random_color)
                    except IndexError:
                        pass # fuck you
                    except pygame.error as e:
                        pass # Pygame is unhappy. Shocker.

                self.screen.blit(self.random_pixel_overlay, (0, 0)) # Slap the pixel chaos onto the screen.

        else:
            render_surface = self.screen

            if self.bg_img_original:
                render_surface.fill((0, 0, 0))
                bg_rect = self.bg_img_original.get_rect(center=(self.window_width // 2, self.window_height // 2))
                render_surface.blit(self.bg_img_original, bg_rect)
            else:
                render_surface.fill((0, 0, 0))

            if self.is_menu_active:
                overlay_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay_surface.fill(self.menu_overlay_color)
                render_surface.blit(overlay_surface, (0, 0))

            textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
            render_surface.blit(self.textbox_img, textbox_rect)

            if self.current_face_image:
                face_x = self.textbox_x + config.FACE_OFFSET_X
                face_y = self.textbox_y + config.FACE_OFFSET_Y
                render_surface.blit(self.current_face_image, (face_x, face_y))

            self.draw_animated_text(target_surface=render_surface)

            if self.draw_arrow and self.arrow_visible:
                arrow_x = self.textbox_x + config.ARROW_OFFSET_X
                arrow_y = self.arrow_base_y + self.arrow_offset_y
                arrow_rect = self.arrow_img.get_rect(centerx=arrow_x, top=arrow_y)
                render_surface.blit(self.arrow_img, arrow_rect)

            if self.is_input_active:
                input_bg_surface = pygame.Surface(self.input_rect.size, pygame.SRCALPHA)
                input_bg_surface.fill(config.INPUT_BOX_BG_COLOR)
                render_surface.blit(input_bg_surface, self.input_rect.topleft)
                pygame.draw.rect(render_surface, config.INPUT_BOX_BORDER_COLOR, self.input_rect, config.INPUT_BOX_BORDER_WIDTH)

                max_text_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                wrapped_text_lines, line_start_indices = self._wrap_input_text(self.user_input_text, max_text_width) # Wrap ALL the text!

                cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING
                cursor_render_y = self.input_rect.top + config.INPUT_BOX_PADDING
                found_cursor_line = False
                line_y = self.input_rect.top + config.INPUT_BOX_PADDING

                for i, line_text in enumerate(wrapped_text_lines):
                    line_start_char_index = line_start_indices[i]
                    line_end_char_index = line_start_indices[i+1] if i + 1 < len(line_start_indices) else len(self.user_input_text)

                    if line_y + self.input_font.get_height() > self.input_rect.bottom - config.INPUT_BOX_PADDING:
                        break

                    try:
                        line_surface = self.input_font.render(line_text, True, config.INPUT_BOX_TEXT_COLOR[:3])
                        line_rect = line_surface.get_rect(topleft=(self.input_rect.left + config.INPUT_BOX_PADDING, line_y))
                        render_surface.blit(line_surface, line_rect)

                        if not found_cursor_line and line_start_char_index <= self.input_cursor_pos <= line_end_char_index:
                            cursor_char_pos_in_line = self.input_cursor_pos - line_start_char_index
                            text_before_cursor_on_line = line_text[:cursor_char_pos_in_line]
                            cursor_offset_x = self.input_font.size(text_before_cursor_on_line)[0]

                            cursor_render_x = line_rect.left + cursor_offset_x + 1
                            cursor_render_y = line_rect.top
                            found_cursor_line = True

                        line_y += self.input_font.get_height()

                    except (pygame.error, AttributeError):
                        line_y += self.input_font.get_height()

                if not found_cursor_line and self.input_cursor_pos == len(self.user_input_text):
                     if wrapped_text_lines:
                         last_line_text = wrapped_text_lines[-1]
                         cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING + self.input_font.size(last_line_text)[0] + 1
                         cursor_render_y = line_y - self.input_font.get_height()
                     else:
                         cursor_render_x = self.input_rect.left + config.INPUT_BOX_PADDING + 1
                         cursor_render_y = self.input_rect.top + config.INPUT_BOX_PADDING

                if self.input_cursor_visible:
                    cursor_height = self.input_font.get_height()
                    cursor_rect = pygame.Rect(cursor_render_x, cursor_render_y, 2, cursor_height)
                    if cursor_rect.right < self.input_rect.right - config.INPUT_BOX_PADDING // 2:
                         pygame.draw.rect(render_surface, config.INPUT_BOX_TEXT_COLOR[:3], cursor_rect) # Draw the blinky cursor line.
                         # this is broken idc

            if self.is_choice_active:
                self.draw_multiple_choice(target_surface=render_surface) # Show them the choices!

        pygame.display.flip() # im not crying, you are

    def draw_multiple_choice(self, target_surface=None):
        if target_surface is None:
            target_surface = self.screen

        if not self.choice_options:
            self.choice_rects = []
            return

        self.choice_rects = []

        max_text_width = 0
        total_text_height = 0
        rendered_surfaces = []

        for option_text in self.choice_options:
            try:
                text_surface = self.choice_font.render(option_text, True, self.choice_color)
                rendered_surfaces.append(text_surface)
                max_text_width = max(max_text_width, text_surface.get_width())
                total_text_height += text_surface.get_height()
            except (pygame.error, AttributeError):
                 rendered_surfaces.append(None)
                 continue

        total_text_height += self.choice_spacing * (len(self.choice_options) - 1)

        bg_width = max_text_width + self.choice_padding * 2
        bg_height = total_text_height + self.choice_padding * 2

        bg_x = (self.window_width - bg_width) // 2
        bg_y = (self.window_height - bg_height) // 2

        bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg_surface.fill(self.choice_bg_color)
        target_surface.blit(bg_surface, (bg_x, bg_y))

        current_y = bg_y + self.choice_padding
        for i, text_surface in enumerate(rendered_surfaces):
            if text_surface is None:
                current_y += self.choice_spacing
                self.choice_rects.append(pygame.Rect(0,0,0,0))
                continue

            option_text = self.choice_options[i]
            is_selected = (i == self.selected_choice_index)
            color = self.choice_highlight_color if is_selected else self.choice_color

            final_surface = text_surface
            if is_selected:
                try:
                    final_surface = self.choice_font.render(option_text, True, color)
                except (pygame.error, AttributeError):
                    pass

            text_rect = final_surface.get_rect(centerx=bg_x + bg_width // 2, top=current_y)
            target_surface.blit(final_surface, text_rect)
            self.choice_rects.append(text_rect)
            current_y += text_surface.get_height() + self.choice_spacing


    def draw_animated_text(self, target_surface=None):
        if target_surface is None:
            target_surface = self.screen

        text_x = self.textbox_x + config.TEXT_OFFSET_X
        text_y = self.textbox_y + config.TEXT_OFFSET_Y
        plain_chars_drawn_total = 0
        current_render_x = text_x

        segment_font = self.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE))
        if self.use_bold and self.use_italic and 'bold_italic' in self.fonts:
            segment_font = self.fonts['bold_italic']
        elif self.use_bold:
            segment_font = self.fonts.get('bold', self.fonts['regular'])
        elif self.use_italic and 'bold_italic' in self.fonts:
            segment_font = self.fonts['bold_italic']

        segment_regex = re.compile(
            r'(\[face:([a-zA-Z0-9_]+)\])'
            r'|(\[sfx:([a-zA-Z0-9_]+)\])'
            r'|([^\[]+(?:\[(?!face:|sfx:)[^\[]*)*)'
        )

        for i, line in enumerate(self.rendered_lines):
            if plain_chars_drawn_total >= self.current_char_index:
                break

            line_y = text_y + i * config.LINE_SPACING
            current_render_x = text_x
            marker_idx = 0

            for match in segment_regex.finditer(line):
                if plain_chars_drawn_total >= self.current_char_index:
                    break

                segment_start_plain_char_index = plain_chars_drawn_total
                face_marker_match = match.group(1)
                sfx_marker_match = match.group(3)
                text_segment = match.group(5)

                if face_marker_match:
                    if segment_start_plain_char_index <= self.current_char_index:
                        face_name = match.group(2)
                        new_face = self.active_face_images.get(face_name)
                        if new_face:
                            self.current_face_image = new_face
                    continue

                elif sfx_marker_match:
                    marker_key = (i, marker_idx)
                    if segment_start_plain_char_index <= self.current_char_index and marker_key not in self._played_sfx_markers:
                        sfx_name = match.group(4)
                        sound = self.other_sfx.get(sfx_name)
                        if sound:
                            can_play_sound = not (self.is_forced_quitting and self.forced_quit_timer >= self.forced_quit_shake_start_delay)
                            if can_play_sound:
                                sound.play()
                        self._played_sfx_markers.add(marker_key)
                    marker_idx += 1
                    continue

                elif text_segment:
                    plain_sub_segment_len = len(text_segment)
                    remaining_chars_needed = self.current_char_index - plain_chars_drawn_total
                    chars_to_draw_in_sub_segment = max(0, min(plain_sub_segment_len, remaining_chars_needed))

                    if chars_to_draw_in_sub_segment > 0:
                        text_to_render = text_segment[:chars_to_draw_in_sub_segment]
                        try:
                            text_surface = segment_font.render(text_to_render, True, config.INPUT_BOX_TEXT_COLOR[:3])
                            target_surface.blit(text_surface, (current_render_x, line_y))
                            current_render_x += text_surface.get_width()
                        except (pygame.error, AttributeError) as e:
                            pass

                    plain_chars_drawn_total += chars_to_draw_in_sub_segment

                    if chars_to_draw_in_sub_segment < plain_sub_segment_len:
                        break

            if plain_chars_drawn_total >= self.current_char_index:
                break

    def handle_event(self, event) -> tuple[str, str | int | None] | None:
        if self.is_forced_quitting:
            # No input for you, you disapointed niko.
            if event.type == pygame.QUIT:
                self.running = False
                return ("quit", None)
            return None

        if event.type == pygame.QUIT:
            self.running = False
            return ("quit", None)

        if self.is_history_active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if not self.is_menu_active and not self.is_input_active and not self.is_choice_active:
                    return ("toggle_menu", None)
            elif event.key == pygame.K_ESCAPE:
                if self.is_menu_active:
                    self.play_sound("menu_cancel")
                    return ("toggle_menu", None)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left clicky
                mouse_pos = event.pos
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                input_interaction_rect = self.input_rect.inflate(10, 10)
                is_on_choice = False
                if self.is_choice_active or self.is_menu_active:
                    for rect in self.choice_rects:
                        if rect.collidepoint(mouse_pos):
                            is_on_choice = True
                            break

                if not textbox_rect.collidepoint(mouse_pos) and \
                   not (self.is_input_active and input_interaction_rect.collidepoint(mouse_pos)) and \
                   not is_on_choice:
                    self.dragging = True
                    current_window_x, current_window_y = self.window_x, self.window_y

                    if platform.system() == "Windows" and self.hwnd:
                         try:
                             # More Windows witchcraft
                             rect = ctypes.wintypes.RECT()
                             ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
                             current_window_x = rect.left
                             current_window_y = rect.top
                         except Exception as e:
                             pass # Magic failed. Sad.

                    self.drag_offset_x = current_window_x - mouse_pos[0]
                    self.drag_offset_y = current_window_y - mouse_pos[1]
                    return ("drag_start", None)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.dragging:
                    self.dragging = False # Okay, stop dragging now.
                    return ("drag_end", None)

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                # Weeeee! Window go zoom!
                mouse_pos = event.pos
                new_x = mouse_pos[0] + self.drag_offset_x
                new_y = mouse_pos[1] + self.drag_offset_y

                if platform.system() == "Windows" and self.hwnd:
                    try:
                        # Even MORE Windows magic to move the window!
                        flags = 0x0001 | 0x0004 | 0x0010 # Magic flags, don't ask.
                        ctypes.windll.user32.SetWindowPos(self.hwnd, 0, new_x, new_y, 0, 0, flags)
                        self.window_x = new_x
                        self.window_y = new_y
                    except Exception as e:
                        self.dragging = False # Magic failed AGAIN. Windows is fickle.
                else:
                    pass # Not Windows? No dragging for you! (except if you're on X11, i love linux)
                return ("dragging", (new_x, new_y))

        if self.dragging and event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
             if event.type == pygame.MOUSEMOTION: return ("dragging", None)
             if event.type == pygame.MOUSEBUTTONDOWN: return ("drag_start", None)


        if self.is_choice_active:
            
            prev_selected_index = self.selected_choice_index
            action_taken = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_choice_index = (self.selected_choice_index - 1) % len(self.choice_options)
                    action_taken = True
                elif event.key == pygame.K_DOWN:
                    self.selected_choice_index = (self.selected_choice_index + 1) % len(self.choice_options)
                    action_taken = True
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.play_confirm_sound()
                    chosen_index = self.selected_choice_index
                    return ("choice_made", chosen_index)
                elif event.key == pygame.K_ESCAPE:
                     if not self.is_menu_active:
                          return None

            elif event.type == pygame.MOUSEMOTION:
                 mouse_pos = event.pos
                 for i, rect in enumerate(self.choice_rects):
                      if rect.collidepoint(mouse_pos):
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

            if action_taken and self.selected_choice_index != prev_selected_index:
                 self.play_sound("menu_cursor")

            return None

        elif self.is_input_active:

            if event.type == pygame.KEYDOWN:
                prev_text = self.user_input_text
                prev_cursor_pos = self.input_cursor_pos
                needs_redraw = False # Flag to indicate if text/cursor changed

                if event.key == pygame.K_RETURN:
                    submitted_text = self.user_input_text
                    self.play_confirm_sound()
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
                    self.input_cursor_pos = max(0, self.input_cursor_pos - 1)
                    needs_redraw = True
                elif event.key == pygame.K_RIGHT:
                    self.input_cursor_pos = min(len(self.user_input_text), self.input_cursor_pos + 1)
                    needs_redraw = True
                elif event.key == pygame.K_HOME:
                     self.input_cursor_pos = 0
                     needs_redraw = True
                elif event.key == pygame.K_END:
                     self.input_cursor_pos = len(self.user_input_text)
                     needs_redraw = True
                elif event.key == pygame.K_ESCAPE:
                    return ("input_escape", None)
                else:
                    if event.unicode.isprintable(): # FUCK GEMINI
                        new_char = event.unicode
                        # 1. Update text and cursor position first
                        self.user_input_text = self.user_input_text[:self.input_cursor_pos] + new_char + self.user_input_text[self.input_cursor_pos:]
                        self.input_cursor_pos += len(new_char)
                        needs_redraw = True

                        # 2. Now calculate required height based on the *new* text
                        try:
                            max_render_width = self.input_rect.width - config.INPUT_BOX_PADDING * 2
                            wrapped_lines, _ = self._wrap_input_text(self.user_input_text, max_render_width)
                            num_lines = len(wrapped_lines)
                            required_height = (num_lines * self.input_font.get_height()) + config.INPUT_BOX_PADDING * 2

                            max_input_height = config.TEXTBOX_HEIGHT - 20 # Max height constraint
                            min_height = config.INPUT_BOX_HEIGHT # Min height constraint

                            # 3. Adjust height if needed
                            new_height = max(min_height, min(required_height, max_input_height))

                            # Only resize if the new height is different and within bounds
                            if new_height != self.input_rect.height:
                                if required_height > max_input_height and self.input_rect.height == max_input_height:
                                     # Already at max height, but text grew? Play buzzer, revert change.
                                     self.play_sound("menu_buzzer")
                                     # Revert the text change
                                     self.user_input_text = prev_text
                                     self.input_cursor_pos = prev_cursor_pos
                                     needs_redraw = False # No change occurred
                                else:
                                     # Allow resizing (grow or shrink)
                                     self.input_rect.height = new_height
                            elif required_height > max_input_height:
                                 # Text requires more than max height, but box is already maxed. Buzzer. Revert.
                                 self.play_sound("menu_buzzer")
                                 self.user_input_text = prev_text
                                 self.input_cursor_pos = prev_cursor_pos
                                 needs_redraw = False


                        except (pygame.error, AttributeError) as e:
                            # Error during wrapping/sizing, proceed with text change but don't resize
                            print(f"Warning: Error calculating input box size: {e}")
                            pass # Text already updated, just skip resizing logic

                # Reset cursor blink if text or cursor position changed
                if needs_redraw: # Use the flag
                    self.input_cursor_visible = True
                    self.input_cursor_timer = 0.0
                return None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                 if self.input_rect.collidepoint(event.pos):
                      return None
                 else:
                      pass
            return None

        else: # Normal dialogue state
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    # User wants to go faster! Skip pause, skip animation, or advance.
                    if self.is_paused:
                         self.is_paused = False
                         self.pause_timer = 0.0
                         self.current_pause_duration = 0.0
                         return ("skip_pause", None)
                    elif self.is_animating:
                        self.current_char_index = self.total_chars_to_render
                        self.is_animating = False
                        self.is_paused = False
                        self.draw_arrow = True
                        self.text_animation_timer = 0
                        if self.active_text_sfx:
                            self.active_text_sfx.stop()
                        return ("skip_anim", None)
                    elif self.draw_arrow:
                        return ("advance", None)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                 if event.button == 1:
                    # Clicky clicky on the textbox
                    textbox_clickable_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                    if textbox_clickable_rect.collidepoint(event.pos):
                        # Same logic as keydown for skipping/advancing
                        if self.is_paused:
                            self.is_paused = False
                            self.pause_timer = 0.0
                            self.current_pause_duration = 0.0
                            return ("skip_pause", None)
                        elif self.is_animating:
                            self.current_char_index = self.total_chars_to_render
                            self.is_animating = False
                            self.is_paused = False
                            self.draw_arrow = True
                            self.text_animation_timer = 0
                            if self.active_text_sfx:
                                self.active_text_sfx.stop()
                            return ("skip_anim", None)
                        elif self.draw_arrow:
                            return ("advance", None)
        return None # Nothing interesting happened? Move along.

    def clear_input(self):
        self.user_input_text = ""
        self.input_cursor_pos = 0
        self.input_rect.height = config.INPUT_BOX_HEIGHT

    def play_confirm_sound(self):
        if self.confirm_sfx:
            self.confirm_sfx.play()
        else:
            pass

    def play_sound(self, name: str):
        sound = self.other_sfx.get(name)
        if sound:
            sound.play()
        else:
            pass

    def _wrap_input_text(self, text: str, max_width: int) -> tuple[list[str], list[int]]:
        """Wraps input text based on font size and max width."""
        
        wrapped_lines = []
        line_start_indices = [0]
        current_wrap_line = ""
        original_text_ptr = 0
        # Use raw string for regex to avoid SyntaxWarning
        words = re.split(r'(\s+)', text) # Split by spaces, keep the spaces. Clever? Maybe.
        words = [w for w in words if w] # Clean up again.

        font = self.input_font

        for word in words:
            is_space = word.isspace()
            test_line = current_wrap_line + word
            try:
                line_width = font.size(test_line)[0]
                if line_width <= max_width:
                    current_wrap_line += word
                    original_text_ptr += len(word)
                else:
                    if current_wrap_line:
                        wrapped_lines.append(current_wrap_line)
                        line_start_indices.append(original_text_ptr)

                    if not is_space and font.size(word)[0] > max_width:
                        temp_long_word_line = ""
                        for char_idx, char in enumerate(word):
                            if font.size(temp_long_word_line + char)[0] <= max_width:
                                temp_long_word_line += char
                            else:
                                wrapped_lines.append(temp_long_word_line)
                                original_text_ptr += len(temp_long_word_line)
                                line_start_indices.append(original_text_ptr)
                                temp_long_word_line = char
                        current_wrap_line = temp_long_word_line
                        original_text_ptr += len(current_wrap_line)
                    elif is_space:
                        current_wrap_line = word
                        original_text_ptr += len(word)
                    else:
                        current_wrap_line = word
                        original_text_ptr += len(word)

            except (pygame.error, AttributeError):
                if current_wrap_line:
                    wrapped_lines.append(current_wrap_line)
                    line_start_indices.append(original_text_ptr)
                current_wrap_line = word
                original_text_ptr += len(word)

        if current_wrap_line:
            wrapped_lines.append(current_wrap_line) # Don't forget the# Oh god, more text wrapping. Will it ever end?

        # Add the missing return statement
        return wrapped_lines, line_start_indices
