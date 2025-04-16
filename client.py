import socket
import json
import threading
import time
import uuid

HOST = 'localhost'
PORT = 5000

# AODV message types
AODV_RREQ   = "AODV_RREQ"
AODV_RREP   = "AODV_RREP"
AODV_DATA   = "AODV_DATA"

CLIENT_ID = input("Enter client ID: ")

routing_table = {}
received_rreq = set()
forwarded_data_packets = set()
forwarded_rrep_packets = set()

client_socket = None

def process_packet(data):
    packet = json.loads(data.decode())
    cmd = packet.get("cmd")
    
    if cmd == "serverGPS":
        print(f"Your current GPS is {packet['data']}.")
    elif cmd == "serverBroadcast":
        print(f"[SERVER BROADCAST] {packet['data']}")
    elif cmd == AODV_RREQ:
        handle_aodv_rreq(packet)
    elif cmd == AODV_RREP:
        handle_aodv_rrep(packet)
    elif cmd == AODV_DATA:
        handle_aodv_data(packet)
    else:
        print(f"[WARN] Unknown packet received: {packet}")

def handle_aodv_rreq(packet):
    broadcast_id = packet.get("broadcast_id")
    src = packet.get("src")
    if src == CLIENT_ID:
        return
    if broadcast_id in received_rreq:
        return
    received_rreq.add(broadcast_id)
    dst = packet.get("dst")
    hop_count = packet.get("hop_count", 0)
    print(f"[RREQ] From {src} -> {dst}")
    
    if CLIENT_ID == dst:
        rrep = {
            "cmd": AODV_RREP,
            "src": dst,          # The destination
            "dst": src,          # The original requester
            "hop_count": 0,
            "sequence": int(time.time()),
            "path": [CLIENT_ID]  # Starting path with my own ID
        }
        send_packet(json.dumps(rrep))
        print(f"[RREP] I am destination. Sending RREP to {src}")
    else:
        if dst in routing_table:
            route = routing_table[dst]
            rrep = {
                "cmd": AODV_RREP,
                "src": dst,
                "dst": src,
                "hop_count": route['hop_count'] + 1,
                "sequence": route['sequence'],
                "path": [CLIENT_ID]
            }
            send_packet(json.dumps(rrep))
            print(f"[RREP] Forwarding RREP for {dst} to {src}")
        else:
            packet["hop_count"] = hop_count + 1
            send_packet(json.dumps(packet))
            print(f"[RREQ] Rebroadcasting RREQ for {dst}")

def handle_aodv_rrep(packet):
    packet_id = f"{packet.get('src')}_{packet.get('dst')}_{packet.get('sequence')}"
    if packet_id in forwarded_rrep_packets:
        return
    forwarded_rrep_packets.add(packet_id)
    
    src = packet.get("src")   # The destination of the original route discovery
    dst = packet.get("dst")   # The original source of the RREQ (i.e. where RREP should go)
    hop_count = packet.get("hop_count", 0)
    sequence = packet.get("sequence")
    path = packet.get("path", [])
    
    routing_table[src] = {
        "next_hop": None,
        "hop_count": hop_count + 1,
        "sequence": sequence,
        "timestamp": time.time()
    }
    print(f"[RREP] Received for route {src} → {dst} | Path: {path}")
    
    if dst != CLIENT_ID:
        if CLIENT_ID not in path:
            path.append(CLIENT_ID)
            packet["path"] = path
            packet["hop_count"] = hop_count + 1
            send_packet(json.dumps(packet))
            print(f"[RREP] Forwarding to {dst} | New Path: {path}")
        else:
            print(f"[RREP] Dropped. Already in path: {path}")

def handle_aodv_data(packet):
    packet_id = packet.get("id")
    if packet_id in forwarded_data_packets:
        return
    forwarded_data_packets.add(packet_id)
    
    dst = packet.get("dst")
    src = packet.get("src")
    path = packet.get("path", [])
    print(f"[DATA] Received | From: {src} → To: {dst} | Path: {path}")
    
    if dst == CLIENT_ID or dst == "BROADCAST":
         print(f"[DELIVERED] Message from {src}: {packet.get('data')}")
    else:
        if CLIENT_ID not in path:
            packet["hop_count"] = packet.get("hop_count", 0) + 1
            path.append(CLIENT_ID)
            packet["path"] = path
            send_packet(json.dumps(packet))
            print(f"[FORWARD] Data packet ID: {packet_id} → {dst} | New Path: {path}")
        else:
            print(f"[SKIP] Packet ID: {packet_id} already contains this node.")

def send_packet(packet_str):
    try:
        client_socket.sendall(packet_str.encode())
    except Exception as e:
        print("Error sending packet:", e)

def listen_for_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if data:
                process_packet(data)
        except Exception as e:
            print("Error receiving data:", e)
            break

def initiate_route_discovery(destination):
    rreq_packet = {
        "cmd": AODV_RREQ,
        "src": CLIENT_ID,
        "dst": destination,
        "hop_count": 0,
        "broadcast_id": str(uuid.uuid4()),
        "origin_seq": int(time.time())
    }
    print(f"[INIT] Starting route discovery → {destination}")
    send_packet(json.dumps(rreq_packet))

def send_aodv_data(dst, data_msg):
    if dst != "BROADCAST" and dst not in routing_table:
        print(f"[INFO] No route to {dst}. Route discovery initiated...")
        initiate_route_discovery(dst)
        time.sleep(2)
        if dst not in routing_table:
            print(f"[WARN] Route to {dst} not found. Aborting message.")
            return

    packet = {
        "cmd": AODV_DATA,
        "src": CLIENT_ID,
        "dst": dst,
        "data": data_msg,
        "hop_count": 0,
        "path": [CLIENT_ID],
        "id": str(uuid.uuid4())
    }
    send_packet(json.dumps(packet))
    print(f"[SEND] AODV_DATA sent → {dst}")

def main():
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    
    # Start the receiver thread.
    receiver_thread = threading.Thread(target=listen_for_messages, args=(client_socket,), daemon=True)
    receiver_thread.start()

    while True:
        print("\nOptions:")
        print("1. Broadcast a message (server mediated)")
        print("2. Send message via AODV routing")
        print("3. Get GPS location from server")
        print("4. Quit")
        choice = input("Enter your choice (1/2/3/4): ")

        if choice == "1":
            msg = input("Enter message to broadcast: ")
            json_packet = json.dumps({"cmd": "clientBroadcast", "data": msg})
            send_packet(json_packet)
        elif choice == "2":
            dst = input("Enter destination node ID (or type 'BROADCAST'): ")
            msg = input("Enter message to send: ")
            send_aodv_data(dst, msg)
        elif choice == "3":
            json_packet = json.dumps({"cmd": "clientGPS", "data": None})
            send_packet(json_packet)
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, or 4.")

    client_socket.close()

if __name__ == "__main__":
    main()
