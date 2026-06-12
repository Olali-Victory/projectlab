import serial
import time

ser = serial.Serial("/dev/ttyTHS1",9600,timeout=1)
message = input()


ser.write(message.encode())
time.sleep(0.1)

received = ser.readline()

print("Sent: ", message)
print("Received: ", received.decode())

if received.decode() == message:
    print("UART LOOPBACK: PASS")

else:
    print("UART LOOPBACK FAILED")

ser.close()