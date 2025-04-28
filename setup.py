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
        is_background_step = step.get("type") == "background"

        gui.set_dialogue(NikoResponse(text=question, face=face, speed="normal", bold=False, italic=False))

        # --- Prepare state BEFORE the pre-loop render ---
        if is_background_step:
            # Activate input mode and set initial text *before* rendering
            current_value = temp_options.get(option_key, config.DEFAULT_BG_IMG)
            gui.user_input_text = current_value # Pre-fill input
            gui.input_cursor_pos = len(gui.user_input_text) # Set cursor to end
            gui.is_input_active = True
            gui.input_cursor_visible = True # Ensure cursor starts visible
            gui.input_cursor_timer = 0.0

            # Force an update cycle to process the new state *before* height calc/render
            # This allows internal GUI logic (like cursor state) to initialize based on is_input_active
            gui.update(0)

            # Ensure input box height is calculated initially before rendering (using updated state)
            try:
                # Ensure input_rect exists before accessing width
                if hasattr(gui, 'input_rect'):
                    max_render_width = gui.input_rect.width - config.INPUT_BOX_PADDING * 2
                    # Explicitly call wrap text here to get dimensions needed
                    wrapped_lines, _ = gui._wrap_input_text(gui.user_input_text, max_render_width)
                    num_lines = len(wrapped_lines) if wrapped_lines else 1
                    required_height = (num_lines * gui.input_font.get_height()) + config.INPUT_BOX_PADDING * 2
                    min_height = config.INPUT_BOX_HEIGHT
                    max_input_height = config.TEXTBOX_HEIGHT - 20
                    gui.input_rect.height = max(min_height, min(required_height, max_input_height))
                else:
                     print("Warning: gui.input_rect not found during initial height calculation.")
                     # Cannot calculate height yet, maybe default? Or rely on GUI init?
                     # If input_rect is created in GUI.update or GUI.render, this might still fail.

            except Exception as e:
                print(f"Warning: Error calculating initial input box size: {e}")
                if hasattr(gui, 'input_rect'): # Set fallback height if rect exists
                    gui.input_rect.height = config.INPUT_BOX_HEIGHT

        elif not is_background_step and step.get("options"): # Prepare choice state if it's a choice step
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
                       pass # Keep default index 0
             gui.is_choice_active = True # Activate choice mode before render
             # Force update for choice state too? Might not be necessary but for consistency:
             gui.update(0)

        # Render once before entering choice/input loop to display the question AND the initial input/choice state
        gui.render()

        # --- Enter loop for interaction ---
        if is_background_step:
            # Input state already set above
            input_submitted = False
            while not input_submitted and gui.running:
                dt = gui.clock.tick(config.FPS) / 1000.0
                for event in pygame.event.get():
                    result = gui.handle_event(event)
                    if result:
                        action, data = result
                        if action == "quit":
                            pygame.quit()
                            sys.exit()
                        elif action == "submit_input":
                            submitted_path = data.strip()
                            # Basic validation: check if file exists (optional but good)
                            if os.path.exists(submitted_path) or submitted_path == config.DEFAULT_BG_IMG:
                                temp_options[option_key] = submitted_path
                                gui.load_and_set_background(submitted_path) # Update preview on submit
                                input_submitted = True
                                gui.play_confirm_sound() # Play sound on successful submit
                            else:
                                # Handle invalid path - maybe flash input box or show error message?
                                print(f"Warning: Background path not found: {submitted_path}")
                                gui.play_sound("menu_buzzer") # Play error sound
                                # Keep input active for correction
                            break # Exit event loop for this frame
                        elif action == "input_escape":
                            # Revert to original value on escape? Or just proceed?
                            # For setup, let's just proceed with the value before input started.
                            input_submitted = True # Treat escape as finishing the step
                            break # Exit event loop for this frame
                if not gui.running: break
                gui.update(dt) # Update animations, cursor blink etc.
                gui.render() # Render the input interface

            # Clean up input state AFTER the loop
            gui.is_input_active = False
            gui.clear_input() # Clear text and reset input state

        elif not is_background_step and step.get("options"): # Handle choice step loop
            # Choice state already set above
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

                            choice_made = True
                            break # Exit event loop once choice is made
                if not gui.running: break
                gui.update(dt) # Update animations, etc.
                gui.render() # Render the choice interface

            # Clean up choice state AFTER the loop
            gui.is_choice_active = False
            gui.choice_options = []
            gui.choice_rects = []
        else:
             # Handle steps without options or input (if any added later)
             # For now, just advance past them if they aren't input/choice
             pass


        if not gui.running: break
        current_step_index += 1

    if gui.running:
        # Final message before saving
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
