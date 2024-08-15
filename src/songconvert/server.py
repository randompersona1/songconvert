import socket
import threading
import queue
import os
import songconvert.server_tasks as server_tasks
from ultrastarparser import Song
from dataclasses import dataclass
from pathlib import Path

# Configuration
HOST = "127.0.0.1"
PORT = 6745

split_queue = queue.Queue()
reencode_queue = queue.Queue()


@dataclass(frozen=True, unsafe_hash=True)
class Task:
    """Dataclass to hold task information"""

    songfolder: Path
    connection: socket.socket


def get_song(songfolder: Path) -> Song:
    """
    Get the Song from the song folder.
    """
    for file in os.listdir(songfolder):
        if file.endswith(".txt"):
            song = Song(os.path.join(songfolder.as_posix(), file))
            break

    return song


def handle_split(task: Task):
    """Function to handle the split task"""
    try:
        song = get_song(task.songfolder)
        server_tasks.create_vocals_instrumental(song)
        task.connection.sendall(b"Split completed.")
    except Exception as e:
        print(f"An error occurred while splitting {task.songfolder}: {e}")


def handle_reencode(task: Task):
    """Function to handle the reencode task"""
    try:
        song = get_song(task.songfolder)
        server_tasks.reencode_video(song)
        task.connection.sendall(b"Reencode completed.")
        task.connection.sendall(b"OK")
    except Exception as e:
        print(f"An error occurred while reencoding {task.songfolder}: {e}")
        task.connection.sendall(b"ERROR")


def split_processor():
    """Thread that processes tasks from the queue"""
    while True:
        task = split_queue.get()
        if task is None:  # Sentinel to exit
            break
        print(f"Splitting {task.songfolder}")
        handle_split(task)
        print(f"Splitting {task.songfolder} completed.")
        split_queue.task_done()
        reencode_queue.put(task)


def reencode_processor():
    """Thread that processes tasks from the queue"""
    while True:
        task = reencode_queue.get()
        if task is None:  # Sentinel to exit
            break
        handle_reencode(task)
        reencode_queue.task_done()


def start_daemon():
    """Function to start the daemon"""
    print("Daemon started...")
    task_processor_thread_1 = threading.Thread(target=split_processor)
    task_processor_thread_2 = threading.Thread(target=reencode_processor)
    task_processor_thread_3 = threading.Thread(target=reencode_processor)
    task_processor_thread_1.start()
    task_processor_thread_2.start()
    task_processor_thread_3.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")
            data = conn.recv(1024)
            if not data:
                continue
            songfolder = data.decode("utf-8")
            if songfolder == "STOP":
                split_queue.put(None)  # Send sentinel to stop the thread
                split_queue.put(None)  # Send sentinel to stop the second thread
                break
            songfolder = Path(songfolder)

            task = Task(songfolder, conn)
            split_queue.put(task)
            print(f"Task for {songfolder} added to the queue.")

    task_processor_thread_1.join()
    task_processor_thread_2.join()
    task_processor_thread_3.join()
    print("Daemon stopped.")


if __name__ == "__main__":
    start_daemon()
