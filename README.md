Jetson Nano Remote Test Bench 

Contained within the Final_Version_SSH file is a windows py file that validates the hardware interfaces on the 40-pin expansion header of the Jetson Nano Developer Kit over SSH. 
The Windows side runs the interface, the sequencing, and the result tracking. The Jetson holds one small script per interface. The easiest place to run these tests and set them up 
is in the computer lab in the ECE building, as there is easy access to an ethernet port, and external keyboards and monitors

What goes where

FINAL_VERSION_SSH

    The windows host application/computer

    Keep the files together in the same directory 

DEMO_NANO_CODE

    The Jetson Nano 

    file directory == /home/ <"username">/Documents/projectlab

    "username" is whatever the username is for your specific nano. For ours, it is group7 Or group72 depending on which nano you are using 


  JETSON SETUP

    Copy DEMO_NANO_CODE/ to ~/Documents/projectlab

    run the following commands on the terminal on the nano 

    cd /Documents/projectlab/setup

    sudo bash install.sh

    install.sh installs system packages, Python packages, and other configurations that are required to run tests that would otherwise have to be done by hand 

    run hostname -I and write down the IP address displayed and keep it handy 
    
    Run sudo /opt/nvidia/jetson-io/jetson-io.py   

    Select configure pin header and manually configure pins. 

    enable the i2s4, pwm0, pm2, uart, and spi funtionality

    save changes and reboot

    

  WINDOWS SETUP

    Python 3 is the only requirement you must install yourself

    The py file automatically installs paramiko and Pillow itself on the first run. 

    there are four hard-coded values near the top of the file 

    JETSON_IP = "10.131.17.154"

    JETSON_USERNAME = "group7"

    JETSON_PASSWORD = "group7"

    REMOTE_TEST_DIR = "/home/group7/Documents/projectlab" OR "/home/{JETSON_USERNAME}/Documents/projectlab if you don't want to change the username in two locations 

    replace the JETSON_IP with the IP address you acquired when running "hostname -I" on the Jetson. 

    Make sure the JETSON is connected via Ethernet cable to an Ethernet port and that the windows device is on the same network. EX. ttunet
    


  Eight files within DEMO_NANO_CODE/ are called by the windows application. 

    1. GPIO
    2. PWM
    3. UART
    4. I2S Input
    5. I2S Output
    6. SPI
    7. I2C
    8. Camera

  Two are handled within the GUI itself 

    9. USB
    10. Wifi


nanogui.py is a second version of the interface that runs purely on the Jetson itself. Kept as a fallback when there is an external monitor and keyboard attached to the Jetson. Not used by remote test bench. 

Every script configures its own hardware before each run, so the tests can be run in any order. 
