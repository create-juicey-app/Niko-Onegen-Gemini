from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold, GenerateContentConfig, SafetySetting
import json
import re
from pydantic import ValidationError

import config
from config import NikoResponse, AIResponse
from typing import List

class NikoAI:
    """Handles interaction with the Google Generative AI model."""

    def __init__(self, ai_model_name: str = config.AI_MODEL_NAME): # Accept model name
        if not config.GOOGLE_API_KEY:
            raise ValueError("Google API Key not configured.")
        try:
            self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google GenAI Client: {e}")

        self.model_name = ai_model_name # Use passed model name
        self.conversation_history = []
        self.safety_settings = [
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        ]

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

    def generate_response(self, user_input: str, formatted_prompt: str) -> List[NikoResponse] | None:
        current_turn = {'role': 'user', 'parts': [user_input]}
        full_history_for_api = self._format_history_for_api()
        full_history_for_api.append(types.Content(role='user', parts=[types.Part.from_text(text=user_input)]))

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
            print("System Instruction (Prompt):")
            print(formatted_prompt)
            print("Conversation History Sent:")
            # Optionally print the full history, or just a summary
            # print(json.dumps([{'role': c.role, 'parts': [p.text for p in c.parts]} for c in full_history_for_api], indent=2))
            print(f"  - Turns: {len(full_history_for_api)}")
            print("Safety Settings:")
            for setting in self.safety_settings:
                print(f"  - Category: {setting.category.name}, Threshold: {setting.threshold.name}")
            print("Request Config:")
            print(f"  - Response MIME Type: {request_config.response_mime_type}")
            print("--- End Debug Info ---\n")
            # --- End Debug Print Statements ---

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_history_for_api,
                config=request_config,
            )

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

            return ai_response_obj.segments

        except json.JSONDecodeError as e:
            print(f"Error: AI response is not valid JSON: {e}")
            raw_resp_text = "N/A"
            if 'response' in locals() and response.candidates:
                try: raw_resp_text = response.candidates[0].content.parts[0].text
                except (AttributeError, IndexError): pass
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

    def get_initial_greeting(self, formatted_prompt: str) -> List[NikoResponse] | None:
        greeting_prompt_input = "(Start the conversation by greeting the user as Niko.)"
        self.conversation_history = []
        return self.generate_response(greeting_prompt_input, formatted_prompt)
