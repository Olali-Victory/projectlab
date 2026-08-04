import struct
import subprocess
import sys
import time

CARD = "tegrasndt210ref"
DEVICE = "hw:%s,1" % CARD
RATE = 48000
BLOCK = 4800
SCALE = 16384.0

SKIP_BLOCKS = 6
CAL_BLOCKS = 10
THRESH_MULT = 5.0
MIN_THRESHOLD = 2500.0
HOLD_BLOCKS = 4


def say(msg):
    print(msg, flush=True)


def run(cmd):
    return subprocess.run(cmd, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode


def read_reg(addr):
    """Returns the current value of a register, or None if it can't be read."""
    try:
        done = subprocess.run("busybox devmem %s" % addr, shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              timeout=5)
        if done.returncode == 0:
            return int(done.stdout.decode(errors="ignore").strip(), 16)
    except Exception:
        pass
    return None


def setup():
    say("SETUP: pinmux fix, I2S4 pins GPIO -> SFIO")
    current = read_reg("0x6000d204")
    if current is None:
        run("busybox devmem 0x6000d204 32 0")
    elif current & 0xF0:
        run("busybox devmem 0x6000d204 32 %s" % hex(current & ~0xF0))

    say("SETUP: routing ADMAIF2 capture <- I2S4")
    if run("amixer -c %s cset name='ADMAIF2 Mux' 'I2S4'" % CARD) != 0:
        say("I2S INPUT TEST: FAIL")
        say("Could not set 'ADMAIF2 Mux'. Confirm I2S4 is enabled in "
            "jetson-io and that the Jetson was rebooted afterwards.")
        return False

    say("SETUP: I2S4 codec master mode = cbs-cfs")
    run("amixer -c %s cset name='I2S4 codec master mode' cbs-cfs" % CARD)

    say("SETUP: I2S4 codec frame mode = i2s")
    run("amixer -c %s cset name='I2S4 codec frame mode' i2s" % CARD)

    say("SETUP: complete")
    return True


def analyse(raw):
    n = len(raw) // 4
    vals = struct.unpack("<%di" % n, raw[:n * 4])

    peak = 0
    total = 0.0
    for v in vals:
        a = v if v >= 0 else -v
        if a > peak:
            peak = a
        total += v

    mean = total / n
    sq = 0.0
    crossings = 0
    prev = vals[0] - mean
    for v in vals:
        d = v - mean
        sq += d * d
        if (d >= 0.0) != (prev >= 0.0):
            crossings += 1
        prev = d

    rms = (sq / n) ** 0.5
    freq = (crossings / 2.0) * (RATE / float(n))
    return peak / SCALE, rms / SCALE, freq


def monitor_i2s(stop_event, data_queue):
    forced = None
    if len(sys.argv) > 1:
        try:
            forced = float(sys.argv[1])
        except ValueError:
            forced = None

    if not setup():
        sys.exit(1)

    cmd = ["arecord", "-D", DEVICE, "-r", str(RATE), "-f", "S32_LE",
           "-c", "1", "-t", "raw", "-q", "-"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        say("I2S INPUT TEST: FAIL")
        say("arecord not found. Install alsa-utils.")
        sys.exit(1)

    time.sleep(0.2)
    if proc.poll() is not None:
        say("I2S INPUT TEST: FAIL")
        say("arecord could not open %s" % DEVICE)
        sys.exit(1)

    need = BLOCK * 4
    skipped = 0
    cal_peaks = []
    threshold = None
    hold = 0
    detected_once = False

    say("MONITOR: settling - discarding the capture startup transient")

    try:
        while not stop_event.is_set():
            raw = proc.stdout.read(need)
            if not raw or len(raw) < need:
                say("I2S INPUT TEST: FAIL")
                say("Capture stream ended unexpectedly.")
                break

            peak, rms, freq = analyse(raw)
            data_queue.put((peak, rms, freq))

            if skipped < SKIP_BLOCKS:
                skipped += 1
                #say("I2S LEVEL peak=%.1f rms=%.1f freq=0 over=0"
                   # % (peak, rms))
                if skipped == SKIP_BLOCKS:
                    if forced is not None:
                        threshold = forced
                        say("THRESHOLD peak=%.1f" % threshold)
                        say("MONITOR: make noise near the microphone now")
                    else:
                        say("MONITOR: measuring the noise floor - stay quiet")
                continue

            if threshold is None:
                cal_peaks.append(peak)
                #say("I2S LEVEL peak=%.1f rms=%.1f freq=0 over=0"
                    #% (peak, rms))
                if len(cal_peaks) >= CAL_BLOCKS:
                    floor = sum(cal_peaks) / len(cal_peaks)
                    threshold = max(MIN_THRESHOLD, floor * THRESH_MULT)
                    say("BASELINE peak=%.1f" % floor)
                    say("THRESHOLD peak=%.1f" % threshold)
                    say("MONITOR: make noise near the microphone now")
                continue

            if peak > threshold:
                hold = HOLD_BLOCKS
                if not detected_once:
                    detected_once = True
                    say("SOUND DETECTED peak=%.1f threshold=%.1f"
                        % (peak, threshold))
                    say("I2S RECORD: COMPLETE")
            elif hold > 0:
                hold -= 1

            over = 1 if hold > 0 else 0
            shown = freq if over else 0.0
            #say("I2S LEVEL peak=%.1f rms=%.1f freq=%.0f over=%d"
                #% (peak, rms, shown, over))

    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
