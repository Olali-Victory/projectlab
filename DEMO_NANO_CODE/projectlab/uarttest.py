import os
import subprocess
import sys
import time

PORT = "/dev/ttyTHS1"
BAUD = 115200


def unlock_port():
    """Stops nvgetty and opens permissions on the port. Previously done by
    the Windows GUI at connect time; owned by this script now so the test
    works whatever order it is run in."""
    if os.geteuid() != 0:
        print("SETUP: WARNING - not running as root, cannot stop nvgetty or "
              "chmod %s" % PORT)
        return
    for cmd in ("systemctl stop nvgetty", "chmod 666 %s" % PORT):
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    time.sleep(0.2)


unlock_port()

try:
    import serial
except ImportError:
    print("UART LOOPBACK: FAIL")
    print("pyserial is not installed (pip3 install pyserial)")
    sys.exit(1)

message = sys.argv[1] if len(sys.argv) > 1 else "Hello Jetson"

print("PORT: %s @ %d baud" % (PORT, BAUD))
print("SENT: %s" % message)

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
except PermissionError:
    print("UART LOOPBACK: FAIL")
    print("Permission denied on %s. Run: sudo chmod 666 %s" % (PORT, PORT))
    sys.exit(1)
except Exception as e:
    print("UART LOOPBACK: FAIL")
    print("Could not open %s: %s" % (PORT, e))
    sys.exit(1)

try:
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write((message + "\n").encode())
    ser.flush()
    time.sleep(0.15)
    received = ser.readline().decode(errors="ignore").strip()
finally:
    try:
        ser.close()
    except Exception:
        pass

print("RECEIVED: %s" % received)

if received == message:
    print("UART LOOPBACK: PASS")
else:
    if not received:
        print("Nothing came back. Check the jumper from pin 8 (TX) to "
              "pin 10 (RX).")
    else:
        print("Received text did not match what was sent.")
    print("UART LOOPBACK: FAIL")
