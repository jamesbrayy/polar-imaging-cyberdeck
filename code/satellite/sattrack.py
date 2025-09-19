from skyfield.api import EarthSatellite, load, Topos, wgs84
from geopy.distance import geodesic
from datetime import datetime, timezone, timedelta
import requests, time, urllib3, re, os
import numpy as np
import urwid
from rich.prompt import Prompt
from rich.console import Console

# GPIO imports - wrapped in try/except for development environments
try:
    from gpiozero import AngularServo
    from gpiozero.pins.pigpio import PiGPIOFactory
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: GPIO libraries not available. Servo control will be simulated.")

# setup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()
tle_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather"
tle_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satellites.txt")
colourlist = ["white", "cyan", "dark_blue", "dark_gray", "blue", "magenta", "red", "yellow"]
palette = [
    ("black", "black", ""), ("dark_red", "dark red", ""), ("dark_green", "dark green", ""),
    ("brown", "brown", ""), ("dark_blue", "dark blue", ""), ("dark_magenta", "dark magenta", ""),
    ("dark_cyan", "dark cyan", ""), ("dark_gray", "dark gray", ""), ("gray", "light gray", ""),
    ("red", "light red", ""), ("green", "light green", ""), ("yellow", "yellow", ""),
    ("blue", "light blue", ""), ("magenta", "light magenta", ""), ("cyan", "light cyan", ""),
    ("white", "white", ""), ("border", "dark green", ""), ("button", "white", ""),
    ("button_focus", "white", "dark green"), ("slider", "white", "dark blue"),
    ("slider_focus", "black", "light cyan")
]

# ASCII world map (truncated for brevity)
ascii_map = [  # this ascii map is composed of braille characters and forms an equirectangular projection of the earth in terminal
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣠⣄⢠⣤⣤⣶⣾⣿⣿⣿⣿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠛⠂⠀⠀⠀⠀⠀⠀⢶⣶⡶⡶⠆⠀⠀⠀⠀⠐⠒⠀⠒⠒⣒⣀⡀⠀⠀⠀⠀⠀⠲⢶⢶⣤⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠄⠀⠀⠀⢀⣀⣀⣀⣀⣀⡀⠀⠀⢀⣀⣶⡾⣿⣿⣯⣿⣹⣿⣿⡟⣿⣿⣿⣶⣤⣄⡀⠀⠉⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⡀⠀⠀⠀⠀⠀⠰⠾⢋⠉⢡⣴⣤⣤⣴⣶⣿⣿⣿⣿⣿⣿⣿⣷⣶⣦⣶⣦⣠⣤⣭⣿⣥⣥⣀⣀⡀⠀⢀⢀⣀⠀"),
        list("⠻⠶⠆⠠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⣿⡏⠻⠿⣿⣿⠖⠀⠀⠾⣿⣿⣿⠿⠛⠉⠉⠠⢤⣤⠀⠀⠀⠀⠀⠀⣀⣴⣿⠿⣻⣿⣿⣟⣓⣦⣿⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"),
        list("⠀⠀⠀⠘⠛⣛⠿⠟⠛⠙⠛⠻⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣄⣀⠀⠀⢸⣿⣶⣴⣦⠀⠀⠀⠉⠙⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡄⠀⠘⢛⣿⠗⠀⣻⣿⣷⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠛⠛⠛⢉⣼⡟⠋⠉⠁⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣿⣿⣿⣿⠿⠟⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠚⠳⢿⣦⣶⣾⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣶⢲⠀⠀⠀⠙⠉⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣾⣿⣿⣿⡿⠻⠖⠀⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣄⣹⣿⠿⠿⣿⣿⣿⣿⣿⠏⠛⠹⢿⣿⡟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠁⠠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠺⣿⣿⣥⣤⣭⡠⠍⠙⠏⠹⠿⣿⣿⣿⣿⣿⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠙⣯⠀⣀⣠⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⡿⠿⠿⠿⡏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣾⣿⣿⣿⣿⣿⣷⣦⣴⣶⣤⣤⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠏⢻⣿⣿⠀⠀⡀⠀⣹⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⣿⣟⠛⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠗⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⠷⣾⣟⣀⠀⠈⠘⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣻⣿⣿⡿⠟⠁⠀⠀⠈⢿⣿⡿⠋⠁⠈⠿⣿⣿⣧⡉⠀⠀⣴⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⣀⣀⣶⣶⣤⣤⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠆⠀⠀⠀⠀⠀⠈⢿⡇⠀⠀⠀⠀⢻⠙⠿⠃⠀⠀⠈⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣿⣶⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠉⠉⠉⠙⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⢮⣷⠀⢀⣴⣾⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⣿⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣷⠘⠛⠃⠾⠀⠀⠈⠢⣶⣤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢘⣿⣿⣿⣿⣿⣿⣿⡄⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠀⠀⠀⠀⣠⣀⠉⣻⠉⠂⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⠟⠁⣶⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣾⣿⣿⣿⣶⣿⣇⡀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⣿⣿⡟⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⠟⠀⠀⠿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⡿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⡿⠿⠻⢿⣿⣿⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⠟⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠛⠛⠋⠀⠀⠀⠀⠀⠀⢰⠄"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠰⠞⠁⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⡅⠀⠒⠀⠀⠀⠀⠀ ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣶⣟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⣀⣀⣤⣤⣤⣄⣀⣀⣀⠀⢀⣠⣤⣤⣤⣴⣶⣦⣤⣤⣤⣤⣤⣴⣶⣤⣤⣤⣤⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀"),
        list("⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣀⣠⣤⣤⣤⣤⣤⣀⣀⣲⣶⣶⣶⣦⣤⣤⣶⣿⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣴⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠷⠆⠀⠀"),
        list("⣷⣶⣶⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣾⣾⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"),
        list("⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿")
]

h, w = len(ascii_map), len(ascii_map[0])

# Servo Control Class
class ServoController:
    def __init__(self):
        self.azimuth_angle = 0
        self.elevation_angle = 0
        
        if GPIO_AVAILABLE:
            try:
                self.pigpio_factory = PiGPIOFactory()
                self.azimuth_servo = AngularServo(
                    18, 
                    min_angle=-135, 
                    max_angle=135, 
                    min_pulse_width=0.0005, 
                    max_pulse_width=0.0025, 
                    pin_factory=self.pigpio_factory
                )
                self.elevation_servo = AngularServo(
                    19, 
                    min_angle=-90, 
                    max_angle=90, 
                    min_pulse_width=0.0005, 
                    max_pulse_width=0.0025, 
                    pin_factory=self.pigpio_factory
                )
                self.azimuth_servo.angle = 0
                self.elevation_servo.angle = 0
                self.hardware_available = True
            except Exception as e:
                self.hardware_available = False
                print(f"Warning: Could not initialize servo hardware: {e}")
        else:
            self.hardware_available = False
    
    def set_azimuth(self, angle):
        if -135 <= angle <= 135:
            self.azimuth_angle = angle
            if self.hardware_available:
                try:
                    self.azimuth_servo.angle = float(angle)
                except Exception as e:
                    print(f"Error setting azimuth: {e}")
            return True
        return False
    
    def set_elevation(self, angle):
        if -90 <= angle <= 90:
            self.elevation_angle = angle
            if self.hardware_available:
                try:
                    self.elevation_servo.angle = float(angle)
                except Exception as e:
                    print(f"Error setting elevation: {e}")
            return True
        return False

# Simple Vertical Slider using IntEdit
class VerticalSlider(urwid.IntEdit):
    def __init__(self, min_val, max_val, initial_val, callback=None, label=""):
        self.min_val = min_val
        self.max_val = max_val
        self.callback = callback
        self.label = label
        super().__init__(caption="", default=initial_val)
        self.set_edit_text(str(initial_val))
    
    def keypress(self, size, key):
        old_val = self.value()
        if old_val is None:
            old_val = 0
            
        if key == 'up':
            new_val = min(self.max_val, old_val + 1)
        elif key == 'down':
            new_val = max(self.min_val, old_val - 1)
        elif key == 'shift up':
            new_val = min(self.max_val, old_val + 10)
        elif key == 'shift down':
            new_val = max(self.min_val, old_val - 10)
        elif key == 'page up':
            new_val = min(self.max_val, old_val + 45)
        elif key == 'page down':
            new_val = max(self.min_val, old_val - 45)
        else:
            return super().keypress(size, key)
        
        self.set_edit_text(str(new_val))
        if self.callback and new_val != old_val:
            self.callback(new_val)
        return None

def parse_colours(s):
    result = []
    pos = 0
    for match in re.finditer(r'\[(\w+)\](.*?)\[/\1\]', s):
        if match.start() > pos:
            result.append(s[pos:match.start()])
        result.append((match.group(1), match.group(2)))
        pos = match.end()
    if pos < len(s):
        result.append(s[pos:])
    return result

def check_connection():
    try:
        requests.get("https://www.google.com", timeout=5, verify=False)
        return True, "[green]✓ Internet connected[/green]"
    except:
        return False, "[bright_red]✗ No internet[/bright_red]"

def fetch_tle_data():
    try:
        r = requests.get(tle_url, timeout=10, verify=False)
        r.raise_for_status()
        lines = r.text.encode("utf-8").decode("utf-8-sig").splitlines()
        
        cleaned = []
        i = 0
        while i < len(lines) - 2:
            if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
                cleaned.extend([lines[i].strip(), lines[i+1].strip(), lines[i+2].strip()])
                i += 3
            else:
                i += 1
        
        with open(tle_file, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned))
        return True, "[green]✓ TLE data updated[/green]"
    except Exception as e:
        return False, f"[bright_red]✗ TLE fetch error: {e}[/bright_red]"

def get_satellites(names):
    try:
        lines = open(tle_file).read().splitlines()
    except FileNotFoundError:
        return [], ["[bright_red]✗ TLE file not found[/bright_red]"]
    
    sats, used_names, messages = [], set(), []
    
    for name in names:
        found = False
        for i in range(0, len(lines), 3):
            line_name = lines[i].strip()
            if name.upper() in line_name.upper() and line_name not in used_names:
                sats.append(EarthSatellite(lines[i+1], lines[i+2], line_name))
                used_names.add(line_name)
                found = True
        if not found:
            messages.append(f"[bright_yellow]⚠ '{name}' not found[/bright_red]")
    
    return sats[:8], messages

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def select_best_satellite(satellites, observer, ts):
    now = datetime.now(timezone.utc)
    t_now = ts.utc(now)
    future_times = ts.utc([now + timedelta(seconds=i * 30) for i in range(10)])
    
    best_sat, best_score, scores = None, -1, {}
    
    for sat in satellites:
        sat_diff = sat - observer
        el_now, _, _ = sat_diff.at(t_now).altaz()
        current_el = el_now.degrees
        
        if current_el <= 0:
            scores[sat] = 0
            continue
        
        future_elevations = [sat_diff.at(t).altaz()[0].degrees for t in future_times]
        avg_el = np.mean(future_elevations)
        dist_km = sat_diff.at(t_now).distance().km
        dist_factor = 1 / np.sqrt(dist_km) if dist_km > 0 else 0.01
        
        score = 19265 * sigmoid((current_el - 10) / 5) * sigmoid((avg_el - 10) / 5) * dist_factor
        scores[sat] = score
        
        if score > best_score:
            best_score, best_sat = score, sat
    
    return scores, best_sat

def latlon_to_map(lat, lon):
    row = int((90 - lat) / 180 * (h - 1))
    col = int((lon + 180) / 360 * (w - 1))
    return max(0, min(h-1, row)), max(0, min(w-1, col))

def draw_map_frame(positions, satellites, ts, observer_lat, observer_lon):
    frame = [row.copy() for row in ascii_map]
    now = datetime.now(timezone.utc)
    forecast_times = [ts.utc(now + timedelta(minutes=i/2)) for i in range(60)]
    
    # Plot orbital paths
    for i, sat in enumerate(satellites):
        colour = colourlist[i % len(colourlist)]
        for t in forecast_times:
            sub = wgs84.subpoint(sat.at(t))
            lat, lon = sub.latitude.degrees, sub.longitude.degrees
            r, c = latlon_to_map(lat, lon)
            frame[r][c] = f"[{colour}]*[/{colour}]"
    
    # Plot observer
    r_obs, c_obs = latlon_to_map(observer_lat, observer_lon)
    frame[r_obs][c_obs] = "[red]O[/red]"
    
    # Plot current satellite positions
    for i, (lat, lon) in enumerate(positions):
        colour = colourlist[i % len(colourlist)]
        r, c = latlon_to_map(lat, lon)
        frame[r][c] = f"[{colour}]{i+1}[/{colour}]"
    
    return "\n".join("".join(row) for row in frame)

class SatelliteApp:
    def __init__(self):
        self.loop = None
        self.satellites = []
        self.observer = None
        self.ts = None
        self.running = False
        self.metrics_row_offset = 0
        self.current_mode = "satellite_tracking"
        self.current_sat_page = 0
        self.servo_controller = ServoController()
    
    def setup_data(self, names, coords):
        self.observer_lat, self.observer_lon = map(float, coords.split())
        self.observer = Topos(latitude_degrees=self.observer_lat, longitude_degrees=self.observer_lon)
        self.satellites, messages = get_satellites(names)
        self.ts = load.timescale()
        return messages
    
    def create_status_line(self, scores, best_sat):
        parts = []
        for i, sat in enumerate(self.satellites):
            score = scores.get(sat, 0)
            name = sat.name
            if sat == best_sat and score > 0:
                parts.append(f"[green]{name} ({score:.1f}) ☆[/green]")
            elif score > 0:
                parts.append(f"[dark_green]{name} ({score:.1f})[/dark_green]")
            else:
                parts.append(f"[gray]{name} ({score:.1f})[/gray]")
        return " | ".join(parts)
    
    def create_metrics_table(self, sat_data):
        boxes = []
        
        if len(sat_data) > 4:
            satellites_per_page = 4
            total_pages = (len(sat_data) + satellites_per_page - 1) // satellites_per_page
            self.current_sat_page = self.current_sat_page % total_pages
            
            start_idx = self.current_sat_page * satellites_per_page
            end_idx = min(start_idx + satellites_per_page, len(sat_data))
            display_data = sat_data[start_idx:end_idx]
            
            self.page_info_text = f"Page {self.current_sat_page + 1} of {total_pages}"
        else:
            display_data = sat_data
            self.page_info_text = None
        
        for i, (name, az, el, lat, lon, alt, gc_dist, sl_dist, speed) in enumerate(display_data):
            if len(sat_data) > 4:
                actual_index = self.current_sat_page * 4 + i
                header = urwid.Text(f"{actual_index+1}. {name}", align='center')
            else:
                header = urwid.Text(f"{i+1}. {name}", align='center')
            
            metrics = [
                ("Azimuth", f"{az.degrees:.1f}°"),
                ("Elevation", f"{el.degrees:.1f}°"),
                ("Latitude", f"{lat:.3f}°"),
                ("Longitude", f"{lon:.3f}°"),
                ("Altitude", f"{alt:.1f} km"),
                ("GC Distance", f"{gc_dist:.1f} km"),
                ("SL Distance", f"{sl_dist:.1f} km"),
                ("Speed", f"{speed:.1f} m/s"),
            ]
            
            rows = [urwid.Columns([
                ('weight', 1, urwid.Text(m_name)),
                ('weight', 1, urwid.Text(m_val, align='right'))
            ]) for m_name, m_val in metrics]
            
            pile = urwid.Pile([header] + rows)
            boxes.append(('weight', 1, urwid.LineBox(pile)))
        
        return urwid.Columns(boxes, dividechars=1)
    
    def cycle_satellite_page(self, direction):
        if len(self.satellites) > 5:
            if direction == 'down':
                self.current_sat_page += 1
            elif direction == 'up':
                self.current_sat_page -= 1
            
            total_pages = (len(self.satellites) + 4) // 5
            self.current_sat_page = self.current_sat_page % total_pages
    
    def on_azimuth_change(self, value):
        self.servo_controller.set_azimuth(value)
        self.az_value_text.set_text(f"{value}°")
    
    def on_elevation_change(self, value):
        self.servo_controller.set_elevation(value)
        self.el_value_text.set_text(f"{value}°")
    
    def create_servo_control_widget(self):
        # Create vertical sliders using IntEdit with AttrMap for focus highlighting
        self.az_slider = urwid.AttrMap(
            VerticalSlider(-135, 135, 0, self.on_azimuth_change, "Azimuth"),
            'slider', 'slider_focus'
        )
        self.el_slider = urwid.AttrMap(
            VerticalSlider(-90, 90, 0, self.on_elevation_change, "Elevation"),
            'slider', 'slider_focus'
        )
        
        # Value display texts
        self.az_value_text = urwid.Text("0°", align='center')
        self.el_value_text = urwid.Text("0°", align='center')
        
        # Status text
        status_text = "Hardware Available" if self.servo_controller.hardware_available else "Simulation Mode"
        status_widget = urwid.Text(f"Status: {status_text}", align='center')
        
        # Instructions
        instructions = urwid.Text(
            "Use Up/Down arrows to adjust\n" +
            "Shift+Up/Down for larger steps\n" +
            "PageUp/PageDown for 45° steps\n" +
            "Tab to switch between controls\n" +
            "Type values directly and press Enter",
            align='center'
        )
        
        # Create servo control walker for proper focus handling
        servo_walker = urwid.SimpleListWalker([
            urwid.Text("Servo Control Interface", align='center'),
            urwid.Divider(),
            status_widget,
            urwid.Divider(),
            urwid.Columns([
                ('weight', 1, urwid.Pile([
                    ('pack', urwid.Text("Azimuth (-135° to 135°)", align='center')),
                    ('pack', urwid.Divider()),
                    ('pack', self.az_slider),
                    ('pack', urwid.Divider()),
                    ('pack', self.az_value_text),
                ])),
                ('weight', 1, urwid.Pile([
                    ('pack', urwid.Text("Elevation (-90° to 90°)", align='center')),
                    ('pack', urwid.Divider()),
                    ('pack', self.el_slider),
                    ('pack', urwid.Divider()),
                    ('pack', self.el_value_text),
                ])),
            ], dividechars=3),
            urwid.Divider(),
            instructions,
        ])
        
        # Create the ListBox
        servo_listbox = urwid.ListBox(servo_walker)
        
        return servo_listbox
    
    def switch_mode(self, button, mode):
        self.current_mode = mode
        self.update_main_content()
    
    def update_main_content(self):
        if self.current_mode == "satellite_tracking":
            status_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.status_text, align='center')), 'border')
            map_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.map_text, align='center'), title="Equirectangular Projection"), 'border')
            metrics_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.metrics_placeholder, align='center'), title="Live Telemetry"), 'border')
            
            content_pile = urwid.Pile([
                ('pack', status_box),
                ('pack', map_box),
                ('weight', 1, metrics_box),
            ])
            
            self.info_content = content_pile
        else:
            self.info_content = self.create_servo_control_widget()
        
        self.info_widget = urwid.AttrMap(
            urwid.LineBox(self.info_content, title=f"{'Satellite Tracker' if self.current_mode == 'satellite_tracking' else 'Servo Control'}"), 
            'border'
        )
        self.main_content.original_widget = self.info_widget
    
    def update_display(self):
        if not self.running or not self.satellites or self.current_mode != "satellite_tracking":
            if self.running and self.current_mode != "satellite_tracking":
                self.loop.set_alarm_in(0.1, lambda loop, data: self.update_display())
            return
        
        now = datetime.now(timezone.utc)
        positions, sat_data = [], []
        scores, best_sat = select_best_satellite(self.satellites, self.observer, self.ts)
        
        for sat in self.satellites:
            t = self.ts.from_datetime(now)
            sp = sat.at(t).subpoint()
            diff = sat - self.observer
            el, az, _ = diff.at(t).altaz()
            lat, lon, alt = sp.latitude.degrees, sp.longitude.degrees, sp.elevation.km
            positions.append((lat, lon))
            
            sl_dist = diff.at(t).distance().km
            gc_dist = geodesic((self.observer.latitude.degrees, self.observer.longitude.degrees), (lat, lon)).km
            rv = diff.at(t).velocity.m_per_s
            speed = (rv[0]**2 + rv[1]**2 + rv[2]**2)**0.5
            
            sat_data.append((sat.name, az, el, lat, lon, alt, gc_dist, sl_dist, speed))
        
        status_line = self.create_status_line(scores, best_sat)
        map_display = draw_map_frame(positions, self.satellites, self.ts, self.observer_lat, self.observer_lon)
        metrics = self.create_metrics_table(sat_data)
        
        if hasattr(self, 'page_info_text') and self.page_info_text:
            status_line += f" | {self.page_info_text}"
        
        self.status_text.set_text(parse_colours(status_line))
        self.map_text.set_text(parse_colours(map_display))
        self.metrics_placeholder.original_widget = metrics
        
        if self.running:
            self.loop.set_alarm_in(0.1, lambda loop, data: self.update_display())
    
    def create_main_widget(self):
        self.status_text = urwid.Text("", align='center')
        self.map_text = urwid.Text("", align='center')
        self.metrics_placeholder = urwid.WidgetPlaceholder(urwid.SolidFill())
        
        sat_tracking_btn = urwid.AttrMap(urwid.Button("Satellite Tracking", on_press=self.switch_mode, user_data="satellite_tracking"), 'button', 'button_focus')
        servo_control_btn = urwid.AttrMap(urwid.Button("Servo Control", on_press=self.switch_mode, user_data="servo_control"), 'button', 'button_focus')
        
        self.options_listbox = urwid.ListBox(urwid.SimpleListWalker([
            sat_tracking_btn,
            urwid.Divider(),
            servo_control_btn,
        ]))
        
        options_content = urwid.Pile([
            self.options_listbox,
            ('pack', urwid.Divider()),
            ('pack', urwid.Text("Arrow keys to navigate\nEnter to select\n'q' to quit", align='center'))
        ])
        
        self.options_box = urwid.AttrMap(urwid.LineBox(options_content, title="Menu"), 'border')
        
        self.main_content = urwid.WidgetPlaceholder(urwid.SolidFill())
        self.update_main_content()
        
        self.main_columns = urwid.Columns([
            ('weight', 1, self.options_box),
            ('weight', 4, self.main_content),
        ], dividechars=1, focus_column=0)
        
        return self.main_columns
    
    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            self.running = False
            raise urwid.ExitMainLoop()
        elif key == 'right':
            if hasattr(self, 'main_columns'):
                self.main_columns.focus_position = 1
        elif key == 'left':
            if hasattr(self, 'main_columns'):
                self.main_columns.focus_position = 0
        elif key in ('up', 'down'):
            if (hasattr(self, 'main_columns') and 
                self.main_columns.focus_position == 1 and 
                self.current_mode == "satellite_tracking" and 
                len(self.satellites) > 5):
                self.cycle_satellite_page(key)
                return True
    
    def run(self, names, coords):
        messages = self.setup_data(names, coords)
        
        if messages:
            print("")
            for msg in messages:
                console.print(msg)
            time.sleep(3)
        
        if not self.satellites:
            console.print("[bright_red]✗ No satellites loaded[/bright_red]")
            time.sleep(5)
            return
        
        self.running = True
        self.loop = urwid.MainLoop(self.create_main_widget(), palette=palette, unhandled_input=self.unhandled_input)
        self.loop.set_alarm_in(0.1, lambda loop, data: self.update_display())
        
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.running = False

def get_user_input():
    names = [n.strip() for n in Prompt.ask("Enter satellites (comma-separated)", default="Meteor").split(",") if n.strip()]
    coords = Prompt.ask("Observer lat lon", default="-31.9505 115.8605")
    
    if Prompt.ask("Fetch fresh TLEs?", default="n", choices=["y", "n"]) == "y":
        connected, msg = check_connection()
        console.print(msg)
        if connected:
            success, tle_msg = fetch_tle_data()
            console.print(tle_msg)
        else:
            console.print("[bright_yellow]⚠ Using local TLE file[/bright_yellow]")
    else:
        console.print("[bright_cyan]ⓘ Using local TLE file[/bright_cyan]")
    
    time.sleep(1)
    return names, coords

if __name__ == "__main__":
    names, coords = get_user_input()
    app = SatelliteApp()
    console.print("\nStarting satellite tracker. Press '[bright_cyan]q[/bright_cyan]' to quit.")
    time.sleep(1)
    app.run(names, coords)