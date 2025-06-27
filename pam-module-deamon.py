import socket
import os
import sys
import time
import dlib
import numpy as np
import cv2
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOCKET_PATH = os.path.join("/tmp", "face_auth")
FACEDATA_DIR = os.path.join(BASE_DIR, "face_data")
FACE_MODEL = os.path.join(BASE_DIR, "68_face_landmarks_model_v2.dat")
ENCODING_MODEL = os.path.join(BASE_DIR, "dlib_face_recognition_resnet_model_v1.dat")

detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor(FACE_MODEL)
facerec = dlib.face_recognition_model_v1(ENCODING_MODEL)

def load_known_faces(username):
    known_faces = []
    if not os.path.exists(FACEDATA_DIR):
        return known_faces
    
    for file in os.listdir(FACEDATA_DIR):
        if file.startswith(username) and file.endswith(".npy"):
            encoding = np.load(os.path.join(FACEDATA_DIR, file))
            known_faces.append(encoding)
    return known_faces

def authenticate_user(username):
    known_faces = load_known_faces(username)
    if not known_faces:
        return False

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False

    start_time = time.time()
    while time.time() - start_time < 10:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = detector(rgb_frame)

        for face in faces:
            shape = sp(rgb_frame, face)
            encoding = np.array(facerec.compute_face_descriptor(rgb_frame, shape))

            distances = [np.linalg.norm(known - encoding) for known in known_faces]
            if min(distances) < 0.6:
                cap.release()
                return True

    cap.release()
    return False

def daemonize():
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.setsid()
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()

def run_server():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server_socket:
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server_socket.bind(SOCKET_PATH)
        server_socket.listen()

        while True:
            conn, _ = server_socket.accept()
            with conn:
                data = conn.recv(1024)
                if data and data.decode("utf-8").strip() == "faceauth":
                    username = os.getenv("PAM_USER") or os.getenv("USER")

                    if authenticate_user(username):
                        response = struct.pack("i", 0)
                    else:
                        response = struct.pack("i", 1)

                    conn.sendall(response)

def main():
    daemonize()
    run_server()

if __name__ == "__main__":
    main()
