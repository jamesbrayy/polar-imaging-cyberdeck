# Polar Imaging Cyberdeck (PIC)

A portable, fully off-grid system designed to receive and decode weather satellite imagery from polar-orbiting and geostationary satellites via L-band radio. It allows independent operation in remote locations without reliance on mains power or network infrastructure.

## Features

- Reception of live weather images from multiple satellite types
- Fully autonomous operation with Raspberry Pi 4B (*in progress*)
- Servo-based azimuth-elevation dish rotator for precise tracking
- 3D-printed helicone antenna for optimized signal capture
- RTL-SDR Blog V4 dongle for wideband signal reception
- Modular and portable cyberdeck design employing a Pelican 1300 case suitable for outdoors use

## Key Hardware
### Cyberdeck
- **Raspberry Pi 4B (>4GB)** – onboard processing and decoding
- **Waveshare UPS Hat (E)** - battery management system
- **4 x 5000mAh 21700 Li-Ion Batteries** - for around 8 hours of runtime on a single charge
- **Waveshare 10.1-DSI-TOUCH-A** - colour and touchscreen-capable display
- **RTL-SDR Blog V4** – wideband software-defined radio for signal capture
- **Pelican 1300 Case** - houses the internals of the cyberdeck

### Antenna Module
- **3D-printed helicone antenna** – optimized for satellite frequencies (RHCP only)
- **Custom Az-El rotator** – servo-based azimuth and elevation control for accurate satellite tracking

## Software

- Custom Python TUI scripts for satellite tracking and image decoding
- Automated scheduling of satellite passes and data capture (*in progress*)
- Image post-processing and storage locally on the Pi (*in progress*)
- Optional telemetry logging and export for further analysis (*in progress*)

## Assembly Installation

1. Assemble antenna and rotator hardware according to schematics
2. Connect RTL-SDR and Raspberry Pi 4B
3. Clone repository:
   ```bash
   git clone https://github.com/username/polar-imaging-cyberdeck.git
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt

## Usage

- Run `python3 code/satellite/sattrack.py` from the root directory to start the manual satellite tracking and image capture terminal UI
- Autonomous reception is currently a work in progress and will be updated and documented upon completion
- Monitor pass logs and received images either through the UI or the local storage

## Notes

- The antenna rotator and mount is not strictly necessary as the 3D printed helicone dish can be manually aimed at a satellite for reception during a pass
  - This prevents autonomous reception for non-geostationary satellites
- If I were to redesign this with no budget restrictions I would be sure to replace the servo motors with stepper motors as they are much more suited to this application
- Designed for educational and hobbyist research applications and submitted for assessment as my final WACE ATAR Engineering project
