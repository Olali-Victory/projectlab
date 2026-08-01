"""
Wiring:
    signal (orange/yellow) -> pin 32 or 33
    V+     (red)           -> pin 2 or 4  (5V rail, not 3.3V)
    GND    (brown/black)   -> any header ground pin, common with board

Pin mode is configured by this script rather than by the Windows GUI at
connect time, so the test is order-independent: running the GPIO test
first leaves 32/33 in GPIO mode, and configure_pins() hands them back.
"""

import os
import subprocess

import sys
import RPi.GPIO as gpio
import time

PAD_MUX_WRITES = [
    ("0x700031fc", "0x45"),
    ("0x70003248", "0x46"),
]

# CNF bit is CLEARED here, handing each pad to its hardware function.
# gpiotest.py sets the same bits to take the pins back as plain GPIO.
PIN_CNF = {
    32: (0x6000D504, 0x01),
    33: (0x6000D100, 0x40),
}


def _devmem(args):
    for prefix in ([], ["sudo", "-n"]):
        try:
            done = subprocess.run(prefix + ["busybox", "devmem"] + args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, timeout=5)
            if done.returncode == 0:
                return done.stdout.decode(errors="ignore").strip()
        except Exception:
            pass
    return None


def configure_pins(pins):
    if os.geteuid() != 0:
        print("SETUP: WARNING - not running as root, register writes may be "
              "refused", flush=True)

    for addr, value in PAD_MUX_WRITES:
        _devmem([addr, "32", value])

    for pin in pins:
        entry = PIN_CNF.get(pin)
        if entry is None:
            continue
        addr, mask = entry
        current = _devmem([hex(addr)])
        if current is None:
            print(f"SETUP: WARNING - could not read CNF for pin {pin}",
                  flush=True)
            continue
        try:
            value = int(current, 16)
        except ValueError:
            continue
        if value & mask:
            _devmem([hex(addr), "32", hex(value & ~mask)])
            print(f"SETUP: pin {pin} was in GPIO mode, handed back to SFIO",
                  flush=True)


VALID_PINS = (32, 33)
DEFAULT_PINS = [33]
FREQUENCY_HZ = 50


MIN_DUTY = 2.5
MAX_DUTY = 12.5

ANGLE_STEP_DEG = 1
TOTAL_SWEEP_SECONDS = 6.3
SETTLE_SECONDS = 0.5
SETTLE_PULSE_INTERVAL = 0.02


def angle_to_duty(angle_deg):
    angle_deg = max(0, min(180, angle_deg))
    return MIN_DUTY + (angle_deg / 180.0) * (MAX_DUTY - MIN_DUTY)


def parse_pins(argv):
    if len(argv) < 2:
        return list(DEFAULT_PINS)

    arg = argv[1].strip().lower()
    if arg == "both":
        return list(VALID_PINS)

    try:
        pin = int(arg)
    except ValueError:
        raise ValueError(f"unrecognised argument '{argv[1]}' - use 32, 33 or both")

    if pin not in VALID_PINS:
        raise ValueError(f"pin {pin} is not PWM-capable - use 32, 33 or both")

    return [pin]


def pwmtest(pins=None):
    if pins is None:
        try:
            pins = parse_pins(sys.argv)
        except ValueError as e:
            print(f"PWM TEST: FAIL - {e}")
            return False

    configure_pins(pins)

    gpio.setmode(gpio.BOARD)
    gpio.setwarnings(False)

    channels = []
    for pin in pins:
        gpio.setup(pin, gpio.OUT)
        channel = gpio.PWM(pin, FREQUENCY_HZ)
        channel.start(angle_to_duty(0))
        channels.append(channel)

    steps = list(range(0, 181, ANGLE_STEP_DEG))
    step_delay = TOTAL_SWEEP_SECONDS / len(steps)

    def write(angle_deg):
        duty = angle_to_duty(angle_deg)
        for channel in channels:
            channel.ChangeDutyCycle(duty)

    def hold(angle_deg, seconds):
        end_time = time.time() + seconds
        while time.time() < end_time:
            write(angle_deg)
            time.sleep(SETTLE_PULSE_INTERVAL)

    try:
        print("PWM PINS: " + ",".join(str(p) for p in pins))

        hold(0, SETTLE_SECONDS)

        print("Sweeping servo 0 -> 90 degrees...")
        for angle in steps:
            write(angle)
            time.sleep(step_delay)

        print("Sweeping servo 90 -> 0 degrees...")
        for angle in reversed(steps):
            write(angle)
            time.sleep(step_delay)

        hold(0, SETTLE_SECONDS)

        print("PWM TEST: PASS")
        return True

    except Exception as e:
        print(f"PWM TEST: FAIL - {e}")
        return False

    finally:
        for channel in channels:
            channel.stop()
        gpio.cleanup()


if __name__ == "__main__":
    pwmtest()
