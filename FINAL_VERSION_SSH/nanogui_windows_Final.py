import os
import sys
import subprocess
import importlib
import importlib.util

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(APP_DIR, "libs")
if VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)

REQUIRED_PACKAGES = [
    ("paramiko", "paramiko"),
    ("PIL", "pillow"),
]


def _pip(*args):
    cmd = [sys.executable, "-m", "pip", "--disable-pip-version-check", *args]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kwargs).returncode == 0
    except Exception:
        return False


def _ensure_packages():
    missing = [(m, p) for m, p in REQUIRED_PACKAGES
               if importlib.util.find_spec(m) is None]
    if missing:
        if importlib.util.find_spec("pip") is None:
            try:
                import ensurepip
                ensurepip.bootstrap()
                importlib.invalidate_caches()
            except BaseException:
                pass
        for module_name, pip_name in missing:
            print("Installing missing package: " + pip_name)
            (_pip("install", pip_name)
             or _pip("install", "--user", pip_name)
             or _pip("install", "--target", VENDOR_DIR, pip_name))
        importlib.invalidate_caches()
    return [p for m, p in REQUIRED_PACKAGES
            if importlib.util.find_spec(m) is None]


_MISSING = _ensure_packages()
if _MISSING:
    _msg = ("Required packages could not be installed automatically:\n\n"
            + "\n".join("    " + name for name in _MISSING)
            + "\n\nThis machine may have no internet access.\n"
              "Run this from a command prompt while online:\n\n"
              '"' + sys.executable + '" -m pip install --target "'
            + VENDOR_DIR + '" ' + " ".join(_MISSING))
    print(_msg)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _root = _tk.Tk()
        _root.withdraw()
        _mb.showerror("Missing Packages", _msg)
        _root.destroy()
    except Exception:
        pass
    sys.exit(1)


import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import shlex
import csv
import os
import time
from datetime import datetime
import paramiko


JETSON_IP       = "10.131.17.154"
JETSON_USERNAME = "group7"
JETSON_PASSWORD = "group7"
REMOTE_TEST_DIR = "/home/group7/Documents/projectlab"

CSV_FILE = "test_results.csv"

GPIO_PASS_LINE    = "GPIO TEST: PASS"
GPIO_PINS_PREFIX  = "GPIO PINS:"
GPIO_LIST_PREFIX  = "GPIO LIST:"
GPIO_NOW_PREFIX   = "GPIO NOW:"
PWM_PASS_LINE     = "PWM TEST: PASS"
PWM_PINS_PREFIX   = "PWM PINS:"
UART_PASS_LINE    = "UART LOOPBACK: PASS"
I2S_IN_DONE_LINE  = "I2S RECORD: COMPLETE"
I2S_OUT_DONE_LINE = "I2S PLAYBACK: COMPLETE"
SPI_PASS_LINE     = "SPI TEST: PASS"
I2C_PASS_LINE     = "I2C TEST: PASS"
I2C_FAIL_LINE     = "I2C TEST: FAIL"
I2C_SCAN_PREFIX   = "I2C SCAN:"
I2C_DIST_PREFIX   = "Distance:"
I2C_SPREAD_MM     = 100
I2C_SAMPLE_SEC    = 0.2
I2C_MAX_RANGE_MM  = 8000
USB_PORTS_PREFIX  = "USB PORTS:"
WIFI_PASS_LINE    = "WIFI TEST: PASS"

PWM_PINS = (32, 33)


USB_PORT_MAP = [
    ("USB 1", "1-2.1"),
    ("USB 2", "1-2.3"),
    ("USB 3", "1-2.2"),
    ("USB 4", "1-2.4"),
]
USB_DIAGRAM_FILE = "usbdiagram.png"
USB_SCAN_TAG = "nanogui_usb_scan"


USB_SCAN_CMD = (
    ": " + USB_SCAN_TAG + "; i=0; "
    "while [ $i -lt 2400 ]; do s=\"\"; "
    "for d in " + " ".join(node for _, node in USB_PORT_MAP) + "; do "
    "if [ -e /sys/bus/usb/devices/$d ]; then s=\"${s}1\"; "
    "else s=\"${s}0\"; fi; done; "
    "echo \"" + USB_PORTS_PREFIX + " $s\"; "
    "i=$((i+1)); sleep 0.5; done"
)


WIFI_CMD = r"""
DEV=$(nmcli -t -f DEVICE,TYPE device status 2>/dev/null | awk -F: '$2=="wifi"{print $1; exit}')
[ -z "$DEV" ] && DEV=wlan0
if [ ! -e /sys/class/net/$DEV ]; then
  echo "WIFI DEV: $DEV"
  echo "WIFI STATE: missing"
  echo "WIFI TEST: FAIL"
  exit 0
fi
ST=$(nmcli -t -f DEVICE,STATE device status 2>/dev/null | awk -F: -v d=$DEV '$1==d{print $2; exit}')
SSID=$(nmcli -t -f DEVICE,CONNECTION device status 2>/dev/null | awk -F: -v d=$DEV '$1==d{print $2; exit}')
IP=$(ip -4 -o addr show dev $DEV 2>/dev/null | awk '{print $4; exit}')
SIG=$(iw dev $DEV link 2>/dev/null | awk -F': ' '/signal/{print $2; exit}')
RATE=$(iw dev $DEV link 2>/dev/null | awk -F': ' '/bitrate/{print $2; exit}')
echo "WIFI DEV: $DEV"
echo "WIFI STATE: ${ST:-unknown}"
echo "WIFI SSID: ${SSID:-none}"
echo "WIFI IP: ${IP:-none}"
echo "WIFI SIGNAL: ${SIG:-unknown}"
echo "WIFI RATE: ${RATE:-unknown}"
if ping -I $DEV -c 3 -W 2 8.8.8.8 >/dev/null 2>&1; then
  echo "WIFI PING: PASS"
  P=1
else
  echo "WIFI PING: FAIL"
  P=0
fi
if ping -I $DEV -c 1 -W 3 www.google.com >/dev/null 2>&1; then
  echo "WIFI DNS: PASS"
else
  echo "WIFI DNS: FAIL"
fi
if [ "$P" = "1" ]; then
  echo "WIFI TEST: PASS"
else
  echo "WIFI TEST: FAIL"
fi
"""

WIFI_BROWSER_CMD = ("export DISPLAY=:0; xdg-open https://www.youtube.com "
                    ">/dev/null 2>&1 &")


BG        = "#f4f6f8"
PANEL_BG  = "#ffffff"
BORDER    = "#d8dee6"
INK       = "#1f2933"
INK_SOFT  = "#6b7684"
ACCENT    = "#2563cc"
ACCENT_HI = "#1d4ed8"
TRACK     = "#eef1f5"

STATE_IDLE    = "#e3e8ee"
STATE_IDLE_FG = "#6b7684"
STATE_RUN     = "#f0a020"
STATE_PASS    = "#1a9e56"
STATE_FAIL    = "#d23c3c"

F_TITLE  = ("Segoe UI Light", 22)
F_SUB    = ("Segoe UI", 10)
F_HEAD   = ("Segoe UI Semibold", 14)
F_BODY   = ("Segoe UI", 10)
F_BODYB  = ("Segoe UI Semibold", 10)
F_BIG    = ("Segoe UI Semibold", 15)
F_BTN    = ("Segoe UI Semibold", 11)
F_PILL   = ("Segoe UI Semibold", 9)
F_TINY   = ("Segoe UI", 8)
F_MONO   = ("Consolas", 9)

TESTS = ["GPIO", "PWM", "UART", "I2S IN", "I2S OUT", "SPI", "I2C", "CAMERA",
         "USB", "WIFI"]
LIVE_TESTS = ["GPIO", "PWM", "UART", "I2S IN", "I2S OUT", "SPI", "I2C",
              "CAMERA", "USB", "WIFI"]
PILLS_PER_ROW = 5

INTRO_TEXTS = {
    "GPIO": ("GPIO Output Test",
             "Each pin is driven high and low on its own, one at a time, "
             "in the order listed below. Watch the labelled LED for the "
             "pin highlighted as it runs, then uncheck any pin whose LED "
             "did not blink."),
    "PWM": ("PWM Output Test",
            "Both PWM pins are driven together on every run, so the servo "
            "sweeps whichever of the two it is plugged into. Run once with "
            "the signal lead on pin 32 and tick that pin, then move the "
            "lead to pin 33 and run again. Ticks are kept until you reset "
            "them, so both pins can be confirmed across two runs."),
    "UART": ("UART Loopback Test",
             "Jumper pin 8 (TX) to pin 10 (RX). Type any string, "
             "press Send, and the Jetson writes it out on "
             "/dev/ttyTHS1 and reads it straight back. The test "
             "passes if sent and received match."),
    "I2S IN": ("I2S Input  -  SPH0645 Microphone",
               "Mic BCLK to pin 12, LRCL to pin 35, DOUT to pin 38, 3V to "
               "pin 1, GND and SEL to pin 39. Press Start, stay quiet for "
               "one second while baseline is measured, then knock near "
               "microphone."),
    "I2S OUT": ("I2S Output  -  PCM5102A DAC",
                "DAC BCK to pin 12, LCK to pin 35, DIN to pin 40, VIN to "
                "pin 2, GND to pin 39, SCK to GND, XSMT to 3.3V. FMT to "
                "GND, FLT to GND. Plug earbuds into the DAC jack and "
                "listen for tone."),
    "SPI": ("SPI  -  ST7735 LCD Display",
            "Display SCK to pin 23, MOSI to pin 19, CS to pin 24, DC to "
            "pin 22, RESET to pin 18, VCC to 3.3V, BL to 3.3V, GND to "
            "pin 25. Watch the screen cycle red, green and blue twice."),
    "I2C": ("I2C  -  VL53L0X Distance Sensor",
            "Sensor J1 pin 5 (VDD) to pin 1 on nano (3.3V), J1 pin 2 (SDA) to "
            "pin 5 on nano, J1 pin 4 (SCL) to pin 3 on nano, J1 pin 6 (GND) to pin 9 on nano. "
            "Press Start Reading, then move a target toward and away "
            "from the sensor - the distance is streamed live and the "
            "test arms once the reading has followed the target."),
    "CAMERA": ("CSI Camera Test",
               "Live MJPEG frames are streamed from the Jetson over "
               "the existing SSH connection. Press Stop before "
               "switching cameras."),
    "USB": ("USB Port Test",
            "The Jetson is polled twice a second and each port lights up "
            "while a device is plugged into it. Use the diagram to find "
            "each socket, then move one flash drive around all four ports. "
            "A port stays marked as seen once it has enumerated, so all "
            "four can be confirmed with a single drive."),
    "WIFI": ("WiFi Test",
             "Read-only check of the wireless interface: association "
             "state, SSID, address, signal, then three pings sent out of "
             "the wireless device itself. Nothing is reconfigured, so the "
             "Ethernet link carrying this SSH session is left alone. The "
             "Jetson must already be associated to a network."),
}

BLOCK_SEC = 0.1
LIST_ROWS = 400
LIST_HEIGHT = 20
CAM_W = 640
CAM_H = 480


class NanoGUI:
    def __init__(self):
        self.client = None
        self.pills = {}
        self.pill_subs = {}
        self.buttons = {}
        self.btn_states = {}
        self.results = {}

        self.gpio_auto = None
        self.pwm_auto = None
        self.i2s_in_auto = None
        self.i2s_out_auto = None
        self.spi_auto = None
        self.i2c_auto = None

        self.i2s_in_channel = None
        self.i2s_in_error = None
        self.i2s_in_gen = 0
        self.i2s_in_threshold = None
        self.i2s_in_over = False
        self.i2s_in_blocks = 0

        self.i2c_channel = None
        self.i2c_error = None
        self.i2c_gen = 0
        self.i2c_found = None
        self.i2c_min = None
        self.i2c_max = None
        self.i2c_samples = 0

        self.cam_channel = None
        self.cam_error = None
        self.cam_saw_frame = False
        self.cam_sensor = None
        self.cam_gen = 0
        self.cam_photo = None

        self.usb_channel = None
        self.usb_error = None
        self.usb_gen = 0
        self.usb_scanned = False
        self.usb_seen = {label: False for label, _ in USB_PORT_MAP}
        self.usb_live = {label: False for label, _ in USB_PORT_MAP}
        self.usb_rows = {}
        self.usb_photo = None

        self.wifi_auto = None
        self.wifi_info = {}

        self.root = tk.Tk()
        self.root.title("Jetson Nano Test Bench")
        self.root.geometry("1280x820")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.gpio_vars = {}
        self.gpio_rows = {}
        self.gpio_pin_auto = {}

        # Deliberately built once and never rebuilt.  The servo can only be
        # watched on one pin at a time, so a tick has to survive the next
        # run or the second pin could never be confirmed alongside the first.
        self.pwm_vars = {p: tk.IntVar(value=0) for p in PWM_PINS}
        self.pwm_rows = {}
        self.pwm_driven = []
        self.ivar_in = tk.IntVar(value=0)
        self.ivar_out = tk.IntVar(value=0)
        self.svar = tk.IntVar(value=0)
        self.icvar = tk.IntVar(value=0)
        self.cvar = tk.IntVar(value=0)
        self.uart_msg = tk.StringVar(value="Hello Jetson")

        self._build_header()
        self._build_dashboard()
        self._build_body()

        self._show_frame(self.logFrame)
        self.add_log("Test bench started.")
        self.root.after(100, self._connect_ssh_async)
        self.root.mainloop()

    def _build_header(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill=tk.X, padx=28, pady=(16, 10))
        tk.Label(head, text="Jetson Nano Test Bench", font=F_TITLE,
                 bg=BG, fg=INK).pack(side=tk.LEFT)
        tk.Button(head, text="Disconnect", font=F_TINY, relief=tk.FLAT,
                  bd=0, cursor="hand2", bg=BG, fg=INK_SOFT,
                  command=self.disconnect).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(head, text="Reconnect", font=F_TINY, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=BG, fg=ACCENT,
                  command=self.reconnect).pack(side=tk.RIGHT, padx=(14, 0))
        self.conn_label = tk.Label(head, text="Connecting to Jetson...",
                                   font=F_BODY, bg=BG, fg=STATE_RUN)
        self.conn_label.pack(side=tk.RIGHT)

    def _build_dashboard(self):
        dash = tk.Frame(self.root, bg=PANEL_BG, highlightbackground=BORDER,
                        highlightthickness=1)
        dash.pack(fill=tk.X, padx=28, pady=(0, 10))

        rows = []
        for _ in range((len(TESTS) + PILLS_PER_ROW - 1) // PILLS_PER_ROW):
            r = tk.Frame(dash, bg=PANEL_BG)
            r.pack(fill=tk.X, padx=14, pady=(12, 0))
            rows.append(r)

        for i, name in enumerate(TESTS):
            row = rows[i // PILLS_PER_ROW]
            col = i % PILLS_PER_ROW
            row.grid_columnconfigure(col, weight=1)
            cell = tk.Frame(row, bg=STATE_IDLE)
            cell.grid(row=0, column=col, padx=4, sticky="ew")
            inner = tk.Frame(cell, bg=STATE_IDLE)
            inner.pack(padx=14, pady=7)
            dot = tk.Label(inner, text="\u25cf", font=F_PILL,
                           bg=STATE_IDLE, fg=STATE_IDLE_FG)
            dot.pack(side=tk.LEFT)
            lab = tk.Label(inner, text=name, font=F_PILL,
                           bg=STATE_IDLE, fg=STATE_IDLE_FG)
            lab.pack(side=tk.LEFT, padx=(6, 8))
            sub = tk.Label(inner, text="Not run", font=F_TINY,
                           bg=STATE_IDLE, fg=STATE_IDLE_FG)
            sub.pack(side=tk.LEFT)
            self.pills[name] = (cell, inner, dot, lab)
            self.pill_subs[name] = sub

        self.summary_label = tk.Label(dash, text=f"0 / {len(TESTS)} passed",
                                      font=F_BODYB, bg=PANEL_BG, fg=INK_SOFT)
        self.summary_label.pack(anchor="e", padx=20, pady=(8, 10))

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=(0, 18))

        side = tk.Frame(body, bg=BG, width=210)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)

        tk.Label(side, text="INTERFACES", font=("Segoe UI", 9),
                 bg=BG, fg=INK_SOFT).pack(anchor="w", pady=(4, 10))

        specs = [
            ("GPIO", "Test GPIO", self.gpio_intro, True),
            ("PWM", "Test PWM", self.pwm_intro, True),
            ("UART", "Test UART", self.uart_intro, True),
            ("I2S IN", "Test I2S Input", self.i2s_in_intro, True),
            ("I2S OUT", "Test I2S Output", self.i2s_out_intro, True),
            ("SPI", "Test SPI", self.spi_intro, True),
            ("I2C", "Test I2C", self.i2c_intro, True),
            ("CAMERA", "Test Camera", self.cam_intro, True),
            ("USB", "Test USB", self.usb_intro, True),
            ("WIFI", "Test WiFi", self.wifi_intro, True),
        ]
        for name, text, cmd, live in specs:
            b = tk.Button(side, text=text, font=F_BTN, relief=tk.FLAT, bd=0,
                          cursor="hand2", width=18, pady=8,
                          command=cmd if cmd else (lambda: None))
            b.pack(pady=2)
            self.buttons[name] = b
            self._set_button_state(name, "ready" if live else "na")

        self.content = tk.Frame(body, bg=PANEL_BG, highlightbackground=BORDER,
                                highlightthickness=1)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        self.logFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.introFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.gpioFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.pwmFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.uartFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.i2sInFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.i2sOutFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.spiFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.i2cFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.camFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.usbFrame = tk.Frame(self.content, bg=PANEL_BG)
        self.wifiFrame = tk.Frame(self.content, bg=PANEL_BG)

        for f in (self.logFrame, self.introFrame, self.gpioFrame,
                  self.pwmFrame, self.uartFrame, self.i2sInFrame,
                  self.i2sOutFrame, self.spiFrame, self.i2cFrame,
                  self.camFrame, self.usbFrame, self.wifiFrame):
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_log_frame()
        self._build_intro_frame()
        self._build_gpio_frame()
        self._build_pwm_frame()
        self._build_uart_frame()
        self._build_i2s_in_frame()
        self._build_i2s_out_frame()
        self._build_spi_frame()
        self._build_i2c_frame()
        self._build_cam_frame()
        self._build_usb_frame()
        self._build_wifi_frame()

    def _panel_head(self, parent, title, subtitle, extra=None):
        bar = tk.Frame(parent, bg=PANEL_BG)
        bar.pack(fill=tk.X, padx=22, pady=(18, 2))
        tk.Label(bar, text=title, font=F_HEAD, bg=PANEL_BG,
                 fg=INK).pack(side=tk.LEFT)
        if extra:
            tk.Button(bar, text=extra[0], font=F_TINY, relief=tk.FLAT, bd=0,
                      cursor="hand2", bg=PANEL_BG, fg=ACCENT,
                      command=extra[1]).pack(side=tk.RIGHT)
        tk.Label(parent, text=subtitle, font=F_BODY, bg=PANEL_BG, fg=INK_SOFT,
                 justify=tk.LEFT, wraplength=800).pack(anchor="w", padx=22,
                                                       pady=(0, 10))

    def _back_button(self, parent, cmd, side=tk.TOP):
        tk.Button(parent, text="Back to Log", font=F_BODYB, relief=tk.FLAT,
                  bd=0, cursor="hand2", bg=STATE_IDLE, fg=INK, padx=18, pady=7,
                  command=cmd).pack(side=side, anchor="w", padx=22, pady=14)

    def _build_log_frame(self):
        self._panel_head(self.logFrame, "Test Log",
                         "Every action, result and error is recorded here and "
                         "appended to test_results.csv.",
                         extra=("Download Log", self.download_log))
        wrap = tk.Frame(self.logFrame, bg=PANEL_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 22))
        bar = tk.Scrollbar(wrap)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(wrap, font=F_MONO, bg="#fbfcfd", fg=INK,
                                relief=tk.FLAT, highlightbackground=BORDER,
                                highlightthickness=1, wrap=tk.WORD,
                                yscrollcommand=bar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        bar.config(command=self.log_text.yview)
        self.log_text.tag_config("pass", foreground=STATE_PASS)
        self.log_text.tag_config("fail", foreground=STATE_FAIL)
        self.log_text.tag_config("info", foreground=INK_SOFT)
        self.log_text.config(state=tk.DISABLED)

    def _build_intro_frame(self):
        bar = tk.Frame(self.introFrame, bg=PANEL_BG)
        bar.pack(fill=tk.X, padx=22, pady=(18, 2))
        self.intro_title = tk.Label(bar, text="", font=F_HEAD, bg=PANEL_BG,
                                    fg=INK)
        self.intro_title.pack(side=tk.LEFT)
        self.intro_text = tk.Label(self.introFrame, text="", font=F_BODY,
                                   bg=PANEL_BG, fg=INK_SOFT, justify=tk.LEFT,
                                   wraplength=800)
        self.intro_text.pack(anchor="w", padx=22, pady=(0, 10))
        row = tk.Frame(self.introFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22, pady=(6, 0))
        self.intro_continue_btn = tk.Button(row, text="Continue",
                                            font=F_BODYB, relief=tk.FLAT,
                                            bd=0, cursor="hand2", bg=ACCENT,
                                            fg="white",
                                            activebackground=ACCENT_HI,
                                            activeforeground="white",
                                            padx=22, pady=7)
        self.intro_continue_btn.pack(side=tk.LEFT)
        tk.Button(row, text="Back", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=STATE_IDLE, fg=INK, padx=22, pady=7,
                  command=self.intro_back).pack(side=tk.LEFT, padx=8)

    def _build_gpio_frame(self):
        self._panel_head(self.gpioFrame, *INTRO_TEXTS["GPIO"])
        self.gpio_running_label = tk.Label(self.gpioFrame, text="",
                                           font=F_BODYB, bg=PANEL_BG, fg=INK,
                                           justify=tk.LEFT, wraplength=800)
        self.gpio_running_label.pack(anchor="w", padx=22)
        self.gpio_hint_label = tk.Label(self.gpioFrame, text="", font=F_BODY,
                                        bg=PANEL_BG, fg=INK_SOFT,
                                        justify=tk.LEFT, wraplength=800)
        self.gpio_hint_label.pack(anchor="w", padx=22, pady=(4, 0))
        self.gpio_pin_box = tk.Frame(self.gpioFrame, bg=PANEL_BG)
        self.gpio_pin_box.pack(anchor="w", padx=22, pady=12)
        self._back_button(self.gpioFrame, self.gpio_back)

    def _gpio_build_rows(self, pins):
        for w in self.gpio_pin_box.winfo_children():
            w.destroy()
        self.gpio_vars = {}
        self.gpio_rows = {}
        for i, pin in enumerate(pins):
            cell = tk.Frame(self.gpio_pin_box, bg=PANEL_BG)
            cell.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 24),
                      pady=2)
            var = tk.IntVar(value=1)
            box = tk.Checkbutton(cell, text=f"Pin {pin}", variable=var,
                                 font=F_BODY, bg=PANEL_BG, fg=INK,
                                 activebackground=PANEL_BG,
                                 selectcolor=PANEL_BG)
            box.pack(side=tk.LEFT)
            state = tk.Label(cell, text="waiting", font=F_TINY, bg=PANEL_BG,
                             fg=INK_SOFT, width=9, anchor="w")
            state.pack(side=tk.LEFT)
            self.gpio_vars[pin] = var
            self.gpio_rows[pin] = (box, state)

    def _build_pwm_frame(self):
        self._panel_head(self.pwmFrame, *INTRO_TEXTS["PWM"])
        self.pwm_running_label = tk.Label(self.pwmFrame, text="", font=F_BODYB,
                                          bg=PANEL_BG, fg=INK,
                                          justify=tk.LEFT, wraplength=800)
        self.pwm_running_label.pack(anchor="w", padx=22)
        self.pwm_hint_label = tk.Label(self.pwmFrame, text="", font=F_BODY,
                                       bg=PANEL_BG, fg=INK_SOFT,
                                       justify=tk.LEFT, wraplength=800)
        self.pwm_hint_label.pack(anchor="w", padx=22, pady=(4, 0))

        box = tk.Frame(self.pwmFrame, bg=PANEL_BG)
        box.pack(anchor="w", padx=22, pady=12)
        for i, pin in enumerate(PWM_PINS):
            cell = tk.Frame(box, bg=PANEL_BG)
            cell.grid(row=i, column=0, sticky="w", pady=3)
            chk = tk.Checkbutton(
                cell, text=f"Pin {pin}  -  servo swept on this pin",
                variable=self.pwm_vars[pin], font=F_BODY, bg=PANEL_BG, fg=INK,
                activebackground=PANEL_BG, selectcolor=PANEL_BG)
            chk.pack(side=tk.LEFT)
            state = tk.Label(cell, text="not run", font=F_TINY, bg=PANEL_BG,
                             fg=INK_SOFT, width=16, anchor="w")
            state.pack(side=tk.LEFT, padx=(8, 0))
            self.pwm_rows[pin] = (chk, state)

        tk.Button(self.pwmFrame, text="Reset both ticks", font=F_TINY,
                  relief=tk.FLAT, bd=0, cursor="hand2", bg=PANEL_BG,
                  fg=ACCENT, command=self.pwm_reset_confirmations).pack(
                      anchor="w", padx=20)
        self._back_button(self.pwmFrame, self.pwm_back)

    def _build_uart_frame(self):
        self._panel_head(self.uartFrame, *INTRO_TEXTS["UART"])
        row = tk.Frame(self.uartFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22, pady=(4, 12))
        self.uart_entry = tk.Entry(row, textvariable=self.uart_msg,
                                   font=("Consolas", 11), width=46,
                                   relief=tk.FLAT, bg="#fbfcfd",
                                   highlightbackground=BORDER,
                                   highlightthickness=1)
        self.uart_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 10))
        self.uart_entry.bind("<Return>", lambda e: self.uart_send())
        self.uart_send_btn = tk.Button(row, text="Send", font=F_BODYB,
                                       relief=tk.FLAT, bd=0, cursor="hand2",
                                       bg=ACCENT, fg="white", padx=22, pady=7,
                                       command=self.uart_send)
        self.uart_send_btn.pack(side=tk.LEFT)

        self.uart_sent_label = tk.Label(self.uartFrame, text="Sent:  -",
                                        font=F_MONO, bg=PANEL_BG, fg=INK_SOFT,
                                        justify=tk.LEFT, wraplength=800)
        self.uart_sent_label.pack(anchor="w", padx=22)
        self.uart_recv_label = tk.Label(self.uartFrame, text="Received:  -",
                                        font=F_MONO, bg=PANEL_BG, fg=INK_SOFT,
                                        justify=tk.LEFT, wraplength=800)
        self.uart_recv_label.pack(anchor="w", padx=22, pady=(2, 10))
        self.uart_running_label = tk.Label(self.uartFrame, text="",
                                           font=F_BIG, bg=PANEL_BG, fg=INK,
                                           justify=tk.LEFT, wraplength=800)
        self.uart_running_label.pack(anchor="w", padx=22)
        self._back_button(self.uartFrame, self.uart_back)

    def _build_i2s_in_frame(self):
        self._panel_head(self.i2sInFrame, *INTRO_TEXTS["I2S IN"])

        row = tk.Frame(self.i2sInFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22)
        self.i2s_in_start_btn = tk.Button(row, text="Start Monitor",
                                          font=F_BODYB, relief=tk.FLAT, bd=0,
                                          cursor="hand2", bg=ACCENT,
                                          fg="white", padx=18, pady=7,
                                          command=self.i2s_in_start)
        self.i2s_in_start_btn.pack(side=tk.LEFT)
        tk.Button(row, text="Stop", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=STATE_IDLE, fg=INK, padx=18, pady=7,
                  command=self.i2s_in_stop).pack(side=tk.LEFT, padx=8)

        self.i2s_in_running_label = tk.Label(self.i2sInFrame, text="Idle.",
                                             font=F_BIG, bg=PANEL_BG,
                                             fg=INK_SOFT, justify=tk.LEFT,
                                             wraplength=800)
        self.i2s_in_running_label.pack(anchor="w", padx=22, pady=(12, 0))

        self.i2s_in_armed_label = tk.Label(self.i2sInFrame, text="",
                                           font=F_TINY, bg=PANEL_BG,
                                           fg=INK_SOFT)
        self.i2s_in_armed_label.pack(anchor="w", padx=22, pady=(0, 2))

        self.i2s_in_read_label = tk.Label(
            self.i2sInFrame,
            text="peak  -        rms  -        freq  -        threshold  -",
            font=F_MONO, bg=PANEL_BG, fg=INK_SOFT)
        self.i2s_in_read_label.pack(anchor="w", padx=22, pady=(0, 8))

        tk.Label(self.i2sInFrame, font=F_MONO, bg=PANEL_BG, fg=INK_SOFT,
                 text="%8s %9s %9s %7s      %s"
                      % ("time", "peak", "rms", "freq", "status")
                 ).pack(anchor="w", padx=22, pady=(4, 0))

        # Reserved from the bottom before the list is packed, for the same
        # reason as the camera panel below.  The 20-line list asks for more
        # height than the panel has, so packing it first consumed the whole
        # cavity and left the checkbox and Back button unmapped.
        self._back_button(self.i2sInFrame, self.i2s_in_back, side=tk.BOTTOM)
        tk.Checkbutton(self.i2sInFrame,
                       text="Yes - the readings responded to sound",
                       variable=self.ivar_in, font=F_BODY, bg=PANEL_BG, fg=INK,
                       activebackground=PANEL_BG,
                       selectcolor=PANEL_BG).pack(side=tk.BOTTOM, anchor="w",
                                                  padx=20)

        wrap = tk.Frame(self.i2sInFrame, bg=PANEL_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=22, pady=(2, 8))
        bar = tk.Scrollbar(wrap)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.i2s_in_list = tk.Text(wrap, font=F_MONO, height=LIST_HEIGHT,
                                   bg="#fbfcfd", fg=INK, relief=tk.FLAT,
                                   highlightbackground=BORDER,
                                   highlightthickness=1, wrap=tk.NONE,
                                   yscrollcommand=bar.set)
        self.i2s_in_list.pack(fill=tk.BOTH, expand=True)
        bar.config(command=self.i2s_in_list.yview)
        self.i2s_in_list.tag_config("hit", foreground=STATE_PASS)
        self.i2s_in_list.tag_config("quiet", foreground=INK_SOFT)
        self.i2s_in_list.tag_config("note", foreground=ACCENT)
        self.i2s_in_list.config(state=tk.DISABLED)

    def _build_i2s_out_frame(self):
        self._panel_head(self.i2sOutFrame, *INTRO_TEXTS["I2S OUT"])
        self.i2s_out_running_label = tk.Label(self.i2sOutFrame, text="",
                                              font=F_BODYB, bg=PANEL_BG,
                                              fg=INK, justify=tk.LEFT,
                                              wraplength=800)
        self.i2s_out_running_label.pack(anchor="w", padx=22)
        wrap = tk.Frame(self.i2sOutFrame, bg=PANEL_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=22, pady=10)
        bar = tk.Scrollbar(wrap)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.i2s_out_output = tk.Text(wrap, font=F_MONO, height=12,
                                      bg="#fbfcfd", fg=INK, relief=tk.FLAT,
                                      highlightbackground=BORDER,
                                      highlightthickness=1, wrap=tk.WORD,
                                      yscrollcommand=bar.set)
        self.i2s_out_output.pack(fill=tk.BOTH, expand=True)
        bar.config(command=self.i2s_out_output.yview)
        self.i2s_out_output.config(state=tk.DISABLED)
        tk.Checkbutton(self.i2sOutFrame,
                       text="Yes - I heard the tone clearly",
                       variable=self.ivar_out, font=F_BODY, bg=PANEL_BG,
                       fg=INK, activebackground=PANEL_BG,
                       selectcolor=PANEL_BG).pack(anchor="w", padx=20)
        self._back_button(self.i2sOutFrame, self.i2s_out_back)

    def _build_spi_frame(self):
        self._panel_head(self.spiFrame, *INTRO_TEXTS["SPI"])
        self.spi_running_label = tk.Label(self.spiFrame, text="",
                                          font=F_BODYB, bg=PANEL_BG, fg=INK,
                                          justify=tk.LEFT, wraplength=800)
        self.spi_running_label.pack(anchor="w", padx=22)
        wrap = tk.Frame(self.spiFrame, bg=PANEL_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=22, pady=10)
        bar = tk.Scrollbar(wrap)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.spi_output = tk.Text(wrap, font=F_MONO, height=12,
                                  bg="#fbfcfd", fg=INK, relief=tk.FLAT,
                                  highlightbackground=BORDER,
                                  highlightthickness=1, wrap=tk.WORD,
                                  yscrollcommand=bar.set)
        self.spi_output.pack(fill=tk.BOTH, expand=True)
        bar.config(command=self.spi_output.yview)
        self.spi_output.config(state=tk.DISABLED)
        tk.Checkbutton(self.spiFrame,
                       text="Yes - the display cycled red, green and blue",
                       variable=self.svar, font=F_BODY, bg=PANEL_BG,
                       fg=INK, activebackground=PANEL_BG,
                       selectcolor=PANEL_BG).pack(anchor="w", padx=20)
        self._back_button(self.spiFrame, self.spi_back)

    def _build_i2c_frame(self):
        self._panel_head(self.i2cFrame, *INTRO_TEXTS["I2C"])

        row = tk.Frame(self.i2cFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22)
        self.i2c_start_btn = tk.Button(row, text="Start Reading",
                                       font=F_BODYB, relief=tk.FLAT, bd=0,
                                       cursor="hand2", bg=ACCENT,
                                       fg="white", padx=18, pady=7,
                                       command=self.i2c_start)
        self.i2c_start_btn.pack(side=tk.LEFT)
        tk.Button(row, text="Stop", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=STATE_IDLE, fg=INK, padx=18, pady=7,
                  command=self.i2c_stop).pack(side=tk.LEFT, padx=8)

        self.i2c_running_label = tk.Label(self.i2cFrame, text="Idle.",
                                          font=F_BIG, bg=PANEL_BG,
                                          fg=INK_SOFT, justify=tk.LEFT,
                                          wraplength=800)
        self.i2c_running_label.pack(anchor="w", padx=22, pady=(12, 0))

        self.i2c_armed_label = tk.Label(self.i2cFrame, text="",
                                        font=F_TINY, bg=PANEL_BG,
                                        fg=INK_SOFT)
        self.i2c_armed_label.pack(anchor="w", padx=22, pady=(0, 2))

        self.i2c_read_label = tk.Label(
            self.i2cFrame,
            text="distance  -        nearest  -        farthest  -"
                 "        spread  -",
            font=F_MONO, bg=PANEL_BG, fg=INK_SOFT)
        self.i2c_read_label.pack(anchor="w", padx=22, pady=(0, 8))

        tk.Label(self.i2cFrame, font=F_MONO, bg=PANEL_BG, fg=INK_SOFT,
                 text="%8s %11s      %s" % ("time", "distance", "status")
                 ).pack(anchor="w", padx=22, pady=(4, 0))

        # Reserved from the bottom before the list is packed, for the same
        # reason as the I2S input panel above.
        self._back_button(self.i2cFrame, self.i2c_back, side=tk.BOTTOM)
        tk.Checkbutton(self.i2cFrame,
                       text="Yes - the reading followed the target",
                       variable=self.icvar, font=F_BODY, bg=PANEL_BG,
                       fg=INK, activebackground=PANEL_BG,
                       selectcolor=PANEL_BG).pack(side=tk.BOTTOM, anchor="w",
                                                  padx=20)

        wrap = tk.Frame(self.i2cFrame, bg=PANEL_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=22, pady=(2, 8))
        bar = tk.Scrollbar(wrap)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.i2c_list = tk.Text(wrap, font=F_MONO, height=LIST_HEIGHT,
                                bg="#fbfcfd", fg=INK, relief=tk.FLAT,
                                highlightbackground=BORDER,
                                highlightthickness=1, wrap=tk.NONE,
                                yscrollcommand=bar.set)
        self.i2c_list.pack(fill=tk.BOTH, expand=True)
        bar.config(command=self.i2c_list.yview)
        self.i2c_list.tag_config("hit", foreground=STATE_PASS)
        self.i2c_list.tag_config("quiet", foreground=INK_SOFT)
        self.i2c_list.tag_config("note", foreground=ACCENT)
        self.i2c_list.tag_config("bad", foreground=STATE_FAIL)
        self.i2c_list.config(state=tk.DISABLED)

    def _build_cam_frame(self):
        self._panel_head(self.camFrame, *INTRO_TEXTS["CAMERA"])
        row = tk.Frame(self.camFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22)
        tk.Button(row, text="Test CAM 0", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=ACCENT, fg="white", padx=16, pady=7,
                  command=lambda: self.cam_start(0)).pack(side=tk.LEFT)
        tk.Button(row, text="Test CAM 1", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=ACCENT, fg="white", padx=16, pady=7,
                  command=lambda: self.cam_start(1)).pack(side=tk.LEFT, padx=8)
        tk.Button(row, text="Stop", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=STATE_IDLE, fg=INK, padx=16, pady=7,
                  command=self.cam_stop).pack(side=tk.LEFT)

        # These are packed BEFORE the video box on purpose. pack fills the
        # cavity in call order, so a fixed 480px box packed first consumed
        # the whole panel and left the checkbox and Back button unmapped.
        # Reserving them from the bottom first guarantees they are visible
        # at any window size; the video box then takes whatever is left.
        self._back_button(self.camFrame, self.cam_back, side=tk.BOTTOM)
        tk.Checkbutton(self.camFrame, text="Yes - I saw live video",
                       variable=self.cvar, font=F_BODY, bg=PANEL_BG, fg=INK,
                       activebackground=PANEL_BG,
                       selectcolor=PANEL_BG).pack(side=tk.BOTTOM, anchor="w",
                                                  padx=20, pady=6)
        self.cam_status_label = tk.Label(self.camFrame, text="Camera idle.",
                                         font=F_BODYB, bg=PANEL_BG,
                                         fg=INK_SOFT)
        self.cam_status_label.pack(side=tk.BOTTOM, anchor="w", padx=22)

        self.cam_box = tk.Frame(self.camFrame, bg=TRACK, width=CAM_W,
                                height=CAM_H, highlightbackground=BORDER,
                                highlightthickness=1)
        self.cam_box.pack(anchor="w", padx=22, pady=12, fill=tk.Y,
                          expand=True)
        self.cam_box.pack_propagate(False)
        self.cam_view = tk.Label(self.cam_box, bg=TRACK, fg=INK_SOFT,
                                 font=F_BODY, text="")
        self.cam_view.pack(fill=tk.BOTH, expand=True)
        self._cam_idle_view()

    def _load_usb_diagram(self):
        """Tk 8.6 reads PNG natively, so the port diagram needs no Pillow.
        The file is looked for next to the script first so the GUI still
        finds it when launched from a different working directory."""
        here = os.path.dirname(os.path.abspath(__file__))
        for path in (os.path.join(here, USB_DIAGRAM_FILE), USB_DIAGRAM_FILE):
            try:
                if os.path.exists(path):
                    return tk.PhotoImage(file=path).subsample(3, 3)
            except Exception:
                continue
        return None

    def _build_usb_frame(self):
        self._panel_head(self.usbFrame, *INTRO_TEXTS["USB"])

        row = tk.Frame(self.usbFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22)
        self.usb_start_btn = tk.Button(row, text="Start Scan", font=F_BODYB,
                                       relief=tk.FLAT, bd=0, cursor="hand2",
                                       bg=ACCENT, fg="white", padx=18, pady=7,
                                       command=self.usb_start)
        self.usb_start_btn.pack(side=tk.LEFT)
        tk.Button(row, text="Stop", font=F_BODYB, relief=tk.FLAT, bd=0,
                  cursor="hand2", bg=STATE_IDLE, fg=INK, padx=18, pady=7,
                  command=self.usb_stop).pack(side=tk.LEFT, padx=8)
        tk.Button(row, text="Reset seen ports", font=F_TINY, relief=tk.FLAT,
                  bd=0, cursor="hand2", bg=PANEL_BG, fg=ACCENT,
                  command=self.usb_reset_seen).pack(side=tk.LEFT, padx=(8, 0))

        self.usb_running_label = tk.Label(self.usbFrame, text="", font=F_BODYB,
                                          bg=PANEL_BG, fg=INK_SOFT,
                                          justify=tk.LEFT, wraplength=800)
        self.usb_running_label.pack(anchor="w", padx=22, pady=(10, 0))

        body = tk.Frame(self.usbFrame, bg=PANEL_BG)
        body.pack(anchor="w", padx=22, pady=10, fill=tk.X)

        self.usb_photo = self._load_usb_diagram()
        pic = tk.Frame(body, bg=TRACK, highlightbackground=BORDER,
                       highlightthickness=1)
        pic.grid(row=0, column=0, sticky="nw")
        if self.usb_photo is not None:
            tk.Label(pic, image=self.usb_photo, bg=TRACK,
                     bd=0).pack(padx=6, pady=6)
        else:
            tk.Label(pic, bg=TRACK, fg=INK_SOFT, font=F_BODY, justify=tk.LEFT,
                     text=(f"{USB_DIAGRAM_FILE} not found.\n\n"
                           "Put it in the same folder as this script to see "
                           "the port diagram.\n\n"
                           "Looking at the rear ports:\n"
                           "  USB 1 top left     USB 2 top right\n"
                           "  USB 3 bottom left  USB 4 bottom right"),
                     padx=18, pady=18).pack()

        grid = tk.Frame(body, bg=PANEL_BG)
        grid.grid(row=0, column=1, sticky="nw", padx=(24, 0))
        self.usb_rows = {}
        for i, (label, node) in enumerate(USB_PORT_MAP):
            cell = tk.Frame(grid, bg=PANEL_BG)
            cell.grid(row=i, column=0, sticky="w", pady=6)
            dot = tk.Canvas(cell, width=22, height=22, bg=PANEL_BG,
                            highlightthickness=0)
            dot.pack(side=tk.LEFT)
            led = dot.create_oval(3, 3, 19, 19, fill=STATE_IDLE,
                                  outline=BORDER)
            tk.Label(cell, text=label, font=F_BODYB, bg=PANEL_BG, fg=INK,
                     width=7, anchor="w").pack(side=tk.LEFT, padx=(8, 0))
            live = tk.Label(cell, text="idle", font=F_BODY, bg=PANEL_BG,
                            fg=INK_SOFT, width=11, anchor="w")
            live.pack(side=tk.LEFT)
            seen = tk.Label(cell, text="not seen yet", font=F_TINY,
                            bg=PANEL_BG, fg=INK_SOFT, width=14, anchor="w")
            seen.pack(side=tk.LEFT)
            tk.Label(cell, text=node, font=F_TINY, bg=PANEL_BG,
                     fg=INK_SOFT).pack(side=tk.LEFT, padx=(6, 0))
            self.usb_rows[label] = (dot, led, live, seen)

        self._back_button(self.usbFrame, self.usb_back)

    def _build_wifi_frame(self):
        self._panel_head(self.wifiFrame, *INTRO_TEXTS["WIFI"])

        row = tk.Frame(self.wifiFrame, bg=PANEL_BG)
        row.pack(anchor="w", padx=22)
        self.wifi_run_btn = tk.Button(row, text="Run WiFi Check",
                                      font=F_BODYB, relief=tk.FLAT, bd=0,
                                      cursor="hand2", bg=ACCENT, fg="white",
                                      padx=18, pady=7,
                                      command=self.wifi_run)
        self.wifi_run_btn.pack(side=tk.LEFT)
        tk.Button(row, text="Open YouTube on Jetson display", font=F_TINY,
                  relief=tk.FLAT, bd=0, cursor="hand2", bg=PANEL_BG,
                  fg=ACCENT, command=self.wifi_open_browser).pack(
                      side=tk.LEFT, padx=(12, 0))

        self.wifi_running_label = tk.Label(self.wifiFrame, text="",
                                           font=F_BODYB, bg=PANEL_BG,
                                           fg=INK_SOFT, justify=tk.LEFT,
                                           wraplength=800)
        self.wifi_running_label.pack(anchor="w", padx=22, pady=(10, 0))

        box = tk.Frame(self.wifiFrame, bg=PANEL_BG)
        box.pack(anchor="w", padx=22, pady=12)
        self.wifi_fields = {}
        for i, (key, label) in enumerate([
                ("DEV", "Interface"), ("STATE", "State"), ("SSID", "Network"),
                ("IP", "Address"), ("SIGNAL", "Signal"), ("RATE", "Bitrate"),
                ("PING", "Ping 8.8.8.8"), ("DNS", "DNS lookup")]):
            tk.Label(box, text=label, font=F_BODY, bg=PANEL_BG, fg=INK_SOFT,
                     width=14, anchor="w").grid(row=i, column=0, sticky="w",
                                                pady=2)
            val = tk.Label(box, text="-", font=F_MONO, bg=PANEL_BG, fg=INK,
                           anchor="w")
            val.grid(row=i, column=1, sticky="w", padx=(10, 0))
            self.wifi_fields[key] = val

        self._back_button(self.wifiFrame, self.wifi_back)

    def _show_frame(self, frame):
        frame.tkraise()

    def _set_pill(self, name, state):
        if name not in self.pills:
            return
        cell, inner, dot, lab = self.pills[name]
        sub = self.pill_subs[name]
        colors = {
            "idle":    (STATE_IDLE, STATE_IDLE_FG, "Not run"),
            "running": (STATE_RUN, "#ffffff", "Running"),
            "pass":    (STATE_PASS, "#ffffff", "Pass"),
            "fail":    (STATE_FAIL, "#ffffff", "Fail"),
        }
        bg, fg, text = colors.get(state, colors["idle"])
        for w in (cell, inner):
            w.config(bg=bg)
        for w in (dot, lab, sub):
            w.config(bg=bg, fg=fg)
        sub.config(text=text)
        self.results[name] = state
        passed = sum(1 for v in self.results.values() if v == "pass")
        self.summary_label.config(
            text=f"{passed} / {len(TESTS)} passed",
            fg=STATE_PASS if passed == len(TESTS) else INK_SOFT)

    def _set_button_state(self, name, state):
        if name not in self.buttons:
            return
        b = self.buttons[name]
        self.btn_states[name] = state
        if state in ("disabled", "na"):
            b.config(bg=STATE_IDLE, fg=STATE_IDLE_FG, state=tk.DISABLED)
        elif state == "ready":
            b.config(bg=ACCENT, fg="white", activebackground=ACCENT_HI,
                     state=tk.NORMAL)
        elif state == "running":
            b.config(bg=STATE_RUN, fg="white", state=tk.DISABLED)
        elif state == "pass":
            b.config(bg=STATE_PASS, fg="white", activebackground=STATE_PASS,
                     state=tk.NORMAL)
        elif state == "fail":
            b.config(bg=STATE_FAIL, fg="white", activebackground=STATE_FAIL,
                     state=tk.NORMAL)

    def _set_test_buttons(self, state):
        for name in LIVE_TESTS:
            b = self.buttons.get(name)
            if b is None:
                continue
            b.config(state=tk.DISABLED if state == tk.DISABLED else tk.NORMAL)

    def add_log(self, message, kind="info"):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n", kind)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    RESULT_WORD = {"pass": "PASS", "fail": "FAIL",
                   "running": "INCOMPLETE", "idle": "NOT RUN"}

    def _result_word(self, name):
        return self.RESULT_WORD.get(self.results.get(name, "idle"), "NOT RUN")

    def _log_export_text(self):
        out = []
        out.append("Jetson Nano Interface Test Bench - session log")
        out.append("=" * 60)
        out.append("Generated   : %s" % datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        out.append("Jetson      : %s@%s" % (JETSON_USERNAME, JETSON_IP))
        out.append("Remote path : %s" % REMOTE_TEST_DIR)
        out.append("Connection  : %s" % ("connected" if self.client
                                         else "not connected"))
        out.append("")
        out.append("RESULTS")
        out.append("-" * 60)
        for name in TESTS:
            out.append("  %-9s %s" % (name, self._result_word(name)))
        passed = sum(1 for v in self.results.values() if v == "pass")
        out.append("")
        out.append("  %d of %d interfaces passed" % (passed, len(TESTS)))
        out.append("")
        out.append("LOG")
        out.append("-" * 60)
        out.append(self.log_text.get("1.0", tk.END).rstrip())
        out.append("")
        return "\n".join(out)

    def _write_log_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["section", "timestamp", "test", "detail"])
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            w.writerow(["session", stamp, "jetson",
                        "%s@%s" % (JETSON_USERNAME, JETSON_IP)])
            for name in TESTS:
                w.writerow(["result", stamp, name, self._result_word(name)])
            for line in self.log_text.get("1.0", tk.END).splitlines():
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("[") and "]" in line:
                    ts, msg = line[1:].split("]", 1)
                    w.writerow(["log", ts.strip(), "", msg.strip()])
                else:
                    w.writerow(["log", "", "", line])

    def download_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"nano_test_log_{datetime.now():%Y%m%d_%H%M%S}",
            filetypes=[("Text file", "*.txt"), ("CSV file", "*.csv"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                self._write_log_csv(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._log_export_text())
            self.add_log(f"Log saved to {path}", "pass")
        except Exception as e:
            self.add_log(f"Could not save log: {e}", "fail")

    def _log_failure_detail(self, output, max_lines=25):
        if not output:
            self.add_log("  (no output returned)", "fail")
            return
        for line in output.splitlines()[:max_lines]:
            if "[sudo] password for" in line:
                continue
            self.add_log("  " + line, "fail")

    def log_local_result(self, test_name, passed, output):
        try:
            new = not os.path.exists(CSV_FILE)
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["timestamp", "test", "result", "output"])
                w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            test_name, "PASS" if passed else "FAIL",
                            " | ".join(output.splitlines())[:1500]])
        except Exception as e:
            print(f"CSV write failed: {e}")

    def _connect_ssh_async(self):
        threading.Thread(target=self._ssh_connect_worker, daemon=True).start()

    def _ssh_connect_worker(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(JETSON_IP, username=JETSON_USERNAME,
                           password=JETSON_PASSWORD, timeout=10)
        except Exception as e:
            self.root.after(0, self._on_ssh_failed, str(e))
            return
        self.root.after(0, self._on_ssh_connected, client)

    def reconnect(self):
        try:
            if self.client is not None:
                self.client.close()
        except Exception:
            pass
        self.client = None
        self.conn_label.config(text="Reconnecting...", fg=STATE_RUN)
        self.add_log("Reconnecting to the Jetson...")
        self._connect_ssh_async()

    def disconnect(self):
        if self.client is None:
            self.add_log("Already disconnected from the Jetson.")
            return
        self._cam_teardown()
        self._i2s_in_teardown()
        self._usb_teardown()
        self._cam_idle_view()
        try:
            self.client.exec_command('pkill -f "[c]amtest.py"; '
                                     'pkill -f "[I]2S_live_input.py"; '
                                     'pkill -f "[n]anogui_usb_scan"; '
                                     'pkill -x arecord')
        except Exception:
            pass
        try:
            self.client.close()
        except Exception:
            pass
        self.client = None
        self.conn_label.config(text="Disconnected", fg=INK_SOFT)
        self.add_log("Disconnected from the Jetson.")

    def _on_ssh_connected(self, client):
        self.client = client
        self.conn_label.config(text=f"Connected to {JETSON_IP}", fg=STATE_PASS)
        self.add_log(f"Connected to {JETSON_IP}. Each test script configures "
                     f"its own pins when it runs.", "pass")

    def _on_ssh_failed(self, err):
        self.conn_label.config(text="SSH connection failed", fg=STATE_FAIL)
        self.add_log(f"SSH connection failed: {err}", "fail")
        self.add_log("Tests can still be run without a connection - "
                     "they will report FAIL.")
        messagebox.showerror("SSH Connection Failed",
                             f"Could not reach the Jetson at {JETSON_IP}.\n\n"
                             f"{err}")

    def _require_client(self, name):
        """Refuses to start a test with no SSH session, rather than letting
        it run and marking the interface FAIL for a dropped link."""
        if self.client is not None:
            return True
        self.add_log(f"{name} test not started: no SSH session. Press "
                     f"Reconnect in the top right.", "fail")
        self._set_pill(name, "idle")
        self._set_button_state(name, "ready")
        return False

    def run_remote_test(self, script_name, extra_args="", test_name=None,
                        use_sudo=False):
        if self.client is None:
            return "SSH ERROR: not connected to the Jetson"
        cmd = f"cd {REMOTE_TEST_DIR} && python3 {script_name} {extra_args}"
        cmd = cmd.strip()
        if use_sudo:
            cmd = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                   f"sudo -S -p '' sh -c {shlex.quote(cmd)}")
        return self._exec_blocking(cmd)

    def run_remote_script(self, script_name, use_sudo=False):
        if self.client is None:
            return "SSH ERROR: not connected to the Jetson"
        cmd = (f"cd {REMOTE_TEST_DIR} && chmod +x {script_name} && "
               f"./{script_name}")
        if use_sudo:
            cmd = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                   f"sudo -S -p '' sh -c {shlex.quote(cmd)}")
        return self._exec_blocking(cmd)

    def _exec_blocking(self, cmd):
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            out = stdout.read().decode(errors="ignore").strip()
            err = stderr.read().decode(errors="ignore").strip()
        except Exception as e:
            return f"SSH ERROR: {e}"
        err = "\n".join(l for l in err.splitlines()
                        if "[sudo] password for" not in l).strip()
        if err:
            return (out + "\n[stderr]: " + err).strip()
        return out

    def _open_stream(self, command, use_sudo=False):
        if self.client is None:
            raise RuntimeError("not connected to the Jetson")
        if use_sudo:
            command = (f"echo {shlex.quote(JETSON_PASSWORD)} | "
                       f"sudo -S -p '' sh -c {shlex.quote(command)}")
        transport = self.client.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)
        return channel

    def _read_lines(self, channel, alive):
        buf = b""
        while alive():
            got = False
            if channel.recv_ready():
                chunk = channel.recv(65536)
                if not chunk:
                    break
                buf += chunk
                got = True
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    yield line.decode(errors="ignore").rstrip("\r")
            if channel.recv_stderr_ready():
                err = channel.recv_stderr(65536).decode(errors="ignore")
                got = True
                for l in err.splitlines():
                    if "[sudo] password for" in l or not l.strip():
                        continue
                    yield "[stderr] " + l.rstrip("\r")
            if not got:
                if channel.exit_status_ready() and not channel.recv_ready():
                    break
                time.sleep(0.02)
        if buf:
            yield buf.decode(errors="ignore").rstrip("\r")

    def _show_intro(self, name, proceed):
        title, wiring = INTRO_TEXTS[name]
        self.intro_title.config(text=title)
        self.intro_text.config(text=wiring)
        self.intro_continue_btn.config(command=proceed)
        self._show_frame(self.introFrame)

    def intro_back(self):
        self._show_frame(self.logFrame)

    def gpio_intro(self):
        self._show_intro("GPIO", self.gpio_test)

    def pwm_intro(self):
        self._show_intro("PWM", self.pwm_test)

    def uart_intro(self):
        self._show_intro("UART", self.uart_test)

    def i2s_in_intro(self):
        self._show_intro("I2S IN", self.i2s_in_test)

    def i2s_out_intro(self):
        self._show_intro("I2S OUT", self.i2s_out_test)

    def spi_intro(self):
        self._show_intro("SPI", self.spi_test)

    def i2c_intro(self):
        self._show_intro("I2C", self.i2c_test)

    def cam_intro(self):
        self._show_intro("CAMERA", self.cam_test)

    def usb_intro(self):
        self._show_intro("USB", self.usb_test)

    def wifi_intro(self):
        self._show_intro("WIFI", self.wifi_test)

    def gpio_test(self):
        if not self._require_client("GPIO"):
            return
        self.gpio_auto = None
        self.gpio_pin_auto = {}
        for w in self.gpio_pin_box.winfo_children():
            w.destroy()
        self.gpio_vars = {}
        self.gpio_rows = {}
        self._set_button_state("GPIO", "running")
        self._set_pill("GPIO", "running")
        self.gpio_running_label.config(text="Running on Jetson...",
                                       fg=STATE_RUN)
        self.gpio_hint_label.config(text="")
        self._show_frame(self.gpioFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("GPIO test starting...")
        threading.Thread(target=self._gpio_worker, daemon=True).start()

    def _gpio_worker(self):
        collected = []
        try:
            cmd = f"cd {REMOTE_TEST_DIR} && python3 -u gpiotest.py"
            channel = self._open_stream(cmd, use_sudo=True)
            for line in self._read_lines(channel, lambda: True):
                collected.append(line)
                self.root.after(0, self._gpio_line, line)
            try:
                channel.close()
            except Exception:
                pass
        except Exception as e:
            collected.append(f"SSH ERROR: {e}")
        self.root.after(0, self._gpio_done, "\n".join(collected))

    def _gpio_line(self, line):
        line = line.strip()
        if line.startswith(GPIO_LIST_PREFIX):
            pins = []
            for part in line.split(":", 1)[1].split(","):
                part = part.strip()
                if part.isdigit():
                    pins.append(int(part))
            self._gpio_build_rows(pins)
            self.gpio_hint_label.config(
                text="Watch the highlighted pin. Every box starts checked - "
                     "uncheck only the pins whose LED did not blink.")
            return

        if line.startswith(GPIO_NOW_PREFIX):
            active = line.split(":", 1)[1].strip()
            if not active.isdigit():
                return
            active = int(active)
            for pin, (box, state) in self.gpio_rows.items():
                if pin == active:
                    box.config(fg=ACCENT, font=F_BODYB)
                    state.config(text="driving", fg=ACCENT)
                else:
                    box.config(fg=INK, font=F_BODY)
                    if state.cget("text") == "driving":
                        state.config(text="done", fg=INK_SOFT)
            return

        if line.startswith(GPIO_PINS_PREFIX):
            for entry in line.split(":", 1)[1].strip().split(","):
                if "=" not in entry:
                    continue
                pin, res = entry.split("=", 1)
                if not pin.strip().isdigit():
                    continue
                pin = int(pin.strip())
                res = res.strip().upper()
                self.gpio_pin_auto[pin] = res
                if pin not in self.gpio_rows:
                    continue
                box, state = self.gpio_rows[pin]
                box.config(fg=INK, font=F_BODY)
                if res == "PASS":
                    state.config(text="driven", fg=STATE_PASS)
                else:
                    # The script itself errored on this pin, so there is
                    # nothing for the operator to confirm.
                    state.config(text="FAIL", fg=STATE_FAIL)
                    self.gpio_vars[pin].set(0)
                    box.config(state=tk.DISABLED)

    def _gpio_done(self, output):
        auto = any(l.strip() == GPIO_PASS_LINE for l in output.splitlines())
        self.gpio_auto = auto
        if auto:
            self.gpio_running_label.config(
                text="Every pin was driven without error. Uncheck any pin "
                     "whose LED stayed dark, then go back.", fg=STATE_PASS)
        else:
            self.gpio_running_label.config(
                text="Script reported a failure - see the Test Log.",
                fg=STATE_FAIL)
            self._log_failure_detail(output)
        self.add_log(f"GPIO script result: {'PASS' if auto else 'FAIL'}",
                     "pass" if auto else "fail")
        self._set_test_buttons(tk.NORMAL)

    def gpio_back(self):
        if self.gpio_auto is None:
            self.add_log("GPIO test: INCOMPLETE (left before finishing).")
            self._set_pill("GPIO", "idle")
            self._set_button_state("GPIO", "ready")
            self._show_frame(self.logFrame)
            return

        auto_failed = sorted(p for p, r in self.gpio_pin_auto.items()
                             if r != "PASS")
        unconfirmed = sorted(p for p, v in self.gpio_vars.items()
                             if v.get() != 1 and p not in auto_failed)
        passed = self.gpio_auto and not auto_failed and not unconfirmed

        detail = []
        if auto_failed:
            detail.append("script failed on " +
                          ",".join(str(p) for p in auto_failed))
        if unconfirmed:
            detail.append("LED not seen on " +
                          ",".join(str(p) for p in unconfirmed))
        if not self.gpio_rows:
            summary = "script did not report any pin results"
        elif detail:
            summary = "; ".join(detail)
        else:
            summary = f"all {len(self.gpio_vars)} pins driven and confirmed"

        if passed:
            self.add_log(f"GPIO test: PASS ({summary}).", "pass")
        else:
            self.add_log(f"GPIO test: FAIL ({summary}).", "fail")
        self.log_local_result("GPIO", passed, summary)
        self._set_pill("GPIO", "pass" if passed else "fail")
        self._set_button_state("GPIO", "pass" if passed else "fail")
        self._show_frame(self.logFrame)

    def pwm_reset_confirmations(self):
        for var in self.pwm_vars.values():
            var.set(0)
        self.add_log("PWM confirmations cleared - both pins need watching "
                     "again.")
        self._pwm_refresh_rows()

    def _pwm_refresh_rows(self):
        for pin, (chk, state) in self.pwm_rows.items():
            if self.pwm_vars[pin].get() == 1:
                state.config(text="confirmed", fg=STATE_PASS)
            elif self.pwm_auto is None:
                state.config(text="not run", fg=INK_SOFT)
            elif pin in self.pwm_driven:
                state.config(text="awaiting watch", fg=STATE_RUN)
            else:
                state.config(text="not driven", fg=STATE_FAIL)

    def pwm_test(self):
        if not self._require_client("PWM"):
            return
        # Ticks are intentionally left alone here - see self.pwm_vars.
        self.pwm_auto = None
        self.pwm_driven = []
        self._set_button_state("PWM", "running")
        self._set_pill("PWM", "running")
        self.pwm_running_label.config(text="Running on Jetson...", fg=STATE_RUN)
        already = [p for p in PWM_PINS if self.pwm_vars[p].get() == 1]
        todo = [p for p in PWM_PINS if p not in already]
        if already and todo:
            self.pwm_hint_label.config(
                text=f"Pin {already[0]} is already confirmed. Move the servo "
                     f"signal lead to pin {todo[0]} for this run.")
        else:
            self.pwm_hint_label.config(
                text="Both pins are driven with the same sweep. Watch "
                     "whichever pin the servo is wired to.")
        self._pwm_refresh_rows()
        self._show_frame(self.pwmFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("PWM test starting on pins "
                     + ", ".join(str(p) for p in PWM_PINS) + "...")
        threading.Thread(target=self._pwm_worker, daemon=True).start()

    def _pwm_worker(self):
        # "both" is passed explicitly so the GUI never depends on whatever
        # DEFAULT_PINS happens to be set to in pwmtest.py.
        output = self.run_remote_test("pwmtest.py", extra_args="both",
                                      test_name="PWM", use_sudo=True)
        self.root.after(0, self._pwm_done, output)

    def _pwm_parse_pins(self, output):
        pins = []
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith(PWM_PINS_PREFIX):
                continue
            body = line[len(PWM_PINS_PREFIX):].strip()
            for token in body.replace(",", " ").split():
                try:
                    pins.append(int(token))
                except ValueError:
                    continue
        return pins

    def _pwm_done(self, output):
        auto = any(l.strip() == PWM_PASS_LINE for l in output.splitlines())
        self.pwm_auto = auto
        self.pwm_driven = self._pwm_parse_pins(output)
        if auto:
            driven = ", ".join(str(p) for p in self.pwm_driven) or "unknown"
            self.pwm_running_label.config(
                text=f"Script drove pins {driven} without error. Tick the "
                     f"pin the servo was wired to.", fg=STATE_PASS)
            missing = [p for p in PWM_PINS if p not in self.pwm_driven]
            if missing:
                self.add_log("PWM script only reported pins "
                             + ", ".join(str(p) for p in self.pwm_driven)
                             + " - check that pwmtest.py accepts the 'both' "
                               "argument.", "fail")
        else:
            self.pwm_running_label.config(
                text="Script reported a failure - see the Test Log.",
                fg=STATE_FAIL)
            self._log_failure_detail(output)
        self.add_log(f"PWM script result: {'PASS' if auto else 'FAIL'}",
                     "pass" if auto else "fail")
        self._pwm_refresh_rows()
        self._set_test_buttons(tk.NORMAL)

    def pwm_back(self):
        confirmed = [p for p in PWM_PINS if self.pwm_vars[p].get() == 1]
        missing = [p for p in PWM_PINS if p not in confirmed]

        if self.pwm_auto is None:
            if confirmed:
                self.add_log("PWM test: INCOMPLETE (left before running; "
                             "pin " + ", ".join(str(p) for p in confirmed)
                             + " still confirmed from an earlier run).")
            else:
                self.add_log("PWM test: INCOMPLETE (left before finishing).")
            self._set_pill("PWM", "idle")
            self._set_button_state("PWM", "ready")
            self._show_frame(self.logFrame)
            return

        if not self.pwm_auto:
            self.add_log("PWM test: FAIL (script reported failure).", "fail")
            self.log_local_result("PWM", False, "script fail")
            self._set_pill("PWM", "fail")
            self._set_button_state("PWM", "fail")
            self._show_frame(self.logFrame)
            return

        for pin in PWM_PINS:
            if pin in confirmed:
                self.add_log(f"  PWM pin {pin}: CONFIRMED (servo swept)",
                             "pass")
            else:
                self.add_log(f"  PWM pin {pin}: NOT CONFIRMED (not yet "
                             f"watched)")

        if not missing:
            summary = ("signal generated and servo motion confirmed on pins "
                       + ", ".join(str(p) for p in PWM_PINS))
            self.add_log(f"PWM test: PASS ({summary}).", "pass")
            self.log_local_result("PWM", True, summary)
            self._set_pill("PWM", "pass")
            self._set_button_state("PWM", "pass")
        else:
            # An unticked pin means "not watched yet", not "broken", so the
            # interface is left re-runnable instead of being marked failed.
            detail = ("pin " + ", ".join(str(p) for p in missing)
                      + " still needs the servo moved to it")
            self.add_log(f"PWM test: INCOMPLETE ({detail}).")
            self._set_pill("PWM", "idle")
            self._set_button_state("PWM", "ready")
        self._show_frame(self.logFrame)

    def uart_test(self):
        self.uart_running_label.config(
            text="Type a string and press Send.", fg=INK_SOFT)
        self._show_frame(self.uartFrame)
        self.uart_entry.focus_set()

    def uart_send(self):
        if not self._require_client("UART"):
            self.uart_running_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right.", fg=STATE_FAIL)
            return
        message = self.uart_msg.get()
        if not message.strip():
            self.uart_running_label.config(text="Enter a string first.",
                                           fg=STATE_FAIL)
            return
        self.uart_send_btn.config(state=tk.DISABLED)
        self._set_button_state("UART", "running")
        self._set_pill("UART", "running")
        self.uart_sent_label.config(text=f"Sent:  {message}", fg=INK)
        self.uart_recv_label.config(text="Received:  waiting...", fg=INK_SOFT)
        self.uart_running_label.config(text="Sending over /dev/ttyTHS1...",
                                       fg=STATE_RUN)
        self.add_log(f"UART send: {message}")
        threading.Thread(target=self._uart_worker, args=(message,),
                         daemon=True).start()

    def _uart_worker(self, message):
        output = self.run_remote_test("uarttest.py", shlex.quote(message),
                                      use_sudo=True)
        self.root.after(0, self._uart_done, message, output)

    def _uart_done(self, message, output):
        received = ""
        for line in output.splitlines():
            if line.startswith("RECEIVED:"):
                received = line.split(":", 1)[1].strip()
        auto = any(l.strip() == UART_PASS_LINE for l in output.splitlines())
        self.uart_recv_label.config(
            text=f"Received:  {received if received else '(nothing)'}",
            fg=STATE_PASS if auto else STATE_FAIL)
        if auto:
            self.uart_running_label.config(
                text="PASS - the string came back unchanged.", fg=STATE_PASS)
            self.add_log("UART test: PASS", "pass")
            self._set_pill("UART", "pass")
            self._set_button_state("UART", "pass")
        else:
            self.uart_running_label.config(
                text="FAIL - see the Test Log.", fg=STATE_FAIL)
            self.add_log("UART test: FAIL", "fail")
            self._log_failure_detail(output)
            self._set_pill("UART", "fail")
            self._set_button_state("UART", "fail")
        self.log_local_result("UART", auto, output)
        self.uart_send_btn.config(state=tk.NORMAL)

    def uart_back(self):
        self._show_frame(self.logFrame)

    def _i2s_list_clear(self):
        self.i2s_in_list.config(state=tk.NORMAL)
        self.i2s_in_list.delete("1.0", tk.END)
        self.i2s_in_list.config(state=tk.DISABLED)
        self.i2s_in_blocks = 0

    def _i2s_list_add(self, text, tag="quiet"):
        self.i2s_in_list.config(state=tk.NORMAL)
        self.i2s_in_list.insert(tk.END, text + "\n", tag)
        extra = int(self.i2s_in_list.index("end-1c").split(".")[0]) - LIST_ROWS
        if extra > 0:
            self.i2s_in_list.delete("1.0", "%d.0" % (extra + 1))
        self.i2s_in_list.see(tk.END)
        self.i2s_in_list.config(state=tk.DISABLED)

    def i2s_in_test(self):
        self.ivar_in.set(0)
        self.i2s_in_auto = None
        self.i2s_in_error = None
        self.i2s_in_threshold = None
        self.i2s_in_over = False
        self._i2s_list_clear()
        self.i2s_in_armed_label.config(text="")
        self.i2s_in_running_label.config(
            text="Press Start Monitor.", fg=INK_SOFT)
        self.i2s_in_read_label.config(
            text="peak  -        rms  -        freq  -        threshold  -")
        self._show_frame(self.i2sInFrame)

    def i2s_in_start(self):
        if not self._require_client("I2S IN"):
            self.i2s_in_running_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right, then start the monitor again.", fg=STATE_FAIL)
            return
        self._i2s_in_teardown()
        self.i2s_in_gen += 1
        gen = self.i2s_in_gen
        self.i2s_in_auto = None
        self.i2s_in_error = None
        self.i2s_in_threshold = None
        self.i2s_in_over = False
        self._i2s_list_clear()
        self.i2s_in_armed_label.config(text="")
        self._set_pill("I2S IN", "running")
        self._set_button_state("I2S IN", "running")
        self.i2s_in_running_label.config(text="Starting monitor...",
                                         fg=STATE_RUN)
        self.add_log("I2S input live monitor starting...")
        threading.Thread(target=self._i2s_in_worker, args=(gen,),
                         daemon=True).start()

    def _i2s_in_teardown(self):
        self.i2s_in_gen += 1
        ch = self.i2s_in_channel
        self.i2s_in_channel = None
        if ch is not None:
            try:
                ch.close()
            except Exception:
                pass
        if self.client is not None:
            try:
                self.client.exec_command(
                    'pkill -f "[I]2S_live_input.py"; pkill -x arecord')
            except Exception:
                pass
        return ch is not None

    def _i2s_in_worker(self, gen):
        try:
            try:
                self.client.exec_command(
                    'pkill -f "[I]2S_live_input.py"; pkill -x arecord')
                time.sleep(0.4)
            except Exception:
                pass
            if gen != self.i2s_in_gen:
                return
            cmd = f"cd {REMOTE_TEST_DIR} && python3 -u I2S_live_input.py"
            channel = self._open_stream(cmd, use_sudo=True)
            if gen != self.i2s_in_gen:
                try:
                    channel.close()
                except Exception:
                    pass
                return
            self.i2s_in_channel = channel
            for line in self._read_lines(channel,
                                         lambda: gen == self.i2s_in_gen):
                self.root.after(0, self._i2s_in_line, line, gen)
            try:
                channel.close()
            except Exception:
                pass
            if gen == self.i2s_in_gen:
                self.root.after(0, self._i2s_in_ended, gen)
        except Exception as e:
            if gen == self.i2s_in_gen:
                self.root.after(0, self._i2s_in_error, str(e), gen)

    def _i2s_in_line(self, line, gen):
        if gen != self.i2s_in_gen:
            return
        line = line.strip()
        if not line:
            return

        if line.startswith("I2S LEVEL"):
            vals = {}
            for token in line.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    try:
                        vals[k] = float(v)
                    except ValueError:
                        pass
            peak = vals.get("peak", 0.0)
            rms = vals.get("rms", 0.0)
            freq = vals.get("freq", 0.0)
            over = bool(vals.get("over", 0.0))
            thr = self.i2s_in_threshold

            self.i2s_in_blocks += 1
            elapsed = self.i2s_in_blocks * BLOCK_SEC
            if thr is None:
                status = "calibrating"
            elif over:
                status = "SOUND DETECTED"
            else:
                status = "no sound detected"
            self._i2s_list_add(
                "%7.1fs %9.1f %9.1f %7.0f Hz   %s"
                % (elapsed, peak, rms, freq, status),
                "hit" if over else "quiet")

            self.i2s_in_read_label.config(
                text=("peak %8.1f    rms %8.1f    freq %6.0f Hz    "
                      "threshold %s" % (peak, rms, freq,
                                        ("%.1f" % thr) if thr else "-")),
                fg=STATE_PASS if over else INK_SOFT)
            if thr is not None and over != self.i2s_in_over:
                self.i2s_in_over = over
                if over:
                    self.i2s_in_running_label.config(text="SOUND DETECTED",
                                                     fg=STATE_PASS)
                else:
                    self.i2s_in_running_label.config(
                        text="Listening - no sound detected", fg=INK_SOFT)
            return

        if line.startswith("THRESHOLD"):
            for token in line.split():
                if token.startswith("peak="):
                    try:
                        self.i2s_in_threshold = float(token.split("=", 1)[1])
                    except ValueError:
                        pass
            if self.i2s_in_threshold:
                self._i2s_list_add(
                    "         threshold set at %.1f - make noise now"
                    % self.i2s_in_threshold, "note")
            self.add_log(f"I2S input: {line}")
            return

        if line.startswith("MONITOR: make noise"):
            self.i2s_in_running_label.config(
                text="Listening - no sound detected", fg=INK_SOFT)
            self.add_log("I2S input: threshold set, listening for sound.")
            return

        if line.startswith("MONITOR: measuring"):
            self.i2s_in_running_label.config(
                text="Measuring the noise floor - stay quiet.", fg=STATE_RUN)
            return

        if line.startswith("MONITOR: settling"):
            self.i2s_in_running_label.config(
                text="Settling the capture stream...", fg=STATE_RUN)
            return

        if line == I2S_IN_DONE_LINE:
            self.i2s_in_auto = True
            self.i2s_in_armed_label.config(
                text="Sound has crossed the threshold during this run - "
                     "the test can pass.", fg=STATE_PASS)
            self.add_log("I2S input: sound detected above threshold.", "pass")
            return

        if line.startswith("I2S INPUT TEST: FAIL"):
            self.i2s_in_auto = False
            self.i2s_in_running_label.config(
                text="Monitor failed - see the Test Log.", fg=STATE_FAIL)
            self.add_log("I2S input: script reported FAIL.", "fail")
            return

        self.add_log(f"I2S input: {line}")

    def _i2s_in_ended(self, gen):
        if gen != self.i2s_in_gen:
            return
        self.i2s_in_channel = None
        if self.i2s_in_auto is None:
            self.i2s_in_error = ("monitor ended before any sound was "
                                 "detected")
            self.i2s_in_running_label.config(
                text="Monitor stopped before any sound was detected.",
                fg=STATE_FAIL)
            self._set_pill("I2S IN", "fail")
            self._set_button_state("I2S IN", "fail")

    def _i2s_in_error(self, msg, gen):
        if gen != self.i2s_in_gen:
            return
        self.i2s_in_channel = None
        self.i2s_in_error = msg
        self.i2s_in_running_label.config(text="Monitor error - see log.",
                                         fg=STATE_FAIL)
        self.add_log(f"I2S input error: {msg}", "fail")
        self._set_pill("I2S IN", "fail")
        self._set_button_state("I2S IN", "fail")

    def i2s_in_stop(self):
        was_live = self._i2s_in_teardown()
        self.i2s_in_over = False
        if was_live:
            self.add_log("I2S input monitor stopped.")
            if self.i2s_in_auto:
                self.i2s_in_running_label.config(
                    text="Monitor stopped - sound was detected.",
                    fg=STATE_PASS)
            else:
                self.i2s_in_running_label.config(text="Monitor stopped.",
                                                 fg=INK_SOFT)

    def i2s_in_back(self):
        self.i2s_in_stop()
        human_ok = (self.ivar_in.get() == 1)
        if self.i2s_in_error:
            self.add_log(f"I2S input test: FAIL ({self.i2s_in_error}).",
                         "fail")
            self.log_local_result("I2S IN", False, self.i2s_in_error)
            self._set_pill("I2S IN", "fail")
            self._set_button_state("I2S IN", "fail")
        elif self.i2s_in_auto is None:
            self.add_log("I2S input test: INCOMPLETE (monitor was never run "
                         "to a result).")
            self._set_pill("I2S IN", "idle")
            self._set_button_state("I2S IN", "ready")
        elif self.i2s_in_auto and human_ok:
            self.add_log("I2S input test: PASS (level + confirmed).", "pass")
            self.log_local_result("I2S IN", True, "sound detected + confirmed")
            self._set_pill("I2S IN", "pass")
            self._set_button_state("I2S IN", "pass")
        elif self.i2s_in_auto and not human_ok:
            self.add_log("I2S input test: FAIL (not confirmed).", "fail")
            self.log_local_result("I2S IN", False, "detected, not confirmed")
            self._set_pill("I2S IN", "fail")
            self._set_button_state("I2S IN", "fail")
        else:
            self.add_log("I2S input test: FAIL (script reported failure).",
                         "fail")
            self.log_local_result("I2S IN", False, "script fail")
            self._set_pill("I2S IN", "fail")
            self._set_button_state("I2S IN", "fail")
        self._show_frame(self.logFrame)

    def i2s_out_test(self):
        if not self._require_client("I2S OUT"):
            return
        self.ivar_out.set(0)
        self.i2s_out_auto = None
        self.i2s_out_output.config(state=tk.NORMAL)
        self.i2s_out_output.delete("1.0", tk.END)
        self.i2s_out_output.config(state=tk.DISABLED)
        self._set_button_state("I2S OUT", "running")
        self._set_pill("I2S OUT", "running")
        self.i2s_out_running_label.config(text="Setting up playback...",
                                          fg=STATE_RUN)
        self._show_frame(self.i2sOutFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("I2S output (DAC) test starting...")
        threading.Thread(target=self._i2s_out_worker, daemon=True).start()

    def _i2s_out_worker(self):
        collected = []
        try:
            cmd = (f"cd {REMOTE_TEST_DIR} && chmod +x I2S_test_output.sh && "
                   f"./I2S_test_output.sh")
            channel = self._open_stream(cmd, use_sudo=True)
            for line in self._read_lines(channel, lambda: True):
                collected.append(line)
                self.root.after(0, self._i2s_out_line, line)
            try:
                channel.close()
            except Exception:
                pass
        except Exception as e:
            collected.append(f"SSH ERROR: {e}")
        self.root.after(0, self._i2s_out_done, "\n".join(collected))

    def _i2s_out_line(self, line):
        self.i2s_out_output.config(state=tk.NORMAL)
        self.i2s_out_output.insert(tk.END, line + "\n")
        self.i2s_out_output.see(tk.END)
        self.i2s_out_output.config(state=tk.DISABLED)
        if "playing the tone" in line:
            self.i2s_out_running_label.config(
                text="Tone playing now - listen on the DAC headphone jack.",
                fg=STATE_RUN)

    def _i2s_out_done(self, output):
        auto_done = I2S_OUT_DONE_LINE in output
        self.i2s_out_auto = auto_done
        if auto_done:
            self.i2s_out_running_label.config(
                text="Playback finished. Confirm you heard the tone, then "
                     "check the box.", fg=STATE_PASS)
        else:
            self.i2s_out_running_label.config(
                text="Script reported a problem - see the output above.",
                fg=STATE_FAIL)
            self._log_failure_detail(output, max_lines=25)
        self.add_log(f"I2S output script result: "
                     f"{'playback completed' if auto_done else 'FAIL'}",
                     "pass" if auto_done else "fail")
        self._set_test_buttons(tk.NORMAL)

    def i2s_out_back(self):
        human_ok = (self.ivar_out.get() == 1)
        if self.i2s_out_auto is None:
            self.add_log("I2S output test: INCOMPLETE (left before playback "
                         "finished).")
            self._set_pill("I2S OUT", "idle")
            self._set_button_state("I2S OUT", "ready")
        elif self.i2s_out_auto and human_ok:
            self.add_log("I2S output test: PASS (playback + heard tone).",
                         "pass")
            self.log_local_result("I2S OUT", True, "playback + confirmed")
            self._set_pill("I2S OUT", "pass")
            self._set_button_state("I2S OUT", "pass")
        elif self.i2s_out_auto and not human_ok:
            self.add_log("I2S output test: FAIL (tone not heard).", "fail")
            self.log_local_result("I2S OUT", False, "playback ok, not heard")
            self._set_pill("I2S OUT", "fail")
            self._set_button_state("I2S OUT", "fail")
        else:
            self.add_log("I2S output test: FAIL (script reported failure).",
                         "fail")
            self.log_local_result("I2S OUT", False, "script fail")
            self._set_pill("I2S OUT", "fail")
            self._set_button_state("I2S OUT", "fail")
        self._show_frame(self.logFrame)

    def spi_test(self):
        if not self._require_client("SPI"):
            return
        self.svar.set(0)
        self.spi_auto = None
        self.spi_output.config(state=tk.NORMAL)
        self.spi_output.delete("1.0", tk.END)
        self.spi_output.config(state=tk.DISABLED)
        self._set_button_state("SPI", "running")
        self._set_pill("SPI", "running")
        self.spi_running_label.config(text="Initializing the display...",
                                      fg=STATE_RUN)
        self._show_frame(self.spiFrame)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("SPI display test starting...")
        threading.Thread(target=self._spi_worker, daemon=True).start()

    def _spi_worker(self):
        collected = []
        try:
            cmd = f"cd {REMOTE_TEST_DIR} && python3 -u spitest.py"
            channel = self._open_stream(cmd, use_sudo=True)
            for line in self._read_lines(channel, lambda: True):
                collected.append(line)
                self.root.after(0, self._spi_line, line)
            try:
                channel.close()
            except Exception:
                pass
        except Exception as e:
            collected.append(f"SSH ERROR: {e}")
        self.root.after(0, self._spi_done, "\n".join(collected))

    def _spi_line(self, line):
        self.spi_output.config(state=tk.NORMAL)
        self.spi_output.insert(tk.END, line + "\n")
        self.spi_output.see(tk.END)
        self.spi_output.config(state=tk.DISABLED)
        if line.startswith("Displaying"):
            self.spi_running_label.config(
                text="Cycling colors now - watch the display.", fg=STATE_RUN)

    def _spi_done(self, output):
        auto = any(l.strip() == SPI_PASS_LINE for l in output.splitlines())
        self.spi_auto = auto
        if auto:
            self.spi_running_label.config(
                text="Script completed. Confirm the display cycled red, "
                     "green and blue, then check the box.", fg=STATE_PASS)
        else:
            self.spi_running_label.config(
                text="Script reported a problem - see the output above.",
                fg=STATE_FAIL)
            self._log_failure_detail(output)
        self.add_log(f"SPI script result: {'PASS' if auto else 'FAIL'}",
                     "pass" if auto else "fail")
        self._set_test_buttons(tk.NORMAL)

    def spi_back(self):
        human_ok = (self.svar.get() == 1)
        if self.spi_auto is None:
            self.add_log("SPI test: INCOMPLETE (left before finishing).")
            self._set_pill("SPI", "idle")
            self._set_button_state("SPI", "ready")
        elif self.spi_auto and human_ok:
            self.add_log("SPI test: PASS (script + display confirmed).",
                         "pass")
            self.log_local_result("SPI", True, "script pass + human confirmed")
            self._set_pill("SPI", "pass")
            self._set_button_state("SPI", "pass")
        elif self.spi_auto and not human_ok:
            self.add_log("SPI test: FAIL (display not confirmed).", "fail")
            self.log_local_result("SPI", False, "script pass, not confirmed")
            self._set_pill("SPI", "fail")
            self._set_button_state("SPI", "fail")
        else:
            self.add_log("SPI test: FAIL (script reported failure).", "fail")
            self.log_local_result("SPI", False, "script fail")
            self._set_pill("SPI", "fail")
            self._set_button_state("SPI", "fail")
        self._show_frame(self.logFrame)

    def _i2c_list_clear(self):
        self.i2c_list.config(state=tk.NORMAL)
        self.i2c_list.delete("1.0", tk.END)
        self.i2c_list.config(state=tk.DISABLED)

    def _i2c_list_add(self, text, tag="quiet"):
        self.i2c_list.config(state=tk.NORMAL)
        self.i2c_list.insert(tk.END, text + "\n", tag)
        extra = int(self.i2c_list.index("end-1c").split(".")[0]) - LIST_ROWS
        if extra > 0:
            self.i2c_list.delete("1.0", "%d.0" % (extra + 1))
        self.i2c_list.see(tk.END)
        self.i2c_list.config(state=tk.DISABLED)

    def i2c_test(self):
        self.icvar.set(0)
        self.i2c_auto = None
        self.i2c_error = None
        self.i2c_found = None
        self.i2c_min = None
        self.i2c_max = None
        self.i2c_samples = 0
        self._i2c_list_clear()
        self.i2c_armed_label.config(text="")
        self.i2c_running_label.config(text="Press Start Reading.",
                                      fg=INK_SOFT)
        self.i2c_read_label.config(
            text="distance  -        nearest  -        farthest  -"
                 "        spread  -", fg=INK_SOFT)
        self._show_frame(self.i2cFrame)

    def i2c_start(self):
        if not self._require_client("I2C"):
            self.i2c_running_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right, then start the reading again.",
                fg=STATE_FAIL)
            return
        self._i2c_teardown()
        self.i2c_gen += 1
        gen = self.i2c_gen
        self.i2c_auto = None
        self.i2c_error = None
        self.i2c_found = None
        self.i2c_min = None
        self.i2c_max = None
        self.i2c_samples = 0
        self._i2c_list_clear()
        self.i2c_armed_label.config(text="")
        self._set_pill("I2C", "running")
        self._set_button_state("I2C", "running")
        self.i2c_running_label.config(text="Scanning the I2C bus...",
                                      fg=STATE_RUN)
        self.add_log("I2C distance sensor stream starting...")
        threading.Thread(target=self._i2c_worker, args=(gen,),
                         daemon=True).start()

    def _i2c_teardown(self):
        self.i2c_gen += 1
        ch = self.i2c_channel
        self.i2c_channel = None
        if ch is not None:
            try:
                ch.close()
            except Exception:
                pass
        if self.client is not None:
            try:
                self.client.exec_command('pkill -f "[i]2ctest.py"')
            except Exception:
                pass
        return ch is not None

    def _i2c_worker(self, gen):
        try:
            try:
                self.client.exec_command('pkill -f "[i]2ctest.py"')
                time.sleep(0.3)
            except Exception:
                pass
            if gen != self.i2c_gen:
                return
            cmd = f"cd {REMOTE_TEST_DIR} && python3 -u i2ctest.py"
            channel = self._open_stream(cmd, use_sudo=True)
            if gen != self.i2c_gen:
                try:
                    channel.close()
                except Exception:
                    pass
                return
            self.i2c_channel = channel
            for line in self._read_lines(channel,
                                         lambda: gen == self.i2c_gen):
                self.root.after(0, self._i2c_line, line, gen)
            try:
                channel.close()
            except Exception:
                pass
            if gen == self.i2c_gen:
                self.root.after(0, self._i2c_ended, gen)
        except Exception as e:
            if gen == self.i2c_gen:
                self.root.after(0, self._i2c_error, str(e), gen)

    def _i2c_parse_distance(self, line):
        body = line[len(I2C_DIST_PREFIX):].strip()
        token = body.split()[0] if body.split() else ""
        try:
            return int(float(token))
        except ValueError:
            return None

    def _i2c_line(self, line, gen):
        if gen != self.i2c_gen:
            return
        line = line.strip()
        if not line:
            return

        if line.startswith(I2C_DIST_PREFIX):
            mm = self._i2c_parse_distance(line)
            if mm is None:
                self.add_log(f"I2C: {line}")
                return

            status = ""
            if "Status:" in line:
                status = line.split("Status:", 1)[1].strip()

            self.i2c_samples += 1
            elapsed = self.i2c_samples * I2C_SAMPLE_SEC
            out_of_range = (mm <= 0 or mm >= I2C_MAX_RANGE_MM)

            if out_of_range:
                self._i2c_list_add(
                    "%7.1fs %11s      %s" % (elapsed, "out of range",
                                             status or "no target"), "bad")
                return

            if self.i2c_min is None or mm < self.i2c_min:
                self.i2c_min = mm
            if self.i2c_max is None or mm > self.i2c_max:
                self.i2c_max = mm
            spread = (self.i2c_max - self.i2c_min)
            armed = spread >= I2C_SPREAD_MM

            self._i2c_list_add(
                "%7.1fs %8d mm      %s" % (elapsed, mm, status),
                "hit" if armed else "quiet")

            self.i2c_read_label.config(
                text=("distance %6d mm    nearest %6d mm    "
                      "farthest %6d mm    spread %5d mm"
                      % (mm, self.i2c_min, self.i2c_max, spread)),
                fg=STATE_PASS if armed else INK_SOFT)

            if armed and not self.i2c_auto:
                self.i2c_auto = True
                self.i2c_armed_label.config(
                    text="The reading has followed the target over %d mm "
                         "during this run - the test can pass."
                         % I2C_SPREAD_MM, fg=STATE_PASS)
                self.i2c_running_label.config(
                    text="Reading is following the target.", fg=STATE_PASS)
                self.add_log("I2C: reading varied by %d mm - sensor is "
                             "tracking." % spread, "pass")
            elif not armed:
                self.i2c_running_label.config(
                    text="Reading - move a target toward and away from "
                         "the sensor.", fg=INK_SOFT)
            return

        if line.startswith(I2C_SCAN_PREFIX):
            found = "NOT" not in line.upper()
            self.i2c_found = found
            self._i2c_list_add("         " + line,
                               "note" if found else "bad")
            if found:
                self.i2c_running_label.config(
                    text="Sensor acknowledged - move a target toward and "
                         "away from it.", fg=STATE_RUN)
            else:
                self.i2c_running_label.config(
                    text="No device acknowledged at 0x29 - check the "
                         "wiring.", fg=STATE_FAIL)
            self.add_log(f"I2C: {line}", "pass" if found else "fail")
            return

        if line == I2C_PASS_LINE:
            if self.i2c_auto is None:
                self.i2c_auto = True
                self.i2c_armed_label.config(
                    text="The script reported a pass - confirm the readings "
                         "looked correct.", fg=STATE_PASS)
            self.add_log("I2C: script reported PASS.", "pass")
            return

        if line.startswith(I2C_FAIL_LINE):
            self.i2c_auto = False
            self.i2c_running_label.config(
                text="Script reported a failure - see the Test Log.",
                fg=STATE_FAIL)
            self.add_log("I2C: script reported FAIL.", "fail")
            return

        self.add_log(f"I2C: {line}")

    def _i2c_ended(self, gen):
        if gen != self.i2c_gen:
            return
        self.i2c_channel = None
        if self.i2c_auto is None:
            if self.i2c_found is False:
                self.i2c_error = "no device acknowledged at 0x29"
            elif self.i2c_samples == 0:
                self.i2c_error = "stream ended before any reading arrived"
            else:
                self.i2c_error = ("stream ended before the reading followed "
                                  "a target")
            self.i2c_running_label.config(
                text="Stopped before the sensor tracked a target.",
                fg=STATE_FAIL)
            self._set_pill("I2C", "fail")
            self._set_button_state("I2C", "fail")

    def _i2c_error(self, msg, gen):
        if gen != self.i2c_gen:
            return
        self.i2c_channel = None
        self.i2c_error = msg
        self.i2c_running_label.config(text="Stream error - see log.",
                                      fg=STATE_FAIL)
        self.add_log(f"I2C error: {msg}", "fail")
        self._set_pill("I2C", "fail")
        self._set_button_state("I2C", "fail")

    def i2c_stop(self):
        was_live = self._i2c_teardown()
        if was_live:
            self.add_log("I2C reading stopped.")
            if self.i2c_auto:
                self.i2c_running_label.config(
                    text="Stopped - the reading followed the target.",
                    fg=STATE_PASS)
            else:
                self.i2c_running_label.config(text="Reading stopped.",
                                              fg=INK_SOFT)

    def i2c_back(self):
        self.i2c_stop()
        human_ok = (self.icvar.get() == 1)
        if self.i2c_error:
            self.add_log(f"I2C test: FAIL ({self.i2c_error}).", "fail")
            self.log_local_result("I2C", False, self.i2c_error)
            self._set_pill("I2C", "fail")
            self._set_button_state("I2C", "fail")
        elif self.i2c_auto is None:
            self.add_log("I2C test: INCOMPLETE (reading was never run to a "
                         "result).")
            self._set_pill("I2C", "idle")
            self._set_button_state("I2C", "ready")
        elif self.i2c_auto and human_ok:
            self.add_log("I2C test: PASS (readings + confirmed).", "pass")
            self.log_local_result("I2C", True,
                                  "sensor tracked target + confirmed")
            self._set_pill("I2C", "pass")
            self._set_button_state("I2C", "pass")
        elif self.i2c_auto and not human_ok:
            self.add_log("I2C test: FAIL (readings not confirmed).", "fail")
            self.log_local_result("I2C", False, "tracked, not confirmed")
            self._set_pill("I2C", "fail")
            self._set_button_state("I2C", "fail")
        else:
            self.add_log("I2C test: FAIL (script reported failure).", "fail")
            self.log_local_result("I2C", False, "script fail")
            self._set_pill("I2C", "fail")
            self._set_button_state("I2C", "fail")
        self._show_frame(self.logFrame)

    def _cam_idle_view(self, message=None):
        self.cam_photo = None
        self.cam_box.config(bg=TRACK)
        self.cam_view.config(
            image="", bg=TRACK, fg=INK_SOFT,
            text=message or "No camera selected\n\nPress Test CAM 0 or "
                            "Test CAM 1 to start the live stream")

    def _cam_live_view(self, photo):
        self.cam_box.config(bg="#101418")
        self.cam_view.config(image=photo, text="", bg="#101418")

    def cam_test(self):
        self.cvar.set(0)
        self.cam_saw_frame = False
        self.cam_error = None
        self.cam_status_label.config(text="Pick a camera to start streaming.",
                                     fg=INK_SOFT)
        self._cam_idle_view()
        self._show_frame(self.camFrame)

    def cam_start(self, sensor_id):
        if not self._require_client("CAMERA"):
            self.cam_status_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right, then start the camera again.", fg=STATE_FAIL)
            return
        self._cam_teardown()
        self.cam_gen += 1
        gen = self.cam_gen
        self.cam_saw_frame = False
        self.cam_error = None
        self.cam_sensor = sensor_id
        self._set_pill("CAMERA", "running")
        self._set_button_state("CAMERA", "running")
        self.cam_status_label.config(
            text=f"Starting camera sensor {sensor_id}...", fg=STATE_RUN)
        self._cam_idle_view(f"Starting camera sensor {sensor_id}...\n\n"
                            f"Waiting for the first frame")
        self.add_log(f"Camera stream requested (sensor {sensor_id}).")
        threading.Thread(target=self._cam_worker, args=(sensor_id, gen),
                         daemon=True).start()

    def _cam_teardown(self):
        self.cam_gen += 1
        ch = self.cam_channel
        self.cam_channel = None
        if ch is not None:
            try:
                ch.close()
            except Exception:
                pass
        return ch is not None

    def _cam_worker(self, sensor_id, gen):
        MARKER = b"\xff\xd8\xff"
        try:
            if self.client is None:
                raise RuntimeError("not connected to the Jetson")
            try:
                self.client.exec_command('pkill -f "[c]amtest.py"')
                time.sleep(0.5)
            except Exception:
                pass
            if gen != self.cam_gen:
                return
            transport = self.client.get_transport()
            channel = transport.open_session()
            channel.exec_command(
                f"cd {REMOTE_TEST_DIR} && python3 camtest.py {sensor_id}")
            if gen != self.cam_gen:
                try:
                    channel.close()
                except Exception:
                    pass
                return
            self.cam_channel = channel
            buf = b""
            while gen == self.cam_gen:
                if channel.recv_stderr_ready():
                    err = channel.recv_stderr(4096).decode(
                        errors="ignore").strip()
                    if err:
                        self.root.after(0, self.add_log,
                                        f"camtest.py: {err}", "fail")
                if channel.recv_ready():
                    chunk = channel.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                elif channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.01)
                    continue
                while gen == self.cam_gen:
                    idx = buf.find(MARKER)
                    if idx < 0 or len(buf) < idx + 7:
                        break
                    length = int.from_bytes(buf[idx + 3:idx + 7], "big")
                    if length <= 0 or length > 4000000:
                        buf = buf[idx + 3:]
                        break
                    if len(buf) < idx + 7 + length:
                        break
                    jpg = buf[idx + 7: idx + 7 + length]
                    buf = buf[idx + 7 + length:]
                    self.root.after(0, self._cam_show_frame, jpg, gen)
            try:
                channel.close()
            except Exception:
                pass
            if gen == self.cam_gen:
                self.root.after(0, self._cam_stream_ended, gen)
        except Exception as e:
            if gen == self.cam_gen:
                self.root.after(0, self._cam_error, str(e), gen)

    def _cam_show_frame(self, jpg, gen):
        if gen != self.cam_gen:
            return
        try:
            from PIL import Image, ImageTk
            import io
        except ImportError:
            self.cam_status_label.config(
                text="Pillow is not installed on Windows (pip install Pillow).",
                fg=STATE_FAIL)
            self.add_log("Pillow missing - cannot display camera frames.",
                         "fail")
            self._cam_teardown()
            return
        try:
            img = Image.open(io.BytesIO(jpg))
            box_w = max(self.cam_box.winfo_width() - 4, 64)
            box_h = max(self.cam_box.winfo_height() - 4, 64)
            if img.width > box_w or img.height > box_h:
                img.thumbnail((box_w, box_h))
            photo = ImageTk.PhotoImage(img)
        except Exception:
            return
        self.cam_photo = photo
        self._cam_live_view(photo)
        if not self.cam_saw_frame:
            self.cam_saw_frame = True
            self.cam_status_label.config(
                text=f"Live video from sensor {self.cam_sensor}. "
                     f"Press Stop when done.", fg=STATE_PASS)
            self.add_log(f"Camera sensor {self.cam_sensor}: first frame "
                         f"received.", "pass")

    def _cam_stream_ended(self, gen):
        if gen != self.cam_gen:
            return
        self.cam_channel = None
        if not self.cam_saw_frame:
            self.cam_error = "stream ended with no frames received"
            self.cam_status_label.config(
                text="No video received - check the ribbon cable and "
                     "sensor id.", fg=STATE_FAIL)
            self.add_log("Camera stream ended with no frames received.", "fail")
            self._set_pill("CAMERA", "fail")
            self._set_button_state("CAMERA", "fail")

    def _cam_error(self, msg, gen=None):
        if gen is not None and gen != self.cam_gen:
            return
        self.cam_channel = None
        self.cam_error = msg
        self.cam_status_label.config(text="Camera error - see log.",
                                     fg=STATE_FAIL)
        self.add_log(f"Camera error: {msg}", "fail")
        self._set_pill("CAMERA", "fail")
        self._set_button_state("CAMERA", "fail")

    def cam_stop(self):
        was_live = self._cam_teardown()
        self._cam_idle_view()
        if was_live:
            self.cam_status_label.config(text="Camera stopped.", fg=INK_SOFT)
            self.add_log("Camera stream stopped.")

    def cam_back(self):
        self.cam_stop()
        saw = self.cam_saw_frame
        if saw and self.cvar.get() == 1:
            self.add_log("CAMERA test: PASS (saw live video).", "pass")
            self.log_local_result("CAMERA", True,
                                  f"sensor {self.cam_sensor} confirmed")
            self._set_pill("CAMERA", "pass")
            self._set_button_state("CAMERA", "pass")
        elif saw:
            self.add_log("CAMERA test: FAIL (video not confirmed).", "fail")
            self.log_local_result("CAMERA", False, "frames seen, not confirmed")
            self._set_pill("CAMERA", "fail")
            self._set_button_state("CAMERA", "fail")
        elif self.cam_error:
            self.add_log(f"CAMERA test: FAIL ({self.cam_error}).", "fail")
            self.log_local_result("CAMERA", False, self.cam_error)
            self._set_pill("CAMERA", "fail")
            self._set_button_state("CAMERA", "fail")
        else:
            self.add_log("CAMERA test: INCOMPLETE (no stream was run to a "
                         "result).")
            self._set_pill("CAMERA", "idle")
            self._set_button_state("CAMERA", "ready")
        self._show_frame(self.logFrame)

    def _usb_paint(self):
        for label, (dot, led, live, seen) in self.usb_rows.items():
            plugged = self.usb_live.get(label, False)
            if plugged:
                dot.itemconfig(led, fill=STATE_PASS, outline=STATE_PASS)
                live.config(text="connected", fg=STATE_PASS)
            elif self.usb_scanned:
                dot.itemconfig(led, fill=STATE_IDLE, outline=BORDER)
                live.config(text="empty", fg=INK_SOFT)
            else:
                dot.itemconfig(led, fill=STATE_IDLE, outline=BORDER)
                live.config(text="idle", fg=INK_SOFT)
            if self.usb_seen.get(label, False):
                seen.config(text="seen this run", fg=STATE_PASS)
            else:
                seen.config(text="not seen yet", fg=INK_SOFT)

    def usb_reset_seen(self):
        self.usb_seen = {label: False for label, _ in USB_PORT_MAP}
        self.add_log("USB port history cleared.")
        self._usb_paint()

    def usb_test(self):
        self.usb_error = None
        self.usb_scanned = False
        self.usb_live = {label: False for label, _ in USB_PORT_MAP}
        self.usb_running_label.config(
            text="Press Start Scan, then move a flash drive around the four "
                 "ports.", fg=INK_SOFT)
        self._usb_paint()
        self._show_frame(self.usbFrame)

    def usb_start(self):
        if not self._require_client("USB"):
            self.usb_running_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right, then start the scan again.", fg=STATE_FAIL)
            return
        self._usb_teardown()
        self.usb_gen += 1
        gen = self.usb_gen
        self.usb_error = None
        self.usb_scanned = False
        self._set_pill("USB", "running")
        self._set_button_state("USB", "running")
        self.usb_running_label.config(text="Scanning ports...", fg=STATE_RUN)
        self.add_log("USB port scan starting...")
        threading.Thread(target=self._usb_worker, args=(gen,),
                         daemon=True).start()

    def _usb_teardown(self):
        self.usb_gen += 1
        ch = self.usb_channel
        self.usb_channel = None
        if ch is not None:
            try:
                ch.close()
            except Exception:
                pass
        if self.client is not None:
            try:
                self.client.exec_command('pkill -f "[n]anogui_usb_scan"')
            except Exception:
                pass
        return ch is not None

    def _usb_worker(self, gen):
        try:
            try:
                self.client.exec_command('pkill -f "[n]anogui_usb_scan"')
                time.sleep(0.3)
            except Exception:
                pass
            if gen != self.usb_gen:
                return
            channel = self._open_stream(USB_SCAN_CMD)
            if gen != self.usb_gen:
                try:
                    channel.close()
                except Exception:
                    pass
                return
            self.usb_channel = channel
            for line in self._read_lines(channel, lambda: gen == self.usb_gen):
                self.root.after(0, self._usb_line, line, gen)
            try:
                channel.close()
            except Exception:
                pass
            if gen == self.usb_gen:
                self.root.after(0, self._usb_ended, gen)
        except Exception as e:
            if gen == self.usb_gen:
                self.root.after(0, self._usb_error, str(e), gen)

    def _usb_line(self, line, gen):
        if gen != self.usb_gen:
            return
        line = line.strip()
        if not line:
            return
        if line.startswith("[stderr]"):
            self.add_log("USB scan: " + line, "fail")
            return
        if not line.startswith(USB_PORTS_PREFIX):
            return
        bits = line[len(USB_PORTS_PREFIX):].strip()
        if len(bits) != len(USB_PORT_MAP):
            return
        self.usb_scanned = True
        for (label, _), ch in zip(USB_PORT_MAP, bits):
            plugged = (ch == "1")
            self.usb_live[label] = plugged
            # Latched, not momentary: one drive can walk all four sockets.
            if plugged and not self.usb_seen[label]:
                self.usb_seen[label] = True
                self.add_log(f"  {label}: device enumerated", "pass")
        self._usb_paint()
        seen = sum(1 for v in self.usb_seen.values() if v)
        self.usb_running_label.config(
            text=f"Scanning - {seen} of {len(USB_PORT_MAP)} ports seen so "
                 f"far.", fg=STATE_PASS if seen == len(USB_PORT_MAP)
            else STATE_RUN)

    def _usb_ended(self, gen):
        if gen != self.usb_gen:
            return
        self.usb_channel = None
        self.usb_running_label.config(text="Scan stopped.", fg=INK_SOFT)

    def _usb_error(self, msg, gen):
        if gen != self.usb_gen:
            return
        self.usb_channel = None
        self.usb_error = msg
        self.usb_running_label.config(text=f"Scan error: {msg}", fg=STATE_FAIL)
        self.add_log(f"USB scan error: {msg}", "fail")

    def usb_stop(self):
        was_live = self._usb_teardown()
        if was_live:
            self.usb_running_label.config(text="Scan stopped.", fg=INK_SOFT)
            self.add_log("USB port scan stopped.")

    def usb_back(self):
        self.usb_stop()
        seen = [label for label, _ in USB_PORT_MAP if self.usb_seen[label]]
        missing = [label for label, _ in USB_PORT_MAP
                   if not self.usb_seen[label]]

        if not self.usb_scanned and self.usb_error is None:
            self.add_log("USB test: INCOMPLETE (no scan was run).")
            self._set_pill("USB", "idle")
            self._set_button_state("USB", "ready")
            self._show_frame(self.logFrame)
            return

        if self.usb_error:
            self.add_log(f"USB test: FAIL ({self.usb_error}).", "fail")
            self.log_local_result("USB", False, self.usb_error)
            self._set_pill("USB", "fail")
            self._set_button_state("USB", "fail")
            self._show_frame(self.logFrame)
            return

        for label, _ in USB_PORT_MAP:
            if self.usb_seen[label]:
                self.add_log(f"  {label}: CONNECTED", "pass")
            else:
                self.add_log(f"  {label}: NO DEVICE SEEN")

        if not missing:
            summary = "all four ports enumerated a device"
            self.add_log(f"USB test: PASS ({summary}).", "pass")
            self.log_local_result("USB", True, summary)
            self._set_pill("USB", "pass")
            self._set_button_state("USB", "pass")
        else:
            # Same reasoning as PWM: an untested socket is not a failed one.
            detail = ", ".join(missing) + " not tried yet"
            self.add_log(f"USB test: INCOMPLETE ({detail}).")
            self._set_pill("USB", "idle")
            self._set_button_state("USB", "ready")
        self._show_frame(self.logFrame)

    def wifi_test(self):
        self.wifi_auto = None
        self.wifi_info = {}
        for lab in self.wifi_fields.values():
            lab.config(text="-", fg=INK)
        self.wifi_running_label.config(
            text="Press Run WiFi Check. Nothing is reconfigured, so this "
                 "cannot disturb the Ethernet link.", fg=INK_SOFT)
        self._show_frame(self.wifiFrame)

    def wifi_run(self):
        if not self._require_client("WIFI"):
            self.wifi_running_label.config(
                text="Not connected to the Jetson - press Reconnect in the "
                     "top right, then run the check again.", fg=STATE_FAIL)
            return
        self.wifi_auto = None
        self._set_pill("WIFI", "running")
        self._set_button_state("WIFI", "running")
        self.wifi_running_label.config(text="Querying wireless interface...",
                                       fg=STATE_RUN)
        self._set_test_buttons(tk.DISABLED)
        self.add_log("WiFi check starting...")
        threading.Thread(target=self._wifi_worker, daemon=True).start()

    def _wifi_worker(self):
        output = self._exec_blocking(WIFI_CMD)
        self.root.after(0, self._wifi_done, output)

    def wifi_open_browser(self):
        if self.client is None:
            self.add_log("Cannot open browser: no SSH session.", "fail")
            return
        try:
            self.client.exec_command(WIFI_BROWSER_CMD)
            self.add_log("Asked the Jetson to open YouTube on its own "
                         "display (needs a monitor attached).")
        except Exception as e:
            self.add_log(f"Could not launch browser on the Jetson: {e}",
                         "fail")

    def _wifi_done(self, output):
        info = {}
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith("WIFI "):
                continue
            body = line[5:]
            if ":" not in body:
                continue
            key, val = body.split(":", 1)
            info[key.strip().upper()] = val.strip()
        self.wifi_info = info

        for key, lab in self.wifi_fields.items():
            val = info.get(key, "-")
            color = INK
            if key in ("PING", "DNS"):
                color = STATE_PASS if val == "PASS" else STATE_FAIL
            elif key == "STATE" and val not in ("connected", "-"):
                color = STATE_FAIL
            lab.config(text=val or "-", fg=color)

        auto = any(l.strip() == WIFI_PASS_LINE for l in output.splitlines())
        self.wifi_auto = auto

        if info.get("STATE") == "missing":
            self.wifi_running_label.config(
                text="No wireless interface found on the Jetson.",
                fg=STATE_FAIL)
        elif auto:
            self.wifi_running_label.config(
                text=f"Reached the internet through "
                     f"{info.get('DEV', 'wlan0')}.", fg=STATE_PASS)
        else:
            self.wifi_running_label.config(
                text="Wireless did not reach the internet - see the Test "
                     "Log.", fg=STATE_FAIL)
            self._log_failure_detail(output)

        self.add_log(
            "  WiFi interface %s, state %s, network %s, address %s"
            % (info.get("DEV", "?"), info.get("STATE", "?"),
               info.get("SSID", "?"), info.get("IP", "?")))
        self.add_log(f"WiFi check result: {'PASS' if auto else 'FAIL'}",
                     "pass" if auto else "fail")
        self._set_test_buttons(tk.NORMAL)

    def wifi_back(self):
        if self.wifi_auto is None:
            self.add_log("WIFI test: INCOMPLETE (check was not run).")
            self._set_pill("WIFI", "idle")
            self._set_button_state("WIFI", "ready")
        elif self.wifi_auto:
            summary = ("associated to %s on %s, ping out of %s succeeded"
                       % (self.wifi_info.get("SSID", "?"),
                          self.wifi_info.get("IP", "?"),
                          self.wifi_info.get("DEV", "wlan0")))
            self.add_log(f"WIFI test: PASS ({summary}).", "pass")
            self.log_local_result("WIFI", True, summary)
            self._set_pill("WIFI", "pass")
            self._set_button_state("WIFI", "pass")
        else:
            summary = ("state %s, ping %s"
                       % (self.wifi_info.get("STATE", "?"),
                          self.wifi_info.get("PING", "FAIL")))
            self.add_log(f"WIFI test: FAIL ({summary}).", "fail")
            self.log_local_result("WIFI", False, summary)
            self._set_pill("WIFI", "fail")
            self._set_button_state("WIFI", "fail")
        self._show_frame(self.logFrame)

    def on_close(self):
        self._cam_teardown()
        self._i2s_in_teardown()
        self._usb_teardown()
        if self.client is not None:
            try:
                self.client.exec_command('pkill -f "[c]amtest.py"; '
                                         'pkill -f "[n]anogui_usb_scan"')
            except Exception:
                pass
            try:
                self.client.close()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    NanoGUI()
