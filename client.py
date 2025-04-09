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
      pass

    client_socket.close()

if __name__ == "__main__":
    main()
