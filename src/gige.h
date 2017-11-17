#ifndef __GIGE_H_INCLUDED__
#define __GIGE_H_INCLUDED__

#include <sys/socket.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>

#define GIGE_KEY 0xdeadbeef
// #define GIGE_CLIENT_IP "10.0.143"
#define GIGE_CLIENT_IP "127.0.0"

// where the 0xdeadbeef is sent to turn on udp packets
#define GIGE_REGISTER_WRITE_TX_PORT 0x7D00
// not used (yet), reads register host
#define GIGE_REGISTER_READ_TX_PORT  0x7D01
// port that register request writes back to (bound in c)
// could be random and extracted from the datagram sent on 0x7D00
#define GIGE_REGISTER_RX_PORT       0x7D02
// port that the udp packets write to (bound in c)
// presumably this could be sent via one of the above ports?
#define GIGE_DATA_RX_PORT           0x7D03


#define SOF_MARKER_UPPER 0xfeed
#define SOF_MARKER_LOWER 0xface
#define EOF_MARKER_UPPER 0xdeca
#define EOF_MARKER_LOWER 0xfbad

#define REG_ACCESS_OKAY 0x4f6b6179
#define REG_ACCESS_FAIL 0x4661696c

typedef struct {
    int sock;
    char client_ip_addr[512];
    struct sockaddr_in si_recv;

    float    bitrate;
    uint32_t n_pixels;
} gige_data_t;

typedef struct {
    int sock;
    char client_ip_addr[512];

    struct sockaddr_in si_recv;

    struct sockaddr_in si_write;
    socklen_t          si_lenw;

    struct sockaddr_in si_read;
    socklen_t          si_lenr;

} gige_reg_t;

enum GIGE_ERROR {
    REGISTER_READ_FAIL  = 1,
    REGISTER_WRITE_FAIL = 2,
};

#define REGISTER_READ_FAIL 1
#define REGISTER_WRITE_FAIL 2

extern const char *GIGE_ERROR_STRING[];

#ifdef __cplusplus
extern "C" {
#endif

const char *gige_strerr(int code);

gige_reg_t *gige_reg_init(uint16_t reb_id, char *iface);
void gige_reg_close(gige_reg_t *reg);
int gige_reg_read(gige_reg_t *reg, uint32_t addr, uint32_t *value);
int gige_reg_write(gige_reg_t *reg, uint32_t addr, uint32_t value);

gige_data_t *gige_data_init(uint16_t reb_id, char *iface);
void gige_data_close(gige_reg_t *dat);
int gige_data_recv(gige_data_t* dat, uint16_t* data);
double gige_get_bitrate(gige_data_t *dat);
int gige_get_n_pixels(gige_data_t *dat);

#ifdef __cplusplus
}
#endif


#endif  //  __GIGE_H_INCLUDED__
