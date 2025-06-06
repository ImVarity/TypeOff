import socket
import threading
import pickle


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

library = {
    "startup" : ["hello", "world"]
}

book = "startup"

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


    while True:
        # print(games)
        try: # waiting to receive data from client
            msg = recv_next_block(conn)
            
            
            if msg == "READY":
                with lock:
                    games[game_id]["start"][player_id % 2] = 1
            elif msg == "HI":
                with lock:
                    print("hellooooo")
            elif msg == True: # delete
                with lock:
                    games[game_id][player_id % 2]["buffer"] = games[game_id][player_id % 2]["buffer"][1:]
                    if games[game_id][player_id % 2]["buffer"] == "": # buffer is empty
                        popped = games[game_id][player_id % 2]["text"].pop() # remove last element in text
                        games[game_id][not (player_id % 2)]["incoming"].append(popped) # pass last element to incoming for opponent
                        games[game_id][player_id % 2]["buffer"] = games[game_id][player_id % 2]["text"][-1] # set buffer again

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
                "text" : library[book].copy(),
                "buffer" : library[book][-1],
                "incoming" : []
            },

            1 : {
                "text" : library[book].copy(),
                "buffer" : library[book][-1],
                "incoming" : []
            },
            
            "start" : [0, 0], # bits representing ready or not
            "winner" : -1 # id of winner 0 or 1
        }
        threading.Thread(target=handle_client, args=(conn, addr, player_id, game_id)).start()
        game_id = game_id + 1 if player_id % 2 != 0 else game_id # only update if there are 2 players
        player_id += 1

if __name__ == "__main__":
    main()
