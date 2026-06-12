import RPi.GPIO as gpio
import time
def pwmtest(stop_event):
    gpio.setmode(gpio.BOARD)
    gpio.setwarnings(False)
    pwm_pin = 33
    gpio.setup(pwm_pin, gpio.OUT)

    pwm = gpio.PWM(pwm_pin, 50) # freq = 50Hz

    pwm.start(0) #duty cyle 100%


    while not stop_event.set():
        for duty in range(0, 101, 5):
            print(duty)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.3)

        for duty in range(100, -1, -5):
            print(duty)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.3)



    pwm.stop()
    gpio.cleanup()



    

