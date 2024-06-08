import socket
import threading
import time
import logging
import datetime
import json 
from decorators import log_function_call
import fireBaseUtils

HOST = '127.0.0.1'
PORT = 8080
MAX_CONNECTIONS = 2

waiting_players = {}
players = []
game_rooms = {}
pgn_list = []


# def delete_game_room(username):
#     fireBaseUtils.delete_document_by_name(username)
#     if username in game_rooms:
#         # Check if the game room is not empty
#         if game_rooms[username]:
#             # Iterate over the list of players and their sockets
#             for player_info in game_rooms[username]['players']:
#                 sock = player_info[0]
#                 try:
#                     sock.shutdown(socket.SHUT_RDWR)
#                     sock.close()
#                     print(f"{username}'s socket has been")
#                 except OSError as e:
#                     print(f"Error closing socket for {username}: {e}")
#         # Delete the game room entry
#         del game_rooms[username]
def delete_game_room(username):
    if not game_rooms[username]:
        return
    opponent_username = game_rooms[username]['players'][1][1]
    fireBaseUtils.delete_document_by_name(username)
    fireBaseUtils.delete_document_by_name(opponent_username)
    # Close all sockets for the game room
    for player_socket, _ in game_rooms[username]['players']:
        player_socket.close()
        
    # Get opponent's username
    opponent_username = game_rooms[username]['players'][1][1]
    #test
    # Delete the game room entry
    del game_rooms[username]
    del game_rooms[opponent_username]

def notify_opponent_of_disconnection(disconnected_username):
    # Find the opponent in the game room
    for room_username, room_players, _ in game_rooms.values():
        for _, player_username in room_players:
            if player_username != disconnected_username:
                opponent_socket, opponent_username = room_players[0] if room_players[1][1] == disconnected_username else room_players[1]

                # Notify the opponent of the disconnection
                message = f"You win! {disconnected_username} has disconnected. "
                opponent_socket.sendall(message.encode('utf-8'))
                break  # Break out of inner loop
        else:
            continue  # Continue to the next iteration of the outer loop
        break  # Break out of the outer loop


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

                        player1_opponent = player1_info[2].replace("\n", '')
                        player2_opponent = player2_info[2].replace("\n", '')

                        # Ensure that players requested each other as opponents
                        if username1 == player2_opponent and username2 == player1_opponent:
                            # Update game_rooms with usernames and an empty list for moves
                            game_rooms[username1] = {
                                'players': [(player1_info[0], username1), (player2_info[0], username2)],
                                'moves': []
                            }
                            game_rooms[username2] = {
                                'players': [(player2_info[0], username2), (player1_info[0], username1)],
                                'moves': []
                            }

                            print(f"Game room created for {username1} and {username2}")

                            # Send "gameStarted" to both players
                            player1_info[0].sendall("gameStarted\n".encode('utf-8'))
                            player2_info[0].sendall("gameStarted\n".encode('utf-8'))

                            player1_info[0].sendall(f"username:{username2}\n".encode('utf-8'))
                            player2_info[0].sendall(f"username:{username1}\n".encode('utf-8'))

                            print("game started sent")

                            logging.info(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Matched players: {username1}, {username2}")

                            # Start a new thread to handle the players in the same room
                            threading.Thread(target=handle_client, args=(player1_info[0], username1, username2)).start()
                            threading.Thread(target=handle_client, args=(player2_info[0], username2, username1)).start()

                            # Remove players from the waiting list
                            del waiting_players[player1]
                            del waiting_players[player2]

                            matched = True
                            break

            # If no match is found, wait for more players to join
            if not matched:
                time.sleep(1)
                
                
def handle_client(client_socket, username, opponent_username):
    try:
        while True:
            if not game_rooms[username]:
                return
            data = client_socket.recv(1024).decode('utf-8')
            print(f"{username} has sent {data}")
            print("Game rooms :" + str(game_rooms[username]))

            if "rating:" in data:
                # Extract rating from data
                rating = data.split(":")[1].strip()
                # Add rating to the game room of the player
                if username in game_rooms:
                    game_rooms[username]['rating'] = rating
            if "move:" in data:
                # Handle move if needed
                move = data.split(":")[1].strip()
                game_rooms[username]['moves'].append(move)
                game_rooms[opponent_username]['moves'].append(move)
            if "gameOver" in data:
                # Notify opponent before deleting the game room
                # notify_opponent_of_disconnection(username)
                delete_game_room(username)
                return

            if client_socket.fileno() != -1:  # Check if the socket is still open
                if username in game_rooms:
                    players_and_moves = game_rooms[username]['players']
                    for player_socket, user in players_and_moves:
                        if user != username and player_socket.fileno() != -1:  # Check if opponent's socket is open
                            player_socket.sendall(data.encode('utf-8'))

    except Exception as e:
        print(f"Error handling client {username}: {e}")

    finally:
        client_socket.close()


def handle_move(username, move):
    # Append the move to the list of moves for the game room
    if username in game_rooms:
        game_rooms[username][-1].append(move)
        print("Moves : " + game_rooms[username][-1])

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
        # threading.Thread(target=check_socket_connections).start()

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection accepted from {addr}")

            # Receive the message from the client
            message = client_socket.recv(1024).decode('utf-8')
            if message.startswith("spectator:"):
                # Handle the case when a spectator joins
                handle_spectator_join(message, client_socket, addr)
            else:
                # Handle the case when a regular player joins
                handle_player_join(message, client_socket, addr)

    except Exception as e:
        print(f"Error in the server: {e}")

    finally:
        server_socket.close()

        # Clean up game rooms if the server is shutting down
        for username in list(game_rooms.keys()):
            delete_game_room(username)


def handle_spectator_join(message, client_socket, addr):
    # Split the message to extract relevant information
    _, spectator_username, room_players = message.split(":")
    player1, player2 = room_players.split("VS")
    player2 = player2.replace("\n",'')
    # Add the spectator to the game room of player1 and player2
    add_spectator_to_game_room(player1, client_socket, spectator_username)
    add_spectator_to_game_room(player2, client_socket, spectator_username)

    moves_list = game_rooms[player1]['moves']
    ratings = f"{player1}:{game_rooms[player1]['rating']}-{player2}:{game_rooms[player2]['rating']}"
    
    # Send the moves list and the ratings to the spectator
    send_moves_to_spectator(client_socket, moves_list)
    send_ratings_to_spectator(client_socket, ratings)
    #TODO ask players for current timers and send it to the spectator
    
    # Add the spectator to the players list for socket checking
    players.append((spectator_username, (client_socket, addr)))
    
def send_moves_to_spectator(spectator_socket, ratings):
    print("Sending ratings to spectator:", ratings)
    ratings_json = json.dumps(ratings)
    print("Encoded moves list:", ratings_json)
    spectator_socket.sendall(f"move_list:{ratings_json}\n".encode('utf-8'))
    
def send_ratings_to_spectator(spectator_socket, ratings):
    
    print(f"Sending ratings to spectator: {ratings}")
    spectator_socket.sendall(f"ratings:{ratings}\n".encode('utf-8'))

def add_spectator_to_game_room(player_username, spectator_socket, spectator_username):
    if player_username in game_rooms:
        # Add the spectators socket to the game room of the player
        game_rooms[player_username]['players'].append((spectator_socket, spectator_username))
        print(f"Spectator {spectator_username} joined the game room of {player_username}")
    else:
        print(f"Error: Player {player_username} not found.")
        
        
def handle_player_join(message, client_socket, addr):
    # Extract the username and opponent from the message
    username, opponent = message.split('vs')
    print("username :" + username)
    print("opponent :" + opponent)

    # Add both players to the waiting list
    waiting_players[username] = (client_socket, username, opponent)

    players.append((username, (client_socket, addr)))
    
    
if __name__ == '__main__':
    accept_connections()
