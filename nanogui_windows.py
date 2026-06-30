import tkinter as tk
from tkinter import messagebox
import threading
import paramiko

JETSON_IP       = "192.168.137.55"
JETSON_USERNAME = "group72"
JETSON_PASSWORD = "group7"
REMOTE_TEST_DIR = "/home/group72/Documents/projectlab"


class NanoGUI:
    def __init__(self):
        self.client = None

        self.root = tk.Tk()
        self.root.title("Jetson Nano Test Software (Windows / SSH)")
        self.root.geometry("1280x720")

        self.label = tk.Label(self.root, text="Jetson Nano Testbench",
                              font=("Comic Sans MS", 28))
        self.label.pack(pady=20)

        
        self.conn_label = tk.Label(self.root, text="Connecting to Jetson...",
                                   font=("Comic Sans MS", 12), fg="orange")
        self.conn_label.pack()

        
        self.buttonFrame = tk.Frame(self.root)
        self.gpioFrame   = tk.Frame(self.root)
        self.pwmFrame    = tk.Frame(self.root)
        self.uartFrame   = tk.Frame(self.root)

        
        self.buttonFrame.columnconfigure(0, weight=1)
        self.buttonFrame.columnconfigure(1, weight=1)
        self.buttonFrame.columnconfigure(2, weight=1)

        self.gpiobutton = tk.Button(self.buttonFrame, text="Test GPIO",
                                    command=self.gpio_test, width=20, height=5)
        self.pwmbutton  = tk.Button(self.buttonFrame, text="Test PWM",
                                    command=self.pwm_test,  width=20, height=5)
        self.spibutton  = tk.Button(self.buttonFrame, text="Test SPI",
                                    width=20, height=5, state=tk.DISABLED)
        self.uartbutton = tk.Button(self.buttonFrame, text="Test UART",
                                    command=self.uart_test, width=20, height=5)
        self.i2cbutton  = tk.Button(self.buttonFrame, text="Test I2C",
                                    width=20, height=5, state=tk.DISABLED)
        self.i2sbutton  = tk.Button(self.buttonFrame, text="Test I2S",
                                    width=20, height=5, state=tk.DISABLED)
        self.cambutton  = tk.Button(self.buttonFrame, text="Test CAMERA",
                                    width=20, height=5, state=tk.DISABLED)

        self.gpiobutton.grid(row=0, column=0, padx=5, pady=5)
        self.pwmbutton.grid( row=0, column=1, padx=5, pady=5)
        self.spibutton.grid( row=0, column=2, padx=5, pady=5)
        self.uartbutton.grid(row=1, column=0, padx=5, pady=5)
        self.i2cbutton.grid( row=1, column=1, padx=5, pady=5)
        self.i2sbutton.grid( row=1, column=2, padx=5, pady=5)
        self.cambutton.grid( row=2, column=0, padx=5, pady=5)

        
        self.test_buttons = [self.gpiobutton, self.pwmbutton, self.uartbutton]

        
        self.statusframe = tk.Frame(self.root)
        self.statusframe.columnconfigure(0, weight=1)
        self.statusframe.columnconfigure(1, weight=1)

        tk.Label(self.statusframe, text="Status",
                 font=("Comic Sans MS", 20)).grid(row=0, column=1, padx=20, pady=10)

        tk.Label(self.statusframe, text="GPIO Status:",
                 font=("Comic Sans MS", 16)).grid(row=1, column=0, padx=20, pady=10)
        self.gpiostatus = tk.Label(self.statusframe, text="N/A",
                                   font=("Comic Sans MS", 16))
        self.gpiostatus.grid(row=1, column=1, padx=20, pady=10)

        tk.Label(self.statusframe, text="PWM Status:",
                 font=("Comic Sans MS", 16)).grid(row=2, column=0, padx=20, pady=10)
        self.pwmstatus = tk.Label(self.statusframe, text="N/A",
                                  font=("Comic Sans MS", 16))
        self.pwmstatus.grid(row=2, column=1, padx=20, pady=10)

        tk.Label(self.statusframe, text="UART Status:",
                 font=("Comic Sans MS", 16)).grid(row=3, column=0, padx=20, pady=10)
        self.uartstatus = tk.Label(self.statusframe, text="N/A",
                                   font=("Comic Sans MS", 16))
        self.uartstatus.grid(row=3, column=1, padx=20, pady=10)


        tk.Label(self.gpioFrame, text="LEDs should blink for 12 seconds...",
                 font=("Comic Sans MS", 18)).pack(padx=20, pady=20)
        self.gpio_running_label = tk.Label(self.gpioFrame, text="",
                                           font=("Comic Sans MS", 14))
        self.gpio_running_label.pack(padx=10, pady=10)
        tk.Button(self.gpioFrame, text="Back",
                  command=self.back_button).pack()


        tk.Label(self.pwmFrame, text="The servo should sweep up and down...",
                 font=("Comic Sans MS", 18)).pack(padx=20, pady=20)
        self.pwm_running_label = tk.Label(self.pwmFrame, text="",
                                          font=("Comic Sans MS", 14))
        self.pwm_running_label.pack(padx=10, pady=10)
        tk.Button(self.pwmFrame, text="Back",
                  command=self.back_button).pack()


        tk.Label(self.uartFrame, text="UART Echo",
                 font=("Comic Sans MS", 18)).pack(padx=20, pady=20)
        self.uarttextbox = tk.Text(self.uartFrame, width=30, height=10,
                                   font=("Comic Sans MS", 12))
        self.uarttextbox.pack()
        self.uart_send_btn = tk.Button(self.uartFrame, text="Send",
                                       command=self.uart_send)
        self.uart_send_btn.pack(padx=20, pady=20)
        tk.Button(self.uartFrame, text="Back",
                  command=self.back_button).pack(padx=20, pady=5)
        self.received = tk.Text(self.uartFrame, width=30, height=10,
                                font=("Comic Sans MS", 12))
        self.received.pack(pady=10)

   
        self.buttonFrame.place(x=100, y=100)
        self.statusframe.place(x=750, y=100)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

 
        self.root.after(100, self._connect_ssh_async)
        self.root.mainloop()

 
    def _connect_ssh_async(self):
        """Opens the SSH connection in a background thread so the GUI stays
        responsive during the connect attempt."""
        threading.Thread(target=self._ssh_connect_worker, daemon=True).start()

    def _ssh_connect_worker(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=JETSON_IP,
                username=JETSON_USERNAME,
                password=JETSON_PASSWORD,
                timeout=10,
            )
            self.client = client
            self.root.after(0, self._on_ssh_connected)
        except paramiko.AuthenticationException:
            self.root.after(0, self._on_ssh_error,
                            "Authentication failed.\nCheck JETSON_USERNAME and JETSON_PASSWORD in the script.")
        except Exception as e:
            self.root.after(0, self._on_ssh_error,
                            f"Could not connect to Jetson at {JETSON_IP}.\n\n{e}\n\n"
                            "Check that:\n"
                            "  - The Jetson is powered on\n"
                            "  - Both devices are on the same network\n"
                            "  - SSH is running on the Jetson")

    def _on_ssh_connected(self):
        self.conn_label.config(
            text=f"Connected to {JETSON_IP} as {JETSON_USERNAME}", fg="green")
        for btn in self.test_buttons:
            btn.config(state=tk.NORMAL)

    def _on_ssh_error(self, message):
        self.conn_label.config(text="SSH connection failed — see popup", fg="red")
        messagebox.showerror("SSH Connection Error", message)

    def run_remote_test(self, script_name, extra_args=""):
        """Runs a headless script on the Jetson and returns (passed, output)."""
        cmd = f"cd {REMOTE_TEST_DIR} && python3 {script_name}"
        if extra_args:
            cmd += f" {extra_args}"
        stdin, stdout, stderr = self.client.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        full = out
        if err:
            full = (out + "\n[stderr]: " + err).strip()
        passed = "PASS" in out
        return passed, full

    def _set_test_buttons(self, state):
        """Enable or disable all active test buttons at once."""
        for btn in self.test_buttons:
            btn.config(state=state)

    def on_close(self):
        if self.client:
            self.client.close()
        self.root.destroy()


    def gpio_test(self):
        self.buttonFrame.place_forget()
        self.statusframe.place_forget()
        self.gpio_running_label.config(text="Running on Jetson...")
        self.gpioFrame.pack()
        self._set_test_buttons(tk.DISABLED)
        threading.Thread(target=self._gpio_worker, daemon=True).start()

    def _gpio_worker(self):
        passed, output = self.run_remote_test("gpiotest.py")
        self.root.after(0, self._gpio_done, passed, output)

    def _gpio_done(self, passed, output):
        self.gpio_running_label.config(text=output)
        self.gpiostatus.config(
            text="PASS" if passed else "FAIL",
            fg="green" if passed else "red")
        self._set_test_buttons(tk.NORMAL)


    def pwm_test(self):
        self.buttonFrame.place_forget()
        self.statusframe.place_forget()
        self.pwm_running_label.config(text="Running on Jetson...")
        self.pwmFrame.pack()
        self._set_test_buttons(tk.DISABLED)
        threading.Thread(target=self._pwm_worker, daemon=True).start()

    def _pwm_worker(self):
        passed, output = self.run_remote_test("pwmtest.py")
        self.root.after(0, self._pwm_done, passed, output)

    def _pwm_done(self, passed, output):
        self.pwm_running_label.config(text=output)
        self.pwmstatus.config(
            text="PASS" if passed else "FAIL",
            fg="green" if passed else "red")
        self._set_test_buttons(tk.NORMAL)


    def uart_test(self):
        self.buttonFrame.place_forget()
        self.statusframe.place_forget()
        self.uartFrame.pack()

    def uart_send(self):
        message = self.uarttextbox.get('1.0', 'end-1c').strip()
        if not message:
            return
        self.uart_send_btn.config(state=tk.DISABLED)
        self.received.delete('1.0', 'end')
        self.received.insert('1.0', "Sending...\n")
        threading.Thread(target=self._uart_worker, args=(message,),
                         daemon=True).start()

    def _uart_worker(self, message):
        passed, output = self.run_remote_test(
            "uarttest.py", extra_args=f'"{message}"')
        self.root.after(0, self._uart_done, passed, output)

    def _uart_done(self, passed, output):
        self.received.delete('1.0', 'end')
        self.received.insert('1.0', output)
        self.uartstatus.config(
            text="PASS" if passed else "FAIL",
            fg="green" if passed else "red")
        self.uart_send_btn.config(state=tk.NORMAL)


    def back_button(self):

        self.gpioFrame.pack_forget()
        self.pwmFrame.pack_forget()
        self.uartFrame.pack_forget()
        self.gpio_running_label.config(text="")
        self.pwm_running_label.config(text="")
        self.uarttextbox.delete('1.0', 'end')
        self.received.delete('1.0', 'end')
        self.statusframe.place(x=750, y=100)
        self.buttonFrame.place(x=100, y=100)


if __name__ == "__main__":
    NanoGUI()
