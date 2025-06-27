#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>

#define SOCKET_PATH "/tmp/face_auth"

int main() {
    int sock;
    struct sockaddr_un addr;
    int response;

    if ((sock = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("FaceAuth: Błąd tworzenia gniazda");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        perror("FaceAuth: Błąd połączenia");
        return 1;
    }

    printf("FaceAuth: Wyszukiwanie twarzy...\n");
    fflush(stdout);
    
    const char *msg = "faceauth";
    send(sock, msg, strlen(msg), 0);

    recv(sock, &response, sizeof(response), 0);

    if(!response) {
        printf("FaceAuth: Twarz rozpoznana.\n");
        fflush(stdout);
    } else {
        printf("FaceAuth: Twarz nierozpoznana.\n");
        fflush(stdout);
    }

    close(sock);
    return response;
    exit(response);
}
