from skyfield.api import EarthSatellite, load, Topos, wgs84
from geopy.distance import geodesic
from datetime import datetime, timezone, timedelta
import requests, time, urllib3, numpy as np, urwid, re
from rich.prompt import Prompt
from rich.console import Console
# Setup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()
tle_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather"
tle_file = "satellites.txt"
colourlist = ["white", "cyan", "dark_blue", "dark_gray", "blue", "magenta", "red", "yellow"]
# Urwid color palette
palette = [
    ("black", "black", ""), ("dark_red", "dark red", ""), ("dark_green", "dark green", ""),
    ("brown", "brown", ""), ("dark_blue", "dark blue", ""), ("dark_magenta", "dark magenta", ""),
    ("dark_cyan", "dark cyan", ""), ("dark_gray", "dark gray", ""), ("gray", "light gray", ""),
    ("red", "light red", ""), ("green", "light green", ""), ("yellow", "yellow", ""),
    ("blue", "light blue", ""), ("magenta", "light magenta", ""), ("cyan", "light cyan", ""),
    ("white", "white", ""), ("border", "dark green", ""), ("button", "white", ""),
    ("button_focus", "white", "dark green")
]
# ASCII world map
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
        self.current_mode = "satellite_tracking"  # "satellite_tracking" or "servo_control"
        self.current_sat_page = 0  # For cycling through satellite pages
    
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
        # Always use the simple, original approach that worked
        boxes = []
        
        # If more than 5 satellites, show current page of 5
        if len(sat_data) > 4:
            satellites_per_page = 4
            total_pages = (len(sat_data) + satellites_per_page - 1) // satellites_per_page
            self.current_sat_page = self.current_sat_page % total_pages
            
            start_idx = self.current_sat_page * satellites_per_page
            end_idx = min(start_idx + satellites_per_page, len(sat_data))
            display_data = sat_data[start_idx:end_idx]
            
            # Store page info for display elsewhere
            self.page_info_text = f"Page {self.current_sat_page + 1} of {total_pages}"
        else:
            display_data = sat_data
            self.page_info_text = None
        
        # Create boxes using the original working method
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
            
            # Wrap around
            total_pages = (len(self.satellites) + 4) // 5  # 5 satellites per page
            self.current_sat_page = self.current_sat_page % total_pages
    def create_servo_control_widget(self):
        servo_text = urwid.Text("Servo Control Interface\n\nServo controls would go here...", align='center')
        return urwid.Filler(servo_text, valign='middle')
    
    def switch_mode(self, button, mode):
        self.current_mode = mode
        self.update_main_content()
    
    def update_main_content(self):
        """Update the main content area based on current mode"""
        if self.current_mode == "satellite_tracking":
            # Create satellite tracking content
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
            # Create servo control content
            self.info_content = self.create_servo_control_widget()
        
        # Make the content focusable
        self.info_widget = urwid.AttrMap(
            urwid.LineBox(self.info_content, title=f"{'Satellite Tracker' if self.current_mode == 'satellite_tracking' else 'Servo Control'}"), 
            'border'
        )
        self.main_content.original_widget = self.info_widget
    
    def update_display(self):
        if not self.running or not self.satellites or self.current_mode != "satellite_tracking":
            if self.running and self.current_mode != "satellite_tracking":
                # Still schedule updates even in servo mode
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
        
        # Update widgets
        status_line = self.create_status_line(scores, best_sat)
        map_display = draw_map_frame(positions, self.satellites, self.ts, self.observer_lat, self.observer_lon)
        metrics = self.create_metrics_table(sat_data)
        
        # Add page info to status line if cycling
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
        
        # Create mode selection buttons
        sat_tracking_btn = urwid.AttrMap(urwid.Button("Satellite Tracking", on_press=self.switch_mode, user_data="satellite_tracking"), 'button', 'button_focus')
        servo_control_btn = urwid.AttrMap(urwid.Button("Servo Control", on_press=self.switch_mode, user_data="servo_control"), 'button', 'button_focus')
        
        self.options_listbox = urwid.ListBox(urwid.SimpleListWalker([
            sat_tracking_btn,
            urwid.Divider(),
            servo_control_btn,
        ]))
        
        options_content = urwid.Pile([
            self.options_listbox,  # Remove weight specification
            ('pack', urwid.Divider()),
            ('pack', urwid.Text("Arrow keys to navigate\nEnter to select\n'q' to quit", align='center'))
        ])
        
        self.options_box = urwid.AttrMap(urwid.LineBox(options_content, title="Menu"), 'border')
        
        # Create main content placeholder
        self.main_content = urwid.WidgetPlaceholder(urwid.SolidFill())
        self.update_main_content()  # Initialize with satellite tracking mode
        
        # Create the main columns widget with focus capability
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
            # Move focus to info panel
            if hasattr(self, 'main_columns'):
                self.main_columns.focus_position = 1
        elif key == 'left':
            # Move focus back to options panel
            if hasattr(self, 'main_columns'):
                self.main_columns.focus_position = 0
        elif key in ('up', 'down'):
            # Handle satellite page cycling when focused on info panel
            if (hasattr(self, 'main_columns') and 
                self.main_columns.focus_position == 1 and 
                self.current_mode == "satellite_tracking" and 
                len(self.satellites) > 5):
                self.cycle_satellite_page(key)
                return True  # Indicate we handled the key
    
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
