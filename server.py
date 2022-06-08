import socket
import _thread

client_last_message = {}
current_client_id = 0
max_connections = 2

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = "26.8.152.253"
port = 9999

sock.bind((server, port))
sock.listen(max_connections)


def client_thread(connection, address, client_id):
    client_last_message[client_id] = b"idle:0"
    connection.send(str(client_id).encode())

    while True:
        try:
            data = connection.recv(1024)
            if not data:
                break
            if len(client_last_message) == 1:
                connection.send(b"empty")
                continue
            client_last_message[client_id] = data
            for id, message in client_last_message.items():
                if id != client_id:
                    connection.send(f"{id}:".encode() + message)
        except socket.error as error:
            print(error)
            break

    print(f"Connection with {address} closed.")
    del client_last_message[client_id]
    connection.close()


while current_client_id <= max_connections:
    connection, address = sock.accept()
    print(f"Connected to player {current_client_id} at {address}")
    _thread.start_new_thread(client_thread, (connection, address, current_client_id))

    current_client_id += 1
