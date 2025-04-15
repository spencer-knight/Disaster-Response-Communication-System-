import socket
import threading
import random
import json

HOST = 'localhost'
PORT = 5000

clients = {}  
clients_lock = threading.Lock()

def process_packet(conn, addr, data):
  print(data)
  packet = json.loads(data);
  responsePacket = {
      "cmd" : None,
      "data" : None
  }
  #json.dumps({"cmd" : None, "data" : None})
  if packet.get("cmd") == "clientBroadcast":
      #do broadcasting logic here, just responding for now
      packet["data"] = packet["data"] + " received by server."
      packet["cmd"] = "serverBroadcast"
      conn.sendall(json.dumps(packet).encode())
  if packet.get("cmd") == "clientGPS":
    responsePacket["cmd"] = "serverGPS"
    with clients_lock:
      responsePacket["data"] = clients[addr]["gps"]
    conn.sendall(json.dumps(responsePacket).encode())
    
    
  #conn.sendall(json.dumps({"cmd" : "serverBroadcast", "data" : "lah dee doo dah day"}).encode())


def generate_random_coordinates():
    lat = round(random.uniform(-100, 100), 6)
    lon = round(random.uniform(-100, 100), 6)
    return (lat, lon)

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    gps = generate_random_coordinates()
    
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
            #conn.sendall(json.dumps({"serverBroadcast": "test"}).encode())

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
