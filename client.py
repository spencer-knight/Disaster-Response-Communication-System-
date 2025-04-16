import socket
import json
import threading
import time

HOST = 'localhost'
PORT = 5000

# AODV message types
AODV_RREQ   = "AODV_RREQ"
AODV_RREP   = "AODV_RREP"
AODV_DATA   = "AODV_DATA"

CLIENT_ID = input("Enter client ID: ")

# A simple routing table: destination -> route information
# For each entry: { 'next_hop': <node_id>, 'hop_count': <int>, 'sequence': <int>, 'timestamp': <float> }
routing_table = {}

# Set to record received route requests (by broadcast ID) to avoid duplicates.
received_rreq = set()

client_socket = None

def process_packet(data):
    packet = json.loads(data.decode())
    if packet.get("cmd") == "serverGPS":
        print(f"Your current gps is {packet['data']}.")
    elif packet.get("cmd") == "serverBroadcast":
        print(f"[BROADCAST] {packet['data']}")
        
    # AODV handling
    elif cmd == AODV_RREQ:
        handle_aodv_rreq(packet)
    elif cmd == AODV_RREP:
        handle_aodv_rrep(packet)
    elif cmd == AODV_DATA:
        handle_aodv_data(packet)
    else:
        print(f"Invalid packet.")
        print(packet.dumps())

def handle_aodv_rreq(packet):
    broadcast_id = packet.get("broadcast_id")
    if broadcast_id in received_rreq:
        # Duplicate RREQ received – ignore.
        return
    received_rreq.add(broadcast_id)
    
    src = packet.get("src")
    dst = packet.get("dst")
    hop_count = packet.get("hop_count")
    
    print(f"[AODV] Received RREQ from {src} for destination {dst} (hop count: {hop_count})")
    
    if CLIENT_ID == dst:
        rrep = {
            "cmd": AODV_RREP,
            "src": dst,
            "dst": src,
            "hop_count": 0,
            "sequence": int(time.time())
        }
        send_packet(json.dumps(rrep))
        print(f"[AODV] Sent RREP (I am the destination) from {CLIENT_ID} to {src}")
    else:
        if dst in routing_table:
            route = routing_table[dst]
            rrep = {
                "cmd": AODV_RREP,
                "src": dst,
                "dst": src,
                "hop_count": route['hop_count'] + 1,
                "sequence": route['sequence']
            }
            send_packet(json.dumps(rrep))
            print(f"[AODV] Sent RREP (using routing table) from {CLIENT_ID} to {src}")
        else:
            packet["hop_count"] = hop_count + 1
            send_packet(json.dumps(packet))
            print(f"[AODV] Rebroadcasted RREQ from {src} for destination {dst}")

def handle_aodv_rrep(packet):
    src = packet.get("src")
    dst = packet.get("dst")
    hop_count = packet.get("hop_count")
    sequence = packet.get("sequence")
    
    print(f"[AODV] Received RREP: route to {src} via {dst} (hop count: {hop_count})")
    
    routing_table[src] = {
        "next_hop": dst,
        "hop_count": hop_count + 1,
        "sequence": sequence,
        "timestamp": time.time()
    }
    print(f"[AODV] Updated routing table: {routing_table}")

def handle_aodv_data(packet):
    dst = packet.get("dst")
    if dst == CLIENT_ID or dst == "BROADCAST":
        print(f"[AODV DATA] Message from {packet.get('src')}: {packet.get('data')}")
    
def send_packet(packet_str):
    client_socket.sendall(packet_str.encode())

def listen_for_messages(sock):
    while True:
        data = sock.recv(1024)
        if data:
            process_packet(data)

def initiate_route_discovery(destination):
    rreq_packet = {
        "cmd": AODV_RREQ,
        "src": CLIENT_ID,
        "dst": destination,
        "hop_count": 0,
        "broadcast_id": str(uuid.uuid4()),
        "origin_seq": int(time.time())
    }
    print(f"[AODV] Initiating route discovery for destination {destination}")
    send_packet(json.dumps(rreq_packet))

def send_aodv_data(dst, data_msg):
    if dst != "BROADCAST" and dst not in routing_table:
        print(f"[AODV] No route known to destination {dst}. Initiating route discovery...")
        initiate_route_discovery(dst)
        time.sleep(2)
        if dst not in routing_table:
            print(f"[AODV] Route discovery failed or is still pending. Message not sent.")
            return

    packet = {
        "cmd": AODV_DATA,
        "src": CLIENT_ID,
        "dst": dst,
        "data": data_msg,
        "hop_count": routing_table[dst]["hop_count"] if dst in routing_table else 0
    }
    send_packet(json.dumps(packet))
    print(f"[AODV] Sent AODV_DATA message to {dst}")

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

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
        if choice == "2":
            dst = input("Enter destination node ID (or type 'BROADCAST' for network-wide message): ")
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
