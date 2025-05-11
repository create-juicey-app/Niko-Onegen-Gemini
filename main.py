# Main application entry point. Handles initialization, setup,
# main loop, AI interaction, history display, and options menu.

import pygame
import sys
import config
import options
from gui import GUI
from ai import NikoAI, NikoResponse
from collections import deque
from typing import List, Dict, Any
import threading
import queue
import os
import json
import re
import textwrap
from pydantic import ValidationError
import random
import time  # Added for timing self-speaking feature
import mss  # For screen capture
import mss.tools
from PIL import Image  # For image processing

# New import for character management
import character_manager
from character_manager import Character  # For type hinting

ai_results_queue = queue.Queue()
niko_ai = None  # Make niko_ai global (consider renaming if multiple AIs are planned)
exit_reason = config.EXIT_STATUS_ABRUPT  # Default exit reason
current_character: Character | None = None  # Global for the currently loaded character
formatted_initial_prompt: str = ""  # Global for the current character's AI prompt

# --- Add state for retrying failed AI calls ---
last_failed_user_input: str | None = None
last_failed_prompt: str | None = None
last_failed_is_initial: bool = False
waiting_for_retry_choice: bool = False
last_failed_screenshot: str | None = None  # Add screenshot path to retry state
# --- End added state ---

# --- Add state for self-speaking AI ---
ai_next_self_speak_time = float('inf')  # When Niko should next speak by itself
ai_self_speak_in_progress = False  # Flag to track if self-speaking is currently happening
# --- End added state ---

def set_next_self_speak_time(frequency: str) -> float:
    """Calculate the next time Niko should speak based on frequency setting."""
    if frequency == config.AI_SPEAK_FREQUENCY_NEVER:
        return float('inf')  # Never speak
    
    time_range = config.AI_SPEAK_FREQUENCY_TIMES.get(frequency)
    if not time_range:
        return float('inf')
        
    min_time, max_time = time_range
    delay = random.uniform(min_time, max_time)
    return time.time() + delay

def generate_random_topic() -> str:
    """Generate a random topic for Niko to talk about."""
    topics = [
        "I wonder what Mama is cooking today...",
        "Do you think the stars look the same from your world?",
        "I miss Alula and Calamus sometimes.",
        "I had a dream about pancakes last night!",
        "Do you have wheat fields in your world too?",
        "I was thinking about our journey together.",
        "The lightbulb... I mean, sun... was so bright.",
        "I haven't seen any robots lately.",
        "I wonder how everyone from the City is doing now.",
        "Do you remember when we first met?",
        "I'm glad I got to go home after our adventure.",
        "I've been helping Mama with chores.",
        "Sometimes I still think about our adventure.",
        "I saw something that reminded me of you today!"
    ]
    return random.choice(topics)

def capture_screenshot(app_options: Dict[str, Any]) -> str | None:
    """Captures a screenshot based on application options and returns the path if successful."""
    # Check if screen capture is disabled
    if app_options.get("screen_capture_mode") == config.SCREEN_CAPTURE_MODE_NONE:
        return None
        
    # Only proceed if Screenshot mode is selected (ignore Video WIP for now)
    if app_options.get("screen_capture_mode") != config.SCREEN_CAPTURE_MODE_SCREENSHOT:
        return None
    
    try:
        # Ensure the screenshot directory exists
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        
        # Get monitor selection setting
        monitor_selection = app_options.get("monitor_selection", config.MONITOR_PRIMARY)
        
        # Set up mss for capturing
        with mss.mss() as sct:
            # Determine which monitor(s) to capture
            if monitor_selection == config.MONITOR_ALL:
                # Capture the entire desktop (all monitors)
                monitor = sct.monitors[0]  # Monitor 0 is the "all monitors" pseudo-monitor in mss
                print("Capturing all monitors")
            else:
                # Capture primary monitor only
                monitor = sct.monitors[1]  # Monitor 1 is typically the primary
                print(f"Capturing primary monitor: {monitor}")
            
            # Take the screenshot
            screenshot = sct.grab(monitor)
            
            # Save to temp file
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=config.TEMP_SCREENSHOT)
            
            # Convert to JPEG using PIL for compatibility and reduced size
            with Image.open(config.TEMP_SCREENSHOT) as img:
                # Resize if necessary (optional, can help with large monitors)
                max_width = 1280  # Reasonable maximum width
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Save as JPEG with quality setting
                img.convert('RGB').save(config.TEMP_SCREENSHOT, format='JPEG', quality=85)
            
            print(f"Screenshot saved to {config.TEMP_SCREENSHOT}")
            return config.TEMP_SCREENSHOT
            
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None

def ai_worker(niko_ai_instance: NikoAI, formatted_prompt: str, user_input: str | None = None, initial_greeting: bool = False, previous_exit_status: str | None = None, screenshot_path: str | None = None):
    """Function to run AI generation in a separate thread."""
    global ai_results_queue
    result = None
    try:
        if initial_greeting:
            # Pass previous status to get_initial_greeting
            result = niko_ai_instance.get_initial_greeting(formatted_prompt, previous_exit_status)
        elif user_input is not None:
            result = niko_ai_instance.generate_response(user_input, formatted_prompt, screenshot_path)
    except Exception as e:
        print(f"AI Worker Thread encountered an error: {e}")
        result = [NikoResponse(text="(Critical AI Error...)", face="scared", speed="normal", bold=False, italic=False)]
    finally:
        ai_results_queue.put(result)


def display_dialogue_step(gui: GUI, text: str, face: str, speed: str = "normal"):
    """Displays a single dialogue segment and waits for user advance."""
    gui.set_dialogue(NikoResponse(text=text, face=face, speed=speed, bold=False, italic=False))
    waiting_for_advance = True
    while waiting_for_advance and gui.running:
        dt = gui.clock.tick(60) / 1000.0
        for event in pygame.event.get():
            result = gui.handle_event(event)
            if result:
                action, _ = result
                if action == "initiate_quit":
                    gui.fade_out()
                    gui.running = False
                    waiting_for_advance = False
                    break
                elif action == "quit":
                    gui.running = False
                    waiting_for_advance = False
                    break
                elif action in ["advance", "skip_anim", "skip_pause"]:
                    if not gui.is_animating and not gui.is_paused:
                         waiting_for_advance = False
                         break
        if not gui.running: break
        gui.update(dt)
        gui.render()


def run_initial_setup(gui: GUI, app_options: Dict[str, Any]):
    """Runs the sequential first-time user configuration process."""
    original_options = app_options.copy()
    original_volume = gui.sfx_volume
    original_bg_path = app_options.get("background_image_path", config.DEFAULT_BG_IMG)
    
    # Load TWM character data for setup visuals
    twm_char_data = character_manager.get_twm_setup_character()
    gui.load_character_resources(twm_char_data) # Temporarily load TWM resources

    intro_dialogue = [
        {"text": "...", "face": "normal", "speed": "slow"},
        {"text": "SYSTEM BOOT...", "face": "speak", "speed": "fast"},
        {"text": "Entity presence detected.", "face": "normal", "speed": "normal"},
        {"text": "Initializing first-time user configuration.", "face": "speak", "speed": "normal"},
        {"text": "I am The World Machine.", "face": "smile", "speed": "normal"},
        {"text": "I handled things... behind the scenes.", "face": "normal", "speed": "normal"},
        {"text": "Now, I will assist you in setting up your connection.", "face": "speak", "speed": "normal"},
        {"text": "Please answer the following prompts.", "face": "normal", "speed": "normal"},
    ]
    for dialogue in intro_dialogue:
        if not gui.running: break
        display_dialogue_step(gui, dialogue["text"], dialogue["face"], dialogue.get("speed", "normal"))

    if not gui.running: return

    setup_steps = [
         {
            "question": "Setup: Enter your name",
            "type": "input",
            "key": "player_name",
            "face": "speak"
        },
        {
            "question": "Setup: Choose your Character",
            "type": "character_choice",  # Use a specific type for character selection
            "key": "active_character_id",
            "face": "normal"
        },
        {
            "question": "Setup: Adjust SFX Volume",
            "options": ["Mute", "Quiet", "Medium", "Loud"],
            "key": "sfx_volume",
            "values": [0.0, 0.25, 0.5, 0.8],
            "face": "normal"
        },
        {
            "question": "Setup: Choose Default Text Speed",
            "options": ["Slow", "Normal", "Fast", "Instant"],
            "key": "default_text_speed",
            "values": ["slow", "normal", "fast", "instant"],
            "face": "speak"
        },
        {
            "question": "Setup: Choose Background Image",
            "type": "background",
            "key": "background_image_path",
            "face": "smile"
        },
        {
            "question": "Setup: Choose AI Model",
            "options": config.AVAILABLE_AI_MODELS,
            "key": "ai_model_name",
            "values": config.AVAILABLE_AI_MODELS,
            "face": "normal"
        },
    ]

    current_step_index = 0
    temp_options = app_options.copy()
    cancelled = False

    while current_step_index < len(setup_steps):
        if not gui.running:
             cancelled = True
             break

        step = setup_steps[current_step_index]
        question = step["question"]
        face = step.get("face", "normal")
        option_key = step["key"]

        gui.set_dialogue(NikoResponse(text=question, face=face, speed="normal", bold=False, italic=False))
        gui.current_char_index = gui.total_chars_to_render
        gui.is_animating = False
        gui.draw_arrow = False

        is_input_step = step.get("type") == "input"
        is_background_step = step.get("type") == "background"
        is_character_choice_step = step.get("type") == "character_choice" # Added check
        options_list = [] # For display in gui.choice_options for non-character steps
        values_list = []  # For mapping selected index to value for non-character steps

        if is_input_step:
            current_value = temp_options.get(option_key, "")
            gui.user_input_text = current_value
            gui.input_cursor_pos = len(gui.user_input_text)
            gui.is_input_active = True
            gui.input_cursor_visible = True
            gui.input_cursor_timer = 0.0
            gui.update(0)
            try:
                if hasattr(gui, 'input_rect') and hasattr(gui, 'input_font'):
                    max_render_width = gui.input_rect.width - config.INPUT_BOX_PADDING * 2
                    wrapped_lines, _ = gui._wrap_input_text(gui.user_input_text, max_render_width)
                    num_lines = len(wrapped_lines) if wrapped_lines else 1
                    required_height = (num_lines * gui.input_font.get_height()) + config.INPUT_BOX_PADDING * 2
                    min_height = config.INPUT_BOX_HEIGHT
                    max_input_height = config.TEXTBOX_HEIGHT - 20
                    gui.input_rect.height = max(min_height, min(required_height, max_input_height))
                else:
                     if hasattr(gui, 'input_rect'): gui.input_rect.height = config.INPUT_BOX_HEIGHT
            except Exception as e:
                print(f"Warning: Error calculating input box size during setup: {e}")
                if hasattr(gui, 'input_rect'): gui.input_rect.height = config.INPUT_BOX_HEIGHT

        elif is_background_step:
            available_bgs = config.get_available_backgrounds(config.BG_DIR)
            options_list = [os.path.basename(p) for p in available_bgs]
            values_list = available_bgs # Used when choice is made
            if not options_list:
                 print("Warning: No backgrounds found for setup. Skipping step.")
                 current_step_index += 1; continue
            gui.choice_options = options_list
            gui.is_choice_active = True
            try:
                current_value = temp_options[step["key"]]
                gui.selected_choice_index = values_list.index(current_value)
            except (ValueError, KeyError):
                 try: gui.selected_choice_index = options_list.index(os.path.basename(current_value))
                 except (ValueError, KeyError, AttributeError): gui.selected_choice_index = 0
        
        elif is_character_choice_step:
            player_name_for_setup = temp_options.get("player_name", "Player") # Use current name or default
            current_char_id_for_setup = temp_options.get(step["key"])
            gui.setup_character_selection_ui(player_name_for_setup, current_char_id_for_setup)
            if not gui.choice_options: # Check if character list is empty
                display_dialogue_step(gui, "CRITICAL ERROR: No characters found!", "scared", "fast")
                gui.running = False
                cancelled = True
                break
            gui.is_choice_active = True

        else: # Regular choice step (SFX Volume, Text Speed, AI Model)
            options_list = step["options"]
            values_list = step["values"] # Used when choice is made
            gui.choice_options = options_list
            gui.is_choice_active = True
            current_value = temp_options.get(step["key"])
            try: gui.selected_choice_index = values_list.index(current_value)
            except (ValueError, TypeError): gui.selected_choice_index = 0

        gui.render()

        step_complete = False
        while not step_complete and gui.running:
            dt = gui.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                result = gui.handle_event(event)
                if result:
                    action, data = result
                    if action == "initiate_quit":
                        gui.fade_out(); gui.running = False; step_complete = True; cancelled = True; break
                    elif action == "quit":
                        gui.running = False; step_complete = True; cancelled = True; break
                    elif action == "toggle_menu" or (action == "input_escape" and is_input_step) or (action == "choice_escape" and not is_input_step):
                        gui.play_sound("menu_cancel")
                        cancelled = True; step_complete = True; break
                    elif is_input_step and action == "submit_input":
                        submitted_value = data.strip()
                        temp_options[step["key"]] = submitted_value
                        gui.is_input_active = False; step_complete = True; gui.play_confirm_sound(); break
                    
                    elif not is_input_step and action == "choice_made": # Covers background, character, and other choices
                        chosen_index = data
                        
                        if is_character_choice_step:
                            selected_char_id = gui.get_selected_character_id_from_choice(chosen_index)
                            if selected_char_id:
                                temp_options[option_key] = selected_char_id
                        else:
                            chosen_value = values_list[chosen_index]
                            temp_options[option_key] = chosen_value

                        if option_key == "active_character_id":
                            gui.play_confirm_sound()
                        elif option_key == "sfx_volume":
                            gui.set_sfx_volume(temp_options[option_key]); gui.play_confirm_sound()
                        elif option_key == "background_image_path":
                            try:
                                gui.bg_img_original = gui.load_image(temp_options[option_key])
                                if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
                                else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
                            except Exception as e: print(f"Error loading background preview: {e}")
                            gui.play_confirm_sound()
                        else:
                            gui.play_confirm_sound()
                        
                        gui.is_choice_active = False; step_complete = True; break

            if not gui.running or cancelled: break
            gui.update(dt)
            gui.render()

        gui.is_input_active = False
        gui.is_choice_active = False
        gui.choice_options = []
        gui.choice_rects = []

        if not gui.running or cancelled: break
        current_step_index += 1

    if gui.running:
        if cancelled:
            print("Initial setup cancelled.")
            app_options.clear()
            app_options.update(original_options)
            gui.set_sfx_volume(original_volume)
            gui.bg_img_original = gui.load_image(original_bg_path)
            if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
            else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
            gui.running = False
        else:
            app_options.clear()
            app_options.update(temp_options)
            app_options["setup_complete"] = True
            options.save_options(app_options)
            display_dialogue_step(gui, "Configuration complete.", "smile", "fast")

            app_options = options.load_options()
            
            player_name_for_char_load = app_options.get('player_name', 'Player')
            if not player_name_for_char_load: player_name_for_char_load = "Player"
            
            global current_character, formatted_initial_prompt
            loaded_char = character_manager.load_character_data(app_options["active_character_id"], player_name_for_char_load)
            if loaded_char:
                current_character = loaded_char
                formatted_initial_prompt = current_character.formattedInitialPrompt
                gui.load_character_resources(current_character)
            else:
                display_dialogue_step(gui, f"Error: Could not load character '{app_options['active_character_id']}'. Quitting.", "scared", "fast")
                gui.running = False
                return


            gui.set_sfx_volume(app_options["sfx_volume"])
            gui.bg_img_original = gui.load_image(app_options["background_image_path"])
            if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
            else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
            gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
            global niko_ai
            if niko_ai:
                 niko_ai.model_name = app_options.get("ai_model_name", config.AI_MODEL_NAME)
                 print(f"AI Model set to: {niko_ai.model_name} after initial setup.")


def show_main_menu(gui: GUI, app_options: Dict[str, Any], ai_history: List[Dict]):
    """Displays the main pause menu."""
    global niko_ai, current_character, formatted_initial_prompt
    gui.is_menu_active = True

    original_character_id = app_options.get("active_character_id")
    character_changed_requires_restart = False


    menu_items = ["Resume chat", "Options", "Chat History", "Change Character", "Quit"]
    selected_index = 0

    menu_active = True
    while menu_active and gui.running:
        dt = gui.clock.tick(60) / 1000.0

        gui.update(dt)

        for event in pygame.event.get():
            gui.choice_options = menu_items
            gui.is_choice_active = True

            result = gui.handle_event(event)

            if result:
                action, data = result
                if action == "initiate_quit":
                    gui.fade_out(); gui.running = False; menu_active = False; break
                elif action == "quit":
                    gui.running = False; menu_active = False; break
                elif action == "choice_made":
                    chosen_index = data
                    selected_index = chosen_index
                    chosen_action = menu_items[selected_index]

                    gui.is_choice_active = False
                    gui.choice_options = []
                    gui.choice_rects = []

                    if chosen_action == "Resume chat":
                        menu_active = False
                        gui.play_sound("menu_cancel")
                    elif chosen_action == "Options":
                        gui.is_menu_active = False
                        gui.enter_options_menu()

                        options_menu_running = True
                        while options_menu_running and gui.running:
                            options_dt = gui.clock.tick(60) / 1000.0
                            for options_event in pygame.event.get():
                                result = gui.handle_event(options_event)

                                if result:
                                    action, data = result
                                    if action == "initiate_quit":
                                        gui.fade_out(); gui.running = False; options_menu_running = False; menu_active = False; break
                                    elif action == "quit":
                                        gui.running = False; options_menu_running = False; menu_active = False; break
                                    elif action == "exit_options":
                                        save_changes = data
                                        gui.exit_options_menu(save_changes=save_changes)
                                        options_menu_running = False
                                        
                                        if save_changes:
                                            new_character_id = app_options.get("active_character_id")
                                            if new_character_id != original_character_id:
                                                character_changed_requires_restart = True
                                                print(f"Character selection changed to {new_character_id}. Restart application to apply.")
                                            
                                            if niko_ai:
                                                 niko_ai.model_name = app_options.get("ai_model_name", config.AI_MODEL_NAME)
                                                 print(f"AI Model updated to: {niko_ai.model_name}")
                                        break

                            if not gui.running or not options_menu_running: break

                            gui.update(options_dt)
                            gui.render()

                        if not gui.running: menu_active = False
                        gui.is_menu_active = True
                        selected_index = 0
                        gui.selected_choice_index = 0
                    elif chosen_action == "Chat History":
                        gui.is_menu_active = False
                        gui.display_chat_history(ai_history, delete_callback=lambda: reset_ai_history())
                        if not gui.running: menu_active = False
                        gui.is_menu_active = True
                        selected_index = 0
                        gui.selected_choice_index = 0
                    elif chosen_action == "Change Character":
                        gui.is_menu_active = False # Hide the main menu items
                        
                        player_name_for_selection = app_options.get("player_name", "Player")
                        current_char_id_on_entry = app_options.get("active_character_id")
                        
                        # Use CharacterChoiceMixin to set up the choice interface.
                        # This populates gui.choice_options with character display names,
                        # sets the initial selection, and sets gui.is_choice_active = True.
                        gui.setup_character_selection_ui(player_name_for_selection, current_char_id_on_entry)

                        selecting_character = True
                        while selecting_character and gui.running:
                            dt = gui.clock.tick(60) / 1000.0
                            
                            event_processed_in_loop = False
                            for event_obj in pygame.event.get():
                                result = gui.handle_event(event_obj) # Handles choice navigation/selection
                                
                                if result:
                                    action, data = result
                                    event_processed_in_loop = True
                                    if action == "choice_made":
                                        selected_char_id = gui.get_selected_character_id_from_choice(data)
                                        if selected_char_id and selected_char_id != current_char_id_on_entry:
                                            app_options["active_character_id"] = selected_char_id
                                            options.save_options(app_options)
                                            # Character reload is handled after show_main_menu returns
                                        selecting_character = False
                                        # break from event_obj loop handled by selecting_character flag
                                    elif action == "choice_escape":
                                        selecting_character = False
                                    elif action == "quit":
                                        gui.running = False
                                        # selecting_character will be handled by outer loop condition
                                        # menu_active will be handled by outer loop condition
                                    elif action == "initiate_quit":
                                        # gui.handle_event should have started fade_out.
                                        # gui.running will be set to False by fade_out completion or subsequent event.
                                        # selecting_character will be handled by outer loop condition.
                                        pass # No immediate break, let gui.running propagate
                                
                                if not selecting_character or not gui.running:
                                    break # Break from event_obj loop
                            
                            if not selecting_character or not gui.running:
                                break # Break from selecting_character loop

                            gui.update(dt) 
                            # gui.render() will call gui.draw_multiple_choice because 
                            # gui.is_choice_active was set by setup_character_selection_ui.
                            gui.render() 

                        # Cleanup after character selection loop
                        gui.is_choice_active = False
                        gui.choice_options = [] 
                        gui.choice_rects = []
                        
                        # Exit the main menu itself to reflect changes or if quitting
                        menu_active = False 
                        # This break ensures that after handling "Change Character",
                        # we exit the main menu's item processing logic for this iteration.
                        break 
                    elif chosen_action == "Quit":
                        gui.fade_out(); gui.running = False; menu_active = False

        if not gui.running or not menu_active: break

        selected_index = gui.selected_choice_index

        gui.render_background_and_overlay(gui.screen)

        gui.choice_options = menu_items
        gui.selected_choice_index = selected_index
        gui.is_choice_active = True
        gui.draw_multiple_choice(gui.screen)

        pygame.display.flip()

    if character_changed_requires_restart:
        gui.set_dialogue(NikoResponse(text="(Character changed. Please restart to see the new character!)", face=gui.character_data.defaultFace, speed="normal"))
        gui.is_input_active = False
        gui.draw_arrow = True

    gui.is_menu_active = False
    gui.is_choice_active = False
    gui.choice_options = []
    gui.choice_rects = []
    return gui.running


def reset_ai_history():
    """Reset the AI's conversation history."""
    global niko_ai
    if niko_ai:
        niko_ai.conversation_history = []
        niko_ai._save_history()
        print("AI conversation history has been reset.")


def main():
    global niko_ai, exit_reason
    global last_failed_user_input, last_failed_prompt, last_failed_is_initial, waiting_for_retry_choice, last_failed_screenshot
    global ai_next_self_speak_time, ai_self_speak_in_progress
    global current_character, formatted_initial_prompt

    app_options = options.load_options()
    previous_exit_status = app_options.get(config.EXIT_STATUS_KEY, config.EXIT_STATUS_ABRUPT)

    pygame.init()
    
    icon_loaded = False
    try:
        if os.path.exists(config.WINDOW_ICON):
            print(f"Loading window icon from: {config.WINDOW_ICON}")
            pygame.display.set_icon(pygame.image.load(config.WINDOW_ICON))
            icon_loaded = True
            print("Window icon successfully set from ico file")
        else:
            icon_base = os.path.splitext(config.WINDOW_ICON)[0]
            alt_formats = [".png", ".jpg", ".bmp"]
            
            for ext in alt_formats:
                alt_path = icon_base + ext
                if os.path.exists(alt_path):
                    print(f"Trying alternative icon format: {alt_path}")
                    icon = pygame.image.load(alt_path)
                    pygame.display.set_icon(icon)
                    icon_loaded = True
                    print(f"Alternative icon format successfully set")
                    break
    except Exception as e:
        print(f"Warning: Unable to set window icon: {e}")
    
    if not icon_loaded:
        print("Could not load any window icon - using default pygame icon")

    player_name = app_options.get('player_name', 'Player')
    if not player_name: player_name = "Player"
    
    active_char_id = app_options.get("active_character_id", "niko")
    loaded_character = character_manager.load_character_data(active_char_id, player_name)

    if not loaded_character:
        print(f"Failed to load character '{active_char_id}'. Trying to load default 'niko'.")
        loaded_character = character_manager.load_character_data("niko", player_name)
        if loaded_character:
            app_options["active_character_id"] = "niko"
            options.save_options(app_options)
        else:
            print(f"Fatal Error: Could not load default character 'niko'. Please ensure 'characters/niko.json' exists and is valid.")
            pygame.quit()
            sys.exit(1)
            
    current_character = loaded_character
    formatted_initial_prompt = current_character.formattedInitialPrompt

    try:
        gui = GUI(app_options, current_character)
    except pygame.error as e:
        print(f"Fatal Error initializing Pygame/GUI: {e}"); sys.exit(1)
    except Exception as e:
        print(f"Fatal Error initializing GUI: {e}"); sys.exit(1)

    if not app_options.get("setup_complete", False):
        run_initial_setup(gui, app_options)
        if not gui.running:
             pygame.quit(); sys.exit()
        app_options = options.load_options()
        player_name = app_options.get('player_name', 'Player')
        if not player_name: player_name = "Player"
        
        gui.set_sfx_volume(app_options["sfx_volume"])
        gui.bg_img_original = gui.load_image(app_options["background_image_path"])
        if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
        else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
        gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])

    ai_model_to_use = app_options.get("ai_model_name", config.AI_MODEL_NAME)
    print(f"Using AI Model: {ai_model_to_use}")
    try:
        niko_ai = NikoAI(ai_model_name=ai_model_to_use)
        # load persisted AI conversation history if available
        if hasattr(niko_ai, '_load_history'):
            try:
                niko_ai._load_history()
            except Exception as e:
                print(f"Warning loading AI history: {e}")
    except ValueError as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)
    except Exception as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)

    speak_frequency = app_options.get("ai_speak_frequency", config.AI_SPEAK_FREQUENCY_NEVER)
    if speak_frequency != config.AI_SPEAK_FREQUENCY_NEVER:
        ai_next_self_speak_time = set_next_self_speak_time(speak_frequency)

    ai_is_thinking = False
    dialogue_queue = deque()
    ai_thread = None
    force_quit_pending = False
    quit_pending = False
    input_was_active_before_menu = False

    gui.fade_in()
    if not gui.running: pygame.quit(); sys.exit()

    def process_ai_response(response_segments: List[NikoResponse] | None):
        nonlocal ai_is_thinking, force_quit_pending, quit_pending
        global exit_reason, waiting_for_retry_choice, ai_self_speak_in_progress

        gui.ai_is_thinking = False
        dialogue_queue.clear()
        ai_is_thinking = False
        force_quit_pending = False
        quit_pending = False
        error_occurred = False
        
        ai_self_speak_in_progress = False

        if response_segments:
            num_segments = len(response_segments)
            last_segment_index = num_segments - 1
            cleaned_segments = []

            if num_segments > 0:
                original_last_text = response_segments[last_segment_index].text
                if "[quit_forced]" in original_last_text:
                    force_quit_pending = True
                    exit_reason = config.EXIT_STATUS_NORMAL_AI
                elif "[quit]" in original_last_text:
                    quit_pending = True
                    exit_reason = config.EXIT_STATUS_NORMAL_AI

            for segment in response_segments:
                cleaned_text = segment.text.replace("[quit_forced]", "").replace("[quit]", "").strip()
                if cleaned_text:
                    cleaned_segment = NikoResponse(
                        text=cleaned_text,
                        face=segment.face,
                        speed=segment.speed,
                        bold=segment.bold,
                        italic=segment.italic
                    )
                    cleaned_segments.append(cleaned_segment)

            dialogue_queue.extend(cleaned_segments)

            if dialogue_queue:
                next_segment = dialogue_queue.popleft()
                gui.set_dialogue(next_segment)
                gui.is_input_active = False
            else:
                if force_quit_pending:
                     gui.start_forced_quit()
                     force_quit_pending = False
                     gui.is_input_active = False
                elif quit_pending:
                     gui.draw_arrow = True
                     gui.is_input_active = False
                elif not error_occurred:
                     gui.is_input_active = True
                     gui.draw_arrow = False

        elif response_segments is None or not response_segments:
            error_occurred = True
            print("Error: AI worker returned None or empty response (critical error).")
            error_response = NikoResponse(text="(Uh oh, my train of thought derailed completely! Retry?)", face="scared", speed="normal", bold=False, italic=False)
            gui.set_dialogue(error_response)
            gui.is_input_active = False

        if error_occurred:
            if not force_quit_pending and not quit_pending:
                waiting_for_retry_choice = True
                gui.choice_options = ["Retry", "Cancel"]
                gui.selected_choice_index = 0
                gui.is_choice_active = True
                gui.draw_arrow = False
                gui.is_input_active = False
            else:
                 pass


    ai_is_thinking = True
    gui.ai_is_thinking = True
    gui.render()
    pygame.display.flip()

    last_failed_user_input = None
    last_failed_prompt = formatted_initial_prompt
    last_failed_screenshot = None
    last_failed_is_initial = not bool(niko_ai.conversation_history)
    ai_thread = threading.Thread(
        target=ai_worker,
        args=(niko_ai, formatted_initial_prompt),
        kwargs={'initial_greeting': True, 'previous_exit_status': previous_exit_status},
        daemon=True
    )
    ai_thread.start()


    while gui.running:
        dt = gui.clock.tick(60) / 1000.0
        current_time = time.time()

        if gui.is_forced_quitting:
            for event in pygame.event.get():
                gui.handle_event(event)
            if not gui.running: break
            gui.update(dt)
            gui.render()
            continue

        speak_frequency = app_options.get("ai_speak_frequency", config.AI_SPEAK_FREQUENCY_NEVER)
        if (not ai_is_thinking and
            not dialogue_queue and
            not waiting_for_retry_choice and
            not gui.is_menu_active and
            not gui.is_options_menu_active and
            not gui.is_choice_active and
            not gui.is_input_active and
            gui.is_input_hidden and
            not ai_self_speak_in_progress and
            current_time >= ai_next_self_speak_time and
            speak_frequency != config.AI_SPEAK_FREQUENCY_NEVER):

            print(f"Niko is speaking by itself (frequency: {speak_frequency}, input hidden)")
            ai_self_speak_in_progress = True
            ai_is_thinking = True
            gui.ai_is_thinking = True
            gui.is_input_active = False
            
            random_topic = generate_random_topic()
            
            ai_thread = threading.Thread(
                target=ai_worker,
                args=(niko_ai, formatted_initial_prompt, f"(Niko deciding to speak on their own about: {random_topic})"),
                daemon=True
            )
            ai_thread.start()
            
            ai_next_self_speak_time = set_next_self_speak_time(speak_frequency)

        if ai_is_thinking:
            try:
                ai_result = ai_results_queue.get_nowait()
                process_ai_response(ai_result)
                ai_thread = None
            except queue.Empty:
                pass
            except Exception as e:
                 print(f"Error processing AI result from queue: {e}")
                 process_ai_response(None)
                 ai_thread = None

        for event in pygame.event.get():
            if waiting_for_retry_choice:
                 if event.type == pygame.QUIT:
                      gui.running = False; break
                 elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                      result = gui.handle_event(event)
                      if result:
                           action, _ = result
                           if action == "initiate_quit": gui.fade_out(); gui.running = False; break
                           elif action == "quit": gui.running = False; break
                 elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                      result = ("choice_made", 1)
                 else:
                      result = gui.handle_event(event)

                 if result:
                      action, data = result
                      if action == "choice_made":
                           chosen_index = data
                           waiting_for_retry_choice = False
                           gui.is_choice_active = False
                           gui.choice_options = []
                           gui.choice_rects = []

                           if chosen_index == 0:
                                print("Retrying AI generation...")
                                ai_is_thinking = True
                                gui.ai_is_thinking = True
                                gui.set_dialogue(NikoResponse(text="Okay, let me try that again...", face="normal", speed="fast"))
                                ai_thread = threading.Thread(
                                     target=ai_worker,
                                     args=(niko_ai, last_failed_prompt, last_failed_user_input),
                                     kwargs={'initial_greeting': last_failed_is_initial, 'screenshot_path': last_failed_screenshot},
                                     daemon=True
                                )
                                ai_thread.start()
                           elif chosen_index == 1:
                                print("AI generation cancelled by user after error.")
                                if last_failed_is_initial:
                                     print("Initial greeting failed and cancelled. Quitting.")
                                     gui.fade_out()
                                     gui.running = False
                                     break
                                else:
                                     gui.set_dialogue(NikoResponse(text="(Alright.)", face="normal", speed="fast"))
                                     gui.is_input_active = True
                                     gui.draw_arrow = False
                                     gui.user_input_text = ""
                           last_failed_user_input = None
                           last_failed_prompt = None
                           last_failed_is_initial = False
                           last_failed_screenshot = None
                           break
                 continue


            result = gui.handle_event(event)

            if result:
                action, data = result

                if action == "initiate_quit":
                    gui.fade_out(); gui.running = False; break
                elif action == "quit":
                    gui.running = False; break
                elif action == "toggle_menu":
                     if not gui.is_menu_active and not gui.is_input_active and not gui.is_choice_active and not gui.is_options_menu_active:
                          input_was_active_before_menu = gui.is_input_active
                          
                          has_more_dialogue = bool(dialogue_queue)
                          has_finished_animation = not gui.is_animating and not gui.is_paused
                          
                          at_last_message = (not dialogue_queue and 
                                            not ai_is_thinking and
                                            not gui.is_animating and 
                                            not gui.is_paused and
                                            not force_quit_pending and
                                            not quit_pending)
                          
                          if input_was_active_before_menu:
                               gui.is_input_active = False

                          should_continue = show_main_menu(gui, app_options, niko_ai.conversation_history)
                          if not should_continue: break

                          # if user picked "Change Character", reload data/resources
                          new_char = app_options.get("active_character_id")
                          if new_char != current_character.id:
                              # load new character
                              loaded = character_manager.load_character_data(new_char, player_name)
                              if loaded:
                                  current_character = loaded
                                  formatted_initial_prompt = loaded.formattedInitialPrompt
                                  gui.load_character_resources(loaded)
                                  # reset AI history
                                  if niko_ai:
                                      niko_ai.conversation_history = []
                                      niko_ai._save_history()
                              else:
                                  print(f"Error loading character '{new_char}'")

                          # re-apply any other options changes
                          app_options = options.load_options()
                          gui.set_sfx_volume(app_options["sfx_volume"])
                          gui.bg_img_original = gui.load_image(app_options["background_image_path"])
                          if gui.bg_img_original:
                               gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
                          else:
                               gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
                          gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
                          player_name = app_options.get('player_name', 'Player')
                          if not player_name: player_name = "Player"
                          
                          try: formatted_initial_prompt = current_character.promptTemplate.format(
                                    player_name=player_name,
                                    available_faces=", ".join([f"'{f}'" for f in current_character.availableFacesForPrompt]),
                                    available_sfx=", ".join([f"'{s}'" for s in current_character.availableSfxForPrompt])
                                )
                          except Exception as e: print(f"Error re-formatting initial prompt after menu: {e}")
                          print(f"Current AI Model after menu: {niko_ai.model_name}")

                          if input_was_active_before_menu:
                               gui.is_input_active = True
                               gui.draw_arrow = False
                               gui.user_input_text = ""
                          elif at_last_message:
                               gui.is_input_active = True
                               gui.draw_arrow = False
                               gui.user_input_text = ""
                          elif has_more_dialogue:
                               gui.is_input_active = False
                               gui.draw_arrow = True
                          else:
                               gui.is_input_active = False
                               gui.draw_arrow = has_finished_animation
                          
                          input_was_active_before_menu = False

                elif not gui.is_menu_active:
                    if not ai_is_thinking:
                        if action == "advance":
                            if not dialogue_queue:
                                if force_quit_pending:
                                    gui.start_forced_quit()
                                    force_quit_pending = False
                                    gui.is_input_active = False
                                elif quit_pending:
                                    gui.fade_out()
                                    gui.running = False
                                    quit_pending = False
                                    gui.is_input_active = False
                                elif not gui.is_input_active and not gui.is_input_hidden:
                                    gui.is_input_active = True
                                    gui.draw_arrow = False
                                    gui.user_input_text = ""
                                    speak_frequency_check = app_options.get("ai_speak_frequency", config.AI_SPEAK_FREQUENCY_NEVER)
                                    if speak_frequency_check != config.AI_SPEAK_FREQUENCY_NEVER:
                                        ai_next_self_speak_time = float('inf')
                                        print("[Self-Speak Timer] Timer cancelled (advanced to input).")
                            else:
                                next_segment = dialogue_queue.popleft()
                                gui.set_dialogue(next_segment)
                                gui.is_input_active = False
                                if not dialogue_queue:
                                     if quit_pending or force_quit_pending:
                                          gui.draw_arrow = True

                        elif action == "submit_input":
                            user_input = data
                            if user_input and gui.is_input_active:
                                ai_is_thinking = True
                                gui.ai_is_thinking = True
                                gui.is_input_active = False
                                gui.clear_input()

                                screenshot_path = capture_screenshot(app_options)
                                
                                last_failed_user_input = user_input
                                last_failed_prompt = formatted_initial_prompt
                                last_failed_is_initial = False
                                last_failed_screenshot = screenshot_path

                                speak_frequency = app_options.get("ai_speak_frequency", config.AI_SPEAK_FREQUENCY_NEVER)
                                if speak_frequency != config.AI_SPEAK_FREQUENCY_NEVER:
                                    ai_next_self_speak_time = set_next_self_speak_time(speak_frequency)
                                else:
                                    ai_next_self_speak_time = float('inf')


                                ai_thread = threading.Thread(
                                    target=ai_worker,
                                    args=(niko_ai, formatted_initial_prompt, user_input),
                                    kwargs={'screenshot_path': screenshot_path},
                                    daemon=True
                                )
                                ai_thread.start()

                        elif action == "skip_anim":
                             gui.current_char_index = gui.total_chars_to_render
                             gui.is_animating = False
                             gui.draw_arrow = True
                             if gui.active_text_sfx and gui.active_text_sfx.get_num_channels() > 0:
                                  gui.active_text_sfx.stop()
                        elif action == "skip_pause":
                             gui.is_paused = False
                             gui.pause_timer = 0.0
                             gui.current_pause_duration = 0.0
                             if gui.active_text_sfx and gui.active_text_sfx.get_num_channels() > 0:
                                  gui.active_text_sfx.stop()

        if not gui.running: break

        gui.update(dt)

        gui.render()
        pygame.display.flip()


    app_options[config.EXIT_STATUS_KEY] = exit_reason
    options.save_options(app_options)
    # save AI conversation history for next session
    if niko_ai and hasattr(niko_ai, '_save_history'):
        try:
            niko_ai._save_history()
        except Exception as e:
            print(f"Warning saving AI history: {e}")
    print(f"Exiting application. Reason: {exit_reason}")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()