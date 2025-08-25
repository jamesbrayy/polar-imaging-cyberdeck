from skyfield.api import EarthSatellite, load, Topos, wgs84  # import key objects for satellite tracking and earth geometry
from geopy.distance import geodesic  # used for calculating geodesic distances on Earth
from datetime import datetime, timezone, timedelta  # standard datetime handling
import requests, time, urllib3, random, re  # requests for HTTP, time for delays, urllib3 for suppressing warnings
import numpy as np  # numerical operations
import urwid
from rich.prompt import Prompt
from rich.color import Color
from rich.console import Console  # console is the main rich output object

console = Console()  # initializes a rich console for output

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # disables SSL warnings from urllib3
tle_url  = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather"  # url to fetch TLEs (orbital elements) for weather satellites
tle_file = "satellites.txt"  # local filename to save the fetched TLE data

monocolour = ""
colourlist = ["white", "cyan", "dark_blue", "dark_gray", "magenta"]  # colour cycle used for map elements
pal = [
    ("black", "black", ""),
    ("dark_red", "dark red", ""),
    ("dark_green", "dark green", ""),
    ("brown", "brown", ""),
    ("dark_blue", "dark blue", ""),
    ("dark_magenta", "dark magenta", ""),
    ("dark_cyan", "dark cyan", ""),
    ("dark_gray", "dark gray", ""),
    ("gray", "light gray", ""),
    ("red", "light red", ""),
    ("green", "light green", ""),
    ("yellow", "yellow", ""),
    ("blue", "light blue", ""),
    ("magenta", "light magenta", ""),
    ("cyan", "light cyan", ""),
    ("white", "white", ""),
    ("border", "dark green", "")
]
if monocolour:
    pal = [(name, monocolour, "") for (name, *_rest) in pal]
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
h, w = len(ascii_map), len(ascii_map[0])  # get height and width of the ascii map for later layout/display use

# global variables for urwid interface
satellites = []
observer = None
ts = None
olat, olon = 0, 0

def parse_colours(s):
    # naive parser for [bright_red]text[/bright_red] style
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

def check_connection():  # check whether the raspberry pi is running offline
    try:
        requests.get("https://www.google.com", timeout=5, verify=False)  # check internet using google.com as a stable website
        return True, "[bright_green]✓  Internet connection secured.[/bright_green]"
    except:
        return False, "[bright_red]✗  No internet connection.[/bright_red]"

def fetch_tle_data():
    try:
        r = requests.get(tle_url, timeout=10, verify=False)  # download tle text from celestrak
        r.raise_for_status()  # raise an exception if the http status is an error
        lines = r.text.encode("utf-8").decode("utf-8-sig").splitlines()  # ensure correct decoding standard is used and split the lines into a list
        cleaned = []
        i = 0
        while i < len(lines) - 2:  # iterate through the lines searching for valid tle triples
            if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):  # proceed if data matches standard tle format
                cleaned += [lines[i].strip(), lines[i+1].strip(), lines[i+2].strip()]  # store valid tle block in the 'cleaned' list
                i += 3  # move to next group
            else:
                i += 1 # skip if invalid
        with open(tle_file, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned))  # overwrite and save the local tle file with new data
        return True, "[bright_green]✓  TLE data fetched and cleaned[/bright_green]"
    except Exception as e:
        return False, f"[bright_red]✗  TLE fetch error:[/bright_red] {e}"

def get_satellites(names):
    sats = []  # list for EarthSatellite objects
    used_names = set()  # track already-used satellite names
    try:
        lines = open(tle_file).read().splitlines()  # extract lines from tle file
    except FileNotFoundError:
        return sats, ["[bright_red]✗  TLE file not found.[/bright_red]"]
    
    messages = []
    if names == ["*"]:  # check for wildcard input to return all satellites
        for i in range(0, len(lines), 3):  # iterate by sections of three lines to group by satellite
            line_name = lines[i].strip()
            if line_name not in used_names:  # avoid duplicates
                sats.append(EarthSatellite(lines[i+1], lines[i+2], line_name))  # construct satellite object
                used_names.add(line_name)  # track duplicates
    else:
        for name in names:  # iterate through each user input
            matches_found = False  # track if any matches are found
            for i in range(0, len(lines), 3):  # iterate by sections of three lines to group by satellite
                line_name = lines[i].strip()
                if name.upper() in line_name.upper() and line_name not in used_names:  # search for non-case-sensitive user input in the tle section
                    sats.append(EarthSatellite(lines[i+1], lines[i+2], line_name))  # construct satellite object if found
                    used_names.add(line_name)  # track duplicates
                    matches_found = True  # mark as matched
            if not matches_found:
                messages.append(f"[bright_red]✗  \"{name}\" not found or already selected.[/bright_red]")
    return sats, messages

def sigmoid(x):
    return 1 / (1 + np.exp(-x))  # define a standard sigmoid function to normalize elevation values due to its S-like shape

def select_best_satellite(satellites, observer, ts):
    now = datetime.now(timezone.utc)  # get the current utc time
    t_now = ts.utc(now)  # convert this to a skyfield time object
    future_times = ts.utc([now + timedelta(seconds=i * 30) for i in range(10)])  # generate times for a five min window in thirty second steps
    best_sat = None  # define the best satellite variable before it is addressed
    best_score = -1  # define the best_score variable to be impossibly low so it is immediately replaced
    scores = {}  # store individual satellite scores
    for sat in satellites:  # iterate through each satellite
        sat_diff = sat - observer  # calculate the current relative position vector
        el_now, az_now, dist_now = sat_diff.at(t_now).altaz()  # get the current elevation, azimuth, distance
        current_el = el_now.degrees  # get the current elevation angle in degrees
        if current_el <= 0:  # set score to zero if the satellite is out of line-of sight (i.e. below the horizon)
            scores[sat] = 0
            continue
        future_elevations = [  # get future elevation angles over the next five minutes in thirty second steps
            sat_diff.at(t).altaz()[0].degrees for t in future_times
        ]
        avg_el = np.mean(future_elevations)  # determine the average elevation over the next five minutes
        dist_km = sat_diff.at(t_now).distance().km  # determine the distance between the observer and satellite
        dist_factor = 1 / np.sqrt(dist_km) if dist_km > 0 else 0.01  # inverse square root relationship to penalise a higher distance
        norm_cur = sigmoid((current_el - 10) / 5)  # favour a high current elevation angle
        norm_avg = sigmoid((avg_el - 10) / 5)  # favour a high elevation angle over the next five minutes
        score = 19265 * norm_cur * norm_avg * dist_factor  # calculate a composite score and multiply by a scalar to neaten results for the user
        scores[sat] = score
        if score > best_score:  # keep track of which satellite has the highest score at a given moment
            best_score = score
            best_sat = sat
    return scores, best_sat  # return the scores for all satellites in a dictionary and the top satellite object

def latlon_to_map(lat, lon):
    row = int((90 - lat)/(90 - -90)*(h-1))  # map the latitude to to a row of the ascii map
    col = int((lon+180)/360*(w-1))  # map the longitude to a column of the ascii map
    return max(0, min(h-1, row)), max(0, min(w-1, col))  #ensure that the satellite remains within the bounds of the map and return map coordinates

def draw_map_frame(positions, satellites, ts):
    forecast_length = 60  # define the number of characters to predict ahead
    frame = [row.copy() for row in ascii_map]

    # 1. plot future orbital paths
    now = datetime.now(timezone.utc)  # get the current utc time
    forecast_times = [ts.utc(now + timedelta(minutes=i/2)) for i in range(forecast_length)]  # generate times every 30 seconds for 30 minutes (60 characters)
    for i, sat in enumerate(satellites):  # iterate thrugh each satellite
        colour = colourlist[i]
        sat_char = f"[{colour}]*[/{colour}]"  # define the colored asterisk path marker
        for t in forecast_times:
            sub = wgs84.subpoint(sat.at(t))  # create a subsatellite point object
            lat, lon = sub.latitude.degrees, sub.longitude.degrees
            r, c = latlon_to_map(lat, lon)
            cell = frame[r][c]
            frame[r][c] = sat_char  # replace the previous characters with the path marker at the required coordinates to form the path forecast
    
    # 2. plot observer location
    r_obs, c_obs = latlon_to_map(olat, olon)
    frame[r_obs][c_obs] = "[red]O[/red]"  # mark the location of the observer with a red 'O'

    # 3. plot each satellite’s current position
    icons = [str(i) for i in range(1, len(positions) + 1)]  # create a list containing the satellite icons
    for i, (lat, lon) in enumerate(positions):
        colour = colourlist[i]
        r, c = latlon_to_map(lat, lon)
        frame[r][c] = f"[{colour}]{icons[i]}[/{colour}]"  # mark current satellite positions with uniquely coloured icons to match the trails
            

    return "\n".join("".join(row) for row in frame)  # 'render' one full map frame in a string, with rows separated by newline characters

class SatelliteApp:
    def __init__(self):
        self.loop = None
        self.main_widget = None
        self.satellites = []
        self.observer = None
        self.ts = None
        self.olat = 0
        self.olon = 0
        self.running = False
        
    def setup_data(self, names, coords):
        global satellites, observer, ts, olat, olon
        
        # Parse coordinates
        self.olat, self.olon = map(float, coords.split())
        olat, olon = self.olat, self.olon
        self.observer = Topos(latitude_degrees=self.olat, longitude_degrees=self.olon)
        observer = self.observer
        
        # Load satellites
        self.satellites, messages = get_satellites(names)
        satellites = self.satellites
        
        # Load timescale
        self.ts = load.timescale()
        ts = self.ts
        
        return messages
        
    def create_satellite_status_line(self, sat_scores, best_satellite):
        status_parts = []
        for i, sat in enumerate(self.satellites):
            score = sat_scores.get(sat, 0)
            name = sat.name
            if sat == best_satellite and score > 0:
                status_parts.append(f"[green]{name} ({score:.1f}) ☆[/green]")
            elif score > 0:
                status_parts.append(f"[dark_green]{name} ({score:.1f}) [/dark_green]")
            else:
                status_parts.append(f"[gray]{name} ({score:.1f}) [/gray]")
        return " | ".join(status_parts)
    
    def create_metrics_table(self, sat_data):
        boxes = []
        for i, data in enumerate(sat_data):
            name, az, el, lat, lon, alt, disGC, disSL, speed = data
            
            # header with satellite name and colour
            header_text = urwid.Text(('sat'+str(i % len(pal)), parse_colours(f"[{colourlist[i]}]{i+1}. {name}[/{colourlist[i]}]")), align='center')
            
            # rows as Columns: left = metric, right = value
            rows = []
            metrics = [
                ("Azimuth", f"{az.degrees:.1f}°"),
                ("Elevation", f"{el.degrees:.1f}°"),
                ("Latitude", f"{lat:.3f}°"),
                ("Longitude", f"{lon:.3f}°"),
                ("Altitude", f"{alt:.1f} km"),
                ("GC Distance", f"{disGC:.1f} km"),
                ("SL Distance", f"{disSL:.1f} km"),
                ("Speed", f"{speed:.1f} m/s"),
            ]
            for m_name, m_val in metrics:
                row = urwid.Columns([
                    ('weight', 1, urwid.Text(m_name, align='left')),
                    ('weight', 1, urwid.Text(m_val, align='right'))
                ])
                rows.append(row)
            
            pile = urwid.Pile([header_text] + rows)
            box = urwid.LineBox(pile, tlcorner='╭', tline='─', lline='│', trcorner='╮', rline='│', blcorner='╰', bline='─', brcorner='╯')
            boxes.append(('weight', 1, box))
        
        return urwid.Columns(boxes, dividechars=1)
        
    def update_display(self):
        if not self.running or not self.satellites:
            return
            
        now = datetime.now(timezone.utc)
        positions = []
        sat_data = []
        
        scores, best_satellite = select_best_satellite(self.satellites, self.observer, self.ts)
        
        for i, sat in enumerate(self.satellites):
            t = self.ts.from_datetime(now)
            sp = sat.at(t).subpoint()
            name = sat.name
            
            diff = sat - self.observer
            el, az, _ = diff.at(t).altaz()
            lat, long, alt = sp.latitude.degrees, sp.longitude.degrees, sp.elevation.km
            positions.append((lat, long))
            
            sldist = diff.at(t).distance().km
            gcdist = geodesic((self.observer.latitude.degrees, self.observer.longitude.degrees), (lat, long)).km
            
            rv = diff.at(t).velocity.m_per_s
            speed = (rv[0]**2 + rv[1]**2 + rv[2]**2)**0.5
            
            sat_data.append((name, az, el, lat, long, alt, gcdist, sldist, speed))
        
        # update widgets
        status_line = self.create_satellite_status_line(scores, best_satellite)
        map_display = parse_colours(draw_map_frame(positions, self.satellites, self.ts))
        metrics_display = self.create_metrics_table(sat_data)
        
        self.status_text.set_text(parse_colours(status_line))
        self.map_text.set_text(map_display)
        self.metrics_placeholder.original_widget = metrics_display
        
        # schedule next update
        if self.running:
            self.loop.set_alarm_in(0.1, lambda loop, data: self.update_display())
    
    def create_main_widget(self):
        # create text widgets
        self.status_text = urwid.Text("", align='center')
        self.map_text = urwid.Text("", align='center')
        self.metrics_placeholder = urwid.WidgetPlaceholder(urwid.SolidFill())
        
        # create sections with 'border' attribute for LineBox borders
        status_box = urwid.LineBox(
            urwid.Padding(self.status_text, align='center')
        )
        status_box = urwid.AttrMap(status_box, 'border')

        map_box = urwid.LineBox(
            urwid.Padding(self.map_text, align='center'), 
            title="Satellite Locations",
        )
        map_box = urwid.AttrMap(map_box, 'border')

        metrics_box = urwid.LineBox(
            urwid.Padding(self.metrics_placeholder, align='center'), 
            title="Live Telemetry",
        )
        metrics_box = urwid.AttrMap(metrics_box, 'border')
        
        options_text = urwid.Text("Options\n\n- Option 1\n- Option 2\n- Option 3", align='left')
        # turn options into a box widget so it fills height
        options_filler = urwid.Filler(options_text, valign='top')
        options_box = urwid.LineBox(options_filler, title="Menu")
        options_box = urwid.AttrMap(options_box, 'border')
        
        # right-hand panel
        info = urwid.Pile([
            ('pack', status_box),
            ('pack', map_box),
            ('weight', 1, metrics_box),
        ])
        info = urwid.Filler(info, valign='top')
        info = urwid.LineBox(info, title="Satellite Tracker")
        info  = urwid.AttrMap(info , 'border')
        
        # layout: drop the outer Filler, return Columns directly
        main_layout = urwid.Columns([
            ('weight', 1, options_box),
            ('weight', 4, info),
        ], dividechars=1)
        
        return main_layout

    def unhandled_input(self, key):
        if key in ('q', 'Q'):
            self.running = False
            raise urwid.ExitMainLoop()
    
    def run(self, names, coords):
        # setup data
        messages = self.setup_data(names, coords)
        
        if not self.satellites:
            console.print("[bright_yellow]⚠  No satellites loaded. Exiting.[/bright_yellow]")
            for msg in messages:
                console.print(msg)
            return
            
        # create interface
        self.main_widget = self.create_main_widget()
        
        # start the display loop
        self.running = True
        self.loop = urwid.MainLoop(
            self.main_widget, 
            unhandled_input=self.unhandled_input,
            palette=pal
        )
        
        # start updating
        self.loop.set_alarm_in(0.1, lambda loop, data: self.update_display())
        
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.running = False

def get_user_input():
    names = [n.strip() for n in Prompt.ask("Enter up to 5 satellites (comma-separated)", default="Meteor").split(",") if n.strip()][:5]
    coords = Prompt.ask("Observer lat lon", default="-31.9505 115.8605")  # get user input for observer coordinates (default is perth)
    
    if Prompt.ask("Fetch fresh TLEs?", default="n", choices=["y", "n"]) == "y" and check_connection():  # ask the user whether they want to download the latest tle data
        connected, conn_msg = check_connection()
        console.print(conn_msg)
        if connected:
            success, tle_msg = fetch_tle_data()
            console.print(tle_msg)
            if not success:
                console.print("[bright_yellow]⚠  Continuing with local TLE file.[/bright_yellow]")
        else:
            console.print("[bright_yellow]⚠  Using local TLE file.[/bright_yellow]")
    else:
        console.print("[bright_cyan]ⓘ  Using local TLE file.[/bright_cyan]")
    
    time.sleep(1)  # Give user time to read messages
    
    return names, coords

if __name__ == "__main__":
    names, coords = get_user_input()
    app = SatelliteApp()
    console.print("\nStarting satellite tracker. Press '[bright_cyan]q[/bright_cyan]' to quit.")
    time.sleep(1)
    app.run(names, coords)