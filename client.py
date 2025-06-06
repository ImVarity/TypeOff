import socket # for connection
import pickle # for converting to bytes and sending
import pygame
import threading


WIDTH, HEIGHT = 400, 400 # screen size
PLAYER_SIZE = 20
VEL = 5

MAX_FPS = 60

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("10.195.223.46", 7778))


lock = threading.Lock()

pygame.init()
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Battle Type")

font = pygame.font.SysFont(None, 48)
clock = pygame.time.Clock()

player_id = None

# data to manipulate and send
my_text = None

# shared data
players = {}
game = None


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


def receive_state():
    global game, my_text
    while True:
        # print("receiving...")
        try:
            
            loaded_game = recv_next_block(client)
            
            with lock:
                game = loaded_game
                my_text = game[player_id % 2]["buffer"]

        except Exception as e:
            print("receive_state error:", e)
            break


def recv_next_block(conn):
    header = recv_exact(conn, 4)
    total_len = int.from_bytes(header, 'big')
    data = recv_exact(conn, total_len)
    loaded_data = pickle.loads(data)
    return loaded_data


def main():
    global player_id

    player_id = recv_next_block(client)
    print(f"Connected as Player {player_id}")

    threading.Thread(target=receive_state, daemon=True).start()

    send_packet(client, "READY") # triggers the server
    
    while game is None or my_text is None: # make sure that we have everything before we start the game
        print("Waiting for game")



    run = True
    while run:
        clock.tick(MAX_FPS)

        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    try:
                        # client.sendall(pickle.dumps("READY"))
                        pass # TODO
                    except:
                        pass # feature in the game and okay if it doesnt work so dont break

        keys = pygame.key.get_pressed()
        character = clicked(keys)
        match = False
        if character == my_text[0]: # clicked the right key
            match = True
        

        try:
            send_packet(client, match)
        except:
            break # client disconnected

        

        draw_window() if game["start"][0] and game["start"][1] else waiting_screen()

    
    # client disconnected
    pygame.quit()
    client.close() # releases network resources (file descriptors, memory)




def draw_window():
    # print(game)
    window.fill((255, 255, 255))
    # me
    text = font.render(my_text, True, (0, 0, 0))
    window.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - text.get_height()))

    # opp
    opp_text = font.render(game[not player_id % 2]["buffer"], True, (0, 0, 0))
    window.blit(opp_text, (WIDTH // 2 - opp_text.get_width() // 2, opp_text.get_height()))



    pygame.display.update()


def waiting_screen():

    window.fill((255, 255, 255))
    text = font.render("Waiting...", True, (0, 0, 0))
    window.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))

    pygame.display.update()


        
def clicked(keys):
    for i in range(pygame.K_a, pygame.K_z + 1):
        if keys[i]:
            return chr(i)
    return None # didn't click anything



if __name__ == "__main__":
    main()