import socket
import threading
import pickle
import json


HOST = '0.0.0.0' # any machine on same network can join '127.0.0.1' for only my machine
PORT = 7778

# standard block setup
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # af_inet -> IPv4 | sock_stream -> TCP
server.bind((HOST, PORT))
server.listen()


# Shared Game States
clients = {} # player_id -> client socket
games = {} # game_id -> game
# game -> {0: ["hello", "world"], 1: ["hello", "world"]}

library = {}
book = "harry-potter"
book_tokens = []

with open("library.json", "r") as f:
    library = json.load(f)
    book_tokens = library[book]



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
    send_packet(conn, player_id % 2)# sending player id to client who just connected (which is conn)

    user_id = player_id % 2
    while True:
        # print(games)
        try: # waiting to receive data from client
            msg = recv_next_block(conn)
            
            match msg:
                case "READY":
                    with lock:
                        games[game_id]["start"][user_id] = 1
                case "HI":
                    with lock:
                        print("hellooooo")
                
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
                        


                case (multiplier, damage):
                    with lock:
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





def main():
    print("[STARTING] Server is running...")
    player_id = 0
    game_id = 0
    while True:
        conn, addr = server.accept() # when client connects it gets this
        # it just waits here until it gets a connection...

        clients[player_id] = conn

        # only for first player of a new game
        if player_id % 2 == 0:
            games[game_id] = { 
            0 : {
                "text" : book_tokens.copy(),
                "buffer" : book_tokens[0],
                "peek" : book_tokens[1],
                "incoming" : [],
                "health" : 500,
                "mode" : 1, # 1 -> attack | 0 -> defend
                "multiplier" : 1 # multiplier
            },

            1 : {
                "text" : book_tokens.copy(),
                "buffer" : book_tokens[0],
                "peek" : book_tokens[1],
                "incoming" : [],
                "health" : 500,
                "mode" : 1,
                "multiplier" : 1
            },
            
            "start" : [0, 0], # bits representing ready or not
            "winner" : -1 # id of winner 0 or 1
        }
        threading.Thread(target=handle_client, args=(conn, addr, player_id, game_id)).start()
        game_id = game_id + 1 if player_id % 2 != 0 else game_id # only update if there are 2 players
        player_id += 1

if __name__ == "__main__":
    main()
