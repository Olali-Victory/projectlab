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
import serial



class NanoGUI():
        def __init__(self):
                #events to stop functions from other files
                self.stop_gpio_test = Event()
                self.stop_pwm_test = Event()

                #Main Window
                self.root = tk.Tk()
                self.root.title("Jetson Nano Test Software")
                self.root.geometry("1280x720")
                self.root.configure(background='black')
                self.label = tk.Label(self.root,text="Jetson Nano Testbench",
                                font=('Arial', 28, 'bold'), bg='black', fg='white')
                self.label.pack(pady=20)

                #Different frames for different tests
                self.buttonFrame = tk.Frame(self.root, bg='black')
                self.gpioFrame = tk.Frame(self.root, bg='black')
                self.pwmFrame = tk.Frame(self.root, bg='black')
                self.uartFrame = tk.Frame(self.root, bg='black')


                # Frame and widgets for main window

                self.gpiobutton = tk.Button(self.buttonFrame, text="Test GPIO",command=self.gpio_test, width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.pwmbutton = tk.Button(self.buttonFrame, text="Test PWM",command=self.pwm_test, width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.spibutton = tk.Button(self.buttonFrame, text="Test SPI", width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.uartbutton = tk.Button(self.buttonFrame, text="Test UART", command=self.uart_test, width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.i2cbutton = tk.Button(self.buttonFrame, text="Test I2C", width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.i2sbutton = tk.Button(self.buttonFrame, text="Test I2S", width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.cambutton = tk.Button(self.buttonFrame, text="Test CAMERA", width=30, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)

                

                self.gpiobutton.pack(pady=20)
                self.pwmbutton.pack(pady=20)
                self.spibutton.pack(pady=20)
                self.uartbutton.pack(pady=20)
                self.i2cbutton.pack(pady=20)
                self.i2sbutton.pack(pady=20)
                self.cambutton.pack(pady=20)

                self.logFrame = tk.Frame(self.root, bg='black')
                self.loglabel = tk.Label(self.logFrame, text = 'Test Log', font=('Arial', 18, 'bold'),bg='black', fg='white')
                self.loglabel.pack()
                self.logbox = tk.Text(self.logFrame, border=0, relief='flat', highlightthickness=1, highlightcolor='white', bg='black', fg='white')
                self.logbox.pack(fill="both", expand=True, padx=10, pady=10)
                self.logdownload = tk.Button(self.logFrame, text = 'Download Log', command=self.getlogs ,width=50, height=2,bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.logdownload.pack(pady=20)
                self.logwarning = tk.Label(self.logFrame, text='There is nothing in the log at the moment, run some tests and try again :)',
                                           font=("Comic Sans MS", 10), bg='black',fg="red")
        
                # widgets for GPIO frame
                self.gpiolabel = tk.Label(self.gpioFrame, text="LEDs Start Blinking",
                                        font=("Comic Sans MS", 18), bg='black', fg='white')
                self.gpiolabel.pack(padx=20, pady=20)
                self.gvar = tk.IntVar()
                self.gpiocheckbox = tk.Checkbutton(self.gpioFrame, text="Are LEDs blinking?", variable = self.gvar, bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.gpiocheckbox.pack(padx=10, pady=10)
                self.warning = tk.Label(self.gpioFrame, text="Make sure to click the checkbox if it works",
                                        font=("Comic Sans MS", 10), bg='black', fg="red")
                self.warning.pack()
                self.gbutton = tk.Button(self.gpioFrame, text="Back", command=self.gpio_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.gbutton.pack(pady=20)

                # widgets for PWM frame
                self.pwmlabel = tk.Label(self.pwmFrame, text="The servo should spin", 
                                        font=("Comic Sans MS", 18), bg='black', fg='white')
                self.pwmlabel.pack(padx=20, pady=20)
                self.pvar = tk.IntVar()
                self.pwmcheckbox = tk.Checkbutton(self.pwmFrame, text="Is the servo spinning like in the image?", variable = self.pvar, bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.pwmcheckbox.pack(padx=10, pady=10)
                self.warning = tk.Label(self.pwmFrame, text="Make sure to click the checkbox if it works",
                                        font=("Comic Sans MS", 10), bg='black',fg="red")
                self.warning.pack()
                self.pbutton = tk.Button(self.pwmFrame, text="Back", command=self.pwm_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.pbutton.pack(pady=20)

                # widgets for uart frame
                self.uartlabel = tk.Label(self.uartFrame, text="UART Echo", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.uartlabel.pack(padx=20, pady=20)
                self.uarttextbox = tk.Text(self.uartFrame,
                                        width = 30, height = 10, font=("Comic Sans MS", 12), border=0, relief='flat', highlightthickness=1, highlightcolor='white', bg='black', fg='white')
                self.uarttextbox.pack(fill="both")
                self.send = tk.Button(self.uartFrame, text = "Send", command= self.uart_send, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.ubutton = tk.Button(self.uartFrame, text = "Back", command=self.uart_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.received = tk.Text(self.uartFrame, width=30, height=10, font=("Comic Sans MS", 12), border=0, relief='flat', highlightthickness=1, highlightcolor='white', bg='black', fg='white')

                self.send.pack(padx=20, pady=20)
                self.ubutton.pack(padx=20, pady=20)
                self.received.pack(fill="both")

                #Load main screen and start the loop
                self.logFrame.place(x=400, y=100)
                self.buttonFrame.place(x=100, y=100)
                self.root.mainloop()


        def add_log(self,message):
                self.logwarning.pack_forget()
                self.logbox.insert("end", message + "\n")
                self.logbox.see("end")
        #function for gpio button
        def gpio_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.gpioFrame.pack()

                self.stop_gpio_test.clear()
                self.gpio_thread = threading.Thread(
                        target=gpiotest.gpiotest,
                        args=(self.stop_gpio_test,),
                        daemon=True
                )
                self.add_log("GPIO Test Starting...")
                self.gpio_thread.start()
                
                
        #function for pwm button
        def pwm_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.pwmFrame.pack()

                self.stop_pwm_test.clear()
                self.pwm_thread = threading.Thread(
                        target=pwmtest.pwmtest,
                        args=(self.stop_pwm_test,),
                        daemon=True
                )
                self.add_log("PWM Test Starting...")
                self.pwm_thread.start()
                

        def uart_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.add_log("UART Test Starting...")
                self.uartFrame.pack()

        def uart_send(self):
                try:
                        message = self.uarttextbox.get('1.0','end-1c')
                        received = uarttest.uarttest(message)
                        self.received.insert('1.0', received)
                        if message == received:
                                self.add_log("UART Test: PASS")
                        else:
                                self.add_log("UART Test: FAIL")

                except (PermissionError, serial.serialutil.SerialException) as e:
                        self.add_log("UART Test: FAIL")
                        self.add_log(f"{e} errors occured, please restart the software with Admin permissions")
                
                

        #function for back button
        def gpio_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.gvar.get() == 1:
                        self.add_log("GPIO Test: PASS")
                else:
                        self.add_log("GPIO Test: FAIL")

        def pwm_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.pvar.get() == 1:
                        self.add_log("PWM Test: PASS")
                else:
                        self.add_log("PWM Test: FAIL")

        def uart_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)

        def getlogs(self):
                try:
                        if not self.logbox.get('1.0','end-1c').strip():
                                self.logwarning.pack(pady=10)
                        
                        else:
                                self.log = self.logbox.get('1.0','end-1c')
                                with open("testlogs.txt", "a") as f:
                                        f.write(self.log)

                                f.close()
                except PermissionError:
                        pass

            
NanoGUI()