import RPi.GPIO as gpio
import time
import subprocess
def pwmtest(stop_event, pwm_pin):
    gpio.setmode(gpio.BOARD)
    gpio.setwarnings(False)
    gpio.setup(pwm_pin, gpio.OUT)
    password="group7\n"
    subprocess.run(["sudo","busybox", "devmem", "0x700031fc", "32", "0x45"], input=password, universal_newlines=True,)
    subprocess.run(["sudo","busybox", "devmem", "0x6000d504", "32", "0x2"])
    subprocess.run(["sudo","busybox", "devmem", "0x70003248", "32", "0x46"])
    subprocess.run(["sudo","busybox", "devmem", "0x6000d100", "32", "0x00"])
    pwm = gpio.PWM(pwm_pin, 50) # freq = 50Hz

    pwm.start(0)


    while not stop_event.is_set():
        for duty in range(5, 11, 1):
            print(duty)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.3)

        for duty in range(10, 4, -1):
            print(duty)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.3)



    pwm.stop()
    gpio.cleanup()



    

