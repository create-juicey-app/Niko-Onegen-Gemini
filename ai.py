from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold, GenerateContentConfig, SafetySetting
import json
import re
from pydantic import ValidationError
import time
from google.genai import errors
import os  # Added for file operations
import pickle  # Added for serialization
import zlib  # Added for compression

import config
from config import NikoResponse, AIResponse
from typing import List, Optional

MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
HISTORY_FILE = config.HISTORY_FILE  # Assumes HISTORY_FILE is defined in config.py

class NikoAI:
    """Handles interaction with the Google Generative AI model."""

    def __init__(self, ai_model_name: str = config.AI_MODEL_NAME):  # Accept model name
        if not config.GOOGLE_API_KEY:
            raise ValueError("Google API Key not configured.")
        try:
            self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google GenAI Client: {e}")

        self.model_name = ai_model_name  # Use passed model name
        self.conversation_history = []
        self.safety_settings = [
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        ]
        self._load_history()  # Load history on initialization

    def _load_history(self):
        """Loads conversation history from the compressed binary file (.dat)."""
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'rb') as f:  # Open in binary read mode
                    compressed_data = f.read()
                    serialized_data = zlib.decompress(compressed_data)
                    history = pickle.loads(serialized_data)
                print(f"Loaded {len(history)} turns from compressed history file: {HISTORY_FILE}")
                # Basic validation (check if it's a list)
                if not isinstance(history, list):
                    print("Warning: Loaded history is not a list. Starting fresh.")
                    history = []
            except (FileNotFoundError, EOFError, pickle.UnpicklingError, zlib.error, TypeError, ValueError) as e:
                print(f"Error loading or decoding history file '{HISTORY_FILE}': {e}. Starting with empty history.")
                history = []
        self.conversation_history = history

    def _save_history(self):
        """Saves the current conversation history to a compressed binary file (.dat)."""
        try:
            # Create directory if it doesn't exist
            history_dir = os.path.dirname(HISTORY_FILE)
            if history_dir and not os.path.exists(history_dir):
                os.makedirs(history_dir)

            with open(HISTORY_FILE, 'wb') as f:  # Open in binary write mode
                serialized_data = pickle.dumps(self.conversation_history)
                compressed_data = zlib.compress(serialized_data, level=9)  # Use compression level 9
                f.write(compressed_data)
        except (IOError, pickle.PicklingError, zlib.error) as e:
            print(f"Error saving history to '{HISTORY_FILE}': {e}")

    def _format_history_for_api(self) -> List[types.Content]:
        api_history = []
        for turn in self.conversation_history:
            parts_data = turn.get('parts', [])
            if isinstance(parts_data, str):
                parts_list = [parts_data]
            elif isinstance(parts_data, list):
                parts_list = parts_data
            else:
                continue

            parts_objects = [types.Part.from_text(text=part) for part in parts_list if isinstance(part, str)]

            if parts_objects:
                api_history.append(types.Content(role=turn['role'], parts=parts_objects))
        return api_history

    def _clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        cleaned = text.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    def generate_response(self, user_input: str, formatted_prompt: str, screenshot_path: Optional[str] = None) -> List[NikoResponse] | None:
        current_turn = {'role': 'user', 'parts': [user_input]}
        parts = []
        
        # Create the content parts for the API request
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                # Add image content if screenshot was taken
                with open(screenshot_path, 'rb') as f:
                    image_bytes = f.read()
                
                # Save the screenshot path in history
                current_turn['screenshot'] = screenshot_path
                
                # Add text content first, then image
                parts.append(types.Part.from_text(text=user_input))
                parts.append(types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'))
                print(f"Including screenshot from {screenshot_path} in API request")
            except Exception as e:
                print(f"Error reading screenshot file: {e}")
                # If image fails, just use text
                parts.append(types.Part.from_text(text=user_input))
        else:
            # Standard text-only content
            parts.append(types.Part.from_text(text=user_input))

        # Create API content with parts
        user_content = types.Content(role='user', parts=parts)
        
        # Build full history for API
        full_history_for_api = self._format_history_for_api()
        full_history_for_api.append(user_content)

        try:
            request_config = GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=self.safety_settings,
                system_instruction=types.Content(parts=[types.Part.from_text(text=formatted_prompt)]),
            )

            # --- Debug Print Statements ---
            print("\n--- Sending Request to AI ---")
            print(f"Model: {self.model_name}")
            print(f"User Input: {user_input}")
            print(f"With Screenshot: {'Yes' if screenshot_path and os.path.exists(screenshot_path) else 'No'}")
            print("System Instruction (Prompt):")
            print(formatted_prompt)
            print("Conversation History Sent:")
            print(f"  - Turns: {len(full_history_for_api)}")
            print("Safety Settings:")
            for setting in self.safety_settings:
                print(f"  - Category: {setting.category.name}, Threshold: {setting.threshold.name}")
            print("Request Config:")
            print(f"  - Response MIME Type: {request_config.response_mime_type}")
            print("--- End Debug Info ---\n")
            # --- End Debug Print Statements ---

            response = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=full_history_for_api,
                        config=request_config,
                    )
                    break
                except errors.APIError as e:
                    status = getattr(e, "http_status", None) or getattr(e, "code", None)
                    if status in (429, 500, 503) and attempt < MAX_RETRIES - 1:
                        backoff = INITIAL_BACKOFF * (2 ** attempt)
                        print(f"APIError {status}, retrying in {backoff}s (attempt {attempt+1})")
                        time.sleep(backoff)
                        continue
                    print(f"APIError {status}: {e}")
                    self.conversation_history.append(current_turn)
                    msg_map = {
                        400: "(Error: malformed request or billing issue.)",
                        403: "(Error: access key invalid.)",
                        404: "(Error: model not found.)",
                        504: "(Error: request timed out.)",
                    }
                    face_map = {400: "confused", 403: "scared", 404: "confused", 504: "sad"}
                    text = self._clean_text(msg_map.get(status, "(Error: API failure.)"))
                    face = face_map.get(status, "scared")
                    return [NikoResponse(text=text, face=face, speed="normal", bold=False, italic=False)]
            if not response:
                self.conversation_history.append(current_turn)
                text = self._clean_text("(Error: no response after retries.)")
                return [NikoResponse(text=text, face="scared", speed="normal", bold=False, italic=False)]

            if not response.candidates:
                print("Error: AI response was blocked.")
                try:
                    print(f"Block Reason: {response.prompt_feedback.block_reason.name}")
                except AttributeError:
                    pass
                self.conversation_history.append(current_turn)
                error_text = self._clean_text("(Error: My thoughts were blocked!)")
                return [NikoResponse(text=error_text, face="scared", speed="normal", bold=False, italic=False)]

            response_text = response.candidates[0].content.parts[0].text
            response_data = json.loads(response_text)
            ai_response_obj = AIResponse(**response_data)

            for segment in ai_response_obj.segments:
                segment.text = self._clean_text(segment.text)

            self.conversation_history.append(current_turn)
            self.conversation_history.append({'role': 'model', 'parts': [ai_response_obj.model_dump_json()]})
            self._save_history()  # Save after successful interaction

            return ai_response_obj.segments

        except json.JSONDecodeError as e:
            print(f"Error: AI response is not valid JSON: {e}")
            raw_resp_text = "N/A"
            if 'response' in locals() and response.candidates:
                try:
                    raw_resp_text = response.candidates[0].content.parts[0].text
                except (AttributeError, IndexError):
                    pass
            print(f"Raw response text: {raw_resp_text}")
            self.conversation_history.append(current_turn)
            error_text = self._clean_text("(Error: I had trouble thinking...)")
            return [NikoResponse(text=error_text, face="scared", speed="normal", bold=False, italic=False)]
        except ValidationError as e:
            print(f"Error: AI response structure mismatch (AIResponse): {e}")
            print(f"Raw data: {response_data if 'response_data' in locals() else 'N/A'}")
            self.conversation_history.append(current_turn)
            error_text = self._clean_text("(Error: My thoughts got jumbled...)")
            return [NikoResponse(text=error_text, face="confused", speed="normal", bold=False, italic=False)]
        except Exception as e:
            print(f"An unexpected error occurred during AI generation: {e}")
            if 'current_turn' in locals():
                self.conversation_history.append(current_turn)
            error_text = self._clean_text("(Error: Something unexpected went wrong.)")
            return [NikoResponse(text=error_text, face="scared", speed="normal", bold=False, italic=False)]

    def get_initial_greeting(self, formatted_prompt: str, previous_exit_status: str | None) -> List[NikoResponse] | None:
        """Generates the initial message, considering previous exit status if history exists."""
        if self.conversation_history:
            print(f"Existing history found. Previous exit status: {previous_exit_status}")
            if previous_exit_status == config.EXIT_STATUS_NORMAL_AI:
                # History exists and the AI ended the last session normally
                reconnect_message = (
                    "(SYSTEM: You previously ended the conversation using [quit] or [quit_forced]. "
                    "The user has now returned. Greet them back and continue the conversation naturally "
                    "based on the provided history. Do not explicitly mention the word 'SYSTEM' to the user.)"
                )
                print("Generating 'user returned after AI quit' message.")
            else: # Assume abrupt quit (config.EXIT_STATUS_ABRUPT or None/unexpected value)
                # History exists, but the last session ended unexpectedly or by user action
                reconnect_message = (
                    "(SYSTEM: The previous session ended, possibly abruptly or by the user closing the application. "
                    "The user has now returned. Acknowledge their return briefly and continue the conversation naturally "
                    "based on the provided history. Do not explicitly mention the word 'SYSTEM' to the user.)"
                )
                print("Generating 'user returned after abrupt/user quit' message.")

            # Call generate_response with the appropriate system message
            return self.generate_response(reconnect_message, formatted_prompt)
        else:
            # No history, proceed with standard initial greeting
            print("No history found. Generating standard initial greeting.")
            greeting_prompt_input = "(Start the conversation by greeting the user as Niko.)"
            # Clear history just in case (should be empty anyway)
            self.conversation_history = []
            return self.generate_response(greeting_prompt_input, formatted_prompt)
