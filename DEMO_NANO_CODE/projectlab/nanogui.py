"""
Tests to run:
GPIO
PWM
SPI
UART
I2C
I2S
CAMERA PORT
USB PORTS
"""
import tkinter as tk
import threading
from threading import Event
import gpiotest_1
import pwmtest_1
import uarttest_1
import cam
import cam1
import i2s_input
import serial
from datetime import datetime
import time
import subprocess
from pathlib import Path
import webbrowser
import queue
import numpy as np
from PIL import Image, ImageTk
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class NanoGUI():
        def __init__(self):
                #events to stop functions from other files
                self.stop_gpio_test = Event()
                self.stop_pwm_test = Event()
                self.stop_pwm_test2 = Event()
                self.stop_cam_test = Event()

                #Main Window
                self.root = tk.Tk()
                self.root.title("Jetson Nano Test Software")
                self.root.geometry("1280x720")
                self.root.configure(background='black')
                self.label = tk.Label(self.root,text="Jetson Nano Testbench", font=('Arial', 28, 'bold'), bg='black', fg='white')
                self.label.pack(pady=20)

                #Different frames for different tests
                self.buttonFrame = tk.Frame(self.root, bg='black')
                self.gpioFrame = tk.Frame(self.root, bg='black')
                self.pwmFrame = tk.Frame(self.root, bg='black')
                self.uartFrame = tk.Frame(self.root, bg='black')
                self.camFrame = tk.Frame(self.root, bg='black')
                self.i2sFrame = tk.Frame(self.root, bg="black")
                self.i2sFrame2 = tk.Frame(self.root, bg = "black")
                self.usbFrame = tk.Frame(self.root, bg="black")
                self.wifiFrame = tk.Frame(self.root, bg='black')


                # Frame and widgets for main window
                self.gpiobutton = tk.Button(self.buttonFrame, text="Test GPIO",command=self.gpio_test, width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.pwmbutton = tk.Button(self.buttonFrame, text="Test PWM",command=self.pwm_test, width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.spibutton = tk.Button(self.buttonFrame, text="Test SPI", width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.uartbutton = tk.Button(self.buttonFrame, text="Test UART", command=self.uart_test, width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.i2cbutton = tk.Button(self.buttonFrame, text="Test I2C", width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.i2sbutton = tk.Button(self.buttonFrame, text="Test I2S OUTPUT", command=self.i2s_test_output,width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.i2sbutton2 = tk.Button(self.buttonFrame, text="Test I2S INPUT", command=self.i2s_test_input,width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.cambutton = tk.Button(self.buttonFrame, text="Test CAMERA", command=self.cam_test,width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.usbbutton = tk.Button(self.buttonFrame, text="Test USB PORTS", command=self.init_usb_test,width=30, height=2,bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.wifibutton = tk.Button(self.buttonFrame, text="Test WIFI", command=self.init_wifi_test,width=30,height=2,bg='grey',fg='white',border=0, relief='flat', highlightthickness=0)

                self.gpiobutton.pack(pady=10)
                self.pwmbutton.pack(pady=10)
                self.spibutton.pack(pady=10)
                self.uartbutton.pack(pady=10)
                self.i2cbutton.pack(pady=10)
                self.i2sbutton.pack(pady=10)
                self.i2sbutton2.pack(pady=10)
                self.cambutton.pack(pady=10)
                self.usbbutton.pack(pady=10)
                self.wifibutton.pack(pady=10)
        
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
                self.pwmlabel2 = tk.Label(self.pwmFrame, text="Pick which pin to test.", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.pwmlabel2.pack(padx=20, pady=20)
                self.pvar = tk.IntVar()
                self.ttcheckbox = tk.Button(self.pwmFrame, text="Test Pin 32", command=self.pwm_test_32, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.tttcheckbox = tk.Button(self.pwmFrame, text="Test Pin 33", command=self.pwm_test_33, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.ttcheckbox.pack(padx=10, pady=10)
                self.tttcheckbox.pack(padx=10, pady=10)
                self.pwmcheckbox = tk.Checkbutton(self.pwmFrame, text="Is the servo moving?", variable = self.pvar, bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.pwmcheckbox.pack(padx=10, pady=10)
                self.warning = tk.Label(self.pwmFrame, text="Make sure to click the checkbox if it works",
                                        font=("Comic Sans MS", 10), bg='black',fg="red")
                self.warning.pack()
                self.pbutton = tk.Button(self.pwmFrame, text="Back", command=self.pwm_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.pbutton.pack(pady=20)
                self.pFrame = tk.Frame(self.pwmFrame, bg= 'black')
                self.img1 = Image.open("32.jpg").resize((500,300))
                self.img2 = Image.open("33.jpg").resize((500,300))
                self.exampleimg1 = ImageTk.PhotoImage(self.img1)
                self.exampleimg2 = ImageTk.PhotoImage(self.img2)
                self.pwm32ins = tk.Label(self.pFrame, text="To Test pin 32 move the yellow wire to pin 32.", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.pwm33ins = tk.Label(self.pFrame, text="To Test pin 33 move the yellow wire to pin 33.", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.pwmimg1 = tk.Label(self.pFrame, image=self.exampleimg1)
                self.pwmimg2 = tk.Label(self.pFrame, image=self.exampleimg2)
                self.pwm32ins.grid(row=0, column=0, padx = 20)
                self.pwm33ins.grid(row=0, column=1, padx = 20)
                self.pwmimg1.grid(row=1, column=0, padx = 20)
                self.pwmimg2.grid(row=1, column=1, padx = 20)
                self.pFrame.pack(pady=10)

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

                #widgets for CAM frame
                self.camlabel = tk.Label(self.camFrame, text =  "CAM Test", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.camlabel.pack(padx=20, pady=20)
                self.caminstructions = tk.Label(self.camFrame, text =  "Pick which camera to test and see your beautiul smile", font=("Comic Sans MS", 12), bg='black', fg='white')
                self.caminstructions.pack(padx=20, pady=20)
                self.cam1button = tk.Button(self.camFrame, text = "Test CAM 1", command=self.cam1_test, bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.cam1button.pack(padx=20, pady=20)
                self.cam2button = tk.Button(self.camFrame, text = "Test CAM 2", command=self.cam2_test, bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.cam2button.pack(padx=20, pady=20)
                self.cbutton = tk.Button(self.camFrame, text = "Back", command=self.cam_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.cbutton.pack(padx=20, pady=20)

                #widgets for i2s frame
                self.i2slabel = tk.Label(self.i2sFrame, text = "I2S Output Test", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.i2slabel.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC VIN  -> Pin 2 or 4     (5V; board accepts 3.3-5V)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC GND  -> Pin 39         (GND)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC BCK  -> Pin 12         (i2s4b_sclk)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC LCK  -> Pin 35         (i2s4b_fs)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC DIN  -> Pin 40         (i2s4b_dout)   NOT pin 38", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC SCK  -> GND            (lets the DAC self-clock)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC XSMT -> 3.3V           (LOW = muted, must be HIGH)", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="DAC FMT / FLT / DEMP -> GND or left at board defaults", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2spinout = tk.Label(self.i2sFrame, text="Plug earbuds or a speaker into the DAC's 3.5mm jack.", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2sinstructions = tk.Label(self.i2sFrame, text =  "A 440Hz tone was just played.", font=("Comic Sans MS", 12), bg='black', fg='white')
                self.i2sinstructions.pack(padx=20, pady=20)
                self.i2svar = tk.IntVar()
                self.i2scheckbox = tk.Checkbutton(self.i2sFrame, text="Did you hear the tone?", variable = self.i2svar, font=("Comic Sans MS", 12),bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.i2scheckbox.pack(padx=10, pady=10)
                self.warning = tk.Label(self.i2sFrame, text="Make sure to click the checkbox if you hear it",
                                        font=("Comic Sans MS", 10), bg='black', fg="red")
                self.warning.pack()
                self.ibutton = tk.Button(self.i2sFrame, text = "Back",command=self.i2s_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.ibutton.pack(padx=20, pady=20)

                self.i2silabel = tk.Label(self.i2sFrame2, text = "I2S Input Test", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.i2silabel.pack(padx=20, pady=20)
                self.i2spinout = tk.Label(self.i2sFrame2, text="Mic BCLK to Pin 12, LRCL to Pin 35, DOUT to Pin 38, 3V to Pin 1, GND and SEL to Pin 39", font=("Comic Sans MS", 10), bg='black', fg='white')
                self.i2spinout.pack()
                self.i2sinstructions = tk.Label(self.i2sFrame2, text =  "Make a sound and watch the graph", font=("Comic Sans MS", 12), bg='black', fg='white')
                self.i2sinstructions.pack(padx=20, pady=20)
                self.i2svar2 = tk.IntVar()
                self.i2scheckbox = tk.Checkbutton(self.i2sFrame2, text="Do the changes in the graph correspond to the sounds you make?", variable = self.i2svar2, font=("Comic Sans MS", 12),bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.i2scheckbox.pack(padx=10, pady=10)
                self.warning = tk.Label(self.i2sFrame2, text="Make sure to click the checkbox if you hear it",
                                        font=("Comic Sans MS", 10), bg='black', fg="red")
                self.warning.pack()
                self.audio_queue = queue.Queue()
                self.audio_levels = deque([0]*100, maxlen=100)
                self.i2s_stop_event = Event()

                self.figure=Figure(figsize=(6,4), dpi=100)
                self.figure.set_facecolor('black')
                self.audio_plot = self.figure.add_subplot(111)
                self.audio_plot.set_facecolor('black')
                self.audio_line, = self.audio_plot.plot(
                        range(100),
                        list(self.audio_levels),
                        color="white"
                )

                self.audio_plot.set_title("I2S Microphone Level", color="white")
                self.audio_plot.set_xlabel("Recent samples", color="white")
                self.audio_plot.set_ylabel("Amplitude", color="white")
                self.audio_plot.tick_params(colors="white")
                self.audio_plot.set_ylim(0, 1)

                self.audio_canvas = FigureCanvasTkAgg(
                        self.figure,
                        master=self.i2sFrame2
                )
                self.audio_canvas.get_tk_widget().pack()
                self.ibutton = tk.Button(self.i2sFrame2, text = "Back",command=self.i2s_button2, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.ibutton.pack(padx=0, pady=0)

                #widgets for USB frame
                self.usbimage = tk.PhotoImage(file="usbdiagram.png").subsample(3,3)
                self.usblabel = tk.Label(self.usbFrame, text = "USB Port Test", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.usblabel.pack(padx=0, pady=0)
                self.usbinstructions = tk.Label(self.usbFrame, text = "Observe the status of each port on the Jetson.", font=("Comic Sans MS", 12), bg = 'black', fg = 'white')
                self.usbinstructions.pack(padx = 20, pady = 10)
                self.usbbegintest = tk.Button(self.usbFrame, text = "Begin Testing Ports", command=self.usb_test, bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.usbbegintest.pack(padx=20, pady=10)
                self.gridFrame = tk.Frame(self.usbFrame, bg='black')
                self.gridFrame.pack()
                self.image = tk.Label(self.gridFrame, image = self.usbimage)
                self.image.grid(row=0, column=0, rowspan=4, padx=20)

                self.usbindicator1 = tk.Canvas(self.gridFrame, width=30, height=30)
                self.usbindicator1.grid(row=0, column=1)
                self.usbled1 = self.usbindicator1.create_oval(5, 5, 25, 25, fill="red", outline="black")
                self.usblabel1 = tk.Label(self.gridFrame, text = "USB PORT 1", font=("Comic Sans MS", 11), bg='black', fg='white')
                self.usblabel1.grid(row=0, column=2)
                self.usbindicator2 = tk.Canvas(self.gridFrame, width=30, height=30)
                self.usbindicator2.grid(row=1, column=1)
                self.usbled2 = self.usbindicator2.create_oval(5, 5, 25, 25, fill="red", outline="black")
                self.usblabel2 = tk.Label(self.gridFrame, text = "USB PORT 2", font = ("Comic Sans MS", 11), bg='black', fg='white')
                self.usblabel2.grid(row=1, column=2)

                self.usbindicator3 = tk.Canvas(self.gridFrame, width=30, height=30)
                self.usbindicator3.grid(row=2, column=1)
                self.usbled3 = self.usbindicator3.create_oval(5, 5, 25, 25, fill="red", outline="black")
                self.usblabel3 = tk.Label(self.gridFrame, text = "USB PORT 3", font = ("Comic Sans MS", 11), bg='black', fg='white')
                self.usblabel3.grid(row=2, column=2)

                self.usbindicator4 = tk.Canvas(self.gridFrame, width=30, height=30)
                self.usbindicator4.grid(row=3, column=1)
                self.usbled4 = self.usbindicator4.create_oval(5, 5, 25, 25, fill="red", outline="black")
                self.usblabel4 = tk.Label(self.gridFrame, text = "USB PORT 4", font = ("Comic Sans MS", 11), bg='black', fg='white')
                self.usblabel4.grid(row=3, column=2)

                self.usbutton = tk.Button(self.usbFrame, text = "Back",command=self.usb_button, bg='green', fg='white', border=0, relief='flat', highlightthickness=0)
                self.usbutton.pack(padx=20, pady=20)

                #widgets for WiFi frame
                self.wifilabel = tk.Label(self.wifiFrame, text = "WiFi Test", font=("Comic Sans MS", 18), bg='black', fg='white')
                self.wifilabel.pack(padx=20, pady=20)
                self.wifiinstructions = tk.Label(self.wifiFrame, text = "Click the button to browse the Internet via WiFi.", font=("Comic Sans MS", 12), bg = 'black', fg = 'white')
                self.wifiinstructions.pack(padx = 20, pady = 20)
                self.wifibegintest = tk.Button(self.wifiFrame, text = "Open the Internet", command=self.wifi_test, bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.wifibegintest.pack(padx=20, pady=20)
                self.wvar = tk.IntVar()
                self.wifiprompt = tk.Checkbutton(self.wifiFrame, text="Did YouTube successfully load?", variable=self.wvar, bg ='black', fg='white', selectcolor="black",highlightthickness=0)
                self.wifiprompt.pack(padx=20, pady=20)
                self.wifibbutton = tk.Button(self.wifiFrame, text = "Back", command=self.wifi_button, bg='grey', fg='white', border=0, relief='flat', highlightthickness=0)
                self.wifibbutton.pack(padx=20, pady=20)
                #Load main screen and start the loop
                self.logFrame.place(x=400, y=100)
                self.buttonFrame.place(x=100, y=100)
                self.root.mainloop()


        def add_log(self,message):
                now = datetime.now()
                self.logwarning.pack_forget()
                self.logbox.insert("end", now.strftime("%Y-%m-%d %H:%M:%S") +" | "+message + "\n")
                self.logbox.see("end")

        #function for gpio button
        def gpio_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.gpioFrame.pack()

                self.stop_gpio_test.clear()
                self.gpio_thread = threading.Thread(
                        target=gpiotest_1.gpiotest,
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
                self.add_log("PWM Test Starting...")
                

        def pwm_test_32(self):
                self.stop_pwm_test2.set()
                if hasattr(self, "pwm_thread2") and self.pwm_thread2.is_alive():
                        self.pwm_thread2.join()
                self.pwm_pin = 32
                self.stop_pwm_test.clear()
                self.pwm_thread = threading.Thread(
                target=pwmtest_1.pwmtest,
                args=(self.stop_pwm_test, self.pwm_pin),
                daemon=True
                )
                self.pwm_thread.start()
                        

        def pwm_test_33(self):
                self.stop_pwm_test.set()
                if hasattr(self, "pwm_thread") and self.pwm_thread.is_alive():
                        self.pwm_thread.join()
                self.pwm_pin = 33
                self.stop_pwm_test2.clear()
                self.pwm_thread2 = threading.Thread(
                target=pwmtest_1.pwmtest,
                args=(self.stop_pwm_test2, self.pwm_pin),
                daemon=True
                )
                
                self.pwm_thread2.start()
                        

                
                

        def uart_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.add_log("UART Test Starting...")
                self.uartFrame.pack()

        def uart_send(self):
                try:
                        message = self.uarttextbox.get('1.0','end-1c')
                        received = uarttest_1.uarttest(message)
                        self.received.insert('1.0', received)
                        if message == received:
                                self.add_log("UART Test: PASS")
                                self.uartbutton.configure(background='green')
                        else:
                                self.add_log("UART Test: FAIL")
                                self.uartbutton.configure(background='red')

                except (PermissionError, serial.serialutil.SerialException) as e:
                        self.add_log("UART Test: FAIL")
                        self.add_log(f"{e} errors occured, please restart the software with Admin permissions")
                        self.uartbutton.configure(background='red')

        def cam_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.camFrame.pack()

        def cam1_test(self):
                self.stop_cam_test.clear()
                self.cam_thread = threading.Thread(
                        target=cam.camtest,
                        args=(self.stop_cam_test,),
                        daemon=True
                )
                self.add_log("CAM 1 Test Starting...")
                self.cam_thread.start()
                time.sleep(3)
                if cam.status:
                        self.add_log("CAM 1 TEST: PASS")
                        self.cam1button.configure(background='green')
                else:
                        self.add_log("CAM 1 TEST: FAIL")
                        self.cam1button.configure(background='red')

        def cam2_test(self):
                self.stop_cam_test.clear()
                self.cam_thread = threading.Thread(
                        target=cam1.camtest,
                        args=(self.stop_cam_test,),
                        daemon=True
                )
                self.add_log("CAM 2 Test Starting...")
                self.cam_thread.start()
                time.sleep(3)
                if cam1.status:
                        self.add_log("CAM 2 TEST: PASS")
                        self.cam2button.configure(background='green')
                else:
                        self.add_log("CAM 2 TEST: FAIL")
                        self.cam2button.configure(background='red')

                

        def i2s_test_output(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.i2sFrame.pack()
                self.add_log("I2S Output Test Starting...")
                password="group7\n"
                subprocess.run(["sudo","busybox", "devmem", "0x6000d204", "32", "0"], input=password, universal_newlines=True,)
                subprocess.run(["sudo", "./I2S_test_output.sh"], input=password, universal_newlines=True,)

        def i2s_test_input(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.i2sFrame2.pack()
                self.add_log("I2S Input Test Starting...")
                self.i2s_stop_event.clear()
                self.i2s_thread = threading.Thread(
                        target=i2s_input.monitor_i2s,
                        args=(self.i2s_stop_event, self.audio_queue),
                        daemon=True
                )

                self.i2s_thread.start()
                self.update_i2s_graph()

        def update_i2s_graph(self):
                while not self.audio_queue.empty():
                        peak, rms, freq = self.audio_queue.get_nowait()
                        self.audio_levels.append(peak)

                values = list(self.audio_levels)
                self.audio_line.set_ydata(values)

                highest = max(values)

                if highest > 0:
                        self.audio_plot.set_ylim(0, max(5000, highest * 1.2))

                self.audio_canvas.draw_idle()

                if not self.i2s_stop_event.is_set():
                        self.root.after(100, self.update_i2s_graph)

                
        #functions for USB button
        
        def init_usb_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.usbFrame.pack()
                self.add_log("USB TEST STARTING...")

        def usb_test(self):
                global port1, port2, port3, port4
                port1 = False
                port2 = False
                port3 = False
                port4 = False

                usb_root = Path("/sys/bus/usb/devices")
                

                for device in usb_root.iterdir():
                        name = device.name
                        if ":" in name:
                                continue
                        if name == "1-2.1":
                                port1 = True
                        elif name == "1-2.3":
                                port2 = True
                        elif name == "1-2.2":
                                port3 = True
                        elif name == "1-2.4":
                                port4 = True

                if port1:
                        self.usbindicator1.itemconfig(self.usbled1, fill="green")
                else:
                        self.usbindicator1.itemconfig(self.usbled1, fill="red")

                if port2:
                        self.usbindicator2.itemconfig(self.usbled2, fill="green")
                else:
                        self.usbindicator2.itemconfig(self.usbled2, fill="red")

                if port3:
                        self.usbindicator3.itemconfig(self.usbled3, fill="green")
                else:
                        self.usbindicator3.itemconfig(self.usbled3, fill="red")
                
                if port4:
                        self.usbindicator4.itemconfig(self.usbled4, fill="green")
                else:
                        self.usbindicator4.itemconfig(self.usbled4, fill="red")

                self.root.after(500, self.usb_test)

        def init_wifi_test(self):
                self.buttonFrame.place_forget()
                self.logFrame.place_forget()
                self.wifiFrame.pack()
                self.add_log("WIFI TEST STARTING...")

        def wifi_test(self):
                webbrowser.open("https://www.youtube.com")

        #function for back button
        def gpio_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.gvar.get() == 1:
                        self.add_log("GPIO Test: PASS")
                        self.gpiobutton.configure(background='green')
                else:
                        self.add_log("GPIO Test: FAIL")
                        self.gpiobutton.configure(background='red')

        def pwm_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.stop_pwm_test2.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.pvar.get() == 1:
                        self.add_log("PWM Test: PASS")
                        self.pwmbutton.configure(background='green')
                else:
                        self.add_log("PWM Test: FAIL")
                        self.pwmbutton.configure(background='red')

        def uart_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)

        def cam_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.stop_cam_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if cam.status:
                        
                        self.cambutton.configure(background='green')
                else:

                        self.cambutton.configure(background='red')

                if cam1.status:

                        self.cambutton.configure(background='green')
                else:
                        
                        self.cambutton.configure(background='red')

        def i2s_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.stop_cam_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.i2svar.get() == 1:
                        self.add_log("I2S Output Test: PASS")
                        self.i2sbutton.configure(background='green')
                else:
                        self.add_log("I2S Output Test: FAIL")
                        self.i2sbutton.configure(background='red')

        def i2s_button2(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.stop_cam_test.set()
                self.i2s_stop_event.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.i2sFrame2.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.i2svar2.get() == 1:
                        self.add_log("I2S Input Test: PASS")
                        self.i2sbutton2.configure(background='green')
                else:
                        self.add_log("I2S Input Test: FAIL")
                        self.i2sbutton2.configure(background='red')

        def usb_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.usbFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if port1:
                        self.add_log("USB PORT1 CONNECTED")
                else:
                        self.add_log("USB PORT1 DISCONNECTED")

                if port2:
                        self.add_log("USB PORT2 CONNECTED")
                else:
                        self.add_log("USB PORT2 DISCONNECTED")

                if port3:
                        self.add_log("USB PORT3 CONNECTED")
                else:
                        self.add_log("USB PORT3 DISCONNECTED")
                
                if port4:
                        self.add_log("USB PORT4 CONNECTED")
                else:
                        self.add_log("USB PORT4 DISCONNECTED")
                self.usbbutton.configure(bg='Green')

        def wifi_button(self):
                self.stop_gpio_test.set()
                self.stop_pwm_test.set()
                self.pwmFrame.pack_forget()
                self.gpioFrame.pack_forget()
                self.camFrame.pack_forget()
                self.i2sFrame.pack_forget()
                self.usbFrame.pack_forget()
                self.uarttextbox.delete('1.0','end')
                self.received.delete('1.0','end')
                self.uartFrame.pack_forget()
                self.wifiFrame.pack_forget()
                self.buttonFrame.place(x=100, y=100)
                self.logFrame.place(x=400, y=100)
                if self.wvar.get() == 1:
                        self.add_log("WIFI Test: PASS")
                        self.wifibutton.configure(background='green')
                else:
                        self.add_log("WIFI Test: FAIL")
                        self.wifibutton.configure(background='red')

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