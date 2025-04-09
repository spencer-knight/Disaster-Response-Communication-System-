import socket

HOST = 'localhost'
PORT = 5000

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    client_socket.sendall(b"Hello from client node!")
    data = client_socket.recv(1024)

    print(f"[CLIENT] Received: {data.decode()}")

    while True:
        print("\nOptions:")
        print("1. Broadcast a message")
        print("2. Get GPS location from server")
        print("3. Quit")
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            msg = input("Enter message to broadcast: ")
            json_packet = json.dumps({"broadcast": msg})
            client_socket.sendall(json_packet.encode())
            data = client_socket.recv(1024)
            if data:
                print(f"[SERVER] {data.decode()}")
        elif choice == "2":
            json_packet = json.dumps({"get_gps": None})
            client_socket.sendall(json_packet.encode())
            data = client_socket.recv(1024)
            if data:
                print(f"[SERVER] {data.decode()}")
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

    client_socket.close()

if __name__ == "__main__":
    main()
