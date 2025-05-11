# Manages loading and saving application settings from/to a JSON file.
# Provides default values and handles potential file errors.

import json
import os
import config
import logging # Use logging for errors

OPTIONS_FILE = "options.json"

def _get_default_username() -> str:
    """Gets the system username as a default, falling back to 'Player'."""
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get('USER') or os.environ.get('USERNAME') or "Player"
    return username

def load_options() -> dict:
    """Loads options from JSON, returning defaults if file is missing or invalid."""
    default_opts = config.DEFAULT_OPTIONS.copy()
    default_opts["player_name"] = _get_default_username() # Set dynamic default

    if not os.path.exists(OPTIONS_FILE):
        logging.info(f"Options file '{OPTIONS_FILE}' not found. Creating with defaults.")
        # Ensure default character ID is valid before saving for the first time
        if "active_character_id" in default_opts:
            from character_manager import get_available_characters # Local import
            available_chars = get_available_characters()
            if not available_chars: # No characters found at all
                logging.error("CRITICAL: No character JSON files found. Application might not work.")
                # default_opts.pop("active_character_id", None) # Or set to a placeholder
            elif default_opts["active_character_id"] not in available_chars:
                default_opts["active_character_id"] = available_chars[0] # Default to first available
        
        save_options(default_opts)
        return default_opts

    try:
        with open(OPTIONS_FILE, 'r') as f:
            loaded_opts = json.load(f)

        # Merge loaded options with defaults, ensuring all default keys exist
        options = default_opts.copy()
        for key in default_opts:
            if key in loaded_opts:
                # Basic type validation could be added here if needed
                options[key] = loaded_opts[key]

        # Ensure player_name is not empty after loading
        if not options.get("player_name"):
             options["player_name"] = default_opts["player_name"]

        # Validate window size tuple if loaded
        if "window_width" in options and "window_height" in options:
             if not (isinstance(options["window_width"], int) and isinstance(options["window_height"], int)):
                  logging.warning("Invalid window dimensions in options file, resetting to default.")
                  options["window_width"] = default_opts["window_width"]
                  options["window_height"] = default_opts["window_height"]

        if "active_character_id" in options:
            from character_manager import get_available_characters # Local import
            available_chars = get_available_characters()
            if not available_chars:
                logging.warning(f"No character JSONs found, but 'active_character_id' is in options. This might cause issues.")
            elif options["active_character_id"] not in available_chars:
                logging.warning(f"Saved character '{options['active_character_id']}' not found. Resetting to default.")
                options["active_character_id"] = default_opts["active_character_id"]
                # Re-validate default if necessary
                if options["active_character_id"] not in available_chars and available_chars:
                    options["active_character_id"] = available_chars[0]

        return options

    except (IOError, json.JSONDecodeError, TypeError) as e:
        logging.error(f"Error loading options file '{OPTIONS_FILE}': {e}. Using defaults.")
        # Optionally backup the corrupted file here
        return default_opts

def save_options(options: dict):
    """Saves the provided options dictionary to the JSON file."""
    try:
        # Filter options to save only keys present in the defaults
        options_to_save = {key: options.get(key) for key in config.DEFAULT_OPTIONS if key in options}
        with open(OPTIONS_FILE, 'w') as f:
            json.dump(options_to_save, f, indent=4)
    except (IOError, TypeError) as e:
        logging.error(f"Error saving options file '{OPTIONS_FILE}': {e}")

