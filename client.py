import socket
import threading

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 8080         # The port used by the server

def receive_messages(client_socket):
    while True:
        try:
            # Receiving a response from the server
            response = client_socket.recv(1024).decode('utf-8')
            if not response:
                break
            print("Response from server:", response)
        except Exception as e:
            print("Error receiving message:", e)
            break

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        print("Connected to the server.")
        
        # Start a thread to continuously receive messages from the server
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.start()
        
        try:
            while True:
                # Sending a message to the server
                message = input("Enter your message (type 'exit' to quit): ")
                if message.lower() == 'exit':
                    break
                client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print("Error sending message:", e)
        
        # Wait for the receive thread to finish before closing the socket
        receive_thread.join()

if __name__ == "__main__":
    main()
