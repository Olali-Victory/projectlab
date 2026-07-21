#!/bin/bash
# ============================================================
# PCM5102A I2S DAC  --  OUTPUT (playback) test for Jetson Nano
#
#   chmod +x dac_output_test.sh
#   ./dac_output_test.sh
#
# This is the OUTPUT counterpart to the mic test. Instead of the
# Jetson recording audio IN, the Jetson plays audio OUT through the
# PCM5102A DAC, and you listen on earbuds/speaker plugged into the
# DAC's 3.5mm jack.
#
# WHY THIS TEST: the microphone (input) path was blocked by the
# Jetson not generating an I2S4 bit clock. Playback (TX) goes through
# a partially different driver path, so it's worth checking whether
# I2S4 clocks on OUTPUT even though it didn't on input.
#
# ------------------------------------------------------------
# WIRING:  PCM5102A board  ->  Jetson 40-pin header
# ------------------------------------------------------------
#   DAC VIN  -> Jetson 5V  (pin 2 or 4)   [board accepts 3.3-5V; 5V is fine]
#   DAC GND  -> Jetson GND (e.g. pin 39)
#   DAC LCK  -> Jetson pin 35  (LRCLK / word select  = i2s4b_fs)
#   DAC BCK  -> Jetson pin 12  (BCLK / bit clock      = i2s4b_sclk)
#   DAC DIN  -> Jetson pin 40  (data IN to DAC        = i2s4b_dout)
#               ^^^ NOTE: this is pin 40, NOT 38. For OUTPUT the Jetson
#               TRANSMITS data, so we use the data-OUT pin (i2s4b_dout = pin 40),
#               which is different from the mic test (which used pin 38, din).
#   DAC SCK  -> Jetson GND     (ties SCK low = DAC generates its own master
#               clock internally; this is the key "just works" trick)
#
#   On the DAC board, also set the control pins if they're broken out:
#     XSMT (mute) -> HIGH (3.3V)  [low = muted, so it MUST be high]
#     FMT         -> LOW          [low = standard I2S]
#     FLT, DEMP   -> LOW          [defaults]
#   Many PCM5102A boards hardwire these already; check your board's silkscreen.
#
#   Plug earbuds/speaker into the DAC's 3.5mm jack.
# ============================================================

CARD="tegrasndt210ref"

echo "=== Step 1: Route I2S4 <- ADMAIF1 for PLAYBACK ==="
# For OUTPUT, the data flows ADMAIF1 -> I2S4 (opposite of the mic test).
# The I2S4 'Mux' selects what feeds the I2S4 transmitter.
amixer -c $CARD cset name='I2S4 Mux' 'ADMAIF1' 2>/dev/null

echo "=== Step 2: I2S4 clock mode = codec slave (Jetson is master) ==="
amixer -c $CARD cset name='I2S4 codec master mode' cbs-cfs > /dev/null

echo "=== Step 3: I2S4 frame mode = i2s (standard -- DAC uses standard I2S) ==="
amixer -c $CARD cset name='I2S4 codec frame mode' i2s > /dev/null

echo ""
echo "=== Settings applied. Generating a 5-second test tone... ==="

# Generate a clean 440 Hz sine tone WAV with sox if available; otherwise
# fall back to speaker-test's built-in tone generator.
if command -v sox >/dev/null 2>&1; then
    sox -n /tmp/testtone.wav synth 5 sine 440 rate 48000 channels 2
    echo "    Playing 440 Hz tone through the DAC. Listen on the earbuds!"
    aplay -D hw:$CARD,0 /tmp/testtone.wav
else
    echo "    sox not installed; using speaker-test instead."
    echo "    Playing tone through the DAC. Listen on the earbuds! (Ctrl+C to stop)"
    speaker-test -D hw:$CARD,0 -c 2 -t sine -f 440 -l 1
fi

echo ""
echo "=== Done. ==="
echo "If you heard the tone -> I2S OUTPUT works! The interface is validated."
echo "If silent -> probe BCLK (pin 12) on the scope to check if the clock"
echo "             is generated on output (same method as the mic test)."

echo "I2S PLAYBACK: COMPLETE"
