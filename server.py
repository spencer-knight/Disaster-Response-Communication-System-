import socket
import threading
import random
import json
import math

HOST = 'localhost'
PORT = 5000
RANGE = 100

clients = {}  
clients_lock = threading.Lock()

def distance(gps1, gps2):
   x1, y1 = gps1
   x2, y2 = gps2
   return math.sqrt((x2 - x1)**2 + (y2-y1)**2)

def process_packet(conn, addr, data):
  #print(data)
  packet = json.loads(data);
  responsePacket = {
      "cmd" : None,
      "data" : None
  }
  #json.dumps({"cmd" : None, "data" : None})
  if packet.get("cmd") == "clientBroadcast":
      #do broadcasting logic here, just responding for now
      responsePacket["data"] = packet["data"]
      responsePacket["cmd"] = "serverBroadcast"
      with clients_lock:
        gps = clients[addr]["gps"]
        for addr_c,client in clients.items():
          if addr_c != addr:
            print(distance(gps, client["gps"]))
            if distance(gps, client["gps"]) < RANGE:
              client["connection"].sendall(json.dumps(responsePacket).encode())
            
  if packet.get("cmd") == "clientGPS":
    responsePacket["cmd"] = "serverGPS"
    with clients_lock:
      responsePacket["data"] = clients[addr]["gps"]
    conn.sendall(json.dumps(responsePacket).encode())

def generate_random_coordinates():
    lat = round(random.uniform(-100, 100), 6)
    lon = round(random.uniform(-100, 100), 6)
    return (lat, lon)

def handle_client(conn, addr):
    gps = generate_random_coordinates()
    print(f"[NEW CONNECTION] {addr} connected. {gps}")
    
    with clients_lock:
        clients[addr] = {
            'connection': conn,
            'gps': gps,
            'messages': []
        }
    
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode()
            print(f"[{addr}] {message}")
            
            with clients_lock:
                clients[addr]['messages'].append(message)
            
            process_packet(conn, addr, data)

    with clients_lock:
        print(f"[DISCONNECTED] {addr} removed.")
        clients.pop(addr)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    main()
