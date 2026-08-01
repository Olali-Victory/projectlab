#!/usr/bin/env python3

import time
import board
import digitalio
from PIL import Image
from adafruit_rgb_display import st7735


spi = board.SPI()

cs_pin = digitalio.DigitalInOut(board.CE0)      # Pin 24
dc_pin = digitalio.DigitalInOut(board.D25)      # Pin 22
reset_pin = digitalio.DigitalInOut(board.D24)   # Pin 18

display = st7735.ST7735R(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=24000000,
    rotation=90
)

WIDTH = display.width
HEIGHT = display.height

print(f"Display initialized ({WIDTH} x {HEIGHT})")


colors = [
    ("Red",     (255,   0,   0)),
    ("Green",   (0,   255,   0)),
    ("Blue",    (0,     0, 255)),
]


while True:

    for name, color in colors:

        print(f"Displaying {name}")

        image = Image.new("RGB", (WIDTH, HEIGHT), color)

        display.image(image)

        time.sleep(2)