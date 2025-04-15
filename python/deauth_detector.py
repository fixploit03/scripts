#!/usr/bin/env python3
#**********************************************************
#
# Script python untuk mendeteksi serangan Deauthentication
#
#**********************************************************
#
# Author = Rofi (Fixploit03)
# Github = https://github.com/fixploit03/OrayKadut
#
#**********************************************************

import argparse
from scapy.all import *
from datetime import datetime

def detect_deauth(pkt):
    if pkt.haslayer(Dot11Deauth):
        src = pkt.addr2
        dst = pkt.addr1
        bssid = pkt.addr3
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if args.target and args.target.lower() not in [src.lower(), dst.lower(), bssid.lower()]:
            return

        alert = f"[{timestamp}] [DEAUTH] From {src} to {dst} (BSSID: {bssid})"
        print(alert)

        if args.output:
            with open(args.output, "a") as f:
                f.write(alert + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deauthentication Attack Detector")
    parser.add_argument("-i", "--interface", required=True, help="Interface in monitor mode (e.g. wlan0mon)")
    parser.add_argument("-t", "--target", help="Target MAC address to monitor (optional)")
    parser.add_argument("-o", "--output", help="Save alerts to a file (optional)")

    args = parser.parse_args()

    print(f"[*] Listening for Deauth frames on interface {args.interface}...\n")
    sniff(iface=args.interface, prn=detect_deauth, store=0)
