import socket

connections = []
current_id = 0

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket:
    socket.bind(('localhost', 9999))
    socket.listen(2)
    conn, address = socket.accept()
    print(f"connected to {address}")
    if address not in connections:
        connections.append(address)
        conn.send(str(current_id).encode())
        current_id += 1

    while True:
        data = conn.recv(1024)
        print(f"received: {data}")
        conn.send(b"ok buddy")
        if not data:
            break

    conn.close()
