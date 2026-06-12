import time
from pathlib import Path

PWM = Path("/sys/class/pwm/pwmchip0/pwm2") #pin33
#PWM = Path("/sys/class/pwm/pwmchip0/pwm0") #pin32

period = 20_000_000

def write(file, value):
    path = PWM / file
    path.write_text(str(value))

write("enable",0)
write("period", period) #50Hz
write("duty_cycle", 0) #5%
write("enable", 1)

try:
    while True:
        for percent in [0,25,50,75,100]:
            duty = int(period * percent / 100)
            print(f"Duty cycle: {percent}% value: {duty}")
            write("duty_cycle", duty)
            time.sleep(2)


except KeyboardInterrupt:
    print("Stopping PWM")

finally:
    write("duty_cycle", 0)
    write("enable", 0)
