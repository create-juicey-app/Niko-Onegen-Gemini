import pygame
import config
import math # For pulsing alpha

class RenderingMixin:
    """Mixin class for handling the main rendering loop."""

    def render(self):
        """Main rendering function to draw all GUI elements."""
        # Check if history view is active, if so, skip normal rendering
        if getattr(self, 'is_history_active', False):
            return # Don't render the normal UI

        # Get delta time for effects that might need it (like pixel effect rate)
        dt = 0
        if hasattr(self, 'clock'):
             dt = self.clock.get_time() / 1000.0

        is_forced_quitting = getattr(self, 'is_forced_quitting', False)

        if is_forced_quitting:
            # --- Forced Quit Rendering ---
            self.screen.fill((0, 0, 0)) # Start with a black void

            # Create a temporary surface for all UI elements that will be shaken
            ui_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
            ui_surface.fill((0, 0, 0, 0)) # Make it transparent initially

            # 1. Render background onto the UI surface (using method from RenderingComponentsMixin)
            self.render_background_and_overlay(ui_surface)

            # 2. Render Textbox onto the UI surface
            if hasattr(self, 'textbox_img'):
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                ui_surface.blit(self.textbox_img, textbox_rect)

            # 3. Render Face onto the UI surface (use current face)
            if hasattr(self, 'current_face_image') and self.current_face_image:
                face_x = self.textbox_x + config.FACE_OFFSET_X
                face_y = self.textbox_y + config.FACE_OFFSET_Y
                ui_surface.blit(self.current_face_image, (face_x, face_y))

            # 4. Render Text onto the UI surface (using method from RenderingComponentsMixin)
            if hasattr(self, 'draw_animated_text'):
                original_char_index = getattr(self, 'current_char_index', 0)
                original_is_animating = getattr(self, 'is_animating', False)
                self.current_char_index = getattr(self, 'total_chars_to_render', 0) # Force full render
                self.is_animating = False # Ensure it draws statically
                self.draw_animated_text(target_surface=ui_surface)
                self.current_char_index = original_char_index
                self.is_animating = original_is_animating

            # 5. Blit the combined UI surface onto the main screen with shake offset
            shake_x = getattr(self, 'shake_offset_x', 0)
            shake_y = getattr(self, 'shake_offset_y', 0)
            self.screen.blit(ui_surface, (shake_x, shake_y))

            # 6. Render forced quit specific effects (pixels) on top
            if hasattr(self, 'render_forced_quit_effects'):
                self.render_forced_quit_effects(dt)
                if hasattr(self, 'random_pixel_overlay') and self.random_pixel_overlay:
                    self.screen.blit(self.random_pixel_overlay, (0,0))

        else:
            # --- Normal Rendering ---
            render_surface = self.screen # Render directly to the screen

            # 1. Render Background and Menu Overlay (using method from RenderingComponentsMixin)
            self.render_background_and_overlay(render_surface)

            # 2. Render Textbox
            if hasattr(self, 'textbox_img'):
                textbox_rect = self.textbox_img.get_rect(topleft=(self.textbox_x, self.textbox_y))
                render_surface.blit(self.textbox_img, textbox_rect)

            # 3. Render Face (potentially pulsing if AI is thinking)
            face_x = self.textbox_x + config.FACE_OFFSET_X
            face_y = self.textbox_y + config.FACE_OFFSET_Y
            face_to_draw = None
            apply_alpha_pulse = False

            ai_is_thinking = getattr(self, 'ai_is_thinking', False)
            last_face = getattr(self, 'last_face_image', None)
            current_face = getattr(self, 'current_face_image', None)

            if ai_is_thinking:
                if last_face:
                    face_to_draw = last_face
                    apply_alpha_pulse = True
                elif current_face:
                     face_to_draw = current_face
            elif current_face:
                face_to_draw = current_face

            if face_to_draw:
                if apply_alpha_pulse:
                    pulse_speed = 4.0
                    min_alpha = 80
                    max_alpha = 200
                    alpha_range = max_alpha - min_alpha
                    alpha = min_alpha + (alpha_range / 2) * (1 + math.sin(pygame.time.get_ticks() * 0.001 * pulse_speed))
                    alpha = int(max(0, min(255, alpha)))

                    try:
                        face_copy = face_to_draw.copy()
                        face_copy.set_alpha(alpha)
                        render_surface.blit(face_copy, (face_x, face_y))
                    except pygame.error as e:
                        print(f"Error applying alpha to face: {e}. Drawing opaque.")
                        render_surface.blit(face_to_draw, (face_x, face_y))
                else:
                    render_surface.blit(face_to_draw, (face_x, face_y))

            # 4. Render Dialogue Text (Animated) (using method from RenderingComponentsMixin)
            if not ai_is_thinking:
                if hasattr(self, 'draw_animated_text'):
                    self.draw_animated_text(target_surface=render_surface)

            # 5. Render Advance Arrow (if applicable)
            should_draw_arrow = (getattr(self, 'draw_arrow', False) and
                                 getattr(self, 'arrow_visible', False) and
                                 not getattr(self, 'is_input_active', False) and
                                 not getattr(self, 'is_choice_active', False) and
                                 not getattr(self, 'is_paused', False))

            if should_draw_arrow and hasattr(self, 'arrow_img'):
                arrow_x = self.textbox_x + config.ARROW_OFFSET_X
                arrow_y = getattr(self, 'arrow_base_y', self.textbox_y + config.ARROW_OFFSET_Y) + \
                          getattr(self, 'arrow_offset_y', 0)
                arrow_rect = self.arrow_img.get_rect(centerx=arrow_x, top=arrow_y)
                render_surface.blit(self.arrow_img, arrow_rect)

            # 6. Render Input Box (if active) (using method from RenderingComponentsMixin)
            if getattr(self, 'is_input_active', False):
                self.render_input_box(render_surface)

            # 7. Render Multiple Choice Box (if active) (using method from RenderingComponentsMixin)
            if getattr(self, 'is_choice_active', False):
                 if hasattr(self, 'draw_multiple_choice'):
                     self.draw_multiple_choice(target_surface=render_surface)

            # 8. Render Options Menu (if active) (using method from RenderingComponentsMixin)
            if getattr(self, 'is_options_menu_active', False):
                 if hasattr(self, 'draw_options_menu'):
                     self.draw_options_menu(render_surface)

        pygame.display.flip() # Update the full display
