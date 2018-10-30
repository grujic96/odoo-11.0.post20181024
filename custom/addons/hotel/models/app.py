import socket
import threading


import websocket

ws = websocket.WebSocket()
ws.connect("ws://localhost:8069", http_proxy_host="localhost", http_proxy_port=3128)

