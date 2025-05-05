import pygame
import re
import config
import traceback  # Import traceback for detailed error logging

# Pre-compile regexes for efficiency
_marker_regex_str = r'(\[face:[a-zA-Z0-9_]+\]|\[sfx:[a-zA-Z0-9_]+\])'
_word_splitter_regex = re.compile(rf'(\s+|{_marker_regex_str})')
_face_marker_regex = re.compile(r'\[face:([a-zA-Z0-9_]+)\]')
_sfx_marker_regex = re.compile(r'\[sfx:([a-zA-Z0-9_]+)\]')
_space_before_marker_regex = re.compile(r'\s+(\[(?:face|sfx):[^\]]+\])')
_marker_regex_combined = re.compile(_marker_regex_str)

def wrap_text(text: str, font: pygame.font.Font, max_width_pixels: int) -> tuple[list[str], int]:
    """Wraps dialogue text considering inline markers."""
    rendered_lines = []
    current_text_stripped = text.strip()

    if not current_text_stripped or not font:
        return [], 0  # Nothing to wrap

    parts = _word_splitter_regex.split(current_text_stripped)
    parts = [p for p in parts if p]  # Remove empty strings from split

    wrapped_paragraphs = []
    current_line = ""
    current_line_width = 0

    for part in parts:
        is_face_marker = _face_marker_regex.match(part)
        is_sfx_marker = _sfx_marker_regex.match(part)
        is_marker = is_face_marker or is_sfx_marker
        is_space = part.isspace()

        if is_marker:
            current_line += part
            continue
        elif is_space:
            try:
                space_width = font.size(" ")[0] if current_line else 0
            except (pygame.error, AttributeError): space_width = 0

            if current_line_width + space_width <= max_width_pixels:
                current_line += part
                current_line_width += space_width
            else:
                wrapped_paragraphs.append(current_line)
                current_line = part
                current_line_width = space_width
        else:  # It's a word
            word = part
            try:
                word_surface = font.render(word, True, (0, 0, 0))
                word_width = word_surface.get_width()
                space_width = 0
                if current_line and not current_line.endswith(" ") and not is_marker:
                    if not _face_marker_regex.search(current_line[-20:]) and \
                       not _sfx_marker_regex.search(current_line[-20:]):
                          last_char = current_line[-1] if current_line else ''
                          if last_char not in ['(', '[']:
                               space_width = font.size(" ")[0]
            except (pygame.error, AttributeError) as e:
                 print(f"Warning: Error rendering word '{word}' for wrapping: {e}")
                 word_width = 0
                 space_width = 0

            if current_line_width + space_width + word_width <= max_width_pixels:
                if current_line and space_width > 0:
                     current_line += " "
                     current_line_width += space_width
                current_line += word
                current_line_width += word_width
            else:
                wrapped_paragraphs.append(current_line)
                current_line = word
                current_line_width = word_width

    wrapped_paragraphs.append(current_line)

    final_lines = []
    for line in wrapped_paragraphs:
        cleaned_line = _space_before_marker_regex.sub(r'\1', line.strip())
        if cleaned_line:
            final_lines.append(cleaned_line)

    get_visible_char_count = 0
    for line in final_lines:
         line_without_markers = _marker_regex_combined.sub('', line)
         get_visible_char_count += len(line_without_markers)

    return final_lines, get_visible_char_count


def wrap_input_text(text: str, font: pygame.font.Font, max_width: int, cursor_pos: int = -1) -> tuple[list[str], tuple[int, int] | None]:
    """Wraps text for the input box and calculates cursor position. (Revised Logic + Error Handling)"""
    wrapped_lines = []
    cursor_line_char_pos = None

    try:  # Add top-level try-except
        # --- 1. Wrap Text ---
        current_line = ""
        current_width = 0
        line_start_index = 0  # Track start index of the current line in original text

        if max_width <= 0:  # Prevent errors with zero or negative width
            print(f"Warning: wrap_input_text called with max_width <= 0 ({max_width}). Using 1.")
            max_width = 1

        for i, char in enumerate(text):
            if char == '\n':
                wrapped_lines.append(current_line)
                current_line = ""
                current_width = 0
                line_start_index = i + 1
                continue

            try:
                # Use size caching if available or handle potential errors
                char_width = font.size(char)[0]
            except (pygame.error, AttributeError) as e:
                # Fallback estimate if font.size fails
                print(f"Warning: font.size failed for char '{char}': {e}. Estimating width.")
                char_width = font.get_height() // 2 if font.get_height() > 0 else 10

            # Check if adding the character exceeds max width
            # Special case: if the line is empty, always add the first character
            if current_line and current_width + char_width > max_width:
                # Find the last space to wrap nicely if possible
                wrap_index_in_line = current_line.rfind(' ')
                if wrap_index_in_line != -1:
                    # Wrap at the space
                    wrapped_lines.append(current_line[:wrap_index_in_line])
                    # Start new line with the part after the space + the current char
                    remainder = current_line[wrap_index_in_line+1:]
                    current_line = remainder + char
                    try:
                        current_width = font.size(current_line)[0]
                    except (pygame.error, AttributeError):
                        current_width = len(current_line) * (font.get_height() // 2 if font.get_height() > 0 else 10)
                    # Adjust line_start_index for the new line (relative to original text)
                    line_start_index += wrap_index_in_line + 1  # Start index is after the space
                else:
                    # No space found, force wrap mid-character/word
                    wrapped_lines.append(current_line)
                    current_line = char
                    try:
                        current_width = font.size(current_line)[0]
                    except (pygame.error, AttributeError):
                        current_width = len(current_line) * (font.get_height() // 2 if font.get_height() > 0 else 10)
                    # Adjust line_start_index (relative to original text)
                    line_start_index = i  # Start index is the current character
            else:
                # Add character to current line
                current_line += char
                current_width += char_width

        # Add the last line
        wrapped_lines.append(current_line)

        # Ensure wrapped_lines has at least one empty string if text was empty
        if not wrapped_lines and not text:
            wrapped_lines = [""]

        # --- 2. Find Cursor Position in Wrapped Lines ---
        if cursor_pos != -1:
            chars_counted = 0
            found = False
            for line_idx, line in enumerate(wrapped_lines):
                line_len = len(line)
                # Calculate the effective length of this line in the original text,
                # including the newline character if it's not the last line.
                # This helps map the overall cursor_pos correctly.
                effective_len_in_original = line_len + (1 if line_idx < len(wrapped_lines) - 1 else 0)

                # Check if the overall cursor_pos falls within the character range
                # represented by this wrapped line (relative to the original text).
                if chars_counted <= cursor_pos < chars_counted + effective_len_in_original:
                    # Calculate the character index *within this specific wrapped line*.
                    char_index_in_line = cursor_pos - chars_counted
                    # Ensure the calculated index doesn't exceed the actual length of the wrapped line.
                    # (This can happen if the cursor is conceptually where the newline would be).
                    char_index_in_line = min(char_index_in_line, line_len)

                    cursor_line_char_pos = (line_idx, char_index_in_line)
                    found = True
                    break
                chars_counted += effective_len_in_original

            # Handle cursor being exactly at the end of the entire text
            if not found and cursor_pos == len(text):
                last_line_idx = len(wrapped_lines) - 1
                # Ensure last_line_idx is valid before accessing wrapped_lines
                last_line_len = len(wrapped_lines[last_line_idx]) if wrapped_lines and last_line_idx >= 0 else 0
                cursor_line_char_pos = (max(0, last_line_idx), last_line_len)  # Use max(0,...) for safety
                found = True  # Mark as found

            # Fallback if cursor position calculation failed (should be rare with this logic)
            if not found:  # If still not found after checks
                print(f"Warning: Cursor position {cursor_pos} not located in wrapped text (revised). Defaulting to end.")
                last_line_idx = len(wrapped_lines) - 1 if wrapped_lines else 0
                last_line_len = len(wrapped_lines[last_line_idx]) if wrapped_lines and last_line_idx >= 0 else 0
                cursor_line_char_pos = (max(0, last_line_idx), max(0, last_line_len))

        # Final check for empty text case (only if cursor_pos is valid)
        if not text and cursor_pos == 0:  # More specific check for empty text cursor
            cursor_line_char_pos = (0, 0)  # Cursor at start of the single empty line

        # --- Reinforce: Ensure tuple if cursor_pos != -1 ---
        if cursor_pos != -1 and not isinstance(cursor_line_char_pos, tuple):
            print(f"CRITICAL WARNING: cursor_line_char_pos ended up as non-tuple ({type(cursor_line_char_pos)}: {cursor_line_char_pos}) despite cursor_pos={cursor_pos}. Forcing default.")
            last_line_idx = len(wrapped_lines) - 1 if wrapped_lines else 0
            last_line_len = len(wrapped_lines[last_line_idx]) if wrapped_lines and last_line_idx >= 0 else 0
            cursor_line_char_pos = (max(0, last_line_idx), max(0, last_line_len))
        # --- End Reinforcement ---

    except Exception as e:
        print(f"CRITICAL ERROR in wrap_input_text: {e}")
        print(traceback.format_exc())  # Print full traceback
        # Attempt to return safe defaults
        if not wrapped_lines: wrapped_lines = ["<Error>"]
        if cursor_pos != -1:
            cursor_line_char_pos = (0, 0)  # Default to start of first line on error
        else:
            cursor_line_char_pos = None  # Maintain None if cursor_pos was -1

    return wrapped_lines, cursor_line_char_pos
