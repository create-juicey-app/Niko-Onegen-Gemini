
# Handles the first-time setup process for the application,
# guiding the user through initial configuration options via a TWM-themed interface.

import pygame
import sys
import os
import config
import options
from gui import GUI
from config import NikoResponse
from typing import Dict, Any

def display_dialogue_step(gui: GUI, text: str, face: str, speed: str = "normal"):
    """Displays a single dialogue segment and waits for user input."""
    gui.set_dialogue(NikoResponse(text=text, face=face, speed=speed, bold=False, italic=False))
    waiting_for_advance = True
    while waiting_for_advance and gui.running:
        dt = gui.clock.tick(config.FPS) / 1000.0
        for event in pygame.event.get():
            result = gui.handle_event(event)
            if result:
                action, _ = result
                if action == "quit":
                    pygame.quit()
                    sys.exit()
                elif action in ["advance", "skip_anim", "skip_pause"]:
                    if not gui.is_animating and not gui.is_paused:
                         waiting_for_advance = False
                         break # Exit event loop once advance is triggered
        if not gui.running: break
        gui.update(dt)
        gui.render()

def run_setup(gui: GUI, app_options: Dict[str, Any]):
    """Runs the first-time setup sequence."""
    gui.set_active_face_set("twm")
    gui.set_active_sfx("robot")
    gui.set_sfx_volume(app_options.get("sfx_volume", config.DEFAULT_OPTIONS["sfx_volume"])) # Use initial volume

    # Use standard face names (GUI will prefix with 'en_' automatically)
    intro_dialogue = [
        {"text": "...", "face": "normal", "speed": "slow"}, # Changed "" to "normal"
        {"text": "SYSTEM BOOT...", "face": "normal", "speed": "fast"}, # Changed "" to "normal"
        {"text": "Entity presence detected.", "face": "closed"}, # Changed "eyeclosed"
        {"text": "Initializing first-time user configuration.", "face": "closed2"}, # Changed "eyeclosed2"
        {"text": "Hello...", "face": "normal"}, # Changed "2" to "normal"
        {"text": "I am The World Machine.", "face": "speak"}, # Kept "speak"
        {"text": "I handled things... behind the scenes.", "face": "distressed"}, # Changed "distressed_talk"
        {"text": "Now, I will assist you in setting up your connection.", "face": "yawn"}, # Changed "en_yawn" to "yawn"
        {"text": "Please answer the following prompts.", "face": "upset"}, # Changed "upset_meow"
    ]

    for dialogue in intro_dialogue:
        if not gui.running: return
        display_dialogue_step(gui, dialogue["text"], dialogue["face"], dialogue.get("speed", "normal"))

    if not gui.running: return

    setup_steps = [
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
            "question": "Setup: Select Window Size (Requires Restart)",
            "options": ["800x600", "1024x768", "1280x720"],
            "key": "window_size",
            "values": [(800, 600), (1024, 768), (1280, 720)],
            "face": "huh"
        },
        {
            "question": "Setup: Choose Background Image",
            "type": "background",
            "key": "background_image_path",
            "face": "smile"
        },
    ]

    temp_options = app_options.copy()
    current_step_index = 0

    while current_step_index < len(setup_steps) and gui.running:
        step = setup_steps[current_step_index]
        question = step["question"]
        face = step.get("face", "normal")
        option_key = step["key"]

        gui.set_dialogue(NikoResponse(text=question, face=face, speed="normal", bold=False, italic=False))
        # Render once before entering choice loop to display the question
        gui.render()

        options_list = []
        values_list = []
        is_background_step = step.get("type") == "background"

        if is_background_step:
            available_bgs = config.get_available_backgrounds(config.BG_DIR)
            default_bg_path = config.DEFAULT_BG_IMG
            options_list = [os.path.basename(bg) for bg in available_bgs]
            values_list = [os.path.join(config.BG_DIR, bg) if os.path.join(config.BG_DIR, bg) != default_bg_path else default_bg_path for bg in available_bgs]

            # Ensure default is present if dir is empty or default isn't listed
            if default_bg_path not in values_list:
                 options_list.insert(0, os.path.basename(default_bg_path))
                 values_list.insert(0, default_bg_path)

            if not options_list: # Should not happen if default is handled, but as fallback
                 temp_options[option_key] = default_bg_path
                 current_step_index += 1
                 continue
        else:
            options_list = step["options"]
            values_list = step["values"]

        gui.choice_options = options_list
        gui.selected_choice_index = 0 # Default selection

        # Try to pre-select the current value
        current_value = None
        if option_key == "window_size":
             current_value = (temp_options["window_width"], temp_options["window_height"])
        else:
             current_value = temp_options.get(option_key)

        if current_value in values_list:
             try:
                  gui.selected_choice_index = values_list.index(current_value)
             except ValueError:
                  pass # Keep default index 0 if value not found

        gui.is_choice_active = True
        choice_made = False

        while not choice_made and gui.running:
            dt = gui.clock.tick(config.FPS) / 1000.0
            for event in pygame.event.get():
                result = gui.handle_event(event)
                if result:
                    action, data = result
                    if action == "quit":
                        pygame.quit()
                        sys.exit()
                    elif action == "choice_made":
                        chosen_index = data
                        chosen_value = values_list[chosen_index]

                        if option_key == "window_size":
                            temp_options["window_width"] = chosen_value[0]
                            temp_options["window_height"] = chosen_value[1]
                        else:
                            temp_options[option_key] = chosen_value
                            # Apply immediate feedback for relevant options
                            if option_key == "sfx_volume":
                                gui.set_sfx_volume(chosen_value)
                                # Play a test sound maybe? gui.play_sfx('test_sound')
                            elif option_key == "background_image_path":
                                gui.load_and_set_background(chosen_value)

                        choice_made = True
                        break # Exit event loop once choice is made
            if not gui.running: break
            gui.update(dt) # Update animations, etc.
            gui.render() # Render the choice interface

        # Clean up choice state
        gui.is_choice_active = False
        gui.choice_options = []
        gui.choice_rects = []

        if not gui.running: break
        current_step_index += 1

    if gui.running:
        # CHINESE CHINESE CHINESE CHINESE 
        gui.set_active_face_set("twm")
        display_dialogue_step(gui, "Configuration complete. Initializing connection...", "smile", "fast")

        # Save final options and apply them
        app_options.update(temp_options)
        app_options["setup_complete"] = True
        options.save_options(app_options)

        # Reset GUI to Niko defaults
        gui.set_active_face_set("niko")
        gui.set_active_sfx("default")
        gui.set_sfx_volume(app_options["sfx_volume"])
        gui.load_and_set_background(app_options["background_image_path"])
