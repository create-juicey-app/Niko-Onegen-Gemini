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

ai_results_queue = queue.Queue()
niko_ai = None  # Make niko_ai global
exit_reason = config.EXIT_STATUS_ABRUPT  # Default exit reason

# --- Add state for retrying failed AI calls ---
last_failed_user_input: str | None = None
last_failed_prompt: str | None = None
last_failed_is_initial: bool = False
waiting_for_retry_choice: bool = False
# --- End added state ---

def ai_worker(niko_ai_instance: NikoAI, formatted_prompt: str, user_input: str | None = None, initial_greeting: bool = False, previous_exit_status: str | None = None):
    """Function to run AI generation in a separate thread."""
    global ai_results_queue
    result = None
    try:
        if initial_greeting:
            # Pass previous status to get_initial_greeting
            result = niko_ai_instance.get_initial_greeting(formatted_prompt, previous_exit_status)
        elif user_input is not None:
            result = niko_ai_instance.generate_response(user_input, formatted_prompt)
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
    """Runs the sequential first-time setup process."""
    original_options = app_options.copy()
    original_volume = gui.sfx_volume
    original_bg_path = app_options.get("background_image_path", config.DEFAULT_BG_IMG)

    gui.set_active_face_set("twm")
    gui.set_active_sfx("robot")

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
        options_list = []
        values_list = []

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
            values_list = available_bgs
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

        else:
            options_list = step["options"]
            values_list = step["values"]
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
                    elif not is_input_step and action == "choice_made":
                        chosen_index = data
                        chosen_value = values_list[chosen_index]
                        temp_options[option_key] = chosen_value
                        if option_key == "sfx_volume":
                            gui.set_sfx_volume(chosen_value); gui.play_confirm_sound()
                        elif option_key == "background_image_path":
                            try:
                                gui.bg_img_original = gui.load_image(chosen_value)
                                if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
                                else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
                            except Exception as e: print(f"Error loading background preview: {e}")
                            gui.play_confirm_sound()
                        else: gui.play_confirm_sound()
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

            gui.set_sfx_volume(app_options["sfx_volume"])
            gui.bg_img_original = gui.load_image(app_options["background_image_path"])
            if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
            else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
            gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])
            global niko_ai
            if niko_ai:
                 niko_ai.model_name = app_options.get("ai_model_name", config.AI_MODEL_NAME)
                 print(f"AI Model set to: {niko_ai.model_name} after initial setup.")

        if not cancelled:
             gui.set_active_face_set("niko")
             gui.set_active_sfx("default")


def show_main_menu(gui: GUI, app_options: Dict[str, Any], ai_history: List[Dict]):
    """Displays the main pause menu."""
    global niko_ai
    gui.is_menu_active = True

    menu_items = ["Resume chat", "Options", "Chat History", "Quit"]
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
                                        if save_changes and niko_ai:
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
                        # Add callback to reset AI history when history is deleted
                        gui.display_chat_history(ai_history, delete_callback=lambda: reset_ai_history())
                        if not gui.running: menu_active = False
                        gui.is_menu_active = True
                        selected_index = 0
                        gui.selected_choice_index = 0
                    elif chosen_action == "Quit":
                        gui.fade_out(); gui.running = False; menu_active = False

                    break

                elif action == "drag_start" or action == "dragging" or action == "drag_end":
                    pass
                elif action == "toggle_menu":
                    menu_active = False
                    gui.play_sound("menu_cancel")
                    break

        if not gui.running or not menu_active: break

        selected_index = gui.selected_choice_index

        gui.render_background_and_overlay(gui.screen)

        gui.choice_options = menu_items
        gui.selected_choice_index = selected_index
        gui.is_choice_active = True
        gui.draw_multiple_choice(gui.screen)

        pygame.display.flip()

    gui.is_menu_active = False
    gui.is_choice_active = False
    gui.choice_options = []
    gui.choice_rects = []
    return gui.running


def reset_ai_history():
    """Reset the AI's conversation history."""
    global niko_ai
    if niko_ai:
        # Clear the AI's conversation history
        niko_ai.conversation_history = []
        # Immediately save the empty history to disk
        niko_ai._save_history()
        print("AI conversation history has been reset.")


def main():
    global niko_ai, exit_reason  # Add exit_reason to globals
    # --- Add access to global retry state variables ---
    global last_failed_user_input, last_failed_prompt, last_failed_is_initial, waiting_for_retry_choice
    # --- End access ---
    app_options = options.load_options()
    # Load previous exit status, default to abrupt if not found
    previous_exit_status = app_options.get(config.EXIT_STATUS_KEY, config.EXIT_STATUS_ABRUPT)

    try:
        gui = GUI(app_options)
    except pygame.error as e:
        print(f"Fatal Error initializing Pygame/GUI: {e}"); sys.exit(1)
    except Exception as e:
        print(f"Fatal Error initializing GUI: {e}"); sys.exit(1)

    # --- Initial Setup ---
    if not app_options.get("setup_complete", False):
        run_initial_setup(gui, app_options)
        if not gui.running:
             pygame.quit(); sys.exit()
        # Reload options after setup completes
        app_options = options.load_options()
        # Re-apply necessary settings from potentially changed options
        gui.set_active_face_set("niko")
        gui.set_active_sfx("default")
        gui.set_sfx_volume(app_options["sfx_volume"])
        gui.bg_img_original = gui.load_image(app_options["background_image_path"])
        if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
        else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
        gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])

    # --- AI Initialization ---
    player_name = app_options.get('player_name', 'Player')
    if not player_name: player_name = "Player"
    try: formatted_initial_prompt = config.INITIAL_PROMPT.replace('{player_name}', player_name)
    except Exception as e: print(f"Error formatting initial prompt: {e}"); formatted_initial_prompt = f"Hello {player_name}, I am Niko."

    ai_model_to_use = app_options.get("ai_model_name", config.AI_MODEL_NAME)
    print(f"Using AI Model: {ai_model_to_use}")
    try:
        # Initialize AI - it will load history internally if available
        niko_ai = NikoAI(ai_model_name=ai_model_to_use)
    except ValueError as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)
    except Exception as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)

    # --- State Variables ---
    ai_is_thinking = False
    dialogue_queue = deque()
    ai_thread = None
    force_quit_pending = False # Flag to trigger forced quit after dialogue queue finishes
    quit_pending = False       # Flag to trigger normal quit after dialogue queue finishes
    input_was_active_before_menu = False # Track input state before menu

    # --- Initial Fade In ---
    gui.fade_in()
    if not gui.running: pygame.quit(); sys.exit()

    # --- Process AI Response Function ---
    def process_ai_response(response_segments: List[NikoResponse] | None):
        """Queues dialogue segments received from the AI and displays the first. Handles errors and quit commands."""
        # Use nonlocal to modify flags in the outer scope (main)
        nonlocal ai_is_thinking, force_quit_pending, quit_pending
        global exit_reason
        global waiting_for_retry_choice

        # Reset state for this response
        gui.ai_is_thinking = False
        dialogue_queue.clear()
        ai_is_thinking = False
        force_quit_pending = False # Reset pending flags for this response
        quit_pending = False
        error_occurred = False

        if response_segments:
            num_segments = len(response_segments)
            last_segment_index = num_segments - 1
            cleaned_segments = []

            # Check original last segment for quit commands *before* cleaning
            if num_segments > 0:
                original_last_text = response_segments[last_segment_index].text
                if "[quit_forced]" in original_last_text:
                    force_quit_pending = True
                    exit_reason = config.EXIT_STATUS_NORMAL_AI
                elif "[quit]" in original_last_text:
                    quit_pending = True
                    exit_reason = config.EXIT_STATUS_NORMAL_AI

            # Clean all segments and add non-empty ones to a temporary list
            for segment in response_segments:
                # Create a new NikoResponse with cleaned text
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

            # Add cleaned segments to the main dialogue queue
            dialogue_queue.extend(cleaned_segments)

            # Display the first segment if available
            if dialogue_queue:
                next_segment = dialogue_queue.popleft()
                gui.set_dialogue(next_segment)
                gui.is_input_active = False # Ensure input is off when showing new segment
            # If queue is empty *after cleaning* (e.g., only contained tags or was empty initially)
            else:
                # Trigger pending quits immediately if queue is already empty (single segment case)
                if force_quit_pending:
                     gui.start_forced_quit()
                     force_quit_pending = False # Consumed
                     gui.is_input_active = False # Ensure input off
                elif quit_pending:
                     # For normal quit, show arrow briefly before fade on advance
                     gui.draw_arrow = True
                     gui.is_input_active = False # Ensure input off
                     # The actual fade happens on the next 'advance' in the main loop
                # Otherwise, if no quit pending and no error, ready for input
                elif not error_occurred: # Check error flag from potential earlier processing
                     gui.is_input_active = True # Directly enable input
                     gui.draw_arrow = False

        # Handle case where AI worker returned None or empty list initially
        elif response_segments is None or not response_segments:
            error_occurred = True
            print("Error: AI worker returned None or empty response (critical error).")
            error_response = NikoResponse(text="(Uh oh, my train of thought derailed completely! Retry?)", face="scared", speed="normal", bold=False, italic=False)
            gui.set_dialogue(error_response) # Display error message
            gui.is_input_active = False # Ensure input off

        # --- Handle error state ---
        if error_occurred:
            # Set up retry choice only if no quit commands were pending
            if not force_quit_pending and not quit_pending:
                waiting_for_retry_choice = True
                gui.choice_options = ["Retry", "Cancel"]
                gui.selected_choice_index = 0
                gui.is_choice_active = True
                gui.draw_arrow = False
                gui.is_input_active = False
            else:
                 # If an error occurred but a quit was also pending, prioritize the quit.
                 # The quit logic (immediate or pending) already handled above.
                 pass


    # --- Initial AI Call ---
    # Call get_initial_greeting. It will handle whether to greet or reconnect based on loaded history.
    ai_is_thinking = True
    gui.ai_is_thinking = True
    gui.render()
    pygame.display.flip()

    last_failed_user_input = None  # Will be set by get_initial_greeting if it uses generate_response
    last_failed_prompt = formatted_initial_prompt
    # Determine if it's truly initial based on history *before* calling get_initial_greeting
    last_failed_is_initial = not bool(niko_ai.conversation_history)
    # Start the thread for the initial message, passing previous exit status
    ai_thread = threading.Thread(
        target=ai_worker,
        args=(niko_ai, formatted_initial_prompt),
        kwargs={'initial_greeting': True, 'previous_exit_status': previous_exit_status},  # Pass previous status
        daemon=True
    )
    ai_thread.start()


    # --- Main Loop ---
    while gui.running:
        dt = gui.clock.tick(60) / 1000.0

        if gui.is_forced_quitting:
            for event in pygame.event.get():
                gui.handle_event(event)
            if not gui.running: break
            gui.update(dt)
            gui.render()
            continue

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
                                     kwargs={'initial_greeting': last_failed_is_initial},
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
                                     gui.is_input_active = True # Enable input directly
                                     gui.draw_arrow = False
                                     gui.user_input_text = ""
                           last_failed_user_input = None
                           last_failed_prompt = None
                           last_failed_is_initial = False
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
                          # Store current dialogue state before opening menu
                          input_was_active_before_menu = gui.is_input_active
                          
                          # Track if there is unfinished dialogue in the queue or animation
                          has_more_dialogue = bool(dialogue_queue)
                          has_finished_animation = not gui.is_animating and not gui.is_paused
                          
                          # Check if we're at the last message and ready for input
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

                          # Apply option changes
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
                          try: formatted_initial_prompt = config.INITIAL_PROMPT.replace('{player_name}', player_name)
                          except Exception as e: print(f"Error re-formatting initial prompt after menu: {e}")
                          print(f"Current AI Model after menu: {niko_ai.model_name}")

                          # RESTORATION LOGIC - Corrected to handle dialogue advancement case
                          if input_was_active_before_menu:
                               # If input was active before, restore it
                               gui.is_input_active = True
                               gui.draw_arrow = False
                               gui.user_input_text = ""
                          elif at_last_message:
                               # If we were at the last message, enable input
                               gui.is_input_active = True
                               gui.draw_arrow = False
                               gui.user_input_text = ""
                          elif has_more_dialogue:
                               # If there's more dialogue in the queue, set up for advancement
                               gui.is_input_active = False
                               gui.draw_arrow = True
                          else:
                               # Current dialogue segment is still displaying
                               gui.is_input_active = False
                               
                               # Only show arrow if animation and pause are finished
                               # This is critical for allowing advance after return from menu
                               gui.draw_arrow = has_finished_animation
                          
                          # Reset menu state flags
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
                                elif not gui.is_input_active:
                                    gui.is_input_active = True
                                    gui.draw_arrow = False
                                    gui.user_input_text = ""
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

                                last_failed_user_input = user_input
                                last_failed_prompt = formatted_initial_prompt
                                last_failed_is_initial = False

                                ai_thread = threading.Thread(target=ai_worker, args=(niko_ai, formatted_initial_prompt, user_input), daemon=True)
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
    print(f"Exiting application. Reason: {exit_reason}")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()