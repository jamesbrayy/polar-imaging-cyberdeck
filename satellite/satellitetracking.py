from skyfield.api import EarthSatellite, load, Topos, wgs84  # import key objects for satellite tracking and earth geometry
from geopy.distance import geodesic  # used for calculating geodesic distances on Earth
from datetime import datetime, timezone, timedelta  # standard datetime handling
import requests, time, urllib3  # requests for HTTP, time for delays, urllib3 for suppressing warnings
import numpy as np  # numerical operations
import random

# rich is a library that enables interactive terminal output
from rich.console import Console, Group  # console is the main rich output object; group allows combining elements
from rich.panel import Panel  # for framed blocks of text
from rich.table import Table  # for formatted tables
from rich.text import Text  # rich-formatted text
from rich.prompt import Prompt  # for user input
from rich.live import Live  # for dynamic live-updating output
from rich.color import Color  # for managing colors
from rich.columns import Columns  # layout tool for columned output
from rich import box  # for table borders
from rich.align import Align  # for text alignment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # disables SSL warnings from urllib3
console = Console()  # initializes a rich console for output

tle_url  = "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather"  # url to fetch TLEs (orbital elements) for weather satellites
tle_file = "satellites.txt"  # local filename to save the fetched TLE data

colourlist = ["green1", "bright_white", "grey50", "bright_cyan", "yellow1"]  # colour cycle used for map elements
colourlist += [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(95)]  # append 95 random hex colours just in case
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

def check_connection():  # check whether the raspberry pi is running offline
    try:
        requests.get("https://www.google.com", timeout=5, verify=False)  # check internet using google.com as a stable website
        console.print("[green]✓  Internet connection secured[/green]")  # notify user if successful
        return True
    except:
        return False  # if no internet, then return alternate outcome

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
        console.print("[green]\u2713  TLE data fetched and cleaned[/green]")  # display a success message on the screen
    except Exception as e:
        console.print(f"[red]✗  TLE fetch error:[/red] {e}")  # display an error message on the screen and quit loop

def get_satellites(names):
    if Prompt.ask("Fetch fresh TLEs?", default="y", choices=["y", "n"]) == "y" and check_connection():  # ask the user whether they want to download the latest tle data
        fetch_tle_data()  # download the latest tle data
    else:
        console.print("[yellow]\u26a0  Using local TLE file[/yellow]")  # continue without updating old data
    time.sleep(1)  # give the user 1 second to read the console message before loading main UI

    sats = []  # list for EarthSatellite objects
    used_names = set()  # track already-used satellite names
    lines = open(tle_file).read().splitlines()  # extract lines from tle file

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
                console.print(f"[red]✗  “{name}” not found or already selected[/red]")  # warn the user if no match is found for an input term
                time.sleep(3)  # give the user 3 seconds to read the console message before loading main UI

    return sats  # return the list of satellite objects

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

        alt_now, _, _ = sat_diff.at(t_now).altaz()  # get the current altitude in kilometres
        current_el = alt_now.degrees  # get the current elevation angle in degrees

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
    frame[r_obs][c_obs] = "[bright_red]O[/bright_red]"  # mark the location of the observer with a red 'O'

    # 3. plot each satellite’s current position
    icons = [str(i) for i in range(1, len(positions) + 1)]  # create a list containing the satellite icons
    for i, (lat, lon) in enumerate(positions):
        colour = colourlist[i]
        r, c = latlon_to_map(lat, lon)
        frame[r][c] = f"[{colour}]{icons[i]}[/{colour}]"  # mark current satellite positions with uniquely coloured icons to match the trails
            

    return "\n".join("".join(row) for row in frame)  # 'render' one full map frame in a string, with rows separated by newline characters

def make_metric_table(i, name, az, el, lat, lon, alt, disGC, disSL, speed):
    t = Table(title=f"[{colourlist[i]}][bold]{i+1}. {name}[/bold][/{colourlist[i]}]", box=box.ROUNDED)  # title the table with the satellite name and style it
    t.add_column("Metric", style="green4", no_wrap=True)  # define the left column heading
    t.add_column("Value", style="green1")  # define the right column heading
    t.add_row("Azimuth",     f"{az.degrees:.1f}°")  # display the azimuth angle (angle clockwise from north tangent to the surface of the earth)
    t.add_row("Elevation",   f"{el.degrees:.1f}°")  # display the elevation angle (angle increasing moving from the horizon upwards)
    t.add_row("Latitude",         f"{lat:.3f}°")  # display the equivalent latitude 
    t.add_row("Longitude",        f"{lon:.3f}°")  # display the equivalent longitude
    t.add_row("Altitude",         f"{alt:.1f} km")  # display the altitude above sea level
    t.add_row("GC Distance",        f"{disGC:.1f} km")  # display the great circle distance (surface distance)
    t.add_row("SL Distance",        f"{disSL:.1f} km")  # display the straight line distance (actual distance)
    t.add_row("Speed",         f"{speed:.1f} m/s")  # display the speed of the satellite relative to the earth
    return Align.center(t)  # centre align and return the table object

names = [n.strip() for n in Prompt.ask("Enter up to 5 satellites (comma‑separated)", default="NOAA").split(",") if n.strip()][:5]  # get user input for up to five satellite names
coords = Prompt.ask("Observer lat lon", default="-31.9505 115.8605")  # get user input for observer coordinates (default is perth)
olat, olon = map(float, coords.split())  # split the coordinates into latitude and longitude
observer = Topos(latitude_degrees=olat, longitude_degrees=olon)  # create a skyfield topocentric location object to store coordinates
satellites = get_satellites(names)  # load tle data for the user-specified satellites

console.clear()  # clear user prompts and answers from terminal
with Live(screen=True, refresh_per_second=10, console=console) as live:  # begin live terminal render loop
    ts = load.timescale()
    while True:
        now = datetime.now(timezone.utc)  # get current utc time
        positions, tables, top_names = [], [], []  # create empty lists for future use
        scores, best_satellite = select_best_satellite(satellites, observer, ts)  # score all selected satellites based on elevation and distance criteria and return scores and the best satellite object
        
        for i, sat in enumerate(satellites): # iterate through each satellite
            t = ts.from_datetime(now)
            sp = sat.at(t).subpoint()
            name = sat.name
            
            diff = sat - observer
            el, az, _ = diff.at(t).altaz()  # calculate the current elevation and azimuth coordinates (polar)
            lat, long, alt = sp.latitude.degrees, sp.longitude.degrees, sp.elevation.km  # calculate the current latitude, longitude, and altitude (geodetic)
            positions.append((lat, long))
            
            sldist = diff.at(t).distance().km  # calculate straight line distance in km
            gcdist = geodesic((observer.latitude.degrees, observer.longitude.degrees),(lat, long)).km  # calculate great circle distance in km
            
            rv = diff.at(t).velocity.m_per_s  # calculate the relative velocity vector
            speed = (rv[0]**2 + rv[1]**2 + rv[2]**2)**0.5  # use pythagoras to calculate the speed
            
            score = scores.get(sat, 0)  # fetch the previously computed score for the specified satellite
            if ((sat == best_satellite) and (score > 0)):
                top_names.append(f"[green1]{name} ({score:.1f})[/green1]")  # highlight best in neon green
            elif score > 0:
                top_names.append(f"[green4]{name} ({score:.1f})[/green4]")  # display everything above the horizon in dark green
            else:
                top_names.append(f"[grey50]{name} ({score:.1f})[/grey50]")  # grey-out everything below the horizon
            
            tables.append(make_metric_table(
                i, sat.name, az, el, lat, long, alt, gcdist, sldist, speed  # put everything together to form a metric table
            ))
            
        top_line = " | ".join(top_names)  # join the individual satellite names and scores together for display
            
        top = Panel(  # create the header panel, which displays the ranked accessibility of each satellite via their scores
            Align.center(Text.from_markup(top_line)),
            title=f"[green1]Tracked Satellites ({len(satellites)})[/green1]",
            style="green4"
        )

        map_panel = Panel( # create the ascii map panel, which displays the current positions and future trajectories of the satellites
            Align.center(draw_map_frame(positions, satellites, ts)),
            title="[green1]ASCII World Map[/green1]", style="green4"
        )
        
        metrics = Columns(tables, expand=True) # align the metric tables horizontally

        live.update(Group( # refresh and update the entire terminal interface for the next frame
            top,
            map_panel,
            Panel(metrics, title="[green1]Live Telemetry[/green1]", style="green4"),
        ))
