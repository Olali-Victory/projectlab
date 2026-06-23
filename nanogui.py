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
import uarttest



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
        self.uartFrame = tk.Frame(self.root)


        # Frame and widgets for main window
        self.buttonFrame.columnconfigure(0, weight=1)
        self.buttonFrame.columnconfigure(1, weight=1)
        self.buttonFrame.columnconfigure(2, weight=1)

        self.gpiobutton = tk.Button(self.buttonFrame, text="Test GPIO",command=self.gpio_test, width=20, height=5)
        self.pwmbutton = tk.Button(self.buttonFrame, text="Test PWM",command=self.pwm_test, width=20, height=5)
        self.spibutton = tk.Button(self.buttonFrame, text="Test SPI", width=20, height=5)
        self.uartbutton = tk.Button(self.buttonFrame, text="Test UART", command=self.uart_test, width=20, height=5)
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

        self.statusframe = tk.Frame(self.root)
        self.statusframe.columnconfigure(0, weight=1)
        self.statusframe.columnconfigure(1, weight=1)
        self.statuslabel = tk.Label(self.statusframe, text="Status", font=("Comic Sans MS",20))
        self.gpiolabel = tk.Label(self.statusframe, text="GPIO Status:", font=("Comic Sans MS",16))
        self.gpiostatus = tk.Label(self.statusframe, text="N/A", font=("Comic Sans MS",16))
        self.pwmlabel = tk.Label(self.statusframe, text="PWM Status:", font=("Comic Sans MS",16))
        self.pwmstatus = tk.Label(self.statusframe, text="N/A", font=("Comic Sans MS",16))
        self.uartlabel = tk.Label(self.statusframe, text="UART Status:", font=("Comic Sans MS",16))
        self.uartstatus = tk.Label(self.statusframe, text="N/A", font=("Comic Sans MS",16))
        
        
        self.statusframe.place(x=750, y=100)
        self.statuslabel.grid(row=0, column=1, padx=20,pady=10)
        self.gpiolabel.grid(row=1, column=0, padx=20, pady=10)
        self.gpiostatus.grid(row=1, column=1, padx=20, pady=10)
        self.pwmlabel.grid(row=2, column=0, padx=20, pady=10)
        self.pwmstatus.grid(row=2, column=1, padx=20, pady=10)
        self.uartlabel.grid(row=3, column=0, padx=20, pady=10)
        self.uartstatus.grid(row=3, column=1, padx=20, pady=10)

        # widgets for GPIO frame
        self.gpiolabel = tk.Label(self.gpioFrame, text="LEDs Start Blinking",
                                  font=("Comic Sans MS", 18))
        self.gpiolabel.pack(padx=20, pady=20)
        self.gvar = tk.IntVar()
        self.gpiocheckbox = tk.Checkbutton(self.gpioFrame, text="Are LEDs blinking?", variable = self.gvar)
        self.gpiocheckbox.pack(padx=10, pady=10)
        self.warning = tk.Label(self.gpioFrame, text="Make sure to click the checkbox if it works",
                                  font=("Comic Sans MS", 10), fg="red")
        self.warning.pack()
        self.gbutton = tk.Button(self.gpioFrame, text="Back", command=self.back_button)
        self.gbutton.pack()

        # widgets for PWM frame
        self.pwmlabel = tk.Label(self.pwmFrame, text="The servo should spin", 
                                 font=("Comic Sans MS", 18))
        self.pwmlabel.pack(padx=20, pady=20)
        self.pvar = tk.IntVar()
        self.pwmcheckbox = tk.Checkbutton(self.pwmFrame, text="Is the servo spinning like in the image?", variable = self.pvar)
        self.pwmcheckbox.pack(padx=10, pady=10)
        self.warning = tk.Label(self.pwmFrame, text="Make sure to click the checkbox if it works",
                                  font=("Comic Sans MS", 10), fg="red")
        self.warning.pack()
        self.pbutton = tk.Button(self.pwmFrame, text="Back", command=self.back_button)
        self.pbutton.pack()

        # widgets for uart frame
        self.uartlabel = tk.Label(self.uartFrame, text="UART Echo", font=("Comic Sans MS", 18))
        self.uartlabel.pack(padx=20, pady=20)
        self.uarttextbox = tk.Text(self.uartFrame,
                                   width = 30, height = 10, font=("Comic Sans MS", 12))
        self.uarttextbox.pack()
        self.send = tk.Button(self.uartFrame, text = "Send", command= self.uart_send)
        self.ubutton = tk.Button(self.uartFrame, text = "Back", command=self.back_button)
        self.received = tk.Text(self.uartFrame, width=30, height=10, font=("Comic Sans MS", 12))

        self.send.pack(padx=20, pady=20)
        self.ubutton.pack(padx=20, pady=20)
        self.received.pack()

        #Load main screen and start the loop
        self.buttonFrame.place(x=100, y=100)
        self.root.mainloop()

    #function for gpio button
    def gpio_test(self):
            self.buttonFrame.place_forget()
            self.statusframe.place_forget()
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
            self.buttonFrame.place_forget()
            self.statusframe.place_forget()
            self.pwmFrame.pack()

            self.stop_pwm_test.clear()
            self.pwm_thread = threading.Thread(
                  target=pwmtest.pwmtest,
                  args=(self.stop_pwm_test,),
                  daemon=True
            )

            self.pwm_thread.start()
            if self.pvar.get() == 1:
                  self.pwmstatus.config(text="PASS")
            else:
                  self.pwmstatus.config(text="FAIL")

    def uart_test(self):
          self.buttonFrame.place_forget()
          self.statusframe.place_forget()
          self.uartFrame.pack()

    def uart_send(self):
            message = self.uarttextbox.get('1.0','end-1c')
            received = uarttest.uarttest(message)
            self.received.insert('1.0', received)
            if message == received:
                  self.uartstatus.config(text= "PASS")
            else:
                  self.uartstatus.config(text= "FAIL")
          

    #function for back button
    def back_button(self):
            self.stop_gpio_test.set()
            self.stop_pwm_test.set()
            

            
            self.pwmFrame.pack_forget()
            self.gpioFrame.pack_forget()
            self.uarttextbox.delete('1.0','end')
            self.received.delete('1.0','end')
            self.uartFrame.pack_forget()
            self.statusframe.place(x=750, y=100)
            self.buttonFrame.place(x=100, y=100)
            
NanoGUI()