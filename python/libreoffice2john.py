#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Ekstrak hash file LibreOffice/OpenOffice ODF ke format JTR (John The Ripper)
# Dibuat oleh: Rofi (Fixploit03)
# Sumber Referensi: https://github.com/pmittaldev/john-the-ripper/blob/master/run/odf2john.py
# Ditulis ulang menggunakan Python 3 dan disesuaikan untuk komunitas Indonesia
#
# Lisensi: MIT License
#
# Hak Cipta (c) 2025 Fixploit03
#
# Dengan ini diberikan izin, secara cuma-cuma, kepada siapa pun yang memperoleh salinan perangkat lunak ini dan file dokumentasi terkait ("Perangkat Lunak"), 
# untuk menggunakan Perangkat Lunak tanpa batasan, termasuk tanpa batasan hak untuk menggunakan, menyalin, mengubah, menggabungkan, menerbitkan, 
# mendistribusikan, mensublisensikan, dan/atau menjual salinan Perangkat Lunak, serta mengizinkan orang yang diberikan Perangkat Lunak 
# untuk melakukan hal tersebut, tunduk pada ketentuan berikut:
#
# PEMBERITAHUAN HAK CIPTA DAN LISENSI DI ATAS HARUS DISERTAKAN DALAM SETIAP SALINAN ATAU BAGIAN SUBSTANTIAL DARI PERANGKAT LUNAK.
#
# PERANGKAT LUNAK INI DIBERIKAN "SEBAGAIMANA ADANYA", TANPA JAMINAN APA PUN, BAIK TERSURAT MAUPUN TERSIRAT, TERMASUK NAMUN TIDAK TERBATAS 
# PADA JAMINAN DIPERDAGANGKAN, KESESUAIAN UNTUK TUJUAN TERTENTU DAN BEBAS DARI PELANGGARAN. 
# DALAM HAL APA PUN PENULIS ATAU PEMEGANG HAK CIPTA TIDAK BERTANGGUNG JAWAB ATAS KLAIM, KERUSAKAN ATAU KEWAJIBAN LAIN, 
# BAIK DALAM TINDAKAN KONTRAK, KESALAHAN ATAU LAINNYA, YANG TIMBUL DARI, DARI ATAU SEHUBUNGAN DENGAN PERANGKAT LUNAK ATAU PENGGUNAAN ATAU PERJANJIAN LAIN 
# DALAM PERANGKAT LUNAK TERSEBUT.

"""
odf2john.py memproses file ODF menjadi format yang sesuai untuk digunakan dengan JtR.

Format Output:

filename:$odf*cipher type*checksum type*iterations*key-size*checksum*
iv length*iv*salt length*salt*inline or not*content.xml atau path-nya
"""

from xml.etree.ElementTree import ElementTree
import zipfile
import sys
import base64
import binascii


def proses_file(nama_file):
    try:
        zf = zipfile.ZipFile(nama_file)
    except zipfile.BadZipfile:
        print("%s bukan file OpenOffice atau LibreOffice!" % nama_file, file=sys.stderr)
        return 2
    try:
        mf = zf.open("META-INF/manifest.xml")
    except KeyError:
        print("%s bukan file OpenOffice atau LibreOffice!" % nama_file, file=sys.stderr)
        return 3
    tree = ElementTree()
    tree.parse(mf)
    r = tree.getroot()
    elemen = list(r.iter())
    terenkripsi = False
    ukuran_kunci = 16
    for i in range(0, len(elemen)):
        element = elemen[i]
        if element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}full-path") == "content.xml":
            for j in range(i + 1, i + 1 + 3):
                element = elemen[j]
                # print element.items()
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}checksum")
                if data:
                    terenkripsi = True
                    checksum = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}checksum-type")
                if data:
                    checksum_type = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}initialisation-vector")
                if data:
                    iv = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}salt")
                if data:
                    salt = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}algorithm-name")
                if data:
                    nama_algoritma = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}iteration-count")
                if data:
                    hitungan_iterasi = data
                data = element.get("{urn:oasis:names:tc:opendocument:xmlns:manifest:1.0}key-size")
                if data:
                    ukuran_kunci = data

    if not terenkripsi:
        print("%s bukan file OpenOffice atau LibreOffice terenkripsi!" % nama_file, file=sys.stderr)
        return 4

    checksum = binascii.hexlify(base64.b64decode(checksum)).decode('ascii')
    iv = binascii.hexlify(base64.b64decode(iv)).decode('ascii')
    salt = binascii.hexlify(base64.b64decode(salt)).decode('ascii')

    # ekstrak dan simpan content.xml, digunakan nanti oleh john
    try:
        content = zf.open("content.xml").read()
    except KeyError:
        print("%s bukan file OpenOffice atau LibreOffice terenkripsi, content.xml hilang!" % nama_file, file=sys.stderr)
        return 5

    if nama_algoritma.find("Blowfish CFB") > -1:
        tipe_algoritma = 0
    elif nama_algoritma.find("aes256-cbc") > -1:
        tipe_algoritma = 1
    else:
        print("%s menggunakan enkripsi yang tidak didukung!" % nama_file, file=sys.stderr)
        return 6

    if checksum_type.find("SHA1") > -1:
        checksum_type = 0
    elif checksum_type.find("SHA256") > -1:
        checksum_type = 1
    else:
        print("%s menggunakan algoritma checksum yang tidak didukung!" % nama_file, file=sys.stderr)
        return 7

    print("%s:$odf$*%s*%s*%s*%s*%s*%d*%s*%d*%s*%d*%s" % (nama_file, tipe_algoritma,
            checksum_type, hitungan_iterasi, ukuran_kunci, checksum, len(iv) // 2,
            iv, len(salt) // 2, salt, 0, binascii.hexlify(content[:1024]).decode('ascii')))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: %s <File OpenOffice / LibreOffice>" % sys.argv[0], file=sys.stderr)
        sys.exit(-1)

    for i in range(1, len(sys.argv)):
        proses_file(sys.argv[i])
