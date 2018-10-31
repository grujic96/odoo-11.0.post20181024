import socket
import threading


i = 0
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 80))
while i<=2:
    print('proso')
    data, address = sock.recvfrom(500)
    print(data)
    if data[3] == 241:
        print(data)
    i += 1