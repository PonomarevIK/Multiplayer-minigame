import socket
from _thread import start_new_thread

client_last_message = {}
client_id = 0
max_connections = 2

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = "localhost"
port = 9999

sock.bind((server, port))
sock.listen(max_connections)


def client_thread(connection, address, client_id):
    connection.send(str(client_id).encode())

    while True:
        try:
            data = connection.recv(1024).decode()
            if not data:
                break

            client_last_message[client_id] = data
            print(f"received: '{data}' from {client_id}")
            if len(client_last_message) == 1:
                connection.send("idle".encode())
            for id, message in client_last_message.items():
                if id != client_id:
                    connection.send(f"{client_id}:{data}".encode())
        except socket.error as error:
            print(error)
            break

    print(f"Connection with {address} closed.")
    connection.close()


while client_id < max_connections:
    connection, address = sock.accept()
    print(f"Connected to player {client_id} at {address}")
    client_last_message[client_id] = "idle"

    start_new_thread(client_thread, (connection, address, client_id))
    client_id += 1
