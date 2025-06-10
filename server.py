import socket
import threading
import pickle
import json
import copy

HOST = '0.0.0.0' # any machine on same network can join '127.0.0.1' for only my machine
PORT = 7778

# standard block setup
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # af_inet -> IPv4 | sock_stream -> TCP
server.bind((HOST, PORT))
server.listen()


# Shared Game States
lobby = [] # (addr)

usernames = {} # player_id -> username
waiters = {} # lobby_id -> client socket
clients = {} # player_id -> client socket
games = {} # game_id -> game
# game -> {0: ["hello", "world"], 1: ["hello", "world"]}

library = {}
book = "harry-potter"
book_tokens = []

with open("library.json", "r") as f:
    library = json.load(f)
    book_tokens = library[book]

new_game = { 
    0 : {
        "text" : book_tokens.copy(),
        "buffer" : book_tokens[0],
        "peek" : book_tokens[1],
        "incoming" : [],
        "health" : 500,
        "mode" : 1, # 1 -> attack | 0 -> defend
        "multiplier" : 1, # multiplier
        "name" : "No Name"
    },

    1 : {
        "text" : book_tokens.copy(),
        "buffer" : book_tokens[0],
        "peek" : book_tokens[1],
        "incoming" : [],
        "health" : 500,
        "mode" : 1,
        "multiplier" : 1,
        "name" : "No Name"
    },
    
    "reset" : 0,
    "resetting" : 0,
    "start" : [0, 0], # bits representing ready or not
    "winner" : -1 # id of winner 0 or 1
}



counter = 0 # shared counter
lock = threading.Lock() # lock to prevent race conditions



def send_packet(conn, obj):
    data = pickle.dumps(obj)
    header = len(data).to_bytes(4, 'big')
    conn.sendall(header + data)

def recv_exact(conn, n):
    data = b'' # bytes
    while len(data) < n: # if i didn't get all data at once, keep looping till
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed during recv_exact")
        data += chunk

    return data


def recv_next_block(conn):
    header = recv_exact(conn, 4)
    total_len = int.from_bytes(header, 'big')
    data = recv_exact(conn, total_len)

    loaded_data = pickle.loads(data)

    return loaded_data


# this is good for giving shared information
def broadcast_state(game_id): # sends game to all connected clients in game
    with lock: # only one thread can read positions and counter at a time
        try:
            send_packet(clients[game_id * 2], games[game_id])
        except:
            pass
        try:
            send_packet(clients[game_id * 2 + 1], games[game_id])
        except:
            pass



def handle_client(conn, addr, player_id, game_id): # ran in another thread
    print(f"[NEW CONNECTION] {addr} connected as Player {player_id} with Game ID {game_id}.")

    send_packet(conn, (player_id, games[game_id]))# sending player id to client who just connected
    # broadcast_state(game_id)

    user_id = player_id % 2
    while True:
        # print(games)
        # print(usernames)

        try: # waiting to receive data from client
            msg = recv_next_block(conn)
            
            match msg:
                case "READY":
                    with lock:
                        games[game_id]["start"][user_id] = 1
                case "HI":
                    with lock:
                        pass
                        # print("hellooooo")
                
                case "INCOMING":
                    with lock:
                        for i in range(len(games[game_id][user_id]["incoming"])):
                            games[game_id][user_id]["incoming"][i][1] += 2
                
                case "OUTGOING":
                    with lock:
                        for i in range(len(games[game_id][user_id]["incoming"])):
                            games[game_id][user_id]["incoming"][i][2] -= 2
                    
                case "MODE": # switch modes
                    with lock:
                        games[game_id][user_id]["mode"] = not games[game_id][user_id]["mode"]
                
                case "INCREASE_MULTI": # add to multiplier
                    with lock:
                        games[game_id][user_id]["multiplier"] = round(games[game_id][user_id]["multiplier"] + 0.01, 2)


                case "RESET_MULTI": # missed a character
                    with lock:
                        games[game_id][user_id]["multiplier"] = 1
                        


                case tuple():
                    if msg[0] == "NAME":
                        with lock:
                            games[game_id][user_id]["name"] = msg[1]
                    else:
                        with lock:
                            multiplier = msg[0]
                            damage = msg[1]
                            games[game_id][user_id]["health"] -= multiplier * damage
                            games[game_id][user_id]["incoming"].pop(0)
                    

                case "DEFEND": # receive words
                    with lock:
                        games[game_id][user_id]["incoming"][0][0] = games[game_id][user_id]["incoming"][0][0][1:]
                        if games[game_id][user_id]["incoming"][0][0] == "": # empty
                            games[game_id][user_id]["incoming"].pop(0)

                case "ATTACK": # send words
                    with lock:
                        games[game_id][user_id]["buffer"] = games[game_id][user_id]["buffer"][1:]
                        if games[game_id][user_id]["buffer"] == "": # buffer is empty

                            popped = games[game_id][user_id]["text"].pop(0) # remove last element in text
                            games[game_id][not (user_id)]["incoming"].append([popped, 22, 550]) # pass first element to incoming for opponent [word, top right]
                            
                            # set next buffer
                            games[game_id][user_id]["buffer"] = games[game_id][user_id]["text"][0] 

                            # set next peek
                            games[game_id][user_id]["peek"] = games[game_id][user_id]["text"][1] # set peek again

                case "WINNER": # user wins
                    with lock:
                        games[game_id]["winner"] = user_id
                
                case "NOTIFY RESET":
                    with lock:
                        games[game_id]["reset"] = 1
                
                case "FINISH RESET":
                    with lock:
                        games[game_id]["resetting"] = 0

                case "RESET GAME": # reset game
                    with lock:
                        conn.setblocking(False)  # or conn.settimeout(0)

                        try:
                            while True:
                                data = conn.recv(4096)
                                if not data:
                                    break
                        except BlockingIOError:
                            # Nothing left to read
                            pass

                        conn.setblocking(True)  # Reset to normal
                        games[game_id] = copy.deepcopy(new_game)
                        games[game_id]["resetting"] = 1


                        
            broadcast_state(game_id) # after updates, send full game state to every connected client

        except:
            break

    
    # client disconnected
    print(f"[DISCONNECT] {addr} disconnected.")
    conn.close()
    with lock:
        del clients[player_id]
        del games[game_id]
    broadcast_state(game_id)


def broadcast_lobby():
    with lock:

        for waiter in waiters.values():
            try:
                send_packet(waiter, lobby)
            except:
                pass

def handle_connection(conn, addr, lobby_id):
    print(f"Merger")
    send_packet(conn, lobby_id)

    username = None
    game_id = None
    player_id = None

    in_lobby = True
    while in_lobby:

        try:
                
            msg = recv_next_block(conn)

            # once here, opp joined the lobby and is waiting for you to load in
            
            if msg == "HI":
                print("HELLO")
            
            elif msg == "JOIN": # when someone joined their lobby, they have to know too
                with lock:
                    # del waiters[lobby_id]

                    game_id = lobby[lobby_id][1]
                    player_id = game_id * 2
                    clients[player_id] = conn

                    in_lobby = False


            elif isinstance(msg, str):
                with lock: # msg is username
                    username = msg
                    lobby[lobby_id][2] = msg # addr, lobby id (-1 if none), username
            
            
            elif isinstance(msg, int): # chose a lobby and gives lobby index
                with lock: # msg is lobby both players join
                    # change lobby they both are in from -1 to their game id
                    # del waiters[lobby_id]

                    game_id = len(games) + 1
                    lobby[lobby_id][1] = game_id
                    player_id = game_id * 2 + 1

                    # opp that needs to chckec
                    lobby[msg][1] = game_id

                    # identify in client your playerid
                    clients[player_id] = conn


                    # identify the game is being created so dont take it
                    games[game_id] = copy.deepcopy(new_game)

                    in_lobby = False

            broadcast_lobby()


        except Exception as e:
            print(f"Error: {e}")
    

    
    # Finished the lobby
    # we got player_id, game_id, username


    handle_client(conn, addr, player_id, game_id)


    # Deleting lobby at the end



def main():
    print("[STARTING] Lobby is running...")
    lobby_id = 0
    while True:
        conn, addr = server.accept() # when client connects it gets this
        # waits here until it gets a connection

        waiters[lobby_id] = conn
        lobby.append([addr, -1, "No Name"]) # idx is current lobby [addr, lobby joined, username]

        threading.Thread(target=handle_connection, args=(conn, addr, lobby_id), daemon=True).start()


        lobby_id += 1


if __name__ == "__main__":
    main()



