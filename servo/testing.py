from gpiozero import AngularServo
from time import sleep

azimuthServo = AngularServo(18, min_angle=-135, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025)
Az = 0
dAz = 0.1
dirAz = 0

elevationServo = AngularServo(19, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
El = 0
dEl = 0.1
dirEl = 0

dt = 0.005

while (True):
	azimuthServo.angle = Az
	sleep(dt)
	if (dirAz == 0):
		Az += dAz
	if (dirAz == 1):
		Az -= dAz
	if (Az > 90) or (Az < -90):
		dirAz = 1 - dirAz

	elevationServo.angle = El
	sleep(dt)
	if(dirEl == 0):
		El += dEl
	if (dirEl == 1):
		El -= dEl
	if (El > 30) or (El < -30):
		dirEl = 1 - dirEl

	print(f"Azimuth: {Az}")
	print(f"Elevation: {El}")
