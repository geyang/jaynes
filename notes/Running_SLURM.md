# Running Trough SSH Tunnels

here is an example of accessing a host inside a protected network through a login node (`cluster-login`).

We need to do this in two steps: **First**, we need to setup the rsa key for the jump host (`luster-login`) to the intra host (192.168.14.15). **Then** we need to to the same for your local computer (your mac) and the intro host.

So first try to create a makefile that looks like the following:

```makefile
# ~/Makefile

# parameters
USERNAME=ge
JUMP_HOST=cluster-login.uchicago.edu
LOCAL_PORT=41000
INTRA_HOST=192.168.14.15
SSH_PORT=22

# targets
jump:
	ssh ${USERNAME}@${JUMP_HOST}
tunnel:
	ssh -N -f -J ${USERNAME}@${JUMP_HOST} -L ${LOCAL_PORT}:${INTRA_HOST}:${SSH_PORT} ${INTRA_HOST}
ssh-test:
	ssh localhost -p ${LOCAL_PORT}
```

1. Now, first try to setup rsa key on the jump host
    ```bash
    ssh ge@cluster-login.uchicago.edu
    # ~ Now you are inside the login node...
    ssh-keygen
    ```
2. Then, use copy ssh key to send the key to the intra host (target)
    ```bash
    ssh-copy-id ge@192.168.14.15
    ```
3. After that you should be able to build the tunnel by running
    ```bash
    make tunnel
    ```
4. Now if the tunnel works successfully, you should be able to login to the intra host from your mac:
    ```bash
    ssh <your_username>@localhost -p 41000
    # OR
    make ssh-test
    ```
    This step will require password; And this will NOT unless you did step 2. This is obviously still inconvenient if we want to log into the `intra host` programmatically. To do that, 
5. Run
    ```bash
    ssh-keygen
    # ... after generating the key
    ssh-copy-id ge@localhost -p 41000
    ```
    
Now finally, you should be able to just 
```bash
ssh localhst -p 41000
```
As long as the tunnel is still connected.

## ToDo:

Test Eternal Terminal. See note [[Running with Eternal Terminal]](./Running_with_Eternal_Terminal.md)

-- ©2018, Ge Yang built with :heart: --
