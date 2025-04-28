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

def ai_worker(niko_ai_instance: NikoAI, formatted_prompt: str, user_input: str | None = None, initial_greeting: bool = False):
    """Function to run AI generation in a separate thread."""
    global ai_results_queue
    result = None
    try:
        if initial_greeting:
            result = niko_ai_instance.get_initial_greeting(formatted_prompt)
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


def display_chat_history(gui: GUI, history: List[Dict]):
    """Displays the chat history in a simulated texting app window."""
    gui.is_history_active = True

    BG_COLOR = (25, 25, 35)
    USER_BUBBLE_COLOR = (0, 80, 150)
    NIKO_BUBBLE_COLOR = (50, 50, 60)
    TEXT_COLOR = (230, 230, 230)
    BUBBLE_PADDING = 10
    BUBBLE_MARGIN_Y = 5
    BUBBLE_MARGIN_X = 15
    MAX_BUBBLE_WIDTH_RATIO = 0.65
    FACE_SIZE = 64
    SCROLL_SPEED = 30

    font = gui.fonts.get('regular', pygame.font.Font(None, config.FONT_SIZE - 2))
    line_height = font.get_height() + 2

    rendered_bubbles = []
    total_content_height = BUBBLE_MARGIN_Y

    for turn_index, turn in enumerate(history):
        role = turn.get('role')
        parts = turn.get('parts', [])
        if not isinstance(parts, list): parts = [parts]

        full_text = ""
        face_name = "normal"

        if role == 'user':
            text = parts[0] if parts else "(Empty Input)"
            full_text = f"{text}"
        elif role == 'model':
            try:
                ai_response_json = parts[0]
                if not isinstance(ai_response_json, str): ai_response_json = str(ai_response_json)

                ai_response_data = json.loads(ai_response_json)
                if 'segments' in ai_response_data and ai_response_data['segments']:
                    full_text = " ".join([seg.get('text', '') for seg in ai_response_data['segments']])
                    face_name = ai_response_data['segments'][0].get('face', 'normal')
                elif isinstance(ai_response_data, list) and ai_response_data:
                     full_text = " ".join([seg.get('text', '') for seg in ai_response_data])
                     face_name = ai_response_data[0].get('face', 'normal')
                else:
                     full_text = "(Error: Unexpected model response format)"

                full_text = re.sub(r'\[(?:face|sfx):[^\]]+\]', '', full_text).strip()
            except (json.JSONDecodeError, ValidationError, IndexError, KeyError, TypeError) as e:
                full_text = f"(Error parsing response: {e})"

        if not full_text: continue

        message_lines = full_text.split('\n')
        is_first_line_of_turn = True

        for line_text in message_lines:
            line_text = line_text.strip()
            if not line_text: continue

            max_bubble_width_pixels = int(gui.window_width * MAX_BUBBLE_WIDTH_RATIO)
            font_char_width = 10
            try:
                font_char_width = font.size("A")[0] * 1.2
                if font_char_width <= 0: font_char_width = 10
            except (pygame.error, AttributeError):
                pass

            wrap_width_chars = int(max_bubble_width_pixels / font_char_width)
            if wrap_width_chars <= 0: wrap_width_chars = 10

            wrapped_lines = textwrap.wrap(line_text, width=wrap_width_chars,
                                           replace_whitespace=True, drop_whitespace=True)

            if not wrapped_lines:
                continue

            text_block_height = len(wrapped_lines) * line_height
            bubble_height = text_block_height + BUBBLE_PADDING * 2

            actual_max_line_width = 0
            rendered_line_surfaces = []
            for line in wrapped_lines:
                 try:
                     line_surf = font.render(line, True, TEXT_COLOR)
                     rendered_line_surfaces.append(line_surf)
                     actual_max_line_width = max(actual_max_line_width, line_surf.get_width())
                 except (pygame.error, AttributeError):
                     rendered_line_surfaces.append(None)

            bubble_width = actual_max_line_width + BUBBLE_PADDING * 2

            show_face = role == 'model' and is_first_line_of_turn
            bubble_x_offset = 0
            if show_face:
                bubble_width += FACE_SIZE + BUBBLE_PADDING
                bubble_x_offset = FACE_SIZE + BUBBLE_PADDING

            bubble_surf = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
            bubble_color = NIKO_BUBBLE_COLOR if role == 'model' else USER_BUBBLE_COLOR
            bubble_surf.fill(bubble_color)

            text_y = BUBBLE_PADDING
            text_x = BUBBLE_PADDING + bubble_x_offset
            if show_face:
                face_image = gui.active_face_images.get(face_name)
                if not face_image: face_image = gui.active_face_images.get("normal")
                if face_image:
                    try:
                        scaled_face = pygame.transform.smoothscale(face_image, (FACE_SIZE, FACE_SIZE))
                        bubble_surf.blit(scaled_face, (BUBBLE_PADDING // 2, BUBBLE_PADDING // 2))
                    except pygame.error: pass

            for line_surf in rendered_line_surfaces:
                if line_surf:
                    bubble_surf.blit(line_surf, (text_x, text_y))
                text_y += line_height

            bubble_rect = bubble_surf.get_rect()
            current_margin = BUBBLE_MARGIN_Y * 2 if is_first_line_of_turn else BUBBLE_MARGIN_Y
            bubble_rect.top = total_content_height + current_margin

            if role == 'model':
                bubble_rect.left = BUBBLE_MARGIN_X
            else:
                bubble_rect.right = gui.window_width - BUBBLE_MARGIN_X

            rendered_bubbles.append((bubble_surf, bubble_rect, role))
            total_content_height = bubble_rect.bottom

            is_first_line_of_turn = False

    total_content_height += BUBBLE_MARGIN_Y

    scroll_y = 0
    max_scroll_y = max(0, total_content_height - gui.window_height)

    history_active = True
    while history_active and gui.running:
        dt = gui.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            result = gui.handle_event(event)
            if result:
                action, _ = result
                if action == "initiate_quit":
                    gui.running = False
                    history_active = False
                    break
                elif action == "history_escape":
                    history_active = False
                    break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    scroll_y = max(0, scroll_y - SCROLL_SPEED)
                elif event.key == pygame.K_DOWN:
                    scroll_y = min(max_scroll_y, scroll_y + SCROLL_SPEED)
                elif event.key == pygame.K_PAGEUP:
                     scroll_y = max(0, scroll_y - gui.window_height)
                elif event.key == pygame.K_PAGEDOWN:
                     scroll_y = min(max_scroll_y, scroll_y + gui.window_height)
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(max_scroll_y, scroll_y - event.y * SCROLL_SPEED))

        if not gui.running: break

        gui.screen.fill(BG_COLOR)

        visible_area = pygame.Rect(0, scroll_y, gui.window_width, gui.window_height)
        for bubble_surf, bubble_rect, role in rendered_bubbles:
            if bubble_rect.colliderect(visible_area):
                draw_pos = bubble_rect.move(0, -scroll_y)
                gui.screen.blit(bubble_surf, draw_pos)

        if max_scroll_y > 0:
            scrollbar_height_ratio = min(1.0, gui.window_height / total_content_height)
            scrollbar_height = max(20, int(gui.window_height * scrollbar_height_ratio))
            scrollbar_y_ratio = scroll_y / max_scroll_y if max_scroll_y > 0 else 0
            scrollbar_y = int(scrollbar_y_ratio * (gui.window_height - scrollbar_height))

            scrollbar_rect = pygame.Rect(gui.window_width - 10, scrollbar_y, 8, scrollbar_height)
            pygame.draw.rect(gui.screen, (100, 100, 100), scrollbar_rect)
            pygame.draw.rect(gui.screen, (150, 150, 150), scrollbar_rect, 1)

        pygame.display.flip()

    gui.is_history_active = False


def show_main_menu(gui: GUI, app_options: Dict[str, Any], ai_history: List[Dict]):
    """Displays the main pause menu."""
    global niko_ai
    gui.is_menu_active = True

    menu_items = ["Resume chat", "Options", "Chat History", "Quit"]
    selected_index = 0

    menu_active = True
    while menu_active and gui.running:
        dt = gui.clock.tick(60) / 1000.0

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
                                if options_event.type == pygame.QUIT:
                                     gui.fade_out(); gui.running = False; options_menu_running = False; menu_active = False; break
                                drag_result = gui.handle_event(options_event)
                                if drag_result and drag_result[0] in ["initiate_quit", "quit", "drag_start", "dragging", "drag_end"]:
                                     if drag_result[0] == "initiate_quit": gui.fade_out()
                                     if drag_result[0] in ["initiate_quit", "quit"]: gui.running = False; options_menu_running = False; menu_active = False; break
                                     continue

                                options_action = gui.handle_options_menu_event(options_event)
                                if options_action == "save":
                                    gui.exit_options_menu(save_changes=True)
                                    options_menu_running = False
                                    if niko_ai: niko_ai.model_name = app_options.get("ai_model_name", config.AI_MODEL_NAME)
                                    break
                                elif options_action == "cancel":
                                    gui.exit_options_menu(save_changes=False)
                                    options_menu_running = False
                                    break
                            if not gui.running: break

                            gui.update(options_dt)
                            gui.draw_options_menu(gui.screen)
                            pygame.display.flip()

                        if not gui.running: menu_active = False
                        gui.is_menu_active = True
                        selected_index = 0
                        gui.selected_choice_index = 0
                    elif chosen_action == "Chat History":
                        gui.is_menu_active = False
                        display_chat_history(gui, ai_history)
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
        gui.draw_multiple_choice()

        pygame.display.flip()

    gui.is_menu_active = False
    gui.is_choice_active = False
    gui.choice_options = []
    gui.choice_rects = []
    return gui.running


def main():
    global niko_ai
    app_options = options.load_options()

    try:
        gui = GUI(app_options)
    except pygame.error as e:
        print(f"Fatal Error initializing Pygame/GUI: {e}"); sys.exit(1)
    except Exception as e:
        print(f"Fatal Error initializing GUI: {e}"); sys.exit(1)

    if not app_options.get("setup_complete", False):
        run_initial_setup(gui, app_options)
        if not gui.running:
             pygame.quit(); sys.exit()
        app_options = options.load_options()
        gui.set_active_face_set("niko")
        gui.set_active_sfx("default")
        gui.set_sfx_volume(app_options["sfx_volume"])
        gui.bg_img_original = gui.load_image(app_options["background_image_path"])
        if gui.bg_img_original: gui.bg_img = pygame.transform.smoothscale(gui.bg_img_original, (gui.window_width, gui.window_height))
        else: gui.bg_img = pygame.Surface((gui.window_width, gui.window_height)); gui.bg_img.fill((50,50,50))
        gui.current_text_speed_ms = config.TEXT_SPEED_MAP.get(app_options.get("default_text_speed", "normal"), config.TEXT_SPEED_MAP["normal"])

    player_name = app_options.get('player_name', 'Player')
    if not player_name: player_name = "Player"
    try: formatted_initial_prompt = config.INITIAL_PROMPT.replace('{player_name}', player_name)
    except Exception as e: print(f"Error formatting initial prompt: {e}"); formatted_initial_prompt = f"Hello {player_name}, I am Niko."

    ai_model_to_use = app_options.get("ai_model_name", config.AI_MODEL_NAME)
    print(f"Using AI Model: {ai_model_to_use}")
    try:
        niko_ai = NikoAI(ai_model_name=ai_model_to_use)
    except ValueError as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)
    except Exception as e: print(f"Fatal Error initializing AI: {e}"); pygame.quit(); sys.exit(1)

    ai_is_thinking = False
    dialogue_queue = deque()
    ready_for_input = False
    ai_thread = None
    quit_initiated_by_ai = False
    force_quit_command_detected = False

    gui.fade_in()
    if not gui.running: pygame.quit(); sys.exit()

    def process_ai_response(response_segments: List[NikoResponse] | None):
        """Queues dialogue segments received from the AI and displays the first. Checks for [quit] or [quit_forced] command."""
        nonlocal ready_for_input, ai_is_thinking, quit_initiated_by_ai, force_quit_command_detected
        gui.ai_is_thinking = False
        dialogue_queue.clear()
        ready_for_input = False
        ai_is_thinking = False
        quit_command_detected = False
        force_quit_command_detected = False

        if response_segments:
            last_segment_index = len(response_segments) - 1
            for i, segment in enumerate(response_segments):
                if i == last_segment_index:
                    if "[quit_forced]" in segment.text:
                        force_quit_command_detected = True
                        segment.text = segment.text.replace("[quit_forced]", "").strip()
                    elif "[quit]" in segment.text:
                        quit_command_detected = True
                        segment.text = segment.text.replace("[quit]", "").strip()

                if segment.text:
                    dialogue_queue.append(segment)

            if dialogue_queue:
                next_segment = dialogue_queue.popleft()
                gui.set_dialogue(next_segment)
            else:
                if not quit_command_detected and not force_quit_command_detected:
                     ready_for_input = True
                     gui.is_input_active = True
                     gui.draw_arrow = False

        elif response_segments is None:
            print("Error: AI worker returned None (critical error).")
            error_response = NikoResponse(text="(Uh oh, my train of thought derailed completely!)", face="scared", speed="normal", bold=False, italic=False)
            gui.set_dialogue(error_response)
            ready_for_input = True
            gui.is_input_active = True
            gui.draw_arrow = False
        else:
            ready_for_input = True
            gui.is_input_active = True
            gui.draw_arrow = False

        if force_quit_command_detected:
            gui.start_forced_quit()
            ready_for_input = False
            gui.is_input_active = False
            gui.draw_arrow = False
        elif quit_command_detected:
            quit_initiated_by_ai = True
            ready_for_input = False
            gui.is_input_active = False
            if not dialogue_queue:
                gui.draw_arrow = True

    ai_is_thinking = True
    gui.ai_is_thinking = True
    gui.render()
    pygame.display.flip()

    ai_thread = threading.Thread(target=ai_worker, args=(niko_ai, formatted_initial_prompt), kwargs={'initial_greeting': True}, daemon=True)
    ai_thread.start()

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
            if gui.is_options_menu_active: continue

            result = gui.handle_event(event)

            if result:
                action, data = result

                if action == "initiate_quit":
                    gui.fade_out(); gui.running = False; break
                elif action == "quit":
                    gui.running = False; break
                elif action == "toggle_menu":
                     if not gui.is_menu_active and not gui.is_input_active and not gui.is_choice_active and not gui.is_options_menu_active:
                          should_continue = show_main_menu(gui, app_options, niko_ai.conversation_history)
                          if not should_continue: break

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

                elif not gui.is_menu_active:
                    if not ai_is_thinking:
                        if action == "advance":
                            if dialogue_queue:
                                next_segment = dialogue_queue.popleft()
                                gui.set_dialogue(next_segment)
                                ready_for_input = False
                            elif quit_initiated_by_ai:
                                gui.fade_out()
                                gui.running = False
                                break
                            elif not gui.is_input_active:
                                ready_for_input = True
                                gui.is_input_active = True
                                gui.draw_arrow = False
                                gui.user_input_text = ""

                        elif action == "submit_input":
                            user_input = data
                            if user_input and ready_for_input:
                                ai_is_thinking = True
                                gui.ai_is_thinking = True
                                ready_for_input = False
                                gui.is_input_active = False
                                gui.clear_input()

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

        if not gui.is_options_menu_active:
             gui.update(dt)

        if not gui.is_options_menu_active:
             gui.render()
             pygame.display.flip()

    options.save_options(app_options)
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()