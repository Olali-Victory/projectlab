import RPi.GPIO as gpio
import time
import csv
import os
import subprocess
from datetime import datetime


PIN_LIST = [7, 11, 12, 13, 15, 16, 18, 26, 29, 31, 32, 33, 35, 36, 37, 38]


PIN_CNF = {
    7:  (0x6000D60C, 0x01),
    11: (0x6000D108, 0x04),
    12: (0x6000D204, 0x80),
    13: (0x6000D004, 0x40),
    15: (0x6000D600, 0x04),
    16: (0x6000D704, 0x01),
    18: (0x6000D004, 0x80),
    24: (0x6000D008, 0x08),
    26: (0x6000D008, 0x10),
    29: (0x6000D408, 0x20),
    31: (0x6000D604, 0x01),
    32: (0x6000D504, 0x01),
    33: (0x6000D100, 0x40),
    35: (0x6000D204, 0x10),
    36: (0x6000D108, 0x08),
    37: (0x6000D004, 0x10),
    38: (0x6000D204, 0x20),
    40: (0x6000D204, 0x40),
}

BLINKS_PER_PIN = 2
BLINK_INTERVAL_SECONDS = 0.25
GAP_SECONDS = 0.15

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "test_results.csv")


def say(msg):
    print(msg, flush=True)


def _devmem(args):
    for prefix in ([], ["sudo", "-n"]):
        try:
            done = subprocess.run(prefix + ["busybox", "devmem"] + args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,
                                  timeout=5)
            if done.returncode == 0:
                return done.stdout.decode(errors="ignore").strip()
        except Exception:
            pass
    return None


def force_gpio_mode():
    """Sets each test pin's CNF bit so the pin is in GPIO mode rather than
    SFIO, whatever a previously run test left it as. Read-modify-write, so
    the other seven pins sharing a port register keep their current mode."""
    if os.geteuid() != 0:
        say("SETUP: WARNING - not running as root, register writes will be "
            "attempted via 'sudo -n' and may be refused")

    reachable = False
    for pin in PIN_LIST:
        entry = PIN_CNF.get(pin)
        if entry is None:
            say(f"SETUP: WARNING - pin {pin} has no CNF entry, mode not forced")
            continue
        addr, mask = entry
        current = _devmem([hex(addr)])
        if current is None:
            continue
        reachable = True
        try:
            value = int(current, 16)
        except ValueError:
            continue
        if (value & mask) != mask:
            if _devmem([hex(addr), "32", hex(value | mask)]) is not None:
                say(f"SETUP: pin {pin} was in SFIO mode, forced back to GPIO")

    if not reachable:
        say("SETUP: WARNING - no CNF register could be read. busybox devmem "
            "is unavailable or permission was refused; pins already muxed "
            "to a hardware function will not blink.")


def log_result(status, details):
    try:
        new_file = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["timestamp", "test", "status", "details"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             "GPIO", status, details])
    except Exception:
        return

    # This script now runs as root, so hand the log back to the login user
    # or the next non-root writer is locked out of its own CSV.
    uid = os.environ.get("SUDO_UID")
    gid = os.environ.get("SUDO_GID")
    if uid and gid:
        try:
            os.chown(LOG_FILE, int(uid), int(gid))
        except Exception:
            pass


def all_off():
    for pin in PIN_LIST:
        try:
            gpio.output(pin, gpio.LOW)
        except Exception:
            pass


def blink(pin):
    for _ in range(BLINKS_PER_PIN):
        gpio.output(pin, gpio.HIGH)
        time.sleep(BLINK_INTERVAL_SECONDS)
        gpio.output(pin, gpio.LOW)
        time.sleep(BLINK_INTERVAL_SECONDS)


def gpiotest():
    force_gpio_mode()

    gpio.setwarnings(False)
    gpio.setmode(gpio.BOARD)

    pin_results = {pin: "PASS" for pin in PIN_LIST}

    for pin in PIN_LIST:
        try:
            gpio.setup(pin, gpio.OUT, initial=gpio.LOW)
        except Exception as e:
            pin_results[pin] = "FAIL"
            say(f"Pin {pin} setup failed: {e}")

    say("GPIO LIST: " + ",".join(str(p) for p in PIN_LIST))
    say(f"Blinking {len(PIN_LIST)} pins one at a time, "
        f"{BLINKS_PER_PIN} blinks each.")

    try:
        for pin in PIN_LIST:
            if pin_results[pin] == "FAIL":
                say(f"GPIO SKIP: {pin}")
                continue
            say(f"GPIO NOW: {pin}")
            try:
                blink(pin)
            except Exception as e:
                pin_results[pin] = "FAIL"
                say(f"Pin {pin} write failed: {e}")
            time.sleep(GAP_SECONDS)

        all_off()

        any_pin_failed = any(s == "FAIL" for s in pin_results.values())
        overall = "FAIL" if any_pin_failed else "PASS"

        pin_summary = ",".join(f"{pin}={status}"
                               for pin, status in pin_results.items())
        say(f"GPIO PINS: {pin_summary}")
        say(f"GPIO TEST: {overall}")

        log_result(overall, f"pins {pin_summary}, sequential blink")
        return not any_pin_failed

    except Exception as e:
        all_off()
        say(f"GPIO TEST: FAIL - {e}")
        log_result("FAIL", str(e))
        return False

    finally:
        
        all_off()


if __name__ == "__main__":
    gpiotest()
