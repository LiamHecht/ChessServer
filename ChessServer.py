import socket
import threading
import time
import logging
import datetime

from decorators import log_function_call

HOST = '127.0.0.1'
PORT = 8080
MAX_CONNECTIONS = 2

waiting_players = {}
players = []
game_rooms = {}

def delete_game_room(username):
    if username in game_rooms:
        for sock, _ in game_rooms[username]:
            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except OSError as e:
                print(f"Error closing socket for {username}: {e}")
        del game_rooms[username]

def notify_opponent_of_disconnection(disconnected_username):
    # Find the opponent in the game room
    print(game_rooms.items)
    for room_username, room_players in game_rooms.items():
        for _, player_username in room_players:
            if player_username != disconnected_username:
                opponent_socket, opponent_username = room_players[0] if room_players[1][1] == disconnected_username else room_players[1]

                # Notify the opponent of the disconnection
                message = f"You win! {disconnected_username} has disconnected. "
                opponent_socket.sendall(message.encode('utf-8'))
                break

@log_function_call
def match_players():
    while True:
        if len(waiting_players) >= MAX_CONNECTIONS:
            usernames = list(waiting_players.keys())

            # Iterate over all possible pairs to find the best match
            matched = False
            for i in range(len(usernames) - 1):
                for j in range(i + 1, len(usernames)):
                    player1 = usernames[i]
                    player2 = usernames[j]

                    player1_info = waiting_players[player1]
                    player2_info = waiting_players[player2]

                
                    # Check if players are still connected before creating a game room
                    if player1_info[0].fileno() != -1 and player2_info[0].fileno() != -1:
                        # Extract usernames from players
                        username1 = player1_info[1]
                        username2 = player2_info[1]

                        print(player1_info)
                        print(player2_info)
                        # print("username1:" + username1)
                        # print("username2:" + username2)
                        
                        # print("player1 : " + player1_info[2])
                        # print("player2 : " + player2_info[2])
                        player1_opponent = player1_info[2].replace("\n",'')
                        player2_opponent = player2_info[2].replace("\n",'')
                        print(player1_opponent)
                        print(player2_opponent)
                        
                        # Ensure that players requested each other as opponents
                        if username1 == player2_opponent and username2 == player1_opponent:
                            print("*"*20)
                            # Update game_rooms with usernames
                            game_rooms[username1] = [(player1_info[0], username1), (player2_info[0], username2)]
                            game_rooms[username2] = [(player1_info[0], username1), (player2_info[0], username2)]

                            print(f"Game room created for {username1} and {username2}")

                            # Send "gameStarted" to both players
                            player1_info[0].sendall("gameStarted\n".encode('utf-8'))
                            player2_info[0].sendall("gameStarted\n".encode('utf-8'))

                            player1_info[0].sendall(f"username:{username2}\n".encode('utf-8'))
                            player2_info[0].sendall(f"username:{username1}\n".encode('utf-8'))

                            print("game started sent")

                            logging.info(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Matched players: {username1}, {username2}")

                            # Start a new thread to handle the players in the same room
                            threading.Thread(target=handle_client, args=(player1_info[0], username1)).start()
                            threading.Thread(target=handle_client, args=(player2_info[0], username2)).start()

                            # Remove players from the waiting list
                            del waiting_players[player1]
                            del waiting_players[player2]

                            matched = True
                            break

            # If no match is found, wait for more players to join
            if not matched:
                time.sleep(1)

def handle_client(client_socket, username):
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                # Empty data indicates client disconnected
                break

            print(data)

            if data == "gameOver":
                # Notify opponent before deleting the game room
                notify_opponent_of_disconnection(username)
                delete_game_room(username)
                break

            if username in game_rooms:
                other_players = [sock for sock, user in game_rooms[username] if user != username]
                if other_players:
                    other_player_socket = other_players[0]
                    other_player_socket.sendall(data.encode('utf-8'))

    except Exception as e:
        print(f"Error handling client {username}: {e}")

    finally:
        if username in game_rooms:
            client_socket.close()
        else:
            # If the game room is already deleted, notify opponent and close the client socket
            notify_opponent_of_disconnection(username)
            client_socket.close()

def check_socket_connections():
    while True:
        # Check players in game rooms
        for username, player_socket in players:
            try:
                player_socket[0].sendall("ping\n".encode('utf-8'))
            except Exception as e:
                print(f"Socket check for {username} in game room: {e}")
                # Handle disconnection, notify opponent, and clean up
                notify_opponent_of_disconnection(username)
                delete_game_room(username)
        time.sleep(5)

def accept_connections():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        print(f"Server listening on {HOST}:{PORT}")

        # Start a thread to match players
        threading.Thread(target=match_players).start()

        # Start the socket check thread
        threading.Thread(target=check_socket_connections).start()

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection accepted from {addr}")

            # Receive the username and opponent from the client
            message = client_socket.recv(1024).decode('utf-8')
            username, opponent = message.split('vs')
            print("username :"  + username)
            print("opponent :"  + opponent)
            
            # Add both players to the waiting list
            waiting_players[username] = (client_socket, username, opponent)

            players.append((username, (client_socket, addr)))
    except Exception as e:
        print(f"Error in the server: {e}")

    finally:
        server_socket.close()

        # Clean up game rooms if the server is shutting down
        for username in list(game_rooms.keys()):
            delete_game_room(username)

if __name__ == '__main__':
    accept_connections()
