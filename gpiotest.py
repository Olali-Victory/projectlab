import Jetson.GPIO as gpio
import time

def gpiotest(stop_event):
    pin = 31

    #Pin Setup
    gpio.setwarnings(False)

    #Board pin-numbering scheme
    gpio.setmode(gpio.BOARD)

    #set pin as an input pin
    gpio.setup(pin, gpio.OUT, initial = gpio.HIGH)
    while not stop_event.is_set():
        gpio.output(pin, gpio.LOW)
        time.sleep(1)
        gpio.output(pin, gpio.HIGH)
        time.sleep(1)

    gpio.output(pin, gpio.LOW)
    gpio.cleanup()
