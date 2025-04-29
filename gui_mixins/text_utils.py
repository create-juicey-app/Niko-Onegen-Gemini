import pygame
import re
import config

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
        return [], 0 # Nothing to wrap

    parts = _word_splitter_regex.split(current_text_stripped)
    parts = [p for p in parts if p] # Remove empty strings from split

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
        else: # It's a word
            word = part
            try:
                word_surface = font.render(word, True, (0,0,0))
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

    accurate_plain_char_count = 0
    for line in final_lines:
         line_without_markers = _marker_regex_combined.sub('', line)
         accurate_plain_char_count += len(line_without_markers)

    return final_lines, accurate_plain_char_count


def wrap_input_text(text: str, font: pygame.font.Font, max_width: int) -> tuple[list[str], list[int]]:
    """Wraps input text based on font size and max width, returning lines and start indices."""
    wrapped_lines = []
    line_start_indices = [0]
    current_wrap_line = ""
    original_text_ptr = 0

    words = re.split(r'(\s+)', text)
    words = [w for w in words if w]

    if not font:
        print("Error: Input font not available for wrapping.")
        return [text], [0]

    current_line_char_count = 0

    for word in words:
        is_space = word.isspace()
        test_line = current_wrap_line + word

        try:
            line_width = font.size(test_line)[0]

            if line_width <= max_width:
                current_wrap_line += word
                current_line_char_count += len(word)
            else:
                if current_wrap_line:
                    wrapped_lines.append(current_wrap_line)
                    line_start_indices.append(original_text_ptr)

                word_width = font.size(word)[0]

                if not is_space and word_width > max_width:
                    temp_long_word_line = ""
                    for char_idx, char in enumerate(word):
                        if font.size(temp_long_word_line + char)[0] <= max_width:
                            temp_long_word_line += char
                        else:
                            wrapped_lines.append(temp_long_word_line)
                            original_text_ptr += len(temp_long_word_line)
                            line_start_indices.append(original_text_ptr)
                            temp_long_word_line = char
                    current_wrap_line = temp_long_word_line
                    current_line_char_count = len(current_wrap_line)
                else:
                    if word_width <= max_width:
                        current_wrap_line = word.lstrip() if wrapped_lines else word
                        current_line_char_count = len(current_wrap_line)
                    else:
                         current_wrap_line = word
                         current_line_char_count = len(word)
        except pygame.error as e:
            print(f"Error calculating text size for wrapping: {e}")
            wrapped_lines.append(current_wrap_line)
            line_start_indices.append(original_text_ptr)
            current_wrap_line = word
            current_line_char_count = len(word)

        original_text_ptr += len(word)

    if current_wrap_line:
        wrapped_lines.append(current_wrap_line)

    if not text:
        return [], [0]

    return wrapped_lines, line_start_indices
