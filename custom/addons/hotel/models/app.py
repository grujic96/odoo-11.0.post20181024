import socket
import threading


def status_sobaa(self):
    threading.Timer(10.0, status_sobaa).start()
    i=0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 80))
    while i<=5:
        data, address = sock.recvfrom(512)
        print(address)
        print(data)
        data[2:]
        databits = bin(data[4])
        if data[3] == 241:
            s = databits[2:].zfill(8)
            if s == 0:
                bool = False
            elif s == 1:
                bool = True
            print(s)
        i+=1
status_sobaa()
    #bit s[0] - SOS
    #bit s[1] - poziv osoblju
    #bit s[2] - ne uznemiravaj
    #bit s[7] - gost u sobi

