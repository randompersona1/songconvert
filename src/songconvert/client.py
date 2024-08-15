import socket
import sys
import subprocess
import os
import time

# Configuration
HOST = "127.0.0.1"
PORT = 6745


def send_task(sock: socket.socket, task: str) -> bool:
    """Send a task to the daemon via socket"""
    sock.sendall(task.encode("utf-8"))
    print(f"Task '{task}' sent to daemon.")

    while True:
        data = sock.recv(1024)
        if data == b"OK":
            print("Task completed successfully.")
            return True
        elif data == b"ERROR":
            print("An error occurred while processing the task.")
            sock.close()
            return False
        else:
            print(data.decode("utf-8"))

    sock.close()


def is_daemon_running() -> socket.socket:
    """Check if the daemon is running. Return a socket object if it is, None otherwise"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
        return s
    except ConnectionRefusedError:
        return None


def start_daemon():
    """Start the daemon process in a detached mode"""
    if os.name == "nt":
        # Windows
        subprocess.Popen(
            [sys.executable, "src/songconvert/server.py"],
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        # Unix-like (Linux, macOS)
        subprocess.Popen(
            [sys.executable, "src/songconvert/server.py"],
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setpgrp,
        )


def main():
    if len(sys.argv) > 1:
        task = sys.argv[1]

        daemon_running = False
        while daemon_running is False:
            s = is_daemon_running()
            if s is None:
                print("Daemon is not running. Starting it...")
                start_daemon()
                time.sleep(7)
            else:
                print("Daemon is already running.")
                daemon_running = True

        try:
            result = send_task(s, task)
        except ConnectionRefusedError:
            sys.exit(1, "Failed to connect to the daemon.")
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("Please provide a task to send.")


if __name__ == "__main__":
    main()
