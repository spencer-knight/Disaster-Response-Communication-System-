import socket
import threading
import random
import json
import math

HOST = 'localhost'
PORT = 5000
RANGE = 12
GRID_SIZE = 15
NUM_MOUNTAINS = 20

clients = {}
clients_lock = threading.Lock()

terrain_map = [[0 for point in range(GRID_SIZE)] for point in range(GRID_SIZE)]
terrain_map_lock = threading.Lock()

print_lock = threading.Lock()

client_count = 0
client_count_lock = threading.Lock()

def print_map():
    with print_lock:
      print("")
      for row in terrain_map:
          line = ""
          for point in row:
              if point == 0:
                  line += "."
              elif point == 1:
                  line += "#"
              else:
                  #display nodes on map in order of connection
                  line += str(point - 1)
          print(line)
      print("")

def create_line(gps1, gps2):
    points = []
    x0, y0 = gps1
    x1, y1 = gps2
    dx = x1 - x0
    dy = y1 - y0

    xsign = 1 if dx > 0 else -1
    ysign = 1 if dy > 0 else -1

    dx = abs(dx)
    dy = abs(dy)

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    D = 2 * dy - dx
    y = 0

    for x in range(dx + 1):
        points.append((x0 + x * xx + y * yx, y0 + x * xy + y * yy))
        if D >= 0:
            y += 1
            D -= 2 * dx
        D += 2 * dy

    return points

def is_transmission_occluded(gps1, gps2):
    for x, y in create_line(gps1, gps2):
        if terrain_map[y][x] == 1:
            return True
    return False

def distance(gps1, gps2):
    x1, y1 = gps1
    x2, y2 = gps2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def process_packet(conn, addr, data):
    packet = json.loads(data)
    responsePacket = {
        "cmd": None,
        "data": None
    }

    if packet.get("cmd") == "clientBroadcast":
        responsePacket["data"] = packet["data"]
        responsePacket["cmd"] = "serverBroadcast"
        with clients_lock:
            gps = clients[addr]["gps"]
            for addr_c, client in clients.items():
                if addr_c != addr:
                    if distance(gps, client["gps"]) < RANGE and not is_transmission_occluded(gps, client["gps"]):
                        client["connection"].sendall(json.dumps(responsePacket).encode())

    elif packet.get("cmd") == "setGPS":
        with clients_lock:
            with terrain_map_lock:
                num = terrain_map[clients[addr]["gps"][1]][clients[addr]["gps"][0]]
                terrain_map[clients[addr]["gps"][1]][clients[addr]["gps"][0]] = 0
                clients[addr]["gps"]= (int(packet.get("x")), int(packet.get("y")))
                terrain_map[clients[addr]["gps"][1]][clients[addr]["gps"][0]] = num
                print_map()


    elif packet.get("cmd") == "clientGPS":
        responsePacket["cmd"] = "serverGPS"
        with clients_lock:
            responsePacket["data"] = clients[addr]["gps"]
        conn.sendall(json.dumps(responsePacket).encode())

    elif packet.get("cmd") in ["AODV_RREQ", "AODV_RREP", "AODV_DATA"]:
      with clients_lock:
          sender_gps = clients[addr]["gps"]
          for addr_c, client in clients.items():
              if addr_c != addr:
                  target_gps = client["gps"]
                  dist = distance(sender_gps, target_gps)
                  if dist < RANGE:
                      if not is_transmission_occluded(sender_gps, target_gps):
                          client["connection"].sendall(json.dumps(packet).encode())
                          with print_lock:
                            #I'd like to change this to to say which type of packet
                            print(f"AODV packet from {clients[addr]["id"]} to {client["id"]} sent")
                      #else:
                          #print(f"AODV packet from {sender_gps} to {target_gps} blocked by mountain.")
                  #else:
                      #print(f"AODV packet from {sender_gps} to {target_gps} not sent due to distance ({dist:.2f} beyond range).")

def generate_random_coordinates():
    x = random.randint(0, GRID_SIZE - 1)
    y = random.randint(0, GRID_SIZE - 1)
    return (x, y)

def handle_client(conn, addr):
    global client_count
    gps = generate_random_coordinates()
    with terrain_map_lock:
      terrain_map[gps[1]][gps[0]] = 2 + len(clients)
    print_map()
    with print_lock:
      print(f"[NEW CONNECTION] {addr} connected. {gps}")

    with clients_lock:
        with client_count_lock:
          client_count += 1
          clients[addr] = {
              'connection': conn,
              'gps': gps,
              'id' : client_count,
              'messages': []
          }

    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode()
            #print(f"[{addr}] {message}")

            with clients_lock:
                clients[addr]['messages'].append(message)

            process_packet(conn, addr, data)

    with clients_lock:
      with print_lock:
        print(f"[DISCONNECTED] {addr} removed.")
      clients.pop(addr)

def main():
    for point in range(NUM_MOUNTAINS):
        x = random.randint(0, GRID_SIZE - 1)
        y = random.randint(0, GRID_SIZE - 1)
        terrain_map[y][x] = 1
    print_map()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    with print_lock:
      print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        with print_lock:
          print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    main()
