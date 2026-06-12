"""
Tests to run:
GPIO
PWM
SPI
UART
I2C
I2S
CAMERA PORT
"""
import tkinter as tk
import threading
from threading import Event
import gpiotest
import pwmtest



class NanoGUI():
    def __init__(self):
        #events to stop functions from other files
        self.stop_gpio_test = Event()
        self.stop_pwm_test = Event()

        #Main Window
        self.root = tk.Tk()
        self.root.title("Jetson Nano Test Software")
        self.root.geometry("1280x720")
        self.label = tk.Label(self.root,text="Jetson Nano Testbench",
                              font=("Comic Sans MS",28))
        self.label.pack(pady=20)

        #Different frames for different tests
        self.buttonFrame = tk.Frame(self.root)
        self.gpioFrame = tk.Frame(self.root)
        self.pwmFrame = tk.Frame(self.root)


        # Frame and widgets for main window
        self.buttonFrame.columnconfigure(0, weight=1)
        self.buttonFrame.columnconfigure(1, weight=1)
        self.buttonFrame.columnconfigure(2, weight=1)

        self.gpiobutton = tk.Button(self.buttonFrame, text="Test GPIO",command=self.gpio_test, width=20, height=5)
        self.pwmbutton = tk.Button(self.buttonFrame, text="Test PWM",command=self.pwm_test, width=20, height=5)
        self.spibutton = tk.Button(self.buttonFrame, text="Test SPI", width=20, height=5)
        self.uartbutton = tk.Button(self.buttonFrame, text="Test UART", width=20, height=5)
        self.i2cbutton = tk.Button(self.buttonFrame, text="Test I2C", width=20, height=5)
        self.i2sbutton = tk.Button(self.buttonFrame, text="Test I2S", width=20, height=5)
        self.cambutton = tk.Button(self.buttonFrame, text="Test CAMERA", width=20, height=5)

        self.gpiobutton.grid(row=0, column=0)
        self.pwmbutton.grid(row=0, column=1)
        self.spibutton.grid(row=0, column=2)
        self.uartbutton.grid(row=1, column=0)
        self.i2cbutton.grid(row=1, column=1)
        self.i2sbutton.grid(row=1, column=2)
        self.cambutton.grid(row=2, column=0)

        # widgets for GPIO frame
        self.gpiolabel = tk.Label(self.gpioFrame, text="The Green LED should be blinking",
                                  font=("Comic Sans MS", 18))
        self.gpiolabel.pack(padx=20, pady=20)
        self.gbutton = tk.Button(self.gpioFrame, text="Back", command=self.back_button)
        self.gbutton.pack()

        # widgets for PWM frame
        self.pwmlabel = tk.Label(self.pwmFrame, text="The servo should spin", 
                                 font=("Comic Sans MS", 18))
        self.pwmlabel.pack(padx=20, pady=20)
        self.pbutton = tk.Button(self.pwmFrame, text="Back", command=self.back_button)
        self.pbutton.pack()

        #Load main screen and start the loop
        self.buttonFrame.pack()
        self.root.mainloop()

    #function for gpio button
    def gpio_test(self):
            self.buttonFrame.pack_forget()
            self.gpioFrame.pack()

            self.stop_gpio_test.clear()
            self.gpio_thread = threading.Thread(
                target=gpiotest.gpiotest,
                args=(self.stop_gpio_test,),
                daemon=True
            )
            self.gpio_thread.start()
    #function for pwm button
    def pwm_test(self):
          self.buttonFrame.pack_forget()
          self.pwmFrame.pack()

          self.stop_pwm_test.clear()
          self.pwm_thread = threading.Thread(
                target=pwmtest.pwmtest,
                args=(self.stop_pwm_test,),
                daemon=True
          )

          self.pwm_thread.start()
    #function for back button
    def back_button(self):
            self.stop_gpio_test.set()
            self.stop_pwm_test.set()

            self.gpioFrame.pack_forget()
            self.pwmFrame.pack_forget()
            self.buttonFrame.pack()

    


NanoGUI()