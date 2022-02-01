#!/usr/bin/env python3

import socket, struct, time, argparse, os

# Argparser to handle the usage / argument handling
parser = argparse.ArgumentParser(description="Raw packet capturer for offline analysis")

# Arguments
parser.add_argument('--out', '-o', default='capture.pcap', help='Name of capture file. (Will save in local file directory)')

args = parser.parse_args()

if not '.pcap' in args.out:
    args.out = args.out + '.pcap'

capture_file = os.getcwd() + os.sep + args.out

with open(capture_file,"wb") as file_writer:

    file_writer.write(struct.pack('!IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1))

    s=socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(0x3))
    while True:
        t,p=time.time(),s.recvfrom(65535)
        ts=int(t)
        tu=int((t-ts)*1000000)

        file_writer.write(struct.pack('!IIII',ts,tu,len(p[0]),len(p[0]))+p[0])