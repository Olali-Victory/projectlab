"""
    Mic BCLK  -> Pin 12
    Mic LRCL  -> Pin 35
    Mic DOUT  -> Pin 38
    Mic 3V    -> Pin 1 (3.3V)
    Mic GND   -> Any GND pin
    Mic SEL   -> GND (selects left channel)

    sudo apt install python3-pyaudio portaudio19-dev
    pip3 install pyaudio numpy
"""

import pyaudio
import numpy as np
import wave
import sys

SAMPLE_RATE = 16000      
CHANNELS = 1                
FORMAT = pyaudio.paInt32   
CHUNK = 1024
RECORD_SECONDS = 3
OUTPUT_FILE = "i2s_mic_test.wav"


SIGNAL_THRESHOLD = 500


def find_i2s_input_device(p):
    
    target_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info.get("name", "")
        max_in = info.get("maxInputChannels", 0)
        print(f"  [{i}] {name}  (input channels: {max_in})")
        if max_in > 0 and target_index is None:
            target_index = i
    return target_index


def record_audio(p, device_index):
    print(f"\nRecording {RECORD_SECONDS} seconds of audio... (make some noise!)")
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK,
    )

    frames = []
    for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    return frames


def analyze_audio(frames):
    """Combines recorded chunks and checks if real signal was captured."""
    raw = b"".join(frames)
    samples = np.frombuffer(raw, dtype=np.int32)

    peak_amplitude = np.max(np.abs(samples))
    avg_amplitude = np.mean(np.abs(samples))

    print(f"\nPeak amplitude:    {peak_amplitude}")
    print(f"Average amplitude: {avg_amplitude:.1f}")

    return peak_amplitude, avg_amplitude


def save_wav(frames, p):
    wf = wave.open(OUTPUT_FILE, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b"".join(frames))
    wf.close()
    print(f"Saved recording to {OUTPUT_FILE}")


def main():
    p = pyaudio.PyAudio()

    device_index = find_i2s_input_device(p)
    if device_index is None:
        print("FAIL - No input-capable audio device found.")
        print("   Check that jetson-io has I2S enabled and the Jetson was rebooted.")
        p.terminate()
        sys.exit(1)

    frames = record_audio(p, device_index)
    peak, avg = analyze_audio(frames)
    save_wav(frames, p)

    p.terminate()

    print("\n--- RESULT ---")
    if peak > SIGNAL_THRESHOLD:
        print(f"PASS - Real audio signal detected (peak {peak} > threshold {SIGNAL_THRESHOLD}).")
        print("   I2S receive path (microphone -> Jetson) is working.")
    else:
        print(f"FAIL - Signal too low (peak {peak} <= threshold {SIGNAL_THRESHOLD}).")
        print("   Check wiring, pin configuration (jetson-io), and that the mic has power.")


if __name__ == "__main__":
    main()
