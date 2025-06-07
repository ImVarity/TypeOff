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
client.connect((local_ip, 7778))


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
# USER
buffer = None
buffer_def = None
health = None
mode = None
multiplier = 1

# OPPONENT
mode_opp = None
health_opp = None
multiplier_opp = 1


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
    global game, mode, mode_opp, buffer, buffer_def, health, health_opp, multiplier, multiplier_opp
    while True:
        # print("receiving...")
        try:
            
            loaded_game = recv_next_block(client)
            
            with lock:
                game = loaded_game
                # USER DATA
                buffer = game[player_id % 2]["buffer"]
                buffer_def = game[player_id % 2]["incoming"][0][0] if len(game[player_id % 2]["incoming"]) > 0 else None
                mode = game[player_id % 2]["mode"]
                health = game[player_id % 2]["health"]
                multiplier = game[player_id % 2]["multiplier"]


                # OPPONENT DATA
                mode_opp = game[not player_id % 2]["mode"]
                health_opp = game[not player_id % 2]["health"]
                multiplier_opp = game[not player_id % 2]["multiplier"]



        except Exception as e:
            print("receive_state error:", e)
            break





def main():
    global player_id, client_id

    player_id = recv_next_block(client)
    client_id = player_id % 2
    print(f"Connected as Player {player_id}")

    threading.Thread(target=receive_state, daemon=True).start()

    send_packet(client, "HI") # triggers the server
    
    while game is None or buffer is None: # make sure that we have everything before we start the game
        print("Waiting for game")



    run = True
    while run:
        clock.tick(MAX_FPS)
        character = None
        
        for event in pygame.event.get():
            click = clicked(event)
            if click:
                character = click

            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        send_packet(client, "READY")
                    except:
                        pass
                    

        match = False

        # offense
        if mode == 1 and character == buffer[0]: # clicked the matching key
            # update matched character
            send_packet(client, "ATTACK")
            match = True


        # defense
        if mode == 0 and buffer_def is not None and character == buffer_def[0]:
            send_packet(client, "DEFEND")
            match = True
        
        # increase or reset multiplier
        if match:
            send_packet(client, "INCREASE_MULTI")

        if character is not None and not match and multiplier > 1:
            send_packet(client, "RESET_MULTI")

        if len(game[player_id % 2]["incoming"]) > 0 and game[player_id % 2]["incoming"][0][1] > 600:
            # if passes your side deal (multiplier * damage)
            send_packet(client, (multiplier_opp, DAMAGE)) 

        
        
        
        # update floating words only when there are
        if len(game[player_id % 2]["incoming"]) > 0:
            send_packet(client, "INCOMING")
        if len(game[client_id]["incoming"]) > 0:
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

    # MULTIPLIER ABOVE PEEK WORD
    multi = font.render(f"x{multiplier}", True, (255, 255, 255))
    window.blit(multi, (250, HEIGHT // 2 + HEIGHT // 6 - 27))

    # PEEK WORD PLACED AT MIDDLE BOTTOM
    peek = font.render(game[player_id % 2]["peek"], True, FOCUS_COLOR if mode else UNFOCUS_COLOR)
    window.blit(peek, (250, HEIGHT // 2 + HEIGHT // 6))

    # INCOMING WORDS TOP RIGHT
    for buf, y, z in game[player_id % 2]["incoming"]:
        inc_buf = font.render(buf, True, FOCUS_COLOR if (not mode) else UNFOCUS_COLOR)
        window.blit(inc_buf, (475, y))


    # HEALTH BAR BOTTOM
    percentage = health / 500 # temporary
    health_bar = pygame.Rect(0, 580, percentage * 600, 20)
    pygame.draw.rect(window, FOCUS_COLOR, health_bar)



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

    # HEALTH BAR TOP
    percentage = health_opp / 500 # temporary
    health_bar = pygame.Rect(0, 0, percentage * 600, 20)
    pygame.draw.rect(window, OPP_FOCUS_COLOR, health_bar)



slide_x = 0
blink = 0
show = True
def waiting_screen():
    global slide_x, blink, show
    blink += 1
    if blink % 20 == 0:
        show = not show

    window.fill((255, 255, 255))
    
    ## YOU BOTTOM LEFT
    text = font.render(f"YOU", True, (0, 0, 0))
    window.blit(text, (50, 550))

    ## READY INDICATOR
    ready = game["start"][client_id]
    ready_text = font.render(f"{"READY" if ready else "NOT READY"}", True, (0, 0, 0))

    if show:
        window.blit(ready_text, (WIDTH // 2 - ready_text.get_width() // 2, 550))


    ## INSTRUCTIONS
    instruction = font.render(f"Press ENTER to ready up", True, (0, 0, 0))
    window.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, HEIGHT // 2 - instruction.get_height() // 2))
    

    ## OPP TOP RIGHT
    opp_text = font.render(f"OPP", True, (0, 0, 0))
    window.blit(opp_text, (550 - opp_text.get_width(), 28))

    ## OPP READY INDICATOR
    opp_ready = game["start"][not client_id]
    opp_ready_text = font.render(f"{"READY" if opp_ready else "NOT READY"}", True, (0, 0, 0))
    if show:
        window.blit(opp_ready_text, (WIDTH // 2 - opp_ready_text.get_width() // 2, 28))

    pygame.display.update()


        
def clicked(event):
    if event.type == pygame.KEYDOWN:
        key = event.key
        if pygame.K_a <= key <= pygame.K_z: # ascii
            return chr(key)
    return None # didn't click anything


if __name__ == "__main__":
    main()