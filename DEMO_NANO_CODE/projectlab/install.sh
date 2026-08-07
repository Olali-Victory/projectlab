#!/bin/bash
# Installs everything the test bench needs on a Jetson Nano that does not
# already have it. Safe to run more than once.
#
#   cd ~/Documents/projectlab/setup
#   sudo bash install.sh
#
# What this cannot do is listed at the end of the run. Those steps have to be
# done by hand, because they write to the boot partition or depend on how the
# board is wired.

set -u

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this with sudo:  sudo bash install.sh" >&2
    exit 1
fi

HERE=$(cd "$(dirname "$0")" && pwd)
TARGET_USER=${SUDO_USER:-$(logname 2>/dev/null || echo "")}

step() { echo; echo "== $*"; }
ok()   { echo "   ok   $*"; }
warn() { echo "   WARN $*"; }

# ---------------------------------------------------------------- apt packages

step "System packages"
APT_PKGS="busybox alsa-utils python3-pip openssh-server i2c-tools"
MISSING=""
for p in $APT_PKGS; do
    dpkg -s "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"
done
if [ -n "$MISSING" ]; then
    echo "   installing:$MISSING"
    apt-get update -qq && apt-get install -y -qq $MISSING \
        && ok "installed$MISSING" \
        || warn "apt install failed. Check the network and rerun."
else
    ok "all present"
fi

# ------------------------------------------------------------ python packages

step "Python packages"
if [ -f "$HERE/requirements-jetson.txt" ]; then
    if pip3 install -q -r "$HERE/requirements-jetson.txt" 2>/dev/null \
       || pip3 install -q --break-system-packages -r "$HERE/requirements-jetson.txt" 2>/dev/null; then
        ok "installed from requirements-jetson.txt"
    else
        warn "pip3 install failed. The SPI, I2C and UART tests will report an import error."
    fi
else
    warn "requirements-jetson.txt not found next to this script"
fi

# ---------------------------------------------------------------- sudoers rule

step "Passwordless busybox devmem"
if [ -f "$HERE/devmem" ]; then
    if visudo -c -f "$HERE/devmem" >/dev/null 2>&1; then
        install -o root -g root -m 0440 "$HERE/devmem" /etc/sudoers.d/devmem
        ok "installed to /etc/sudoers.d/devmem"
    else
        warn "devmem failed syntax check, not installed"
    fi
else
    warn "devmem not found next to this script"
fi

# ------------------------------------------------------------ pinmux at boot

step "DAP4 pad ownership fix at boot"
if [ -f "$HERE/i2s4-pinmux.sh" ] && [ -f "$HERE/i2s4-pinmux.service" ]; then
    install -o root -g root -m 0755 "$HERE/i2s4-pinmux.sh" /usr/local/sbin/i2s4-pinmux.sh
    install -o root -g root -m 0644 "$HERE/i2s4-pinmux.service" \
        /etc/systemd/system/i2s4-pinmux.service
    systemctl daemon-reload
    systemctl enable i2s4-pinmux.service >/dev/null 2>&1
    systemctl start i2s4-pinmux.service >/dev/null 2>&1
    STATE=$(systemctl is-enabled i2s4-pinmux.service 2>/dev/null)
    if [ "$STATE" = "enabled" ]; then
        ok "i2s4-pinmux.service enabled and applied"
        echo "        port J register now reads $(busybox devmem 0x6000d204 2>/dev/null || echo unreadable)"
    else
        warn "service files installed but systemd reports '${STATE:-no state}'"
    fi
else
    warn "i2s4-pinmux.sh or i2s4-pinmux.service not found next to this script"
fi

# ---------------------------------------------------------------- serial getty

step "Serial console on /dev/ttyTHS1"
if systemctl is-enabled nvgetty >/dev/null 2>&1; then
    systemctl stop nvgetty >/dev/null 2>&1
    systemctl disable nvgetty >/dev/null 2>&1
    ok "nvgetty stopped and disabled"
else
    ok "nvgetty already disabled"
fi

# -------------------------------------------------------------------- groups

step "Group membership for $TARGET_USER"
if [ -n "$TARGET_USER" ]; then
    ADDED=""
    for g in gpio i2c spi dialout audio video; do
        getent group "$g" >/dev/null 2>&1 || continue
        id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx "$g" && continue
        usermod -aG "$g" "$TARGET_USER" && ADDED="$ADDED $g"
    done
    if [ -n "$ADDED" ]; then
        ok "added to$ADDED (log out and back in for this to take effect)"
    else
        ok "already in every group that exists on this board"
    fi
else
    warn "could not work out which account to add to the hardware groups"
fi

# ------------------------------------------------------------------- ssh

step "SSH server"
systemctl enable ssh >/dev/null 2>&1
systemctl start ssh >/dev/null 2>&1
if systemctl is-active ssh >/dev/null 2>&1; then
    ok "running, reachable at: $(hostname -I | tr ' ' '\n' | grep -v '^$' | tr '\n' ' ')"
else
    warn "ssh is not running. The test bench cannot reach this board."
fi

# ------------------------------------------------------- what is left by hand

cat <<EOF

== Still to do by hand

1. Device tree, through jetson-io. This writes to the boot partition and is
   specific to the board revision, so it is not scripted here. Run:

       sudo /opt/nvidia/jetson-io/jetson-io.py

   Enable, on the 40-pin header: i2s4, pwm0, pwm2, spi1.
   Save the configuration and reboot. Nothing in software reports the
   difference if this is skipped, which is the finding in Section 6.2 of the
   report. Confirm afterwards with:

       arecord -l                                    # I2S4 card should appear
       sudo sh -c 'cat /sys/kernel/debug/pinctrl/*/pinmux-pins' | grep -i pwm
       ls /dev/spidev*                               # SPI nodes should exist

2. Wiring. Every device on the header, the UART jumper from pin 8 to pin 10,
   XSMT on the PCM5102A tied to 3.3 V, and FLT and FMT tied to ground.

3. Network. Give this board a fixed address the Windows host can reach, then
   put that address, the username, and the password at the top of
   nanogui_windows_Final.py on the Windows side.

4. Reboot once, then run the test bench.
EOF

echo
exit 0
