import Jetson.GPIO as gpio
import board
from busio import I2C
import adafruit_vl53l0x
import time

LED_PIN = 31


#gpio.setmode(gpio.BOARD)
gpio.setup(LED_PIN, gpio.OUT)

i2c = I2C(board.SCL, board.SDA)
sensor = adafruit_vl53l0x.VL53L0X(i2c)

try:
    while True:
        distance = sensor.range

        print(f"Distance: {distance} mm")

        if distance < 200:
            gpio.output(LED_PIN, gpio.HIGH)
        else:
            gpio.output(LED_PIN, gpio.LOW)

        time.sleep(0.1)

finally:
    gpio.cleanup()
