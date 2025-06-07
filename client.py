import socket # for connection
import pickle # for converting to bytes and sending
import pygame
import threading


WIDTH, HEIGHT = 600, 600 # screen size
PLAYER_SIZE = 20
VEL = 5
MAX_FPS = 60
DAMAGE = 40

# if mode on words
FOCUS_COLOR = (255, 99, 99)
UNFOCUS_COLOR = (255, 160, 150)


BACKGROUND_COLOR = (239, 228, 210)


OPP_FOCUS_COLOR = (58, 89, 209)
OPP_UNFOCUS_COLOR = (122, 198, 210)





hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((local_ip, 7777))


lock = threading.Lock()

pygame.init()
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Battle Type")

# FONTS
font = pygame.font.Font('mc.otf', 28)

# font = pygame.font.SysFont(None, 48)
clock = pygame.time.Clock()

player_id = None # player_id from server | 0 ... N
client_id = None # player_id in the game on client | 0 or 1

# simplified variables
buffer = None
buffer_def = None
mode = None
mode_opp = None

# shared data
players = {}
game = None

def send_packet(conn, obj):
    try:
        data = pickle.dumps(obj)
        header = len(data).to_bytes(4, 'big')
        conn.sendall(header + data)
    except:
        raise ConnectionError("Could not send data")

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

def receive_state():
    global game, mode, mode_opp, buffer, buffer_def
    while True:
        # print("receiving...")
        try:
            
            loaded_game = recv_next_block(client)
            
            with lock:
                game = loaded_game
                buffer = game[player_id % 2]["buffer"]
                buffer_def = game[player_id % 2]["incoming"][0][0] if len(game[player_id % 2]["incoming"]) > 0 else None
                mode = game[player_id % 2]["mode"]

                mode_opp = game[not player_id % 2]["mode"]

        except Exception as e:
            print("receive_state error:", e)
            break





def main():
    global player_id, client_id

    player_id = recv_next_block(client)
    # client_id = player_id % 2
    print(f"Connected as Player {player_id}")

    threading.Thread(target=receive_state, daemon=True).start()

    send_packet(client, "READY") # triggers the server
    
    while game is None or buffer is None: # make sure that we have everything before we start the game
        print("Waiting for game")



    run = True
    while run:
        clock.tick(MAX_FPS)

        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        send_packet(client, "MODE")
                    except:
                        pass
                    

                

        keys = pygame.key.get_pressed()
        character = clicked(keys)


        # offense
        if mode == 1 and character == buffer[0]: # clicked the matching key
            # update matched character
            send_packet(client, "ATTACK")

        # defense
        if buffer_def is not None:
            print(buffer_def)
        if mode == 0 and buffer_def is not None and character == buffer_def[0]:
            send_packet(client, "DEFEND")
        


        if len(game[player_id % 2]["incoming"]) > 0 and game[player_id % 2]["incoming"][0][1] > 600:
            # if passes your side deal (multiplier * damage)
            send_packet(client, (1, DAMAGE)) 

            
        
        # update floating words
        send_packet(client, "INCOMING")
        send_packet(client, "OUTGOING")
        

        # once both players ready, get off waiting screen
        draw_window() if game["start"][0] and game["start"][1] else waiting_screen()

    
    # client disconnected
    pygame.quit()
    client.close() # releases network resources (file descriptors, memory)




def draw_window():
    # print(game)
    window.fill(BACKGROUND_COLOR)

    # me
    draw_user()
    

    # opp
    draw_opp()
    

    pygame.display.update()


def draw_user():
    x_word = 50
    y_word = 550


    # BUFFER WORD PLACED BOTTOM LEFT
    text = font.render(buffer, True, FOCUS_COLOR if mode else UNFOCUS_COLOR)
    window.blit(text, (x_word, y_word))

    # PEEK WORD PLACED AT MIDDLE BOTTOM
    peek = font.render(game[player_id % 2]["peek"], True, FOCUS_COLOR if mode else UNFOCUS_COLOR)
    window.blit(peek, (250, HEIGHT // 2 + HEIGHT // 6))

    # INCOMING WORDS TOP RIGHT
    for buf, y, z in game[player_id % 2]["incoming"]:
        inc_buf = font.render(buf, True, FOCUS_COLOR if (not mode) else UNFOCUS_COLOR)
        window.blit(inc_buf, (475, y))




    

def draw_opp():
    x_word = 475
    y_word = 50

    # OPP BUFFER ON THE TOP RIGHT
    text = font.render(game[not player_id % 2]["buffer"], True, OPP_FOCUS_COLOR if mode_opp else OPP_UNFOCUS_COLOR)
    window.blit(text, (x_word, y_word - text.get_height()))

    # PEEK WORD PLACED AT MIDDLE TOP
    peek = font.render(game[not player_id % 2]["peek"], True, OPP_FOCUS_COLOR if mode_opp else OPP_UNFOCUS_COLOR)
    window.blit(peek, (250, HEIGHT // 4))

    # OUTGOING WORDS BOTTOM LEFT
    for buf, y, z in game[not player_id % 2]["incoming"]:
        out_buf = font.render(buf, True, OPP_FOCUS_COLOR if (not mode_opp) else OPP_UNFOCUS_COLOR)
        window.blit(out_buf, (50, z))

def draw_health_bars():
    pass





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