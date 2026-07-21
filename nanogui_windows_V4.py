import tkinter as tk
from tkinter import messagebox
import threading
import shlex
from datetime import datetime
import paramiko


JETSON_IP       = "192.168.137.55"
JETSON_USERNAME = "group72"
JETSON_PASSWORD = "group7"
REMOTE_TEST_DIR = "/home/group72/Documents/projectlab"

GPIO_PASS_LINE = "GPIO TEST: PASS"
PWM_PASS_LINE  = "PWM TEST: PASS"
UART_PASS_LINE = "UART LOOPBACK: PASS"
I2S_DONE_LINE  = "I2S PLAYBACK: COMPLETE"

UART_UNLOCK_CMD = ("systemctl stop nvgetty 2>/dev/null; "
                   "chmod 666 /dev/ttyTHS1")

PWM_REGISTER_CMDS = (
    "busybox devmem 0x700031fc 32 0x45; "
    "busybox devmem 0x6000d504 32 0x2; "
    "busybox devmem 0x70003248 32 0x46; "
    "busybox devmem 0x6000d100 32 0x00"
)

HARDWARE_SETUP_CMD = PWM_REGISTER_CMDS + "; " + UART_UNLOCK_CMD

BG        = "#f4f6f8"
PANEL_BG  = "#ffffff"
BORDER    = "#d8dee6"
INK       = "#1f2933"
INK_SOFT  = "#6b7684"
ACCENT    = "#2563cc"
ACCENT_HI = "#1d4ed8"

STATE_IDLE    = "#e3e8ee"
STATE_IDLE_FG = "#6b7684"
STATE_RUN     = "#f0a020"
STATE_PASS    = "#1a9e56"
STATE_FAIL    = "#d23c3c"
WHITE         = "#ffffff"

TITLE_FONT   = ("Segoe UI Semibold", 22)
SUB_FONT     = ("Segoe UI", 11)
HEADER_FONT  = ("Segoe UI Semibold", 15)
BODY_FONT    = ("Segoe UI", 13)
STATUS_FONT  = ("Segoe UI", 12)
PIN_FONT     = ("Segoe UI Semibold", 12)
SMALL_FONT   = ("Segoe UI", 9)
TEXT_FONT    = ("Consolas", 11)
BTN_FONT     = ("Segoe UI Semibold", 13)
PILL_FONT    = ("Segoe UI Semibold", 10)
PILL_SUB     = ("Segoe UI", 8)


class NanoGUI:
    def __init__(self):
        self.client = None
        self.gpio_auto = None
        self.pwm_auto = None
        self.i2s_auto = None
        self.gpio_pin_labels = []
        self.uart_prepared = True

        self.status = {"GPIO": "idle", "PWM": "idle", "UART": "idle",
                       "I2S": "idle", "SPI": "idle", "I2C": "idle",
                       "CAMERA": "idle"}
        self.pills = {}

        self.root = tk.Tk()
        self.root.title("Jetson Nano Test Bench")
        self.root.geometry("1280x720")
        self.root.configure(background=BG)

        self._build_header()
        self._build_dashboard()
        self._build_body()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._connect_ssh_async)
        self.root.mainloop()


    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=30, pady=(20, 8))
        tk.Label(header, text="Jetson Nano Test Bench", font=TITLE_FONT,
                 bg=BG, fg=INK).pack(side="left")
        self.conn_label = tk.Label(header, text="Connecting to Jetson...",
                                   font=SUB_FONT, bg=BG, fg=STATE_RUN)
        self.conn_label.pack(side="right", pady=(8, 0))

    def _build_dashboard(self):
        wrap = tk.Frame(self.root, bg=BORDER)
        wrap.pack(fill="x", padx=30, pady=(0, 4))
        bar = tk.Frame(wrap, bg=PANEL_BG)
        bar.pack(fill="x", padx=1, pady=1)

        inner = tk.Frame(bar, bg=PANEL_BG)
        inner.pack(padx=16, pady=12)

        for name in ("GPIO", "PWM", "UART", "I2S", "SPI", "I2C", "CAMERA"):
            self.pills[name] = self._make_pill(inner, name)

        self.summary_label = tk.Label(bar, text="0 / 7 passed",
                                      font=HEADER_FONT, bg=PANEL_BG, fg=INK_SOFT)
        self.summary_label.pack(side="right", padx=20)

    def _make_pill(self, parent, name):
        cell = tk.Frame(parent, bg=STATE_IDLE, highlightthickness=0)
        cell.pack(side="left", padx=6)
        dot = tk.Label(cell, text="\u25cf", font=("Segoe UI", 11),
                       bg=STATE_IDLE, fg=STATE_IDLE_FG)
        dot.pack(side="left", padx=(10, 4), pady=6)
        name_lbl = tk.Label(cell, text=name, font=PILL_FONT,
                            bg=STATE_IDLE, fg=STATE_IDLE_FG)
        name_lbl.pack(side="left", pady=6)
        state_lbl = tk.Label(cell, text="Not run", font=PILL_SUB,
                            bg=STATE_IDLE, fg=STATE_IDLE_FG)
        state_lbl.pack(side="left", padx=(6, 12), pady=6)
        return {"cell": cell, "dot": dot, "name": name_lbl, "state": state_lbl}

    def _set_pill(self, name, state):
        colors = {
            "idle": (STATE_IDLE, STATE_IDLE_FG, "Not run"),
            "running": (STATE_RUN, WHITE, "Running"),
            "pass": (STATE_PASS, WHITE, "Pass"),
            "fail": (STATE_FAIL, WHITE, "Fail"),
        }
        bg, fg, text = colors[state]
        p = self.pills[name]
        for key in ("cell", "dot", "name", "state"):
            p[key].config(bg=bg)
        p["dot"].config(fg=fg)
        p["name"].config(fg=fg)
        p["state"].config(fg=fg, text=text)
        self.status[name] = state
        self._update_summary()

    def _update_summary(self):
        passed = sum(1 for s in self.status.values() if s == "pass")
        self.summary_label.config(text=f"{passed} / 7 passed")


    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=30, pady=16)

        self.leftPanel = tk.Frame(body, bg=BG)
        self.leftPanel.pack(side="left", fill="y", padx=(0, 16))

        tk.Label(self.leftPanel, text="INTERFACES", font=SMALL_FONT,
                 bg=BG, fg=INK_SOFT).pack(anchor="w", pady=(0, 8))

        self.gpiobutton = self._test_button("GPIO", "Test GPIO", self.gpio_test)
        self.pwmbutton  = self._test_button("PWM", "Test PWM", self.pwm_test)
        self.uartbutton = self._test_button("UART", "Test UART", self.uart_test)
        self.i2sbutton  = self._test_button("I2S", "Test I2S", self.i2s_test)
        self.spibutton  = self._test_button("SPI", "Test SPI", None)
        self.i2cbutton  = self._test_button("I2C", "Test I2C", None)
        self.cambutton  = self._test_button("CAMERA", "Test CAMERA", None)

        self.buttons = {
            "GPIO": self.gpiobutton, "PWM": self.pwmbutton,
            "UART": self.uartbutton, "I2S": self.i2sbutton,
            "SPI": self.spibutton, "I2C": self.i2cbutton,
            "CAMERA": self.cambutton,
        }
        self.test_buttons = [self.gpiobutton, self.pwmbutton,
                             self.uartbutton, self.i2sbutton]

        self.rightWrap = tk.Frame(body, bg=BORDER)
        self.rightWrap.pack(side="left", fill="both", expand=True)
        self.rightPanel = tk.Frame(self.rightWrap, bg=PANEL_BG)
        self.rightPanel.pack(fill="both", expand=True, padx=1, pady=1)

        self.logFrame  = tk.Frame(self.rightPanel, bg=PANEL_BG)
        self.gpioFrame = tk.Frame(self.rightPanel, bg=PANEL_BG)
        self.pwmFrame  = tk.Frame(self.rightPanel, bg=PANEL_BG)
        self.uartFrame = tk.Frame(self.rightPanel, bg=PANEL_BG)
        self.i2sFrame  = tk.Frame(self.rightPanel, bg=PANEL_BG)

        self._build_log_frame()
        self._build_gpio_frame()
        self._build_pwm_frame()
        self._build_uart_frame()
        self._build_i2s_frame()

        self._show_frame(self.logFrame)


    def _test_button(self, name, text, command):
        wrap = tk.Frame(self.leftPanel, bg=STATE_IDLE, highlightthickness=0)
        wrap.pack(fill="x", pady=4)
        btn = tk.Button(wrap, text=text, font=BTN_FONT, width=18, height=2,
                        bg=STATE_IDLE, fg=STATE_IDLE_FG, border=0,
                        relief="flat", activebackground=STATE_IDLE,
                        activeforeground=INK, disabledforeground=STATE_IDLE_FG,
                        cursor="hand2", state=tk.DISABLED, command=command)
        btn.pack(fill="x", padx=2, pady=2)
        btn._wrap = wrap
        return btn

    def _set_button_state(self, name, state):
        btn = self.buttons[name]
        colors = {
            "idle":    (STATE_IDLE, STATE_IDLE_FG),
            "ready":   (ACCENT, WHITE),
            "running": (STATE_RUN, WHITE),
            "pass":    (STATE_PASS, WHITE),
            "fail":    (STATE_FAIL, WHITE),
        }
        bg, fg = colors[state]
        btn.config(bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                   disabledforeground=fg)
        btn._wrap.config(bg=bg)

    def _show_frame(self, frame):
        for f in (self.logFrame, self.gpioFrame, self.pwmFrame,
                  self.uartFrame, self.i2sFrame):
            f.pack_forget()
        frame.pack(fill="both", expand=True)


    def _build_log_frame(self):
        f = self.logFrame
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(head, text="Test Log", font=HEADER_FONT,
                 bg=PANEL_BG, fg=INK).pack(side="left")
        self.logdownload = tk.Button(head, text="Download Log",
                                     font=SMALL_FONT, bg=BG, fg=INK,
                                     border=0, relief="flat", cursor="hand2",
                                     activebackground=BORDER,
                                     command=self.getlogs)
        self.logdownload.pack(side="right")

        box_wrap = tk.Frame(f, bg=BORDER)
        box_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.logbox = tk.Text(box_wrap, border=0, relief="flat",
                              highlightthickness=0, bg=PANEL_BG, fg=INK,
                              font=TEXT_FONT, wrap="word", padx=12, pady=12)
        self.logbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        scroll = tk.Scrollbar(box_wrap, command=self.logbox.yview)
        scroll.pack(side="right", fill="y")
        self.logbox.config(yscrollcommand=scroll.set)

        self.logbox.tag_config("pass", foreground=STATE_PASS)
        self.logbox.tag_config("fail", foreground=STATE_FAIL)
        self.logbox.tag_config("info", foreground=INK_SOFT)
        self.logbox.tag_config("time", foreground=INK_SOFT)

        self.logwarning = tk.Label(
            f, text="Nothing logged yet - run a test and it will show up here.",
            font=SMALL_FONT, bg=PANEL_BG, fg=INK_SOFT)

    def _build_gpio_frame(self):
        f = self.gpioFrame
        tk.Label(f, text="GPIO Test", font=HEADER_FONT,
                 bg=PANEL_BG, fg=INK).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="All LEDs should blink ON and OFF together for a few seconds.",
                 font=BODY_FONT, bg=PANEL_BG, fg=INK_SOFT,
                 wraplength=520, justify="left").pack(anchor="w", padx=24)

        self.gpio_running_label = tk.Label(f, text="", font=STATUS_FONT,
                                           bg=PANEL_BG, fg=INK_SOFT)
        self.gpio_running_label.pack(anchor="w", padx=24, pady=(16, 8))

        self.gpio_pin_frame = tk.Frame(f, bg=PANEL_BG)
        self.gpio_pin_frame.pack(anchor="w", padx=24, pady=4)

        self.gvar = tk.IntVar()
        self.gpiocheckbox = tk.Checkbutton(
            f, text="Yes - all LEDs blinked together", variable=self.gvar,
            font=BODY_FONT, bg=PANEL_BG, fg=INK, selectcolor=WHITE,
            activebackground=PANEL_BG, activeforeground=INK,
            highlightthickness=0)
        self.gpiocheckbox.pack(anchor="w", padx=24, pady=(16, 4))
        tk.Label(f, text="Confirm the LEDs before going back to record a PASS.",
                 font=SMALL_FONT, bg=PANEL_BG, fg=INK_SOFT).pack(anchor="w", padx=24)

        self._accent_button(f, "Back to Tests", self.gpio_back).pack(
            anchor="w", padx=24, pady=20)

    def _build_pwm_frame(self):
        f = self.pwmFrame
        tk.Label(f, text="PWM Test", font=HEADER_FONT,
                 bg=PANEL_BG, fg=INK).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="The PWM output should ramp up and down - an LED fades "
                         "bright and dim, or a servo sweeps.",
                 font=BODY_FONT, bg=PANEL_BG, fg=INK_SOFT,
                 wraplength=520, justify="left").pack(anchor="w", padx=24)

        self.pwm_running_label = tk.Label(f, text="", font=STATUS_FONT,
                                          bg=PANEL_BG, fg=INK_SOFT)
        self.pwm_running_label.pack(anchor="w", padx=24, pady=(16, 8))

        self.pvar = tk.IntVar()
        self.pwmcheckbox = tk.Checkbutton(
            f, text="Yes - the LED faded (or the servo swept)", variable=self.pvar,
            font=BODY_FONT, bg=PANEL_BG, fg=INK, selectcolor=WHITE,
            activebackground=PANEL_BG, activeforeground=INK,
            highlightthickness=0)
        self.pwmcheckbox.pack(anchor="w", padx=24, pady=(16, 4))
        tk.Label(f, text="Confirm the fade before going back to record a PASS.",
                 font=SMALL_FONT, bg=PANEL_BG, fg=INK_SOFT).pack(anchor="w", padx=24)

        self._accent_button(f, "Back to Tests", self.pwm_back).pack(
            anchor="w", padx=24, pady=20)

    def _build_i2s_frame(self):
        f = self.i2sFrame
        tk.Label(f, text="I2S Audio Output Test", font=HEADER_FONT,
                 bg=PANEL_BG, fg=INK).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="The Jetson plays a 440 Hz tone out through the PCM5102A "
                         "DAC. Plug earbuds or a speaker into the DAC's 3.5 mm "
                         "jack and listen.",
                 font=BODY_FONT, bg=PANEL_BG, fg=INK_SOFT,
                 wraplength=520, justify="left").pack(anchor="w", padx=24)

        self.i2s_running_label = tk.Label(f, text="", font=STATUS_FONT,
                                          bg=PANEL_BG, fg=INK_SOFT)
        self.i2s_running_label.pack(anchor="w", padx=24, pady=(16, 8))

        self.ivar = tk.IntVar()
        self.i2scheckbox = tk.Checkbutton(
            f, text="Yes - I heard the tone clearly", variable=self.ivar,
            font=BODY_FONT, bg=PANEL_BG, fg=INK, selectcolor=WHITE,
            activebackground=PANEL_BG, activeforeground=INK,
            highlightthickness=0)
        self.i2scheckbox.pack(anchor="w", padx=24, pady=(16, 4))
        tk.Label(f, text="Confirm the tone before going back to record a PASS. "
                         "If silent, probe BCLK on pin 12 with a scope.",
                 font=SMALL_FONT, bg=PANEL_BG, fg=INK_SOFT,
                 wraplength=520, justify="left").pack(anchor="w", padx=24)

        self._accent_button(f, "Back to Tests", self.i2s_back).pack(
            anchor="w", padx=24, pady=20)

    def _build_uart_frame(self):
        f = self.uartFrame
        tk.Label(f, text="UART Loopback Test", font=HEADER_FONT,
                 bg=PANEL_BG, fg=INK).pack(anchor="w", padx=24, pady=(20, 4))
        tk.Label(f, text="Type a message and send it. With pins 8 and 10 jumpered, "
                         "the same text should come back.",
                 font=BODY_FONT, bg=PANEL_BG, fg=INK_SOFT,
                 wraplength=520, justify="left").pack(anchor="w", padx=24)

        tk.Label(f, text="Message to send", font=SMALL_FONT,
                 bg=PANEL_BG, fg=INK_SOFT).pack(anchor="w", padx=24, pady=(16, 2))
        tw = tk.Frame(f, bg=BORDER)
        tw.pack(anchor="w", padx=24)
        self.uarttextbox = tk.Text(tw, width=44, height=4, font=TEXT_FONT,
                                   border=0, relief="flat", highlightthickness=0,
                                   bg=WHITE, fg=INK, insertbackground=INK,
                                   padx=8, pady=8)
        self.uarttextbox.pack(padx=1, pady=1)

        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(anchor="w", padx=24, pady=12)
        self.uart_send_btn = self._accent_button(row, "Send", self.uart_send)
        self.uart_send_btn.pack(side="left")
        self._ghost_button(row, "Back to Tests", self.uart_back).pack(
            side="left", padx=8)

        tk.Label(f, text="Received", font=SMALL_FONT,
                 bg=PANEL_BG, fg=INK_SOFT).pack(anchor="w", padx=24, pady=(8, 2))
        rw = tk.Frame(f, bg=BORDER)
        rw.pack(anchor="w", padx=24, pady=(0, 20))
        self.received = tk.Text(rw, width=44, height=5, font=TEXT_FONT,
                                border=0, relief="flat", highlightthickness=0,
                                bg=WHITE, fg=INK, padx=8, pady=8)
        self.received.pack(padx=1, pady=1)


    def _accent_button(self, parent, text, command):
        return tk.Button(parent, text=text, font=BTN_FONT, bg=ACCENT, fg=WHITE,
                         border=0, relief="flat", cursor="hand2",
                         activebackground=ACCENT_HI, activeforeground=WHITE,
                         padx=20, pady=8, command=command)

    def _ghost_button(self, parent, text, command):
        return tk.Button(parent, text=text, font=BTN_FONT, bg=BG, fg=INK,
                         border=0, relief="flat", cursor="hand2",
                         activebackground=BORDER, activeforeground=INK,
                         padx=20, pady=8, command=command)


    def add_log(self, message, tag="info"):
        now = datetime.now().strftime("%H:%M:%S")
        self.logwarning.pack_forget()
        self.logbox.insert("end", now + "  ", "time")
        self.logbox.insert("end", message + "\n", tag)
        self.logbox.see("end")

    def getlogs(self):
        try:
            if not self.logbox.get("1.0", "end-1c").strip():
                self.logwarning.pack(pady=10)
            else:
                log = self.logbox.get("1.0", "end-1c")
                with open("testlogs.txt", "a") as fh:
                    fh.write(log + "\n")
        except PermissionError:
            pass


    def _connect_ssh_async(self):
        threading.Thread(target=self._ssh_connect_worker, daemon=True).start()

    def _ssh_connect_worker(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=JETSON_IP, username=JETSON_USERNAME,
                           password=JETSON_PASSWORD, timeout=10)
            self.client = client
            full_cmd = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                        f"sudo -S -p '' sh -c {shlex.quote(HARDWARE_SETUP_CMD)}")
            stdin, stdout, stderr = client.exec_command(full_cmd)
            stdout.read()
            self.root.after(0, self._on_ssh_connected)
        except paramiko.AuthenticationException:
            self.root.after(0, self._on_ssh_error,
                            "Authentication failed. Check JETSON_USERNAME "
                            "and JETSON_PASSWORD in the script.")
        except Exception as e:
            self.root.after(0, self._on_ssh_error,
                            f"Could not connect to Jetson at {JETSON_IP}.\n\n{e}")

    def _on_ssh_connected(self):
        self.conn_label.config(
            text=f"Connected to {JETSON_IP}  \u2022  hardware ready",
            fg=STATE_PASS)
        for name in ("GPIO", "PWM", "UART", "I2S"):
            self._set_button_state(name, "ready")
            self.buttons[name].config(state=tk.NORMAL)
        self.add_log(f"Connected to {JETSON_IP} - PWM registers set, UART unlocked.",
                     "pass")

    def _on_ssh_error(self, message):
        self.conn_label.config(text="Connection failed", fg=STATE_FAIL)
        self.add_log("SSH connection failed.", "fail")
        messagebox.showerror("SSH Connection Error", message)

    def run_remote_test(self, script_name, extra_args="", use_sudo=False):
        if self.client is None:
            return "SSH ERROR: not connected to the Jetson"
        cmd = f"cd {REMOTE_TEST_DIR} && python3 {script_name}"
        if extra_args:
            cmd += f" {extra_args}"
        if use_sudo:
            cmd = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                   f"sudo -S -p '' sh -c {shlex.quote(cmd)}")
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
        except Exception as e:
            return f"SSH ERROR: {e}"
        if err:
            err = "\n".join(l for l in err.splitlines()
                            if "[sudo] password for" not in l).strip()
        full = out
        if err:
            full = (out + "\n[stderr]: " + err).strip()
        return full

    def run_remote_script(self, script_name, use_sudo=False):
        if self.client is None:
            return "SSH ERROR: not connected to the Jetson"
        cmd = (f"cd {REMOTE_TEST_DIR} && chmod +x {script_name} && "
               f"./{script_name}")
        if use_sudo:
            cmd = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                   f"sudo -S -p '' sh -c {shlex.quote(cmd)}")
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
        except Exception as e:
            return f"SSH ERROR: {e}"
        if err:
            err = "\n".join(l for l in err.splitlines()
                            if "[sudo] password for" not in l).strip()
        full = out
        if err:
            full = (out + "\n[stderr]: " + err).strip()
        return full

    def _set_test_buttons(self, state):
        for btn in self.test_buttons:
            btn.config(state=state)

    def _log_failure_detail(self, output, max_lines=3):
        for line in output.splitlines()[:max_lines]:
            if line.strip():
                self.add_log("    " + line.strip(), "fail")

    def on_close(self):
        if self.client:
            self.client.close()
        self.root.destroy()


    def gpio_test(self):
        self.gvar.set(0)
        self.gpio_auto = None
        self._clear_pin_labels()
        self._set_button_state("GPIO", "running")
        self._set_pill("GPIO", "running")
        self.gpio_running_label.config(text="Running on Jetson...", fg=STATE_RUN)
        self._show_frame(self.gpioFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("GPIO test starting...")
        threading.Thread(target=self._gpio_worker, daemon=True).start()

    def _gpio_worker(self):
        output = self.run_remote_test("gpiotest.py")
        self.root.after(0, self._gpio_done, output)

    @staticmethod
    def _parse_gpio_output(output):
        pin_results = {}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("GPIO PINS:"):
                summary = line.split(":", 1)[1]
                for part in summary.split(","):
                    if "=" in part:
                        pin, _, status = part.strip().partition("=")
                        pin_results[pin.strip()] = status.strip()
        auto_pass = GPIO_PASS_LINE in output
        return pin_results, auto_pass

    def _clear_pin_labels(self):
        for lbl in self.gpio_pin_labels:
            lbl.destroy()
        self.gpio_pin_labels = []

    def _gpio_done(self, output):
        pin_results, auto_pass = self._parse_gpio_output(output)
        self.gpio_auto = auto_pass
        for pin, status in pin_results.items():
            ok = (status == "PASS")
            chip = tk.Label(self.gpio_pin_frame,
                            text=f"  Pin {pin}: {status}  ", font=PIN_FONT,
                            bg=(STATE_PASS if ok else STATE_FAIL), fg=WHITE)
            chip.pack(side="left", padx=4)
            self.gpio_pin_labels.append(chip)
            self.add_log(f"GPIO Pin {pin}: {status}", "pass" if ok else "fail")
        if not pin_results:
            self.add_log("GPIO test: no per-pin results found in output.", "fail")
        if auto_pass:
            self.gpio_running_label.config(
                text="Script finished. Confirm the LEDs below, then check the box.",
                fg=STATE_PASS)
        else:
            self.gpio_running_label.config(
                text="Script reported a problem - see the Test Log.", fg=STATE_FAIL)
            self._log_failure_detail(output)
        self.add_log(f"GPIO script result: {'PASS' if auto_pass else 'FAIL'}",
                     "pass" if auto_pass else "fail")
        self._set_test_buttons(tk.NORMAL)

    def gpio_back(self):
        human_ok = (self.gvar.get() == 1)
        if self.gpio_auto is None:
            self.add_log("GPIO test: INCOMPLETE (left before the script finished).")
            self._set_pill("GPIO", "idle")
            self._set_button_state("GPIO", "ready")
        elif self.gpio_auto and human_ok:
            self.add_log("GPIO test: PASS (script + visual check).", "pass")
            self._set_pill("GPIO", "pass")
            self._set_button_state("GPIO", "pass")
        elif self.gpio_auto and not human_ok:
            self.add_log("GPIO test: FAIL (visual check not confirmed).", "fail")
            self._set_pill("GPIO", "fail")
            self._set_button_state("GPIO", "fail")
        else:
            self.add_log("GPIO test: FAIL (script reported failure).", "fail")
            self._set_pill("GPIO", "fail")
            self._set_button_state("GPIO", "fail")
        self._show_frame(self.logFrame)


    def pwm_test(self):
        self.pvar.set(0)
        self.pwm_auto = None
        self._set_button_state("PWM", "running")
        self._set_pill("PWM", "running")
        self.pwm_running_label.config(text="Running on Jetson...", fg=STATE_RUN)
        self._show_frame(self.pwmFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("PWM test starting...")
        threading.Thread(target=self._pwm_worker, daemon=True).start()

    def _pwm_worker(self):
        output = self.run_remote_test("pwmtest.py", use_sudo=True)
        self.root.after(0, self._pwm_done, output)

    def _pwm_done(self, output):
        auto_pass = PWM_PASS_LINE in output
        self.pwm_auto = auto_pass
        if auto_pass:
            self.pwm_running_label.config(
                text="Sweep finished. Confirm the fade below, then check the box.",
                fg=STATE_PASS)
        else:
            self.pwm_running_label.config(
                text="Script reported a problem - see the Test Log.", fg=STATE_FAIL)
            self._log_failure_detail(output, max_lines=25)
        self.add_log(f"PWM script result: {'PASS' if auto_pass else 'FAIL'}",
                     "pass" if auto_pass else "fail")
        self._set_test_buttons(tk.NORMAL)

    def pwm_back(self):
        human_ok = (self.pvar.get() == 1)
        if self.pwm_auto is None:
            self.add_log("PWM test: INCOMPLETE (left before the script finished).")
            self._set_pill("PWM", "idle")
            self._set_button_state("PWM", "ready")
        elif self.pwm_auto and human_ok:
            self.add_log("PWM test: PASS (script + visual check).", "pass")
            self._set_pill("PWM", "pass")
            self._set_button_state("PWM", "pass")
        elif self.pwm_auto and not human_ok:
            self.add_log("PWM test: FAIL (visual check not confirmed).", "fail")
            self._set_pill("PWM", "fail")
            self._set_button_state("PWM", "fail")
        else:
            self.add_log("PWM test: FAIL (script reported failure).", "fail")
            self._set_pill("PWM", "fail")
            self._set_button_state("PWM", "fail")
        self._show_frame(self.logFrame)


    def i2s_test(self):
        self.ivar.set(0)
        self.i2s_auto = None
        self._set_button_state("I2S", "running")
        self._set_pill("I2S", "running")
        self.i2s_running_label.config(text="Playing tone on Jetson...", fg=STATE_RUN)
        self._show_frame(self.i2sFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("I2S test starting...")
        threading.Thread(target=self._i2s_worker, daemon=True).start()

    def _i2s_worker(self):
        output = self.run_remote_script("I2S_test.sh", use_sudo=True)
        self.root.after(0, self._i2s_done, output)

    def _i2s_done(self, output):
        auto_done = I2S_DONE_LINE in output
        self.i2s_auto = auto_done
        if auto_done:
            self.i2s_running_label.config(
                text="Playback finished. Confirm you heard the tone, "
                     "then check the box.",
                fg=STATE_PASS)
        else:
            self.i2s_running_label.config(
                text="Script reported a problem - see the Test Log.", fg=STATE_FAIL)
            self._log_failure_detail(output, max_lines=25)
        self.add_log(f"I2S script result: "
                     f"{'playback completed' if auto_done else 'FAIL'}",
                     "pass" if auto_done else "fail")
        self._set_test_buttons(tk.NORMAL)

    def i2s_back(self):
        human_ok = (self.ivar.get() == 1)
        if self.i2s_auto is None:
            self.add_log("I2S test: INCOMPLETE (left before playback finished).")
            self._set_pill("I2S", "idle")
            self._set_button_state("I2S", "ready")
        elif self.i2s_auto and human_ok:
            self.add_log("I2S test: PASS (playback + heard tone).", "pass")
            self._set_pill("I2S", "pass")
            self._set_button_state("I2S", "pass")
        elif self.i2s_auto and not human_ok:
            self.add_log("I2S test: FAIL (tone not heard).", "fail")
            self._set_pill("I2S", "fail")
            self._set_button_state("I2S", "fail")
        else:
            self.add_log("I2S test: FAIL (script reported failure).", "fail")
            self._set_pill("I2S", "fail")
            self._set_button_state("I2S", "fail")
        self._show_frame(self.logFrame)


    def uart_test(self):
        self._show_frame(self.uartFrame)
        self.add_log("UART test opened.")

    def uart_send(self):
        message = self.uarttextbox.get("1.0", "end-1c").strip()
        if not message:
            return
        self.uart_send_btn.config(state=tk.DISABLED)
        self._set_pill("UART", "running")
        self._set_button_state("UART", "running")
        self.received.delete("1.0", "end")
        self.received.insert("1.0", "Sending...\n")
        threading.Thread(target=self._uart_worker, args=(message,),
                         daemon=True).start()

    def _uart_worker(self, message):
        output = self.run_remote_test("uarttest.py",
                                      extra_args=shlex.quote(message))
        self.root.after(0, self._uart_done, output)

    def _uart_done(self, output):
        passed = UART_PASS_LINE in output
        self.received.delete("1.0", "end")
        self.received.insert("1.0", output)
        if passed:
            self.add_log("UART test: PASS", "pass")
            self._set_pill("UART", "pass")
            self._set_button_state("UART", "pass")
        else:
            self.add_log("UART test: FAIL", "fail")
            self._set_pill("UART", "fail")
            self._set_button_state("UART", "fail")
        self.uart_send_btn.config(state=tk.NORMAL)

    def uart_back(self):
        self._show_frame(self.logFrame)


if __name__ == "__main__":
    NanoGUI()
