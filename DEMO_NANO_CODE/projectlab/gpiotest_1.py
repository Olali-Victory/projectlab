import Jetson.GPIO as gpio
import time

def gpiotest(stop_event):
    pin_list = [7, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, 29, 31, 32,
            33, 35, 36, 37, 38, 40]

    #Pin Setup
    gpio.setwarnings(False)

    #Board pin-numbering scheme
    gpio.setmode(gpio.BOARD)

    #set pin as an input pin
    for pin in pin_list:
        gpio.setup(pin, gpio.OUT)
    while not stop_event.is_set():
        for pin in pin_list:
            gpio.output(pin, gpio.LOW)
        time.sleep(1)
        for pin in pin_list:
            gpio.output(pin, gpio.HIGH)
        time.sleep(1)

    gpio.output(pin, gpio.LOW)
    gpio.cleanup()
