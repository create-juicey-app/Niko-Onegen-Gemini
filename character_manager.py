import json
import os
from typing import List, Dict, Optional

from pydantic import BaseModel, Field
import config # Assuming config.py contains BASE_DIR and utility functions

class Character(BaseModel):
    id: str
    displayName: str
    faceDir: str # Relative to BASE_DIR
    facePrefix: str
    defaultFace: str
    textSfxPath: str # Relative to BASE_DIR
    promptTemplate: str
    availableFacesOverride: Optional[List[str]] = None # Optional: if faces can't be auto-detected or need specific order/filtering
    availableSfxOverride: Optional[List[str]] = None # Optional: for character-specific SFX list for prompt

    # Populated dynamically
    formattedInitialPrompt: str = ""
    actualFaceDir: str = ""
    actualTextSfxPath: str = ""
    availableFacesForPrompt: List[str] = []
    availableSfxForPrompt: List[str] = []


def get_available_characters() -> List[str]:
    """Scans the characters directory and returns a list of character IDs (filenames without .json)."""
    char_ids = []
    if not os.path.exists(config.CHARACTERS_DIR):
        print(f"Warning: Characters directory not found at {config.CHARACTERS_DIR}")
        return []
    for filename in os.listdir(config.CHARACTERS_DIR):
        if filename.endswith(".json"):
            char_ids.append(os.path.splitext(filename)[0])
    return sorted(char_ids)

def load_character_data(character_id: str, player_name: str) -> Optional[Character]:
    """Loads, validates, and processes a character's data from their JSON file."""
    char_file_path = os.path.join(config.CHARACTERS_DIR, f"{character_id}.json")
    if not os.path.exists(char_file_path):
        print(f"Error: Character file not found: {char_file_path}")
        return None

    try:
        with open(char_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        character = Character(**data)

        # Resolve paths relative to BASE_DIR
        character.actualFaceDir = os.path.join(config.BASE_DIR, character.faceDir)
        character.actualTextSfxPath = os.path.join(config.BASE_DIR, character.textSfxPath)

        # Determine available faces for the prompt
        if character.availableFacesOverride:
            character.availableFacesForPrompt = character.availableFacesOverride
        else:
            character.availableFacesForPrompt = config.get_available_faces(character.actualFaceDir, character.facePrefix)
        
        available_faces_str = ", ".join([f"'{f}'" for f in character.availableFacesForPrompt])
        if not character.availableFacesForPrompt:
            print(f"Warning: No faces found or specified for character '{character.id}' in dir '{character.actualFaceDir}' with prefix '{character.facePrefix}'. Prompt may be affected.")
            available_faces_str = "normal" # Fallback for prompt

        # Determine available SFX for the prompt (using global SFX for now, can be customized)
        # For simplicity, let's assume characters use the global SFX list for their prompts for now,
        # unless an override is provided.
        if character.availableSfxOverride:
            character.availableSfxForPrompt = character.availableSfxOverride
        else:
            # Use global SFX, excluding text/robot sounds, similar to old config
            all_sfx = config.get_available_sfx(config.SFX_DIR, exclude=["text.wav", "textrobot.wav"])
            character.availableSfxForPrompt = [sfx for sfx in all_sfx if not sfx.startswith("glitch")]

        available_sfx_str = ", ".join([f"'{s}'" for s in character.availableSfxForPrompt]) if character.availableSfxForPrompt else "None available"

        # Format the initial prompt
        character.formattedInitialPrompt = character.promptTemplate.format(
            player_name=player_name,
            available_faces=available_faces_str,
            available_sfx=available_sfx_str
        )
        
        return character

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for character '{character_id}': {e}")
        return None
    except Exception as e: # Catch Pydantic validation errors and others
        print(f"Error loading or processing character data for '{character_id}': {e}")
        return None

# Example TWM data for setup - can be a simplified Character object or a dict
# This is a placeholder; ideally, TWM would also have a minimal JSON.
TWM_SETUP_CHARACTER_DATA = {
    "id": "twm_setup",
    "displayName": "The World Machine",
    "faceDir": os.path.join(config.BASE_DIR, "res", "faces", "twm"),
    "facePrefix": "en_",
    "defaultFace": "normal",
    "textSfxPath": os.path.join(config.BASE_DIR, "res", "sfx", "textrobot.wav"),
    "availableFacesForPrompt": config.get_available_faces(os.path.join(config.BASE_DIR, "res", "faces", "twm"), "en_")
    # No prompt needed for TWM setup as dialogue is hardcoded
}

def get_twm_setup_character() -> Character:
    """Returns a Character-like object for TWM during setup."""
    # This is a simplified way to provide TWM data without a full JSON for setup.
    # It assumes TWM faces and robot sfx are at known paths.
    twm_face_dir = os.path.join(config.BASE_DIR, "res", "faces", "twm")
    twm_sfx_path = os.path.join(config.BASE_DIR, "res", "sfx", "textrobot.wav")
    
    return Character(
        id="twm_setup",
        displayName="The World Machine",
        faceDir=os.path.relpath(twm_face_dir, config.BASE_DIR), # Store relative path
        actualFaceDir=twm_face_dir,
        facePrefix="en_",
        defaultFace="normal",
        textSfxPath=os.path.relpath(twm_sfx_path, config.BASE_DIR), # Store relative path
        actualTextSfxPath=twm_sfx_path,
        promptTemplate="", # Not used for setup
        availableFacesForPrompt=config.get_available_faces(twm_face_dir, "en_")
    )

if __name__ == '__main__':
    # Test functions (requires config.py to be set up correctly)
    print("Available characters:", get_available_characters())
    # Create a dummy niko.json in a 'characters' subdir for testing
    # Ensure config.CHARACTERS_DIR points to it.
    # test_char = load_character_data("niko", "TestPlayer")
    # if test_char:
    #     print(f"\nLoaded character: {test_char.displayName}")
    #     print(f"Face dir: {test_char.actualFaceDir}")
    #     print(f"Default face: {test_char.defaultFace}")
    #     print(f"Text SFX: {test_char.actualTextSfxPath}")
    #     print(f"Faces for prompt: {test_char.availableFacesForPrompt}")
    #     # print(f"Formatted prompt snippet: {test_char.formattedInitialPrompt[:300]}...")
    # else:
    #     print("Failed to load test character.")
    
    # twm_char = get_twm_setup_character()
    # print(f"\nTWM Setup Character: {twm_char.displayName}")
    # print(f"TWM Face Dir: {twm_char.actualFaceDir}")

