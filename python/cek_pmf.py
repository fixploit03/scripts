import argparse
from scapy.all import *
from scapy.layers.dot11 import Dot11Elt

def check_pmf(pkt):
    if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp):
        ssid = pkt[Dot11Elt].info.decode(errors="ignore")
        bssid = pkt.addr2
        rsn = pkt.getlayer(Dot11Elt, ID=48)
        pmf_status = "Unknown"

        if rsn:
            rsn_data = rsn.info
            if len(rsn_data) > 18:
                pmf_byte = rsn_data[18]
                if pmf_byte & 0b00000001:
                    pmf_status = "PMF Required"
                elif pmf_byte & 0b00000010:
                    pmf_status = "PMF Capable"
                else:
                    pmf_status = "PMF Not Supported"
            else:
                pmf_status = "PMF Info Not Found"

        print(f"[+] SSID: {ssid}")
        print(f"    BSSID: {bssid}")
        print(f"    PMF Status: {pmf_status}")

        if "PMF Not Supported" in pmf_status:
            print("    ⚠️  AP mungkin RENTAN terhadap deauth attack")
        elif "PMF Capable" in pmf_status:
            print("    ⚠️  AP MUNGKIN rentan (mode mixed)")
        elif "PMF Required" in pmf_status:
            print("    ✅  AP TIDAK rentan terhadap deauth")
        print("-" * 50)

def main():
    parser = argparse.ArgumentParser(
        description="🔍 PMF (802.11w) & WPA3 Deauth Vulnerability Checker by Fixploit03"
    )
    parser.add_argument(
        "-i", "--interface", required=True,
        help="Interface WiFi dalam mode monitor (contoh: wlan0mon)"
    )
    parser.add_argument(
        "-t", "--time", type=int, default=30,
        help="Durasi sniffing dalam detik (default: 30)"
    )
    args = parser.parse_args()

    print(f"[*] Sniffing di interface {args.interface} selama {args.time} detik...")
    sniff(iface=args.interface, prn=check_pmf, timeout=args.time)

if __name__ == "__main__":
    main()
