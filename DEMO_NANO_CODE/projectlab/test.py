import subprocess
password="group7\n"
subprocess.run(["sudo","busybox", "devmem", "0x6000d204", "32", "0"], input=password, universal_newlines=True,)
subprocess.run(["sudo", "./I2S_test.sh"])