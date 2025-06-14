# TypeOff

### Multiplayer typing game using Sockets, Threading, and Pygame. Uses TCP connection and handles synchronization safely to prevent race conditions between threads.

<br><br>


## __Problem__
### __Handling multiple two player games at once__
### Solution
    - Games live in server identified with game id
    - Pass games through the socket. 
    - Use % to identify player one and player two.

<br><br>


## __Problem__
### When second player joined game, stuck in waiting loop waiting for intial game data. This was because through the TCP connection data isn't guaranteed to send all at the same time. So, when receiving, the receiving state function might fail and itll never receive game state -> forever stuck in waiting loop
### Solution
    Create two functions send_packet and recv_exact
    
    send_packet(socket, obj)
        collects data [header] + [obj]
        [header] = size of data
        [obj] = just in bytes
        send all (header + data)

        this is so that we know exactly how many bytes we are looking for when receiving
    
    recv_exact(client, n)
        data = b'' # bytes
        while len(data) < n: # if i didn't get all data at once, keep looping till
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed during recv_exact")
            data += chunk

        return data

<br><br>


## __Problem__
### Creating a lobby for players to join and choose who they want to play against
### Solution
    At first I created a whole new main on the client side that started the user in the lobby and I thought that I needed to run more threads to handle both the game and the lobby. Running a thread in another thread did not seem right. So, I had to combine them and have one while loop handle both the lobby and the game. That took forever... Putting together two different mains so that they both worked independently and not ruining what already worked was horrible. On the server side, I had to handlers for the client and the game as well and had to combine them.. 

<br><br>


## __Problem__
### Having two different players join the same game
### Solution
    This took forever to think of, but I would have the user click on who they wanted to play against and the client would send that lobby_id to the server and change the status of both players to the game_id that would would be in together (this is the idea that took a while. I didn't know how to communicate that they were both in the same room). The server would create a new game and new player_id and then leave the lobby handler while loop. The player that didn't click would have to see that someone joined their lobby, because of their new game_id in their lobby instance, and get their own player_id then leave the while loop.

<br><br>


## __Problem__
### Players would stay in lobby after joining game
### Solution
    It wasn't that bad, but I simple delete them from the lobby. However, for some reason the lobby wouldn't show that the others who have a game have left the lobby... I needed to broadcast the lobby one more time before handling the game. When handing the game it only starts to send the game - not the lobby anymore.


