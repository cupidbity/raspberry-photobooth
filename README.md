# Photobooth

A Raspberry Pi 5 photobooth with live preview, touchscreen UI, and thermal receipt printer output.

## Features

- Live camera preview on a 5" DSI touchscreen
- Trigger via touchscreen tap or arcade button
- 3-second countdown with custom font
- Auto-print captured photo on a thermal receipt printer
- Custom welcome screen design

## Hardware

- Raspberry Pi 5
- Freenove 5" DSI touchscreen (800x480, FT5x06 touch)
- OV5647 camera module (Pi Camera v1 compatible)
- CSN-A4L thermal receipt printer (USB)
- Arcade-style illuminated push button
- 12V LiPo battery + 12V to 5V DC-DC converter (printer power)

Most items can be found here: [Amazon List](https://www.amazon.com/shop/cupidbity/list/DE4TQPVUFN4V?ref_=aipsflist)

Thermal printer: [Mini Thermal Receipt Printer (The Pi Hut)](https://thepihut.com/products/mini-thermal-receipt-printer?srsltid=AfmBOoqyFy_vYgifQd-CT2KruQv0nRyC9_tgL9VE92RPIDdgnvrLr6e5)

See [`docs/hardware.md`](docs/hardware.md) for wiring details.

## Software setup

### 1. Flash Raspberry Pi OS (64-bit) and enable SSH/Wi-Fi via Pi Imager.

### 2. Install system packages

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-pil python3-pip python3-venv git rpicam-apps
```

### 3. Clone and set up the project

```bash
cd ~
git clone https://github.com/cupidbity/raspberry-photobooth photobooth
cd photobooth
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure `/boot/firmware/config.txt`

Make sure these are set:

```
camera_auto_detect=1
display_auto_detect=1
dtoverlay=vc4-kms-v3d
```

### 5. Connect the printer via USB

The printer should appear at `/dev/usb/lp0`. Verify:

```bash
ls /dev/usb/lp*
```

### 6. Wire the arcade button

- Microswitch -> GPIO 17 (Pi pin 11) and GND (Pi pin 9)
- LED -> 5V (Pi pin 2) and GND (Pi pin 14)

### 7. Run

```bash
sudo -E XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 SDL_VIDEODRIVER=wayland ~/photobooth/venv/bin/python ~/photobooth/photobooth.py

```

Or set up an alias (recommended):

```bash
echo 'alias photobooth="sudo -E XDG_RUNTIME_DIR=/run/user/\$(id -u) WAYLAND_DISPLAY=wayland-0 SDL_VIDEODRIVER=wayland ~/photobooth/venv/bin/python ~/photobooth/photobooth.py"' >> ~/.bashrc
source ~/.bashrc
photobooth
```

## Flow

1. **Welcome** - Custom design fills the screen. Wait for input.
2. **Live preview** - Camera feed appears in a 480x480 square overlay on top of the welcome design.
3. **Countdown** - Tap or button press starts a 3-second countdown in custom font at the top.
4. **Capture** - White flash, full-resolution photo captured.
5. **Print** - Captured photo displays in the square with "Printing..." overlay; photo prints on thermal printer.
6. **Returns to welcome** after a few seconds.

## Configuration

Edit constants at the top of `photobooth.py`:

- `SCREEN_W`, `SCREEN_H` - display resolution (800x480 default)
- `SQUARE_SIZE` - preview area size (480 default)
- `COUNTDOWN_SECONDS` - countdown duration (3 default)
- `CAPTURE_RES` - capture resolution (1920x1080 default)
- `PRINTER_DEVICE` - printer device path (`/dev/usb/lp0` default)
- `BUTTON_PIN` - GPIO pin for the arcade button (17 default)

### Print quality

In the `print_photo()` function, adjust:

- Density (`b"\x12\x23\x0A"`) - change `0x0A` (100%) higher for darker, lower for lighter
- Heating (`b"\x1b\x37\x07\x50\x02"`) - see CSN-A4L manual for details

## Photo storage

Captured photos are saved to `~/photobooth/captures/photo_YYYYMMDD_HHMMSS.jpg`.

## Quitting

Press `ESC` or `Q` on a connected keyboard, or `Ctrl+C` in the terminal.

## License

MIT
