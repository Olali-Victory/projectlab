#!/bin/bash
# ============================================================
# I2S OUTPUT TEST -- Jetson Nano -> PCM5102A I2S DAC
#
# WIRING (DAC board -> Jetson 40-pin header)
#   DAC VIN  -> Pin 2 or 4     (5V; board accepts 3.3-5V)
#   DAC GND  -> Pin 39         (GND)
#   DAC BCK  -> Pin 12         (i2s4b_sclk)
#   DAC LCK  -> Pin 35         (i2s4b_fs)
#   DAC DIN  -> Pin 40         (i2s4b_dout)   NOT pin 38
#   DAC SCK  -> GND            (lets the DAC self-clock)
#   DAC XSMT -> 3.3V           (LOW = muted, must be HIGH)
#   DAC FMT / FLT / DEMP -> GND or left at board defaults
#
#   Plug earbuds or a speaker into the DAC's 3.5mm jack.
#
# On success this script is quiet: it prints the playback notice
# and the result. Setup detail is printed only for the step that
# actually fails.
#
# STDOUT CONTRACT (parsed by nanogui_windows_V6.py):
#   "I2S PLAYBACK: COMPLETE"  printed only when aplay succeeds
# ============================================================

CARD="tegrasndt210ref"
TONE="/tmp/dac_testtone.wav"

fail() {
    STEP="$1"
    shift
    echo ""
    echo "--- FAILED AT: $STEP ---"
    for detail in "$@"; do
        [ -n "$detail" ] && echo "$detail"
    done
    echo ""
    echo "I2S OUTPUT TEST: FAIL"
    exit 1
}

ERR=$(busybox devmem 0x6000d204 32 0 2>&1)
if [ $? -ne 0 ]; then
    fail "Step 0 - pinmux fix, switch I2S4 pins from GPIO to SFIO" \
         "$ERR" \
         "Command was: busybox devmem 0x6000d204 32 0" \
         "Check that busybox is installed and this ran as root."
fi

ERR=$(amixer -c $CARD cset name='I2S4 Mux' 'ADMAIF1' 2>&1)
if [ $? -ne 0 ]; then
    fail "Step 1 - route I2S4 playback <- ADMAIF1" \
         "$ERR" \
         "Confirm I2S4 is enabled in jetson-io and the Jetson was rebooted." \
         "List the available controls with:" \
         "  amixer -c $CARD controls | grep -i i2s4"
fi

ERR=$(amixer -c $CARD cset name='I2S4 codec master mode' cbs-cfs 2>&1)
if [ $? -ne 0 ]; then
    fail "Step 2 - I2S4 clock mode = cbs-cfs" \
         "$ERR" \
         "Without cbs-cfs the Jetson will not drive BCLK or LRCLK." \
         "Check the exact control name with:" \
         "  amixer -c $CARD controls | grep -i 'master mode'"
fi

ERR=$(amixer -c $CARD cset name='I2S4 codec frame mode' i2s 2>&1)
if [ $? -ne 0 ]; then
    fail "Step 3 - I2S4 frame mode = i2s" \
         "$ERR" \
         "Check the exact control name with:" \
         "  amixer -c $CARD controls | grep -i 'frame mode'"
fi

rm -f "$TONE"
ERR=$(python3 -u - "$TONE" << 'PYEOF' 2>&1
import math
import struct
import sys
import wave

path = sys.argv[1]
rate = 48000
seconds = 5
freq = 440.0
amp = 0.5

with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    frames = bytearray()
    for i in range(rate * seconds):
        v = int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))
        frames += struct.pack("<hh", v, v)
    w.writeframes(bytes(frames))
PYEOF
)
if [ $? -ne 0 ] || [ ! -s "$TONE" ]; then
    fail "Step 4 - generate the 440 Hz test tone" \
         "$ERR" \
         "Could not write $TONE. Check that python3 is present and /tmp is writable."
fi

echo "Now playing the tone - listen on the DAC headphone jack (5 seconds)."

PLAY_ERR=$(aplay -D hw:$CARD,0 "$TONE" 2>&1)
PLAY_RC=$?
if [ $PLAY_RC -ne 0 ]; then
    fail "Step 5 - playback with aplay" \
         "$PLAY_ERR" \
         "aplay exited with code $PLAY_RC on hw:$CARD,0." \
         "List the playback devices with:  aplay -l"
fi

echo "I2S OUTPUT TEST: PASS"
echo "I2S PLAYBACK: COMPLETE"
echo "Confirm in the GUI that you actually heard the tone."
