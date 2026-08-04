import time
import board
import busio
import adafruit_vl53l0x


def i2c_hardware_test(log_callback=None):
    try:
        #I2C 2 bus on jetson nano
        i2c = busio.I2C(board.SCL, board.SDA)
        if log_callback:
            log_callback("Initializing I2C bus...")

        #check device address
        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        i2c.unlock()
        if log_callback:
            log_callback(f"I2C devices found: {[hex(d) for d in devices]}")

        #check sensor is read
        if 0xXX not in devices: #find correct address with testing
            if log_callback:
                log_callback("ERROR: VL53L0X not found at 0x29")
            return False
        if log_callback:
            log_callback("Sensor found at 0x29")
            log_callback("Initializing VL53L0X...")

        #Initialize sensor
        sensor = adafruit_vl53l0x.VL53L0X(i2c)

        #read distance 
        readings = []

        for i in range(3):
            distance = sensor.range  # mm
            readings.append(distance)

            if log_callback:
                log_callback(f"Reading {i+1}: {distance} mm")

            time.sleep(0.3)

        # average of 3 readings to produce more accurate result
        avg = sum(readings) / len(readings)

        if log_callback:
            log_callback(f"Average distance: {avg:.1f} mm")

        #rejects outlier readings
        if 20 <= avg <= 2000:
            if log_callback:
                log_callback("I2C SENSOR TEST PASSED\n")
            return True
        else:
            if log_callback:
                log_callback("I2C SENSOR OUT OF RANGE\n")
            return False

    except Exception as e:
        if log_callback:
            log_callback(f"I2C ERROR: {e}")
        return False
    #at any point a test fails-> error