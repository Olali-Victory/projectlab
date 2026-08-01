import sys
import time

try:
    import board
    import digitalio
    from PIL import Image
    from adafruit_rgb_display import st7735
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    print("SPI TEST: FAIL")
    sys.exit(1)

CYCLES = 2
HOLD_SEC = 2

COLORS = [
    ("Red", (255, 0, 0)),
    ("Green", (0, 255, 0)),
    ("Blue", (0, 0, 255)),
]


def main():
    try:
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)

        display = st7735.ST7735R(
            spi,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
            rotation=90
        )

        width = display.width
        height = display.height
        print(f"Display initialized ({width} x {height})")

        for _ in range(CYCLES):
            for name, color in COLORS:
                print(f"Displaying {name}")
                image = Image.new("RGB", (width, height), color)
                display.image(image)
                time.sleep(HOLD_SEC)

        display.image(Image.new("RGB", (width, height), (0, 0, 0)))
        print("SPI TEST: PASS")
    except Exception as e:
        print(f"SPI ERROR: {e}")
        print("SPI TEST: FAIL")
        sys.exit(1)


main()
