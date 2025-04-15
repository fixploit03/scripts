#!/usr/bin/env python3
#***********************************************************
#
# Lr4Crack.py
#
# Script python untuk meng-crack kata sandi file ZIP Preset
# Lightroom yang memiliki kata sandi berupa angka 4 digit.
#
#***********************************************************
#
# Author = Rofi (Fixploit03)
# Github = https://github.com/fixploit03/OrayKadut
#
#***********************************************************

import sys
import pyzipper

def crack_zip(zip_path):
    try:
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            for i in range(10000):
                password = f"{i:04d}".encode('utf-8')
                zf.pwd = password
                try:
                    if zf.testzip() is None:
                        print(password.decode('utf-8'))
                        return True
                except Exception:
                    continue
        print("Password not found.")
        return False
    except FileNotFoundError:
        print("ZIP file not found.")
        return False
    except pyzipper.BadZipFile:
        print("File is not a valid ZIP file.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <zip_file>")
        sys.exit(1)
    crack_zip(sys.argv[1])
