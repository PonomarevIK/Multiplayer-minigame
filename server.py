import socket
import threading

clients = {}
client_id = 0
max_connections = 2

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = "localhost"
port = 9999

sock.bind((server, port))
sock.listen(max_connections)


def server(connection, address, client_id):
    global clients
    connection.send(str(client_id).encode())

    while True:
        data = connection.recv(1024)
        if not data:
            break
        for client in clients:
            if client != client_id:
                pass

        print(f"received: {data}")
        # connection.send(b"ok")

    print(f"Connection with {address} closed.")
    connection.close()


while client_id < max_connections:
    connection, address = sock.accept()
    print("Connected to", address)
    threading.Thread(target=server, args=(connection, address, client_id)).run()

    clients[client_id] = address
    client_id += 1
