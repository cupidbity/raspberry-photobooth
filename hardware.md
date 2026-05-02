# Hardware Setup

## Components

| Component | Notes |
|---|---|
| Raspberry Pi 5 | 4GB or 8GB |
| Freenove 5" DSI screen | 800x480, FT5x06 capacitive touch |
| OV5647 camera | Or any Pi-compatible CSI camera |
| CSN-A4L thermal printer | USB + TTL serial; we use USB |
| Arcade button (24mm illuminated) | .110 spade terminals |
| 12V LiPo battery | Main power source |
| 12V to 5V DC-DC converter | Steps battery down to 5V |
| WAGO lever connectors (3-port) | Splits 5V rail to Pi and printer |

## Power architecture

This build runs entirely off a 12V LiPo battery. The power chain looks like this:

```
12V LiPo battery
      |
      v
12V to 5V DC-DC converter
      |
      v
   +5V rail  -----+----- WAGO connector (+)  ---> Raspberry Pi (USB-C)
      |           |
      |           +----- WAGO connector (+)  ---> Printer VH (pin 3)
      |
   GND rail  -----+----- WAGO connector (-)  ---> Raspberry Pi GND
                  |
                  +----- WAGO connector (-)  ---> Printer GND (pin 1)
```

Two 3-port WAGO lever connectors split the converter's 5V output:

- **WAGO #1 (positive rail):** converter +5V in, Pi +5V out, printer VH out
- **WAGO #2 (ground rail):** converter GND in, Pi GND out, printer GND out

This arrangement lets the Pi and printer share the same battery and converter while keeping the wiring tidy and easy to re-route. WAGOs are tool-free, so you can rewire on the fly without crimping or soldering.

### Why both share the same converter

Earlier in development the printer was powered separately from the Pi (Pi on a wall USB-C, printer on its own 5V supply) because the print head's 1.5A peak draw was suspected to be browning out a single shared supply. Once we confirmed the DC-DC converter could handle the combined load (5V/5A rated, well above the ~3-4A combined steady draw), it was simpler to consolidate to one power source via WAGOs.

If you replicate this and run into print quality issues that look like power sag (blank prints, faint prints, Pi resetting during prints), split them onto separate supplies.

### Powering the Pi via 5V GPIO is NOT what's happening here

Important clarification: the Pi is powered via its **USB-C port**, not the GPIO 5V pins. The WAGO splits the converter output into two USB-C-compatible 5V feeds: one goes through a USB-C cable into the Pi, the other goes to the printer's bare-wire VH/GND pins.

Powering the Pi 5 via the GPIO 5V pins bypasses the polyfuse and power negotiation circuitry; it works but offers no protection against shorts or surges. Always go through USB-C if possible.

## Critical notes

### Pi 5 needs 22-pin camera/display cables

The Pi 5's CAM/DISP ports are 22-pin / 0.5mm pitch - physically different from older Pi 4 cameras' 15-pin / 1.0mm cables. If your camera or screen came with the older cable, you'll need a 22 to 15-pin adapter cable.

### Camera must be in the OTHER CAM/DISP port from the screen

Pi 5 has two ports, both labeled CAM/DISP. They're functionally identical, but only one camera and one display can be connected at a time. Use one for the screen, the other for the camera.

## Wiring summary

### Camera (OV5647)
Connected via Pi 5 22-pin CAM/DISP port (whichever one isn't used by the screen). 22-pin end at the Pi, 15-pin end at the camera board.

### Display (Freenove DSI)
Connected via the other Pi 5 22-pin CAM/DISP port using the included 16cm "for 5" cable. Touch input is delivered over the same DSI cable - no separate USB needed.

### Thermal printer (CSN-A4L)
Connected to the Pi via USB cable to any USB-A port for data. Power comes from the WAGO setup described above:
- Printer power port pin 1 (GND) -> WAGO ground rail
- Printer power port pin 3 (VH) -> WAGO +5V rail
- The TTL data port on the printer is unused

### Arcade button (24mm illuminated)

The button has 4 spade terminals: 2 for the microswitch, 2 for the LED. Standard arcade button quick-connect crimp wires (.110 size, female spade) didn't grip the Pi's GPIO header reliably, and DuPont-to-spade adapters were loose inside the spade housings. To get a solid, permanent connection, the spade quick-connects were cut off and **wires were soldered directly to the wires that go to the GPIO header**.

| Button terminal | Pi GPIO header pin | Function |
|---|---|---|
| Microswitch (1) | Pin 9 | GND |
| Microswitch (2) | Pin 11 (GPIO 17) | Input |
| LED (+) | Pin 2 | 5V |
| LED (-) | Pin 14 | GND |

The microswitch is not polarity-sensitive - either of its two terminals can go to GND or to GPIO. The LED has marked + and - terminals on the gray plastic housing.

The Pi's internal pull-up resistor on GPIO 17 is enabled in software (via `gpiozero.Button(17, pull_up=True)`), so no external resistor is needed for the button.

## Initial setup gotchas

- **Always shut down before adjusting CSI/DSI cables.** Hot-plugging can damage connectors.
- **Camera detection happens at boot.** If you reseat a CSI cable, you must reboot for the kernel to re-scan; the system will not pick up a newly connected camera mid-session.
- **The printer auto-detects as `/dev/usb/lp0`** on Bookworm. No driver needed.
- **The DSI screen auto-detects** with `display_auto_detect=1` - no overlay needed for the Freenove panel.
- **WAGO lever connectors** require ~10mm of stripped wire and the lever fully lifted before insertion. Always tug-test each wire after closing the lever.
