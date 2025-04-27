# ///////////////////////////////////////////////////////
#            No copyright! Open Source!
#  Created by JuiceyDev (create-juicey-dev)
# ///////////////////////////////////////////////////////
# This module defines the in-game options menu accessible via ESC.

import pygame
import sys
import config
import options
from gui import GUI
from config import NikoResponse
from typing import Dict, Any

def run_options_menu(gui: GUI, app_options: Dict[str, Any]):
    """Displays the options menu."""
    gui.is_menu_active = True

    menu_steps = [
        {
            "question": "Options: Adjust SFX Volume",
            "options": ["Mute", "Quiet", "Medium", "Loud"],
            "key": "sfx_volume",
            "values": [0.0, 0.25, 0.5, 0.8],
            "face": "normal"
        },
        {
            "question": "Options: Choose Default Text Speed",
            "options": ["Slow", "Normal", "Fast", "Instant"],
            "key": "default_text_speed",
            "values": ["slow", "normal", "fast", "instant"],
            "face": "thinking"
        },
        {
            "question": "Options",
            "options": ["Return to Game", "Quit Game"],
            "key": "action",
            "values": ["return", "quit"],
            "face": "normal"
        },
    ]

    current_step_index = 0
    temp_options = app_options.copy()

    while current_step_index < len(menu_steps) and gui.running:
        step = menu_steps[current_step_index]
        question = step["question"]
        face = step.get("face", "normal")

        gui.set_dialogue(NikoResponse(text=question, face=face, speed="instant", bold=True, italic=False))
        gui.render()

        options_list = step["options"]
        values_list = step["values"]

        gui.choice_options = options_list
        gui.selected_choice_index = 0
        current_value = temp_options.get(step["key"])
        if current_value is not None and step["key"] != "action":
             try:
                  gui.selected_choice_index = values_list.index(current_value)
             except ValueError:
                  gui.selected_choice_index = 0

        gui.is_choice_active = True

        choice_made = False
        while not choice_made and gui.running:
            dt = gui.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                result = gui.handle_event(event)
                if result:
                    action, data = result
                    if action == "quit":
                        gui.running = False
                        break
                    elif action == "choice_made":
                        chosen_index = data
                        chosen_value = values_list[chosen_index]
                        option_key = step["key"]

                        if option_key == "action":
                            if chosen_value == "return":
                                choice_made = True
                                current_step_index = len(menu_steps) # Force exit loop
                            elif chosen_value == "quit":
                                gui.running = False
                                choice_made = True
                        else:
                            temp_options[option_key] = chosen_value
                            if option_key == "sfx_volume":
                                gui.set_sfx_volume(chosen_value)
                            choice_made = True
                        break
            if not gui.running: break
            gui.update(dt)
            gui.render()

        gui.is_choice_active = False
        gui.choice_options = []
        gui.choice_rects = []

        if not gui.running: break
        if choice_made and current_step_index < len(menu_steps) and step["key"] != "action":
             current_step_index += 1

    gui.is_menu_active = False
    if gui.running:
        app_options.update(temp_options)
        options.save_options(app_options)
        gui.set_dialogue(NikoResponse(text="", face="normal", speed="instant", bold=False, italic=False))
        gui.render()
