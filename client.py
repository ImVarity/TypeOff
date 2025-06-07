import socket # for connection
import pickle # for converting to bytes and sending
import pygame
import threading


WIDTH, HEIGHT = 600, 600 # screen size
PLAYER_SIZE = 20
VEL = 5
MAX_FPS = 60
DAMAGE = 40





hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((local_ip, 7776))


lock = threading.Lock()

pygame.init()
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Battle Type")

# FONTS
font = pygame.font.Font('mc.otf', 28)

# font = pygame.font.SysFont(None, 48)
clock = pygame.time.Clock()

player_id = None

# data to manipulate and send
my_text = None

# shared data
players = {}
game = None

key_map = {
    pygame.K_a: 'a',
    pygame.K_b: 'b',
    pygame.K_c: 'c',
    pygame.K_d: 'd',
    pygame.K_e: 'e',
    pygame.K_f: 'f',
    pygame.K_g: 'g',
    pygame.K_h: 'h',
    pygame.K_i: 'i',
    pygame.K_j: 'j',
    pygame.K_k: 'k',
    pygame.K_l: 'l',
    pygame.K_m: 'm',
    pygame.K_n: 'n',
    pygame.K_o: 'o',
    pygame.K_p: 'p',
    pygame.K_q: 'q',
    pygame.K_r: 'r',
    pygame.K_s: 's',
    pygame.K_t: 't',
    pygame.K_u: 'u',
    pygame.K_v: 'v',
    pygame.K_w: 'w',
    pygame.K_x: 'x',
    pygame.K_y: 'y',
    pygame.K_z: 'z',
}


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


        if len(game[player_id % 2]["incoming"]) > 0 and game[player_id % 2]["incoming"][0][1] > 600:
            send_packet(client, (1, DAMAGE)) # if passes your side deal (multiplier * damage)


        try:
            send_packet(client, match)
        except:
            break # client disconnected
        
        # update floating words
        send_packet(client, "INCOMING")
        send_packet(client, "OUTGOING")
        

        draw_window() if game["start"][0] and game["start"][1] else waiting_screen()

    
    # client disconnected
    pygame.quit()
    client.close() # releases network resources (file descriptors, memory)




def draw_window():
    # print(game)
    window.fill((255, 255, 255))

    # me
    draw_user()
    

    # opp
    draw_opp()
    

    pygame.display.update()


def draw_user():
    x_word = 50
    y_word = 550


    # BUFFER WORD PLACED BOTTOM LEFT
    buffer = font.render(my_text, True, (0, 0, 0))
    window.blit(buffer, (x_word, y_word))

    # PEEK WORD PLACED AT MIDDLE BOTTOM
    peek = font.render(game[player_id % 2]["peek"], True, (0, 0, 0))
    window.blit(peek, (250, HEIGHT // 2 + HEIGHT // 4))

    # INCOMING WORDS TOP RIGHT
    for buf, y, z in game[player_id % 2]["incoming"]:
        inc_buf = font.render(buf, True, (0, 0, 0))
        window.blit(inc_buf, (475, y))

    # OUTGOING WORDS BOTTOM LEFT
    for buf, y, z in game[not player_id % 2]["incoming"]:
        out_buf = font.render(buf, True, (0, 0, 0))
        window.blit(out_buf, (50, z))


    

def draw_opp():
    x_word = 475
    y_word = 50

    # OPP BUFFER ON THE TOP RIGHT
    text = font.render(game[not player_id % 2]["buffer"], True, (0, 0, 0))
    window.blit(text, (x_word, y_word - text.get_height()))

    # PEEK WORD PLACED AT MIDDLE TOP
    peek = font.render(game[not player_id % 2]["peek"], True, (0, 0, 0))
    window.blit(peek, (250, HEIGHT // 4))

def draw_health_bars():
    pass





def waiting_screen():

    window.fill((255, 255, 255))
    text = font.render("Waiting...", True, (0, 0, 0))
    window.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))

    pygame.display.update()


        
def clicked(keys):
    for k in key_map:
        if keys[k]:
            return key_map[k]
    return None



if __name__ == "__main__":
    main()