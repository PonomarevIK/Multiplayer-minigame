import socket as sock


class Network:
    def __init__(self, host="localhost", port=9999):
        self.socket = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        self.host = host
        self.port = port
        self.address = (self.host, self.port)

    def request_id(self) -> str:
        if self.host == "0":    # Offline mode for debugging
            return "0"

        print("Connecting...")
        while True:
            try:
                self.socket.connect(self.address)
                print(f"Successfully connected to {self.host}:{self.port}")
                return self.socket.recv(1024).decode()
            except sock.error as error:
                print(error)

    def send(self, data: str) -> str:
        if self.host == "0":
            return "ok"

        try:
            self.socket.send(data.encode())
            return self.socket.recv(1024).decode()
        except sock.error as error:
            print(error)
