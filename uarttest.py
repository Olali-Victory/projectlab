import serial
import time


def uarttest(message):

    ser = serial.Serial("/dev/ttyTHS1",9600,timeout=1)


    ser.write(message.encode())
    time.sleep(0.1)

    received = ser.readline()


    if received.decode() == message:
        print("UART LOOPBACK: PASS")

    else:
        print("UART LOOPBACK FAILED")

    ser.close()
    return received.decode()