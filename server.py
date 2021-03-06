import socket
import threading

client_last_message = {}
current_client_id = 0
max_connections = 4

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_ip = input("Server ip (leave blank for localhost): ") or "localhost"
port = 9999

sock.bind((server_ip, port))
sock.listen(max_connections)


def client_thread(connection, address, client_id):
    client_last_message[client_id] = b"joined:0"
    connection.send(str(client_id).encode())

    while True:
        try:
            data = connection.recv(4096)
            if not data:
                break
            if len(client_last_message) == 1:
                connection.send(b"empty")
                continue
            client_last_message[client_id] = data
            for id, message in client_last_message.items():
                if id != client_id:
                    connection.sendall(f"{id}-".encode() + message)
        except socket.error as error:
            print(error)
            break

    print(f"Connection with {address} closed.")
    del client_last_message[client_id]
    connection.close()


while True:
    connection, address = sock.accept()
    print(f"Connected to player {current_client_id} at {address}")
    threading.Thread(target=client_thread, args=(connection, address, current_client_id)).start()

    current_client_id += 1
