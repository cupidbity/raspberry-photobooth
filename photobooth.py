"""
Photobooth - welcome screen, then live preview, then capture, then print.
"""
import os
import time
from pathlib import Path
from datetime import datetime

os.environ.setdefault("SDL_VIDEODRIVER", "wayland")

import pygame
from picamera2 import Picamera2
from PIL import Image
from gpiozero import Button
from escpos.printer import File as EscposFile

# --- Configuration ---
SCREEN_W, SCREEN_H = 800, 480
SQUARE_SIZE = 480
SQUARE_X = (SCREEN_W - SQUARE_SIZE) // 2  # 160
SQUARE_Y = 0
CAMERA_RES = (800, 480)
CAPTURE_RES = (1920, 1080)
COUNTDOWN_SECONDS = 3
PRINTER_DEVICE = "/dev/usb/lp0"
PRINTER_WIDTH_PX = 384
BUTTON_PIN = 17

ASSETS_DIR = Path.home() / "photobooth" / "assets"
PHOTOS_DIR = Path.home() / "photobooth" / "captures"
BACKGROUND_FILE = ASSETS_DIR / "screen.png"
FONT_FILE = ASSETS_DIR / "BERKY.ttf"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# State machine
STATE_WELCOME = "welcome"
STATE_PREVIEW = "preview"
STATE_COUNTDOWN = "countdown"
STATE_PRINTING = "printing"


def frame_to_square_surface(frame):
    """Center-crop 800x480 camera frame to 480x480 and return as pygame surface."""
    crop_x_start = (frame.shape[1] - 480) // 2
    cropped = frame[:, crop_x_start:crop_x_start + 480, :]
    return pygame.surfarray.make_surface(cropped.swapaxes(0, 1)[:, :, ::-1])


def crop_pygame_image_to_square(surface):
    """Center-crop a pygame surface to a square."""
    w, h = surface.get_size()
    size = min(w, h)
    left = (w - size) // 2
    top = (h - size) // 2
    cropped = pygame.Surface((size, size))
    cropped.blit(surface, (0, 0), area=pygame.Rect(left, top, size, size))
    return pygame.transform.scale(cropped, (SQUARE_SIZE, SQUARE_SIZE))


def draw_text_top(screen, text, font, color, y=20):
    """Draw text horizontally centered at the top of the screen."""
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(SCREEN_W // 2, y + surf.get_height() // 2))
    screen.blit(surf, rect)


def print_photo(image_path):
    p = EscposFile(PRINTER_DEVICE)
    try:
        # Reset and set density/heat each time
        p._raw(b"\x1b\x40")              # ESC @ - initialize
        time.sleep(0.1)
        p._raw(b"\x12\x23\x0A")          # DC2 # 10 - density ~100%
        p._raw(b"\x1b\x37\x07\x50\x02")  # ESC 7 - default heat params
        time.sleep(0.1)

        img = Image.open(image_path)
        size = min(img.width, img.height)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))
        img = img.resize((PRINTER_WIDTH_PX, PRINTER_WIDTH_PX), Image.LANCZOS)
        img = img.rotate(180)            # Flip 180 so it prints right-side-up
        img = img.convert("L")

        p.image(img, impl="bitImageRaster")
        p.text("\n\n\n\n")
        time.sleep(2)
    finally:
        p.close()


def main():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    # Camera
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration(
        main={"size": CAMERA_RES, "format": "RGB888"}
    )
    picam2.configure(preview_config)
    picam2.start()

    # Button
    button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)

    # Pygame
    pygame.init()
    screen = pygame.display.set_mode(
        (SCREEN_W, SCREEN_H),
        pygame.FULLSCREEN | pygame.NOFRAME
    )
    pygame.display.set_caption("Photobooth")
    pygame.mouse.set_visible(False)

    # Load background
    background = pygame.image.load(str(BACKGROUND_FILE)).convert()
    if background.get_size() != (SCREEN_W, SCREEN_H):
        background = pygame.transform.scale(background, (SCREEN_W, SCREEN_H))

    # Load custom font at multiple sizes
    font_countdown = pygame.font.Font(str(FONT_FILE), 120)
    font_printing = pygame.font.Font(str(FONT_FILE), 60)

    # Debounce: ignore presses immediately after state change
    DEBOUNCE = 0.4

    clock = pygame.time.Clock()
    state = STATE_WELCOME
    state_start = time.time()
    last_capture_path = None
    print("Photobooth running. Press ESC or Q to quit.")

    running = True
    while running:
        now = time.time()
        elapsed = now - state_start

        triggered = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                triggered = True

        if button.is_pressed:
            triggered = True

        if elapsed < DEBOUNCE:
            triggered = False

        screen.blit(background, (0, 0))

        if state == STATE_WELCOME:
            if triggered:
                state = STATE_PREVIEW
                state_start = now

        elif state == STATE_PREVIEW:
            frame = picam2.capture_array("main")
            screen.blit(frame_to_square_surface(frame), (SQUARE_X, SQUARE_Y))
            if triggered:
                state = STATE_COUNTDOWN
                state_start = now

        elif state == STATE_COUNTDOWN:
            frame = picam2.capture_array("main")
            screen.blit(frame_to_square_surface(frame), (SQUARE_X, SQUARE_Y))

            remaining = COUNTDOWN_SECONDS - int(elapsed)
            if remaining > 0:
                draw_text_top(screen, str(remaining), font_countdown, WHITE, y=10)
            else:
                # Flash
                screen.fill(WHITE)
                pygame.display.flip()
                pygame.time.wait(80)

                # Capture
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                last_capture_path = PHOTOS_DIR / f"photo_{ts}.jpg"

                capture_config = picam2.create_still_configuration(
                    main={"size": CAPTURE_RES}
                )
                picam2.switch_mode_and_capture_file(
                    capture_config, str(last_capture_path)
                )
                picam2.stop()
                picam2.configure(preview_config)
                picam2.start()

                state = STATE_PRINTING
                state_start = time.time()

        elif state == STATE_PRINTING:
            if last_capture_path and last_capture_path.exists():
                photo = pygame.image.load(str(last_capture_path))
                photo = crop_pygame_image_to_square(photo)
                screen.blit(photo, (SQUARE_X, SQUARE_Y))
            draw_text_top(screen, "Printing...", font_printing, WHITE, y=10)

            if elapsed < 0.1:
                pygame.display.flip()
                try:
                    if last_capture_path:
                        print_photo(last_capture_path)
                except Exception as e:
                    print(f"Print error: {e}")

            if elapsed >= 5.0:
                state = STATE_WELCOME
                state_start = time.time()

        pygame.display.flip()
        clock.tick(30)

    picam2.stop()
    pygame.quit()
    print("Photobooth stopped.")


if __name__ == "__main__":
    main()
