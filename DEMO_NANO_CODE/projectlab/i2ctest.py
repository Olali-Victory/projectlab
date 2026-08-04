import sys
import time

try:
    import board
    import busio
    import adafruit_vl53l0x
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    print("I2C TEST: FAIL")
    sys.exit(1)

SENSOR_ADDR = 0x29
READS = 3


def main():
    try:
        print("Initializing I2C bus...")
        i2c = busio.I2C(board.SCL, board.SDA)

        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        i2c.unlock()
        print(f"I2C devices found: {[hex(d) for d in devices]}")

        if SENSOR_ADDR not in devices:
            print("ERROR: VL53L0X not found at 0x29")
            print("I2C TEST: FAIL")
            sys.exit(1)
        print("Sensor found at 0x29")
        print("Initializing VL53L0X...")

        sensor = adafruit_vl53l0x.VL53L0X(i2c)

        readings = []
        for i in range(READS):
            distance = sensor.range
            readings.append(distance)
            print(f"Reading {i + 1}: {distance} mm")
            time.sleep(0.3)

        avg = sum(readings) / len(readings)
        print(f"Average distance: {avg:.1f} mm")

        if 20 <= avg <= 2000:
            print("I2C TEST: PASS")
        else:
            print("I2C SENSOR OUT OF RANGE")
            print("I2C TEST: FAIL")
            sys.exit(1)
    except Exception as e:
        print(f"I2C ERROR: {e}")
        print("I2C TEST: FAIL")
        sys.exit(1)


main()
