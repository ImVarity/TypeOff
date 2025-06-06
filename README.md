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
