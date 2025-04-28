import pygame
import time
import random
import math
import platform
if platform.system() == "Windows":
    import ctypes # Keep windows specific import here

class EffectsMixin:
    """Mixin class for handling visual effects like fades and forced quit."""

    def fade_out(self, duration=0.5):
        """Fades the screen to black over a specified duration."""
        start_time = time.time()
        # --- Render the current scene once before the loop ---
        # Ensure render method exists on self
        if hasattr(self, 'render'):
            self.render()
        else:
            print("Warning: render method not found for fade_out initial scene.")
            self.screen.fill((0,0,0)) # Fallback: fill screen black

        pygame.display.flip() # Ensure the rendered scene is on screen

        # Ensure fade_surface exists and is the correct size
        if not hasattr(self, 'fade_surface') or self.fade_surface.get_size() != (self.window_width, self.window_height):
            self.fade_surface = pygame.Surface((self.window_width, self.window_height))
            self.fade_surface.fill((0, 0, 0))

        while True:
            elapsed = time.time() - start_time
            alpha = min(255, int(255 * (elapsed / duration)))
            self.fade_surface.set_alpha(alpha)

            # --- Event handling during fade ---
            # Use the main handle_event method if it exists
            if hasattr(self, 'handle_event'):
                for event in pygame.event.get():
                    result = self.handle_event(event)
                    if result:
                        action, _ = result
                        # Check for quit actions specifically
                        if action == "initiate_quit" or action == "quit":
                            self.running = False # Set running flag directly
                            return # Exit fade immediately
            else: # Fallback basic quit handling
                 for event in pygame.event.get():
                      if event.type == pygame.QUIT:
                           self.running = False
                           return

            if not getattr(self, 'running', True): return # Check running flag
            # --- End event handling ---

            # --- Blit the fade surface on top of the last rendered frame ---
            # We don't re-render the scene, just draw the fade overlay
            # The initial scene was already drawn and flipped before the loop
            self.screen.blit(self.fade_surface, (0, 0))
            pygame.display.flip()

            if elapsed >= duration:
                break
            # Use self.clock if available
            clock = getattr(self, 'clock', None)
            if clock:
                clock.tick(60) # Limit frame rate during fade
            else:
                pygame.time.wait(16) # Approx 60fps wait

    def fade_in(self, duration=0.5):
        """Fades the screen in from black over a specified duration."""
        start_time = time.time()
        # --- Render the target scene once before the loop ---
        # Ensure render method exists on self
        if hasattr(self, 'render'):
            self.render() # Render the target scene state
            target_scene_capture = self.screen.copy() # Capture the rendered scene
        else:
            print("Warning: render method not found for fade_in target scene.")
            # Fallback: create a black surface as the target capture
            target_scene_capture = pygame.Surface((self.window_width, self.window_height))
            target_scene_capture.fill((0,0,0))


        # Ensure fade_surface exists and is the correct size
        if not hasattr(self, 'fade_surface') or self.fade_surface.get_size() != (self.window_width, self.window_height):
            self.fade_surface = pygame.Surface((self.window_width, self.window_height))
            self.fade_surface.fill((0, 0, 0))


        while True:
            elapsed = time.time() - start_time
            alpha = max(0, int(255 * (1 - (elapsed / duration))))
            self.fade_surface.set_alpha(alpha)

            # --- Event handling during fade ---
            # Use the main handle_event method if it exists
            if hasattr(self, 'handle_event'):
                for event in pygame.event.get():
                    result = self.handle_event(event)
                    if result:
                        action, _ = result
                        # Check for quit actions specifically
                        if action == "initiate_quit" or action == "quit":
                            self.running = False # Set running flag directly
                            return # Exit fade immediately
            else: # Fallback basic quit handling
                 for event in pygame.event.get():
                      if event.type == pygame.QUIT:
                           self.running = False
                           return

            if not getattr(self, 'running', True): return # Check running flag
            # --- End event handling ---

            # --- Blit the captured scene then the fade surface ---
            self.screen.blit(target_scene_capture, (0, 0)) # Blit the captured target scene first
            self.screen.blit(self.fade_surface, (0, 0)) # Blit the fade surface on top
            pygame.display.flip()

            if elapsed >= duration:
                break
            # Use self.clock if available
            clock = getattr(self, 'clock', None)
            if clock:
                clock.tick(60) # Limit frame rate during fade
            else:
                pygame.time.wait(16) # Approx 60fps wait

    def start_forced_quit(self):
        """Initializes the forced quit sequence state."""
        if getattr(self, 'is_forced_quitting', False): return # Already quitting

        print("Starting forced quit sequence...")
        self.is_forced_quitting = True
        self.forced_quit_timer = 0.0
        self.forced_quit_glitch_index = 0
        self.shake_timer = 0.0
        self.shake_intensity = 0.0
        self.shake_offset_x = 0
        self.shake_offset_y = 0

        self.current_random_pixel_rate = 0.0
        # Initialize the overlay surface for random pixels
        try:
            self.random_pixel_overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
            self.random_pixel_overlay.fill((0, 0, 0, 0)) # Transparent background
        except pygame.error as e:
            print(f"Error creating random pixel overlay surface: {e}")
            self.random_pixel_overlay = None # Disable effect if surface creation fails

        # Define constants for the effect if not already defined in __init__
        # These could be moved to __init__ or config
        self.forced_quit_glitch_delay = getattr(self, 'forced_quit_glitch_delay', 0.6)
        self.forced_quit_shake_start_delay = getattr(self, 'forced_quit_shake_start_delay', 0.2)
        glitch_sfx_count = len(getattr(self, 'glitch_sfx', []))
        self.forced_quit_duration = getattr(self, 'forced_quit_duration', self.forced_quit_glitch_delay * glitch_sfx_count + 1.0)
        self.max_shake_intensity = getattr(self, 'max_shake_intensity', 15)
        self.shake_ramp_up_time = getattr(self, 'shake_ramp_up_time', self.forced_quit_duration * 0.7)
        self.max_random_pixel_rate = getattr(self, 'max_random_pixel_rate', (self.window_width * self.window_height) / (self.forced_quit_duration * 0.8))
        self.random_pixel_ramp_up_time = getattr(self, 'random_pixel_ramp_up_time', self.forced_quit_duration * 0.6)


    def update_forced_quit(self, dt):
        """Updates the state of the forced quit effect."""
        if not getattr(self, 'is_forced_quitting', False): return

        self.forced_quit_timer += dt

        # --- Update Random Pixels ---
        if self.random_pixel_overlay:
            random_pixel_ramp_progress = min(1.0, self.forced_quit_timer / self.random_pixel_ramp_up_time)
            self.current_random_pixel_rate = self.max_random_pixel_rate * random_pixel_ramp_progress
            # (Pixel drawing happens in render phase)

        # --- Play Glitch Sounds ---
        glitch_sfx = getattr(self, 'glitch_sfx', [])
        next_glitch_time = self.forced_quit_glitch_index * self.forced_quit_glitch_delay
        if glitch_sfx and self.forced_quit_glitch_index < len(glitch_sfx) and self.forced_quit_timer >= next_glitch_time:
            sound_to_play = glitch_sfx[self.forced_quit_glitch_index]
            if sound_to_play:
                sound_to_play.play()
                print(f"Playing glitch SFX {self.forced_quit_glitch_index + 1}")
            else:
                print(f"Warning: Glitch SFX {self.forced_quit_glitch_index + 1} is None.")
            self.forced_quit_glitch_index += 1

        # --- Update Screen Shake ---
        if self.forced_quit_timer >= self.forced_quit_shake_start_delay:
            self.shake_timer += dt
            # Calculate ramp progress (ensure ramp up time is not zero)
            ramp_progress = 0.0
            if self.shake_ramp_up_time > 0:
                ramp_progress = min(1.0, self.shake_timer / self.shake_ramp_up_time)
            self.shake_intensity = self.max_shake_intensity * ramp_progress

            # Generate random offsets based on intensity
            self.shake_offset_x = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            self.shake_offset_y = random.randint(-int(self.shake_intensity), int(self.shake_intensity))

            # Stop text animation and sound during shake
            if getattr(self, 'is_animating', False):
                self.is_animating = False
                self.draw_arrow = False # Hide arrow as well
                active_sfx = getattr(self, 'active_text_sfx', None)
                if active_sfx and hasattr(active_sfx, 'stop') and active_sfx.get_num_channels() > 0:
                    active_sfx.stop()
        else:
            # No shake yet
            self.shake_offset_x = 0
            self.shake_offset_y = 0

        # --- Check for Quit Condition ---
        if self.forced_quit_timer >= self.forced_quit_duration:
            print("Forced quit duration reached. Setting running to False.")
            self.running = False # Signal the main loop to terminate


    def render_forced_quit_effects(self, dt):
        """Renders the screen shake and random pixel effects during forced quit."""
        if not getattr(self, 'is_forced_quitting', False): return

        # --- Render Random Pixels ---
        if self.random_pixel_overlay:
            num_random_pixels = int(self.current_random_pixel_rate * dt)
            for _ in range(num_random_pixels):
                try:
                    x = random.randint(0, self.window_width - 1)
                    y = random.randint(0, self.window_height - 1)
                    # Generate a random bright-ish color
                    r = random.randint(100, 255)
                    g = random.randint(100, 255)
                    b = random.randint(100, 255)
                    random_color = (r, g, b, 255) # Opaque pixels
                    self.random_pixel_overlay.set_at((x, y), random_color)
                except IndexError:
                    # This can happen if window size changes unexpectedly, ignore.
                    pass
                except pygame.error as e:
                    # Other Pygame errors (e.g., surface locked)
                    print(f"Warning: Pygame error setting random pixel: {e}")
                    pass

            # Blit the pixel overlay onto the main screen
            # The main render function should handle blitting this onto the final shaken surface
            # self.screen.blit(self.random_pixel_overlay, (0, 0)) # This might be incorrect placement

        # --- Screen Shake ---
        # The actual shake (blit offset) should be handled by the main render function
        # This mixin calculates self.shake_offset_x and self.shake_offset_y
        # The main render function uses these offsets when blitting the UI surface.
        pass
