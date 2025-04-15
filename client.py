import socket
import json
import threading
import time

HOST = 'localhost'
PORT = 5000

def process_packet(data):
    packet = json.loads(data.decode())
    if packet.get("cmd") == "serverGPS":
        print(f"Your current gps is {packet['data']}.")
    elif packet.get("cmd") == "serverBroadcast":
        print(f"[BROADCAST] {packet['data']}")
    else:
        print(f"Invalid packet.")
        print(packet.dumps())

def listen_for_messages(client_socket):
    while True:
        #client_socket.settimeout(1.0)
        data = client_socket.recv(1024)
        if data:
            process_packet(data)

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    receiver_thread = threading.Thread(target=listen_for_messages, args=(client_socket,), daemon=True)
    receiver_thread.start()

    while True:
        print("\nOptions:")
        print("1. Broadcast a message")
        print("2. Get GPS location from server")
        print("3. Quit")
        choice = input("Enter your choice (1/2/3): ")

        if choice == "1":
            msg = input("Enter message to broadcast: ")
            json_packet = json.dumps({"cmd" : "clientBroadcast", "data" : msg})
            client_socket.sendall(json_packet.encode())
        elif choice == "2":
            json_packet = json.dumps({"cmd" : "clientGPS", "data" : None})
            client_socket.sendall(json_packet.encode())
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

    client_socket.close()

if __name__ == "__main__":
    main()
