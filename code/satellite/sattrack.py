from skyfield.api import EarthSatellite, load, Topos, wgs84
from datetime import datetime, timezone, timedelta
import requests, time, urllib3, re, os, threading, math
import numpy as np
import urwid
from rich.console import Console
import subprocess, queue, json
from pathlib import Path

try:
    from gpiozero import AngularServo
    from gpiozero.pins.pigpio import PiGPIOFactory
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()

tle_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather"
tle_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satellites.txt")
ui_update_interval = float(os.getenv("SATTRACK_UPDATE_INTERVAL", "0.1"))
map_update_interval = float(os.getenv("SATTRACK_MAP_UPDATE_INTERVAL", "0.5"))
compute_update_interval = float(os.getenv("SATTRACK_PASS_UPDATE_INTERVAL", "60"))
map_forecast_points = int(os.getenv("SATTRACK_MAP_POINTS", "30"))
map_forecast_length = float(os.getenv("SATTRACK_MAP_HORIZON_MIN", "30"))
max_satellites = int(os.getenv("SATTRACK_max_satellites", "8"))

colourlist = ["white", "cyan", "dark_blue", "dark_gray", "blue", "magenta", "red", "yellow"]
palette = [
    ("black", "black", ""), ("dark_red", "dark red", ""), ("dark_green", "dark green", ""),
    ("brown", "brown", ""), ("dark_blue", "dark blue", ""), ("dark_magenta", "dark magenta", ""),
    ("dark_cyan", "dark cyan", ""), ("dark_gray", "dark gray", ""), ("gray", "light gray", ""),
    ("red", "light red", ""), ("green", "light green", ""), ("yellow", "yellow", ""),
    ("blue", "light blue", ""), ("magenta", "light magenta", ""), ("cyan", "light cyan", ""),
    ("white", "white", ""), ("border", "dark green", ""), ("button", "white", ""),
    ("button_focus", "white", "dark green"), ("slider", "default", "default"),
    ("slider_focus", "white", "dark green")
]

ascii_map = [
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
    
class SatellitePreviewButton(urwid.Button):
    def __init__(self, label, preview_callback, select_callback, sat_index):
        super().__init__(label)
        self.preview_callback = preview_callback
        self.select_callback = select_callback
        self.sat_index = sat_index
    
    def keypress(self, size, key):
        if key == 'enter':
            self.select_callback(self, self.sat_index)
            return None
        return super().keypress(size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        return super().mouse_event(size, event, button, col, row, focus)

def satellite_to_servo_coords(sat_az, sat_el):
    # convert azimuth 0-360° to -180° to 180°
    if sat_az > 180:
        servo_az = sat_az - 360
    else:
        servo_az = sat_az
    
    # map azimuth to servo range
    servo_az = max(-135, min(135, servo_az))
    
    # convert elevation: 0-90° to -90° to 90°
    servo_el = sat_el - 90
    
    # map elevation to safe servo range
    servo_el = max(-70, min(70, servo_el))
    
    return servo_az, servo_el

class servo_controller:
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
                print(f"Warning: Could not initialise servo hardware: {e}")
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

class VerticalSlider(urwid.Pile):
    def __init__(self, min_val, max_val, initial_val, callback=None, label="", height=12):
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val
        self.callback = callback
        self.label = label
        self.height = height
        self._selectable = True

        self.slider_lines = []
        for i in range(height):
            line = urwid.Text("", align='center')
            self.slider_lines.append(line)
        
        super().__init__([('pack', line) for line in self.slider_lines])
        self._update_display()
    
    def selectable(self):
        return True
    
    def set_value(self, value):
        if self.min_val <= value <= self.max_val:
            self.current_val = value
            self._update_display()
    
    def _update_display(self, focus=False):
        rng = self.max_val - self.min_val
        progress = 0.5 if rng == 0 else (self.current_val - self.min_val) / rng
        slider_pos = int((self.height - 3) * (1 - progress)) + 1
        slider_pos = max(1, min(self.height - 2, slider_pos))

        width = 11
        for i, line in enumerate(self.slider_lines):
            # Unicode box-drawing borders for a clean, continuous look
            if i == 0:
                line.set_text([('slider', "┌" + "─" * (width - 2) + "┐")])
                continue
            if i == self.height - 1:
                line.set_text([('slider', "└" + "─" * (width - 2) + "┘")])
                continue
            if i == slider_pos:
                inner = width - 2
                if focus:
                    line.set_text([('slider', '│'), ('slider_focus', ' ' * inner), ('slider', '│')])
                else:
                    thickness = 5
                    left = (inner - thickness) // 2
                    right = inner - thickness - left
                    line.set_text([('slider', '│' + (' ' * left)), ('slider_focus', ' ' * thickness), ('slider', (' ' * right) + '│')])
                continue
            line.set_text([('slider', '│' + ' ' * (width - 2) + '│')])
    
    def render(self, size, focus=False):
        self._update_display(focus)
        return super().render(size, focus)
    
    def keypress(self, size, key):
        old_val = self.current_val
        if key == 'up':
            self.current_val = min(self.max_val, self.current_val + 1)
        elif key == 'down':
            self.current_val = max(self.min_val, self.current_val - 1)
        elif key == 'shift up':
            self.current_val = min(self.max_val, self.current_val + 10)
        elif key == 'shift down':
            self.current_val = max(self.min_val, self.current_val - 10)
        elif key == 'page up':
            self.current_val = min(self.max_val, self.current_val + 45)
        elif key == 'page down':
            self.current_val = max(self.min_val, self.current_val - 45)
        elif key == 'home':
            self.current_val = self.max_val
        elif key == 'end':
            self.current_val = self.min_val
        else:
            return super().keypress(size, key)
        
        if self.current_val != old_val:
            self._update_display()
            if self.callback:
                self.callback(self.current_val)
        return None

class AsciiVerticalSlider(urwid.Pile):
    def __init__(self, min_val, max_val, initial_val, callback=None, label="", height=18):
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val
        self.callback = callback
        self.label = label
        self.height = height
        self._selectable = True

        self.slider_lines = []
        for _ in range(height):
            self.slider_lines.append(urwid.Text("", align='center'))

        super().__init__([('pack', line) for line in self.slider_lines])
        self._update_display()

    def selectable(self):
        return True

    def set_value(self, value):
        if self.min_val <= value <= self.max_val:
            self.current_val = value
            self._update_display()

    def _update_display(self, focus=False):
        rng = self.max_val - self.min_val
        progress = 0.5 if rng == 0 else (self.current_val - self.min_val) / rng
        slider_pos = int((self.height - 3) * (1 - progress)) + 1
        slider_pos = max(1, min(self.height - 2, slider_pos))

        width = 11
        for i, line in enumerate(self.slider_lines):
            # Unicode box-drawing borders for a clean, continuous look
            if i == 0:
                line.set_text([('slider', "┌" + "─" * (width - 2) + "┐")])
                continue
            if i == self.height - 1:
                line.set_text([('slider', "└" + "─" * (width - 2) + "┘")])
                continue
            if i == slider_pos:
                inner = width - 2
                if focus:
                    line.set_text([('slider', '│'), ('slider_focus', ' ' * inner), ('slider', '│')])
                else:
                    thickness = 5
                    left = (inner - thickness) // 2
                    right = inner - thickness - left
                    line.set_text([('slider', '│' + (' ' * left)), ('slider_focus', ' ' * thickness), ('slider', (' ' * right) + '│')])
                continue
            line.set_text([('slider', '│' + ' ' * (width - 2) + '│')])

    def render(self, size, focus=False):
        self._update_display(focus)
        return super().render(size, focus)

    def keypress(self, size, key):
        old_val = self.current_val
        if key == 'up':
            self.current_val = min(self.max_val, self.current_val + 1)
        elif key == 'down':
            self.current_val = max(self.min_val, self.current_val - 1)
        elif key == 'shift up':
            self.current_val = min(self.max_val, self.current_val + 10)
        elif key == 'shift down':
            self.current_val = max(self.min_val, self.current_val - 10)
        elif key == 'page up':
            self.current_val = min(self.max_val, self.current_val + 45)
        elif key == 'page down':
            self.current_val = max(self.min_val, self.current_val - 45)
        elif key == 'home':
            self.current_val = self.max_val
        elif key == 'end':
            self.current_val = self.min_val
        else:
            return super().keypress(size, key)
        if self.current_val != old_val:
            self._update_display()
            if self.callback:
                self.callback(self.current_val)
        return None

class LabeledSlider(urwid.Pile):
    def __init__(self, min_val, max_val, initial_val, callback, title):
        self.slider = AsciiVerticalSlider(min_val, max_val, initial_val, self._on_change, title)
        self.callback = callback
        self.value_text = urwid.Text(f"{initial_val} °", align='center')
        self.title_text = urwid.Text(title, align='center')
        
        super().__init__([
            ('pack', self.title_text),
            ('pack', urwid.Divider()),
            ('pack', self.slider),
            ('pack', urwid.Divider()),
            ('pack', self.value_text),
        ])
        
        self._selectable = True
    
    def set_value(self, value):
        self.slider.set_value(value)
        self.value_text.set_text(f"{value} °")
    
    def _on_change(self, value):
        self.value_text.set_text(f"{value} °")
        if self.callback:
            self.callback(value)
    
    def selectable(self):
        return True
    
    def keypress(self, size, key):
        return self.slider.keypress(size, key)

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
        return True, "[green]Internet connected[/green]"
    except:
        return False, "[red]No internet[/red]"

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
        return True, "[green]TLE data updated[/green]"
    except Exception as e:
        return False, f"[red]TLE fetch error: {e}[/red]"

def get_satellites(names):
    try:
        lines = open(tle_file).read().splitlines()
    except FileNotFoundError:
        return [], ["[red]TLE file not found[/red]"]
    
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
            messages.append(f"[bright_yellow]'{name}' not found[/bright_yellow]")
    
    # sanitise color tags for 'not found' messages (fix mismatched closing tag)
    messages = [
        m.replace("[/red]", "[/yellow]")
        if m.startswith("[yellow]") and "not found" in m else m
        for m in messages
    ]
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

def find_next_pass(sat, observer, ts, min_elevation=20):
    now = datetime.now(timezone.utc)
    
    for minutes_ahead in range(0, 1440):
        check_time = now + timedelta(minutes=minutes_ahead)
        t = ts.from_datetime(check_time)
        diff = sat - observer
        el, _, _ = diff.at(t).altaz()
        
        if el.degrees >= min_elevation:
            seconds_until = minutes_ahead * 60
            return seconds_until
    
    return None

def latlon_to_map(lat, lon):
    row = int((90 - lat) / 180 * (h - 1))
    col = int((lon + 180) / 360 * (w - 1))
    return max(0, min(h-1, row)), max(0, min(w-1, col))

def draw_map_frame(positions, satellites, ts, observer_lat, observer_lon):
    frame = [row.copy() for row in ascii_map]
    now = datetime.now(timezone.utc)
    # Build a limited list of forecast times to lighten rendering
    # Spread map_forecast_points across map_forecast_length minutes
    steps = max(1, map_forecast_points)
    step_min = map_forecast_length / max(1, steps - 1)
    forecast_times = [ts.utc(now + timedelta(minutes=i * step_min)) for i in range(steps)]
    
    for i, sat in enumerate(satellites[:max_satellites]):
        colour = colourlist[i % len(colourlist)]
        for t in forecast_times:
            sub = wgs84.subpoint(sat.at(t))
            lat, lon = sub.latitude.degrees, sub.longitude.degrees
            r, c = latlon_to_map(lat, lon)
            frame[r][c] = f"[{colour}]*[/{colour}]"

    r_obs, c_obs = latlon_to_map(observer_lat, observer_lon)
    frame[r_obs][c_obs] = "[red]O[/red]"

    for i, (lat, lon) in enumerate(positions):
        colour = colourlist[i % len(colourlist)]
        r, c = latlon_to_map(lat, lon)
        frame[r][c] = f"[{colour}]{i+1}[/{colour}]"
    
    return "\n".join("".join(row) for row in frame)

class AutoTrackRunner:
    def __init__(self, cfg_path: Path):
        self.cfg_path = Path(cfg_path)
        self.proc = None
        self.q = queue.Queue()
        self.alive = False
        self._tail = []

    def write_config(self, *, sta_lat, sta_lon, sta_alt_m=0, sat_names, sdr="rtlsdr",
                     samplerate=2_400_000, gain_db=None, record=False, out_dir=None):
        cfg = {
            "station": {"latitude": sta_lat, "longitude": sta_lon, "altitude": sta_alt_m},
            "scheduler": {
                "min_elevation": 10,
                "satellites": [{"name": n} for n in sat_names]
            },
            "sdr": {
                "source": sdr,
                "samplerate": samplerate
            },
            "processing": {
                "enable_recording": bool(record),
            }
        }
        if out_dir:
            cfg["processing"]["output_directory"] = str(out_dir)
        if gain_db is not None:
            cfg["sdr"]["general_gain"] = gain_db
        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg_path.write_text(json.dumps(cfg, indent=2))

    def start(self):
        cmd = ["satdump", "autotrack", str(self.cfg_path)]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.alive = True

        def reader():
            for line in self.proc.stdout:
                line = line.rstrip()
                self._tail.append(line)
                if len(self._tail) > 400:
                    self._tail = self._tail[-400:]
                self.q.put(line)
            self.alive = False

        threading.Thread(target=reader, daemon=True).start()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.alive = False

    def get_new_lines(self, max_n=100):
        out = []
        try:
            while len(out) < max_n:
                out.append(self.q.get_nowait())
        except queue.Empty:
            pass
        return out

    def tail_text(self, n=200):
        return "\n".join(self._tail[-n:])

class satelliteapp:
    def __init__(self):
        self.loop = None
        self.satellites = []
        self.observer = None
        self.ts = None
        self.running = False
        self.metrics_row_offset = 0
        self.current_mode = "satellite_tracking"
        self.current_sat_page = 0
        self.servo_controller = servo_controller()
        self.update_interval = ui_update_interval
        self.map_update_interval = map_update_interval
        self.pass_update_interval = compute_update_interval
        self.hover_satellite_index = None
        self.tracking_locked = False
        self.locked_satellite_index = None

        # persistent decoder ui
        self.decoder_ui = None
        self.dec_target_text = None
        self.dec_status = None
        self.dec_log = None
        self.dec_imgs = None

        # Background compute cache/state
        self._bg_computing = False
        self._bg_result = None
        self._last_map_update = 0.0
        self._next_pass_cache = {}  # sat.name -> (timestamp, seconds)

        self.auto_tracking_enabled = False
        self.selected_satellite_index = 0
        self.current_az = 0.0
        self.current_el = 0.0
        self.auto_tracking_focused = False

        # satdump autotrack state
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.autotrack_cfg = base_dir / "autotrack_runtime.json"
        self.autotrack_out = base_dir / "satdump_out"
        self.autotrack_runner = None
        self.autotrack_seen = set()
        self.autotrack_last_images = []
        self.autotrack_sdr = "rtlsdr"          # or "rtl_tcp" / "soapy"
        self.autotrack_samplerate = 2_400_000  # safe default
        self.autotrack_gain = None             # set a number to force manual gain

    def create_decoder_widget(self):
        # build once; reuse across tab switches so content does not disappear
        if self.decoder_ui is not None:
            return self.decoder_ui

        sel = "None"
        if self.satellites:
            idx = min(self.selected_satellite_index, len(self.satellites) - 1)
            sel = self.satellites[idx].name

        self.dec_status = urwid.Text("", align='left')
        self.dec_log = urwid.Text("", align='left')
        self.dec_imgs = urwid.Text("", align='left')
        self.dec_target_text = urwid.Text(f"target satellite: {sel}")

        info = urwid.Pile([
            ('pack', urwid.Text("Satdump Decoding", align='center')),
            ('pack', urwid.Divider()),
            ('pack', self.dec_target_text),
            ('pack', urwid.Text(f"SDR: {self.autotrack_sdr}  samplerate: {self.autotrack_samplerate}")),
            ('pack', urwid.Text(f"Output: {str(self.autotrack_out)}")),
            ('pack', urwid.Divider()),
            ('pack', urwid.Columns([
                urwid.AttrMap(urwid.Button("Start", on_press=self.autotrack_start), 'button', 'button_focus'),
                urwid.AttrMap(urwid.Button("Stop", on_press=self.autotrack_stop), 'button', 'button_focus'),
            ], dividechars=2)),
            ('pack', urwid.Divider()),
            ('pack', urwid.Text("Status:")),
            ('pack', self.dec_status),
        ])

        log_box = urwid.LineBox(urwid.Filler(self.dec_log, valign='top'), title="SatDump Output")
        img_box = urwid.LineBox(urwid.Filler(self.dec_imgs, valign='top'), title="New Images")

        self.decoder_ui = urwid.Columns([
            ('weight', 2, info),
            ('weight', 3, log_box),
            ('weight', 2, img_box),
        ], dividechars=1)

        return self.decoder_ui

    def refresh_decoder_header(self):
        if not self.dec_target_text:
            return
        sel = "None"
        if self.satellites:
            idx = min(self.selected_satellite_index, len(self.satellites) - 1)
            sel = self.satellites[idx].name
        self.dec_target_text.set_text(f"Target Satellite: {sel}")

    def autotrack_start(self, button):
        if not self.satellites:
            self.dec_status.set_text("No satellites loaded.")
            return
        idx = min(self.selected_satellite_index, len(self.satellites) - 1)
        sat_name = self.satellites[idx].name

        runner = AutoTrackRunner(self.autotrack_cfg)
        runner.write_config(
            sta_lat=self.observer.latitude.degrees,
            sta_lon=self.observer.longitude.degrees,
            sat_names=[sat_name],
            sdr=self.autotrack_sdr,
            samplerate=self.autotrack_samplerate,
            gain_db=self.autotrack_gain,
            record=False,
            out_dir=self.autotrack_out
        )
        self.autotrack_seen.clear()
        self.autotrack_last_images = []
        self.autotrack_out.mkdir(parents=True, exist_ok=True)
        self.autotrack_runner = runner
        self.autotrack_runner.start()
        self.dec_status.set_text("Running")

    def autotrack_stop(self, button):
        if self.autotrack_runner:
            self.autotrack_runner.stop()
            self.autotrack_runner = None
        self.dec_status.set_text("Stopped")

    def _compute_satellite_frame_bg(self):
        """Compute scores, telemetry, and map in a background thread.
        Stores results in self._bg_result to be consumed by the UI thread.
        """
        try:
            if not self.satellites or not self.observer or not self.ts:
                self._bg_result = None
                return
            now = datetime.now(timezone.utc)
            t = self.ts.from_datetime(now)

            scores, best_sat = select_best_satellite(self.satellites, self.observer, self.ts)

            positions, sat_data = [], []
            obs_lat = self.observer.latitude.degrees
            obs_lon = self.observer.longitude.degrees
            for sat in self.satellites:
                sp = sat.at(t).subpoint()
                diff = sat - self.observer
                el, az, _ = diff.at(t).altaz()
                lat, lon, alt = sp.latitude.degrees, sp.longitude.degrees, sp.elevation.km
                positions.append((lat, lon))

                sl_dist = diff.at(t).distance().km
                gc_dist = self._haversine_km(obs_lat, obs_lon, lat, lon)
                rv = diff.at(t).velocity.m_per_s
                speed = (rv[0]**2 + rv[1]**2 + rv[2]**2)**0.5

                # Cache next pass computation per satellite to avoid heavy recalculation every tick
                np_key = sat.name
                now_ts = time.time()
                cache_entry = self._next_pass_cache.get(np_key)
                if cache_entry and (now_ts - cache_entry[0]) < self.pass_update_interval:
                    next_pass_seconds = cache_entry[1]
                else:
                    next_pass_seconds = find_next_pass(sat, self.observer, self.ts, min_elevation=20)
                    self._next_pass_cache[np_key] = (now_ts, next_pass_seconds)
                sat_data.append((sat.name, az, el, lat, lon, alt, gc_dist, sl_dist, speed, next_pass_seconds))

            map_display = draw_map_frame(positions, self.satellites, self.ts, self.observer_lat, self.observer_lon)

            self._bg_result = {
                'scores': scores,
                'best_sat': best_sat,
                'sat_data': sat_data,
                'map_display': map_display,
            }
            self._last_map_update = time.time()
        finally:
            self._bg_computing = False

    def setup_data(self, names, coords):
        self.observer_lat, self.observer_lon = map(float, coords.split())
        self.observer = Topos(latitude_degrees=self.observer_lat, longitude_degrees=self.observer_lon)
        self.ts = load.timescale()

        # If user asks for 'best', auto-pick the top 4 satellites by score from the full TLE list
        if len(names) == 1 and names[0].strip().lower() == 'best':
            try:
                lines = open(tle_file, encoding='utf-8').read().splitlines()
            except FileNotFoundError:
                self.satellites = []
                return ["[bright_red]TLE file not found[/bright_red]"]

            all_sats = []
            for i in range(0, len(lines) - 2, 3):
                n = lines[i].strip()
                l1 = lines[i+1].strip() if i+1 < len(lines) else None
                l2 = lines[i+2].strip() if i+2 < len(lines) else None
                if l1 and l2 and l1.startswith('1 ') and l2.startswith('2 '):
                    try:
                        all_sats.append(EarthSatellite(l1, l2, n))
                    except Exception:
                        pass

            if not all_sats:
                self.satellites = []
                return ["[bright_red]No satellites parsed from TLE file[/bright_red]"]

            scores, _ = select_best_satellite(all_sats, self.observer, self.ts)
            ranked = [s for s in sorted(all_sats, key=lambda s: scores.get(s, 0), reverse=True) if scores.get(s, 0) > 0]
            picked = ranked[:4]
            self.satellites = picked
            picked_names = ", ".join(s.name for s in picked) if picked else "none"
            return [f"[white]Auto-selected best: {picked_names}[/white]"]

        # Otherwise, load the requested satellites by name (up to 8)
        self.satellites, messages = get_satellites(names)
        return messages

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        """Fast spherical great-circle distance (approximate) in kilometers."""
        # convert decimal degrees to radians
        rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = math.sin(dlat/2)**2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 6371.0 * c
    
    def create_status_line(self, scores, best_sat):
        parts = []
        for i, sat in enumerate(self.satellites):
            score = scores.get(sat, 0)
            name = sat.name
            if sat == best_sat and score > 0:
                parts.append(f"[green]{name} ({score:.1f}) +[/green]")
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
        
        for i, (name, az, el, lat, lon, alt, gc_dist, sl_dist, speed, next_pass_seconds) in enumerate(display_data):
            if len(sat_data) > 4:
                actual_index = self.current_sat_page * 4 + i
                header = urwid.Text(f"{actual_index+1}. {name}", align='center')
            else:
                header = urwid.Text(f"{i+1}. {name}", align='center')
            
            if next_pass_seconds is not None:
                if next_pass_seconds < 60:
                    next_pass_str = f"{int(next_pass_seconds)}s"
                elif next_pass_seconds < 3600:
                    minutes = int(next_pass_seconds // 60)
                    seconds = int(next_pass_seconds % 60)
                    next_pass_str = f"{minutes}m {seconds}s"
                else:
                    hours = int(next_pass_seconds // 3600)
                    minutes = int((next_pass_seconds % 3600) // 60)
                    next_pass_str = f"{hours}h {minutes}m"
            else:
                next_pass_str = ">24h"
            
            metrics = [
                ("Azimuth", f"{az.degrees:.1f} deg"),
                ("Elevation", f"{el.degrees:.1f} deg"),
                ("Latitude", f"{lat:.3f} deg"),
                ("Longitude", f"{lon:.3f} deg"),
                ("Altitude", f"{alt:.1f} km"),
                ("GC Distance", f"{gc_dist:.1f} km"),
                ("SL Distance", f"{sl_dist:.1f} km"),
                ("Speed", f"{speed:.1f} m/s"),
                ("Next Pass", next_pass_str),
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

    def toggle_auto_tracking(self, button):
        self.auto_tracking_enabled = not self.auto_tracking_enabled
        self.update_servo_display()
    
    def select_satellite(self, button, sat_index):
        # toggle lock if clicking the same one; otherwise lock new one
        if self.tracking_locked and self.locked_satellite_index == sat_index:
            self.tracking_locked = False
            self.locked_satellite_index = None
        else:
            self.selected_satellite_index = sat_index
            self.tracking_locked = True
            self.locked_satellite_index = sat_index
            # keep hover in sync to avoid any off-by-one visuals
            self.hover_satellite_index = sat_index

        # choose active index explicitly
        if self.tracking_locked and self.locked_satellite_index is not None:
            idx = self.locked_satellite_index
        else:
            idx = self.hover_satellite_index if self.hover_satellite_index is not None else self.selected_satellite_index

        self.current_az, self.current_el = self.preview_satellite_position(idx)
        self.update_servo_display()
    
    def update_satellite_position(self):
        if not self.satellites or not self.observer or not self.ts:
            return

        if self.selected_satellite_index >= len(self.satellites):
            self.selected_satellite_index = 0

        # explicit active index to avoid off-by-one
        if self.tracking_locked and self.locked_satellite_index is not None:
            idx = self.locked_satellite_index
        else:
            idx = self.hover_satellite_index if (self.hover_satellite_index is not None and self.hover_satellite_index < len(self.satellites)) else self.selected_satellite_index

        try:
            sat = self.satellites[idx]
            now = datetime.now(timezone.utc)
            t = self.ts.from_datetime(now)
            diff = sat - self.observer
            el, az, _ = diff.at(t).altaz()

            self.current_az = az.degrees
            self.current_el = el.degrees

            if self.auto_tracking_enabled:  # convert to servo coordinate system
                servo_az, servo_el = satellite_to_servo_coords(self.current_az, self.current_el)

                if self.current_el > 0 and servo_el >= -70:
                    self.servo_controller.set_azimuth(servo_az)
                    self.servo_controller.set_elevation(servo_el)

                    if hasattr(self, 'az_slider_widget'):
                        self.az_slider_widget.set_value(servo_az)
                    if hasattr(self, 'el_slider_widget'):
                        self.el_slider_widget.set_value(servo_el)
                else:
                    self.servo_controller.set_elevation(0)
                    if hasattr(self, 'el_slider_widget'):
                        self.el_slider_widget.set_value(0)
                        
        except Exception as e:
            self.current_az = 0.0
            self.current_el = 0.0

    def preview_satellite_position(self, sat_index):
        if not self.satellites or not self.observer or not self.ts:
            return 0.0, 0.0
        
        if sat_index >= len(self.satellites):
            return 0.0, 0.0
        
        try:
            sat = self.satellites[sat_index]
            now = datetime.now(timezone.utc)
            t = self.ts.from_datetime(now)
            diff = sat - self.observer
            el, az, _ = diff.at(t).altaz()
            return az.degrees, el.degrees
        except Exception:
            return 0.0, 0.0
    
    def update_servo_display(self):
        if hasattr(self, 'auto_status_text'):
            status = "ENABLED" if self.auto_tracking_enabled else "DISABLED"
            self.auto_status_text.set_text(f"Auto Tracking: {status}")

        # pick the same active index used everywhere else
        if self.tracking_locked and self.locked_satellite_index is not None:
            idx = self.locked_satellite_index
            locked_suffix = " [locked]"
        else:
            idx = self.hover_satellite_index if (self.hover_satellite_index is not None and self.hover_satellite_index < len(self.satellites)) else self.selected_satellite_index
            locked_suffix = ""

        if hasattr(self, 'selected_sat_text') and self.satellites and 0 <= idx < len(self.satellites):
            self.selected_sat_text.set_text(f"Target: {self.satellites[idx].name}{locked_suffix}")

        if hasattr(self, 'position_text'):
            self.position_text.set_text(f"Az: {self.current_az:.3f} deg | El: {self.current_el:.3f} deg")
    
    def create_auto_tracking_widget(self):
        # Auto tracking toggle button
        toggle_text = "DISABLE Auto Track" if self.auto_tracking_enabled else "ENABLE Auto Track"
        self.auto_toggle_btn = urwid.AttrMap(
            urwid.Button(toggle_text, on_press=self.toggle_auto_tracking),
            'button', 'button_focus'
        )

        self.auto_status_text = urwid.Text("Auto Tracking: DISABLED", align='center')
        self.selected_sat_text = urwid.Text("Target: None", align='center')
        self.position_text = urwid.Text("Az: 0 ° | El: 0 °", align='center')

        sat_buttons = []
        for i, sat in enumerate(self.satellites):
            btn_text = f"{i+1}. {sat.name[:20]}"
            btn_widget = SatellitePreviewButton(btn_text, self.preview_satellite, self.select_satellite, i)
            btn = urwid.AttrMap(btn_widget, 'button', 'button_focus')
            sat_buttons.append(btn)

        if sat_buttons:
            sat_walker = urwid.SimpleFocusListWalker(sat_buttons)

            _orig_set_focus = sat_walker.set_focus
            def _set_focus_and_preview(pos):
                _orig_set_focus(pos)
                # extract the true sat_index from the focused button (unwrap AttrMap → Button)
                try:
                    btn = sat_walker[pos]
                    # if wrapped in AttrMap, unwrap to the original SatellitePreviewButton
                    core = getattr(btn, "original_widget", btn)
                    sat_idx = getattr(core, "sat_index", pos)
                except Exception:
                    sat_idx = pos

                # update hover to the true index, then recompute and refresh
                self.hover_satellite_index = sat_idx
                self.current_az, self.current_el = self.preview_satellite_position(sat_idx)
                self.update_servo_display()

                # immediately sync sliders/servo if you’re in this tab
                # ensures they match the newly focused satellite without waiting for the timer tick
                if hasattr(self, "az_slider_widget") and hasattr(self, "el_slider_widget"):
                    servo_az, servo_el = satellite_to_servo_coords(self.current_az, self.current_el)
                    self.az_slider_widget.set_value(servo_az)
                    self.el_slider_widget.set_value(servo_el)

            sat_walker.set_focus = _set_focus_and_preview

            # ensure initial focus uses the true sat_index as well
            if len(sat_walker):
                _set_focus_and_preview(0)

            sat_listbox = urwid.BoxAdapter(urwid.ListBox(sat_walker), height=6)
        else:
            sat_listbox = urwid.Text("No satellites available", align='center')



        auto_pile = urwid.Pile([
            ('pack', urwid.Divider()),
            ('pack', self.auto_status_text),
            ('pack', self.selected_sat_text),
            ('pack', self.position_text),
            ('pack', urwid.Divider()),
            ('pack', urwid.Text("Select Target Satellite (Enter to lock):", align='center')),
            ('weight', 1, sat_listbox),
            ('pack', urwid.Divider()),
            ('pack', self.auto_toggle_btn),
        ])
        
        return urwid.AttrMap(urwid.LineBox(auto_pile, title="Auto Tracking"), 'border')

    def preview_satellite(self, sat_index):
        # ignore hover while locked
        if self.tracking_locked:
            return
        self.hover_satellite_index = sat_index
        self.current_az, self.current_el = self.preview_satellite_position(sat_index)
        self.update_servo_display()
    
    def on_azimuth_change(self, value):
        self.servo_controller.set_azimuth(value)
        if self.auto_tracking_enabled:
            self.auto_tracking_enabled = False
            self.update_servo_display()
    
    def on_elevation_change(self, value):
        self.servo_controller.set_elevation(value)
        if self.auto_tracking_enabled:
            self.auto_tracking_enabled = False
            self.update_servo_display()
    
    def create_servo_control_widget(self):
        if not hasattr(self, 'az_slider_widget'):
            self.az_slider_widget = LabeledSlider(
                -135, 135, self.servo_controller.azimuth_angle, self.on_azimuth_change, 
                "Azimuth\n(-135 deg to 135 deg)"
            )
            self.el_slider_widget = LabeledSlider(
                -90, 90, self.servo_controller.elevation_angle, self.on_elevation_change, 
                "Elevation\n(-90 deg to 90 deg)"
            )
        else:
            self.az_slider_widget.set_value(self.servo_controller.azimuth_angle)
            self.el_slider_widget.set_value(self.servo_controller.elevation_angle)

        status_text = "Hardware Available" if self.servo_controller.hardware_available else "Simulation Mode"
        status_widget = urwid.Text(f"Status: {status_text}", align='center')

        instructions = urwid.Text(
            "Up/Down: ±1 deg  |  Shift+Up/Down: ±10 deg\n" +
            "PageUp/PageDown: ±45 deg  |  Home/End: Max/Min\n" +
            "Tab: Switch to Auto",
            align='center'
        )
        
        manual_control = urwid.Pile([
            ('pack', urwid.Divider()),
            ('pack', status_widget),
            ('pack', urwid.Divider()),
            ('pack', urwid.Columns([
                ('weight', 1, self.az_slider_widget),
                ('weight', 1, self.el_slider_widget),
            ], dividechars=5)),
            ('pack', urwid.Divider()),
            ('pack', instructions),
        ])
        
        manual_box = urwid.AttrMap(urwid.LineBox(manual_control, title="Manual Control"), 'border')

        auto_tracking_box = self.create_auto_tracking_widget()

        main_pile = urwid.Pile([
            ('weight', 1, manual_box),
            ('pack', urwid.Divider()),
            ('weight', 1, auto_tracking_box),
        ])

        self.servo_focus_walker = urwid.SimpleListWalker([main_pile])
        servo_listbox = urwid.ListBox(self.servo_focus_walker)

        self.update_servo_display()
        
        return servo_listbox
    
    def switch_mode(self, button, mode):
        self.current_mode = mode
        self.update_main_content()
    
    def update_main_content(self):
        if self.current_mode == "satellite_tracking":
            status_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.status_text, align='center')), 'border')
            map_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.map_text, align='center'), title="Equirectangular Projection"), 'border')
            metrics_box = urwid.AttrMap(urwid.LineBox(urwid.Padding(self.metrics_placeholder, align='center'), title="Live Telemetry"), 'border')

            # build content, then wrap in Filler so it stretches vertically like the servo tab
            content_pile = urwid.Pile([
                ('pack', status_box),
                ('weight', 2, map_box),
                ('weight', 3, metrics_box),
            ])
            self.info_content = urwid.Filler(content_pile, valign='top')
            title = "Satellite Tracker"

        elif self.current_mode == "servo_control":
            # do NOT wrap; the ListBox already fills the space
            self.info_content = self.create_servo_control_widget()
            title = "Servo Control"

        else:  # decoder
            # reuse the persistent decoder ui and wrap in Filler so it stretches
            dec = self.create_decoder_widget()
            self.refresh_decoder_header()
            self.info_content = urwid.Filler(dec, valign='top')
            title = "Decoder"

        self.info_widget = urwid.AttrMap(urwid.LineBox(self.info_content, title=title), 'border')
        self.main_content.original_widget = self.info_widget


    def show_loading_screen(self, messages, duration=2.0, title="Loading"):
        # Build a single urwid.Text markup list that can accept either a plain string
        # title, a string with markup tags, or an already-parsed markup list/tuples.
        segments = []
        if title:
            if isinstance(title, (list, tuple)):
                segments.extend(title)
            elif isinstance(title, str):
                if '[' in title and ']' in title:
                    segments.extend(parse_colours(title))
                else:
                    segments.extend(parse_colours(f"[green]{title}[/green]"))
            else:
                segments.extend(parse_colours(f"[green]{str(title)}[/green]"))

        if messages:
            if segments:
                segments.append("\n\n")
            for i, m in enumerate(messages):
                if i > 0:
                    segments.append("\n\n")
                segments.extend(parse_colours(m))

        text_widget = urwid.Text(segments or "", align='center')
        # Default to green text if no explicit colour was supplied in segments
        text_widget = urwid.AttrMap(text_widget, 'green')
        box = urwid.LineBox(urwid.Padding(text_widget, left=2, right=2))
        box = urwid.AttrMap(box, 'border')
        top = urwid.Padding(urwid.Filler(box, valign='middle'), align='center', width=('relative', 70))
        background = urwid.AttrMap(urwid.SolidFill(' '), 'black')
        overlay = urwid.Overlay(top, background, align='center', width=('relative', 90), valign='middle', height=('relative', 80))

        def _exit(loop, data):
            raise urwid.ExitMainLoop()

        loop = urwid.MainLoop(overlay, palette=palette)
        loop.set_alarm_in(duration, _exit)
        try:
            loop.run()
        except KeyboardInterrupt:
            pass

    def show_loading_task(self, task_fn, title="Working..."):
        messages_holder = {"done": False, "msgs": [], "err": None}

        def worker():
            try:
                res = task_fn()
                messages_holder["msgs"] = res or []
            except Exception as e:
                messages_holder["err"] = str(e)
            finally:
                messages_holder["done"] = True

        # UI elements (title can be plain string, string with markup, or parsed list)
        if isinstance(title, (list, tuple)):
            header_text = urwid.Text(title, align='center')
        elif isinstance(title, str) and ('[' in title and ']' in title):
            header_text = urwid.Text(parse_colours(title), align='center')
        else:
            header_text = urwid.Text(parse_colours(f"[green]{title}[/green]"), align='center')
        spinner_text = urwid.Text(".", align='center')
        spinner = urwid.AttrMap(spinner_text, 'green')
        body = urwid.Pile([
            ('pack', header_text),
            ('pack', urwid.Divider()),
            ('pack', spinner),
        ])
        box = urwid.AttrMap(urwid.LineBox(urwid.Padding(body, left=2, right=2)), 'border')
        top = urwid.Padding(urwid.Filler(box, valign='middle'), align='center', width=('relative', 70))
        background = urwid.AttrMap(urwid.SolidFill(' '), 'black')
        overlay = urwid.Overlay(top, background, align='center', width=('relative', 90), valign='middle', height=('relative', 80))

        def poll(loop, data):
            if messages_holder["done"]:
                raise urwid.ExitMainLoop()
            # simple spinner tick
            spinner_text.set_text(spinner_text.text + '.')
            loop.set_alarm_in(0.2, poll)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        loop = urwid.MainLoop(overlay, palette=palette)
        loop.set_alarm_in(0.2, poll)
        try:
            loop.run()
        except KeyboardInterrupt:
            pass

        if messages_holder["err"]:
            return [f"[red]{messages_holder['err']}[/red]"]
        return messages_holder["msgs"]

    def update_display(self):
        if not self.running:
            return

        if self.current_mode == "servo_control":
            self.update_satellite_position()
            self.update_servo_display()
            
        if not self.satellites or self.current_mode != "satellite_tracking":
            if self.running:
                self.loop.set_alarm_in(self.update_interval, lambda loop, data: self.update_display())
            return

        # Start background compute if stale/not running
        now_ts = time.time()
        if (not self._bg_computing and
            (self._bg_result is None or (now_ts - self._last_map_update) >= self.map_update_interval)):
            self._bg_computing = True
            threading.Thread(target=self._compute_satellite_frame_bg, daemon=True).start()

        # Apply latest cached results if any
        if self._bg_result is not None:
            scores = self._bg_result['scores']
            best_sat = self._bg_result['best_sat']
            sat_data = self._bg_result['sat_data']
            map_display = self._bg_result['map_display']

            status_line = self.create_status_line(scores, best_sat)
            if hasattr(self, 'page_info_text') and self.page_info_text:
                status_line += f" | {self.page_info_text}"

            metrics = self.create_metrics_table(sat_data)

            self.status_text.set_text(parse_colours(status_line))
            self.map_text.set_text(parse_colours(map_display))
            self.metrics_placeholder.original_widget = metrics
        
        # decoder tab live updates
        if self.current_mode == "decoder":
            if self.autotrack_runner and self.autotrack_runner.alive:
                if self.autotrack_runner.get_new_lines():
                    self.dec_log.set_text(self.autotrack_runner.tail_text(200))

            new = []
            if self.autotrack_out.exists():
                for ext in ("*.png","*.jpg","*.jpeg","*.bmp"):
                    for p in self.autotrack_out.glob(f"**/{ext}"):
                        if p not in self.autotrack_seen:
                            self.autotrack_seen.add(p)
                            new.append(p)

            if new:
                self.autotrack_last_images.extend(new)
                self.autotrack_last_images = self.autotrack_last_images[-12:]
                names = [f"- {p.name}" for p in reversed(self.autotrack_last_images)]
                self.dec_imgs.set_text("\n".join(names))

        if self.running:
            self.loop.set_alarm_in(self.update_interval, lambda loop, data: self.update_display())
    
    def create_main_widget(self):
        self.status_text = urwid.Text("", align='center')
        self.map_text = urwid.Text("", align='center')
        self.metrics_placeholder = urwid.WidgetPlaceholder(urwid.SolidFill())
        
        sat_tracking_btn = urwid.AttrMap(urwid.Button("Satellite Tracking", on_press=self.switch_mode, user_data="satellite_tracking"), 'button', 'button_focus')
        servo_control_btn = urwid.AttrMap(urwid.Button("Servo Control", on_press=self.switch_mode, user_data="servo_control"), 'button', 'button_focus')
        decoder_btn = urwid.AttrMap(urwid.Button("Decoder", on_press=self.switch_mode, user_data="decoder"), 'button', 'button_focus')

        self.options_listbox = urwid.ListBox(urwid.SimpleListWalker([
            sat_tracking_btn,
            urwid.Divider(),
            servo_control_btn,
            urwid.Divider(),
            decoder_btn,
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
        elif key == 'tab' and self.current_mode == "servo_control":
            if hasattr(self, 'servo_focus_walker'):
                current_focus = self.servo_focus_walker.focus
                pile = self.servo_focus_walker[0]
                if hasattr(pile, 'focus_position'):
                    if pile.focus_position == 0:
                        pile.focus_position = 2
                    else:
                        pile.focus_position = 0
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
            self.show_loading_screen(messages, duration=3.0, title="Loading telemetry and ephemerides")

        
        if not self.satellites:
            self.show_loading_screen(["[red]No satellites found[/red]"], duration=5.0, title="")
            return
        # Block until the first map/telemetry frame is computed
        self.show_loading_task(lambda: (self._compute_satellite_frame_bg() or ["[green]Map ready[/green]"]), title=parse_colours("[white]Preparing map[/white]"))
        self.running = True
        self.loop = urwid.MainLoop(self.create_main_widget(), palette=palette, unhandled_input=self.unhandled_input)
        self.loop.set_alarm_in(self.update_interval, lambda loop, data: self.update_display())
        
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.running = False
        finally:
            try:
                if os.name == 'nt':
                    os.system('cls')
                else:
                    os.system('clear')
            except Exception:
                pass

def get_user_input_ui():
    default_names = "Meteor"
    default_coords = "-31.9505 115.8605"

    title = urwid.Text("Satellite Tracker Setup", align='center')
    subtitle = urwid.Text("Enter targets and observer location", align='center')

    names_caption = parse_colours(f"Satellites (comma-separated) [white]({default_names})[/white]: ")
    coords_caption = parse_colours(f"Observer lat lon [white]({default_coords})[/white]: ")
    names_edit = urwid.Edit(names_caption, "")
    coords_edit = urwid.Edit(coords_caption, "")
    fetch_checkbox = urwid.CheckBox("Fetch fresh TLEs", state=False)

    message_text = urwid.Text("", align='center')

    result = {"names": None, "coords": None, "cancel": False, "fetch": False}

    def on_quit(button):
        result["cancel"] = True
        raise urwid.ExitMainLoop()

    def on_start(button):
        raw = names_edit.edit_text or ""
        names = [n.strip() for n in raw.split(",") if n.strip()]
        if not names:
            names = [default_names]

        coords_raw = (coords_edit.edit_text or "").strip()
        if not coords_raw:
            coords_raw = default_coords
        else:
            try:
                lat_str, lon_str = coords_raw.split()
                float(lat_str); float(lon_str)
            except Exception:
                message_text.set_text(parse_colours("[red]Enter coordinates as 'lat lon' (e.g. -31.95 115.86)[/red]"))
                return

        result["fetch"] = bool(fetch_checkbox.get_state())
        result["names"], result["coords"] = names, coords_raw
        raise urwid.ExitMainLoop()

    start_btn = urwid.AttrMap(urwid.Button("Start", on_press=on_start), 'button', 'button_focus')
    quit_btn = urwid.AttrMap(urwid.Button("Quit", on_press=on_quit), 'button', 'button_focus')

    form = urwid.Pile([
        ('pack', title),
        ('pack', urwid.Divider()),
        ('pack', subtitle),
        ('pack', urwid.Divider()),
        ('pack', names_edit),
        ('pack', coords_edit),
        ('pack', urwid.Divider()),
        ('pack', fetch_checkbox),
        ('pack', urwid.Divider()),
        ('pack', urwid.Columns([('weight', 1, start_btn), ('weight', 1, quit_btn)], dividechars=3)),
        ('pack', urwid.Divider()),
        ('pack', message_text),
    ])

    boxed = urwid.AttrMap(urwid.LineBox(form, title="Setup"), 'border')
    centered = urwid.Filler(urwid.Padding(boxed, align='center', width=('relative', 60)), valign='middle')
    loop = urwid.MainLoop(centered, palette=palette)
    loop.run()

    if result["cancel"]:
        return None, None, False
    return result["names"], result["coords"], result["fetch"]

if __name__ == "__main__":
    names, coords, fetch_requested = get_user_input_ui()
    if names and coords:
        app = satelliteapp()
        if fetch_requested:
            msgs = app.show_loading_task(
                lambda: (
                    (lambda connected_msg, tle_msg: [connected_msg, tle_msg])(
                        *(
                            (lambda connected, msg: (
                                msg,
                                fetch_tle_data()[1] if connected else "[yellow]Using local TLE file[/yellow]"
                            ))(*check_connection())
                        )
                    )
                ),
                title="Fetching TLEs"
            )
            if msgs:
                app.show_loading_screen(msgs, duration=2.0, title="TLE/Network Messages")
        else:
            app.show_loading_screen(["[white]Using local TLE file[/white]"], duration=1.2, title="")

        app.show_loading_screen(["[white]Starting satellite tracker. Press 'q' to quit.[/white]"], duration=1.0, title="")
        app.run(names, coords)
