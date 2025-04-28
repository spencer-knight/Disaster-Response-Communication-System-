import socket
import json
import threading
import time
import uuid

HOST = 'localhost'
PORT = 5000

AODV_RREQ   = "AODV_RREQ"
AODV_RREP   = "AODV_RREP"
AODV_DATA   = "AODV_DATA"

CLIENT_ID = input("Enter client ID: ")

MENU_DELAY = 2.0

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
    bid = packet["broadcast_id"]
    src = packet["src"]
    dst = packet["dst"]
    hop = packet.get("hop_count", 0)
    path = packet.get("path", [])

    if src == CLIENT_ID or bid in received_rreq:
        return
    received_rreq.add(bid)

    path = path + [CLIENT_ID]
    print(f"[RREQ] From {src}, current path [{ ' to '.join(path) }]")

    if CLIENT_ID == dst:
        rrep = {
            "cmd": AODV_RREP,
            "src": dst,
            "dst": src,
            "hop_count": 0,
            "sequence": int(time.time()),
            "path": path         
        }
        send_packet(json.dumps(rrep))
        print(f"[RREP] Sending reply from {dst} to {src}")
    else:
        fwd = dict(packet)
        fwd["hop_count"] = hop + 1
        fwd["path"] = path
        send_packet(json.dumps(fwd))


def handle_aodv_rrep(packet):
    pkt_id = f"{packet['src']}_{packet['dst']}_{packet['sequence']}"
    if pkt_id in forwarded_rrep_packets:
        return
    forwarded_rrep_packets.add(pkt_id)

    src  = packet["src"]   
    dst  = packet["dst"] 
    path = packet.get("path", [])

    if CLIENT_ID not in path:
        return
    idx = path.index(CLIENT_ID)
    next_hop_toward_dest = path[idx + 1]

    routing_table[src] = {
        "next_hop": next_hop_toward_dest,
        "hop_count": packet.get("hop_count", 0) + 1,
        "sequence": packet.get("sequence"),
        "timestamp": time.time()
    }

    if CLIENT_ID == dst:
        print(f"[RREP] Reply recieved from {src}")
        return

    prev_hop = path[idx - 1]
    fwd = dict(packet)
    fwd["dst"]       = prev_hop
    fwd["hop_count"] = packet.get("hop_count", 0) + 1
    send_packet(json.dumps(fwd))
    print(f"[RREP] Sending reply from {src} to {prev_hop}")


def handle_aodv_data(packet):
    packet_id = packet.get("id")
    if packet_id in forwarded_data_packets:
        return
    forwarded_data_packets.add(packet_id)
    
    dst = packet.get("dst")
    src = packet.get("src")
    path = packet.get("path", [])
    
    if dst == CLIENT_ID or dst == "BROADCAST":
        print(f"[DELIVERED] Message from {src}: {packet.get('data')}")
    else:
        if CLIENT_ID not in path:
            fwd = dict(packet)
            fwd["hop_count"] = packet.get("hop_count", 0) + 1
            fwd_path = path + [CLIENT_ID]
            fwd["path"] = fwd_path
            send_packet(json.dumps(fwd))

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
        "origin_seq": int(time.time()),
        "path": [CLIENT_ID]       
    }
    print(f"[RREQ] From {CLIENT_ID}, current path [{CLIENT_ID}]")
    send_packet(json.dumps(rreq_packet))

def build_and_send_data(dst, data_msg):
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

def wait_and_send(dst, data_msg, timeout=5.0, interval=0.1):
    waited = 0.0
    while waited < timeout:
        time.sleep(interval)
        waited += interval
        if dst in routing_table:
            build_and_send_data(dst, data_msg)
            return
    print(f"[ERROR] Route to {dst} not found. Aborting message.")

def send_aodv_data(dst, data_msg):
    if dst != "BROADCAST" and dst not in routing_table:
        print(f"[INFO] No route to {dst}. Route discovery initiated...")
        initiate_route_discovery(dst)
        threading.Thread(target=wait_and_send, args=(dst, data_msg), daemon=True).start()
        return

    build_and_send_data(dst, data_msg)

def main():
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    
    receiver_thread = threading.Thread(target=listen_for_messages, args=(client_socket,), daemon=True)
    receiver_thread.start()

    while True:
        print("\nOptions:")
        print("1. Broadcast a message (server mediated)")
        print("2. Send message via AODV routing")
        print("3. Get GPS location from server")
        print("4. Set GPS location.")
        print("5. Quit")
        choice = input("Enter your choice (1/2/3/4/5): ")

        if choice == "1":
            msg = input("Enter message to broadcast: ")
            json_packet = {"cmd": "clientBroadcast", "data": msg}
            send_packet(json.dumps(json_packet))  
        elif choice == "2":
            dst = input("Enter destination node ID (or type 'BROADCAST'): ")
            msg = input("Enter message to send: ")
            send_aodv_data(dst, msg)
        elif choice == "3":
            json_packet = {"cmd": "clientGPS", "data": None}
            send_packet(json.dumps(json_packet))
        elif choice == "4":
            x = input("Enter new x coordinate: ")
            y = input("Enter new y coordinate: ")
            json_packet = {"cmd": "setGPS", "x": x, "y": y}
            send_packet(json.dumps(json_packet))
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, or 4.")
        time.sleep(MENU_DELAY)

    client_socket.close()

if __name__ == "__main__":
    main()
