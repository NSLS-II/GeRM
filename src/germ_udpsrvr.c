/**
 * @file    gige.c
 * @author  J. Kuczewski
 * @date    September 2015
 * @version 0.1
 * @brief   UDP interface to FPGA, provides register read/write and high speed
 *          data interface.
 */
#include <zmq.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <sys/time.h>
#include <time.h>
#include <inttypes.h>

#include "gige.h"


//event data buffer for a frame
uint16_t evtdata[1000000000];
//uint32_t evtdata[20000000];

const char *GIGE_ERROR_STRING[] = { "",
    "Client asserted register read failure",
    "Client asserted register write failure" };

const char *gige_strerr(int code)
{
    if (code < 0)
        return strerror(errno);

    return GIGE_ERROR_STRING[code];
}

struct sockaddr_in *find_addr_from_iface(char *iface)
{
   struct ifaddrs *ifap, *ifa;
   struct sockaddr_in *sa;

   getifaddrs (&ifap);
   for (ifa = ifap; ifa; ifa = ifa->ifa_next) {
      if (ifa->ifa_addr->sa_family==AF_INET) {
         sa = (struct sockaddr_in *) ifa->ifa_addr;
         if ( 0 == strcmp(iface, ifa->ifa_name)) {
            return sa;
         }
      }
   }

   freeifaddrs(ifap);
   return NULL;
}


gige_reg_t *gige_reg_init(uint16_t reb_id, char *iface)
{
    int rc = 0;
    struct sockaddr_in *iface_addr;
    gige_reg_t *ret;

    ret = malloc(sizeof(gige_reg_t));
    if (ret == NULL)
        return NULL;

    // IP Address based off of ID
    sprintf(ret->client_ip_addr, "%s.%01i", GIGE_CLIENT_IP, reb_id);

    // Recv socket
    ret->sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (ret->sock == -1) {
        perror(__func__);
        return NULL;
    }

    // Recv Port Setup
    bzero(&ret->si_recv, sizeof(ret->si_recv));
    ret->si_recv.sin_family = AF_INET;

    // Lookup "iface" or default to any address
    if (iface != NULL &&
        (iface_addr = find_addr_from_iface(iface)) != NULL) {
        ret->si_recv.sin_addr.s_addr = iface_addr->sin_addr.s_addr;
    }
    else {
        //fprintf(stderr, "%s: listening on any address\n", __func__);
        ret->si_recv.sin_addr.s_addr = htonl(INADDR_ANY);
    }

    // Bind to Register RX Port
    ret->si_recv.sin_port = htons(GIGE_REGISTER_RX_PORT);
    rc = bind(ret->sock, (struct sockaddr *)&ret->si_recv,
         sizeof(ret->si_recv));
    if (rc < 0) {
        perror(__func__);
        return NULL;
    }

    // Setup client READ TX
    bzero(&ret->si_read, sizeof(ret->si_read));
    ret->si_read.sin_family = AF_INET;
    ret->si_read.sin_port = htons(GIGE_REGISTER_READ_TX_PORT);

    if (inet_aton(ret->client_ip_addr , &ret->si_read.sin_addr) == 0) {
        fprintf(stderr, "inet_aton() failed\n");
    }
    ret->si_lenr = sizeof(ret->si_read);

    // Setup client WRITE TX
    bzero(&ret->si_write, sizeof(ret->si_write));
    ret->si_write.sin_family = AF_INET;
    ret->si_write.sin_port = htons(GIGE_REGISTER_WRITE_TX_PORT);

    if (inet_aton(ret->client_ip_addr , &ret->si_write.sin_addr) == 0) {
        fprintf(stderr, "inet_aton() failed\n");
    }
    ret->si_lenw = sizeof(ret->si_write);

    return ret;
}

void gige_reg_close(gige_reg_t *reg)
{
    close(reg->sock);
    free(reg);
}

int gige_reg_read(gige_reg_t *reg, uint32_t addr, uint32_t *value)
{
    struct sockaddr_in si_other;
    socklen_t len;
    uint32_t msg[10];
    int            ret;
    fd_set         fds;
    struct timeval timeout;

    bzero(&si_other, sizeof(si_other));

    msg[0] = htonl(GIGE_KEY);
    msg[1] = htonl(addr);

    if (sendto(reg->sock, msg, 2*4, 0 ,
        (struct sockaddr *) &reg->si_read, reg->si_lenr)==-1) {
        perror("sendto()");
    }

    // 3 second timeout
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;

    // Setup for select call
    FD_ZERO(&fds);
    FD_SET(reg->sock, &fds);

    // Wait for Socket data ready
    ret = select((reg->sock + 1), &fds, NULL, NULL, &timeout);

    // Detect timeout
    if ( ret < 0 ) {
        printf("%s: Select error!\n", __func__);
        return -1;
    }
    else if ( ret == 0 ) {
        printf("%s: Socket timeout\n", __func__);
        return -1;
    }

    ssize_t n = recvfrom(reg->sock, msg , 10, 0,
                         (struct sockaddr *)&si_other, &len);
    if (n < 0) {
        perror(__func__);
        return -1;
    }

    // Detect FPGA register access failure
    if (ntohl(msg[1]) == REG_ACCESS_FAIL && (ntohl(msg[0]) >> 24) == 0xff) {
        return REGISTER_READ_FAIL;
    }

    *value = (uint32_t)htonl(msg[1]);

    return 0;
}

int gige_reg_write(gige_reg_t *reg, uint32_t addr, uint32_t value)
{
    struct sockaddr_in si_other;
    socklen_t len;
    uint32_t msg[10];
    int            ret;
    fd_set         fds;
    struct timeval timeout;

    bzero(&si_other, sizeof(si_other));

    msg[0] = htonl(GIGE_KEY);
    msg[1] = htonl(addr);
    msg[2] = htonl(value);

    if (sendto(reg->sock, msg, 3*4, 0 ,
        (struct sockaddr *) &reg->si_write, reg->si_lenw)==-1) {
        perror("sendto()");
    }

    // 3 second timeout
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;

    // Setup for select call
    FD_ZERO(&fds);
    FD_SET(reg->sock, &fds);

    // Wait for Socket data ready
    ret = select((reg->sock + 1), &fds, NULL, NULL, &timeout);

    // Detect timeout
    if ( ret < 0 ) {
        printf("%s: Select error!\n", __func__);
        return -1;
    }
    else if ( ret == 0 ) {
        printf("%s: Socket timeout\n", __func__);
        return -1;
    }

    ssize_t n = recvfrom(reg->sock, msg , 10, 0,
                         (struct sockaddr *)&si_other, &len);
    if (n < 0) {
        perror(__func__);
        return -1;
    }

    printf("Len: %d\t Msg: %x\n",(int)n,ntohl(msg[1]));
    // Detect FPGA register access failure
    if (ntohl(msg[1]) == REG_ACCESS_FAIL && (ntohl(msg[0]) >> 24) == 0xff) {
        return REGISTER_WRITE_FAIL;
    }

    // Make sure we wrote the register
    if (ntohl(msg[1]) == REG_ACCESS_OKAY) {
        return 0;
    }

    return -1;
}


gige_data_t *gige_data_init(uint16_t reb_id, char *iface)
{
    int rc = 0;
    struct sockaddr_in *iface_addr;
    gige_data_t *ret;

    ret = malloc(sizeof(gige_reg_t));
    if (ret == NULL)
        return NULL;

    // IP Address based off of ID
    sprintf(ret->client_ip_addr, "%s.%01i", GIGE_CLIENT_IP, reb_id);

    // Recv socket
    ret->sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (ret->sock == -1) {
        perror(__func__);
        return NULL;
    }

    // Recv Port Setup
    bzero(&ret->si_recv, sizeof(ret->si_recv));
    ret->si_recv.sin_family = AF_INET;

    // Lookup "iface" or default to any address
    if (iface != NULL &&
        (iface_addr = find_addr_from_iface(iface)) != NULL) {
        ret->si_recv.sin_addr.s_addr = iface_addr->sin_addr.s_addr;
    }
    else {
        //fprintf(stderr, "%s: listening on any address\n", __func__);
        ret->si_recv.sin_addr.s_addr = htonl(INADDR_ANY);
    }

    int size = 500000000;
    if (setsockopt(ret->sock, SOL_SOCKET, SO_RCVBUF, &size, sizeof(int)) == -1) {
        fprintf(stderr, "Error setting socket opts: %s\n", strerror(errno));
    }

    // Bind to Register RX Port
    ret->si_recv.sin_port = htons(GIGE_DATA_RX_PORT);
    rc = bind(ret->sock, (struct sockaddr *)&ret->si_recv,
         sizeof(ret->si_recv));
    if (rc < 0) {
        perror(__func__);
        return NULL;
    }

    return ret;
}

void gige_data_close(gige_reg_t *dat)
{
    close(dat->sock);
    free(dat);
}


long int time_elapsed(struct timeval time_i, struct timeval time_f)
{
  return (1000000*(time_f.tv_sec-time_i.tv_sec) + (time_f.tv_usec-time_i.tv_usec));
}



uint gige_data_recv(gige_data_t *dat, uint16_t *data)
{
    struct sockaddr_in cliaddr;
    struct timeval tvBegin, tvEnd;
    socklen_t len;
    uint16_t mesg[4096];
    ssize_t n = 0;
    uint total_sz = 0, total_data = 0;
    uint32_t first_packetnum, packet_counter;
    uint src = 0, dest =0 , cnt = 0, end_of_frame = 0, start_of_frame = 0;
    uint i = 0;

    while ( ! end_of_frame) {
        n = recvfrom(dat->sock, mesg, sizeof(mesg), 0,
                     (struct sockaddr *)&cliaddr, &len);
        total_sz += n;
        //printf("Received %d bytes\n",total_sz);

        if (n < 0) {
            perror(__func__);
            return n;
        }

        packet_counter = (ntohs(mesg[0]) << 16 | ntohs(mesg[1]));

        //for(i=0;i<n/2;i=i+2)
        //   printf("%d:\t%4x\n",i,(ntohs(mesg[i]) << 16 | ntohs(mesg[i+1])));

        //printf("Packet Counter: %d\n",packet_counter);
        //for (i=0;i<n;i++)
        //    printf("%d:  %d\n",i,ntohs(mesg[i]));

        src = dest = 2;

        //if (i == 1)
        //    src = dest = 3;

        if (ntohs(mesg[2]) == SOF_MARKER_UPPER &&
            ntohs(mesg[3]) == SOF_MARKER_LOWER) {
            gettimeofday(&tvBegin, NULL);
            total_data = 0;
            cnt = packet_counter;
            first_packetnum = packet_counter;
            //words 0,1 = packet counter
            //words 2,3 = 0xfeedface
            //words 4,5 = 0xframenum
	    src = dest = 2; //4; //5;
            start_of_frame = 1;
            printf("Got Start of Frame\n");
        }

        if (ntohs(mesg[(n/sizeof(uint16_t))-2]) == EOF_MARKER_UPPER &&
            ntohs(mesg[(n/sizeof(uint16_t))-1]) == EOF_MARKER_LOWER) {
            gettimeofday(&tvEnd, NULL);
            end_of_frame = 1;
            dest = 2;
            if ( ! start_of_frame)
                fprintf(stderr, "ERROR: EOF before SOF!\n");
            printf("Got End of Frame\n");
        }

       memcpy(&data[total_data/sizeof(uint16_t)], &mesg[src], n-(dest*sizeof(uint16_t)));
       total_data += n-(dest*sizeof(uint16_t));
       cnt++;
       i++;
    }

    if (packet_counter != cnt-1) {
        fprintf(stderr, "ERROR: Dropped a packet! Missed %i packets\n", packet_counter - cnt);
        return 0;
    }


    printf("Total Packets=%d\tTotal Data=%4.2f MB\n",packet_counter-first_packetnum,total_data/1e6);
    dat->bitrate = total_sz/(1.0*time_elapsed(tvBegin, tvEnd));
    //dat->n_pixels = total_data*8/16;
    printf("Throughput: %4.2f MB,  %f MB/s\n", total_sz/1e6, dat->bitrate);
    //printf("%i pixels, %i bytes\n", total_data*8/16, total_data);

    return total_data/sizeof(uint16_t);   //return number of 16 bit words
}




double gige_get_bitrate(gige_data_t *dat)
{
    return dat->bitrate;
}

int gige_get_n_pixels(gige_data_t *dat)
{
    return dat->n_pixels;
}



int main(void)
{
    int rc = 0;
    uint32_t value;
    gige_reg_t *reg = gige_reg_init(1, NULL);
    gige_data_t *dat = gige_data_init(1, NULL);
    int i,checkval,chkerr=0;
    FILE *fp;
    struct timeval tvBegin, tvEnd;
    void *context = zmq_ctx_new();
    void *responder = zmq_socket (context, ZMQ_REP);
    int zmqrc = zmq_bind(responder, "tcp://*:5557");
    //assert (zmqrc == 0);
    char filename[128] = {0};
    int filenamelen, framenum;
    char framestr[3];
    char eofmsg[64], fwmsg[64] = {0};
    uint64_t frame_md[3] = {0};


    /*while (1) {
       char buffer[10];
       zmq_recv(responder, buffer, 10, 0);
       printf("Received Hello\n");
       sleep(1);
       zmq_send(responder, "World", 5, 0);
    }*/

    //Enable UDP Interface on GeRM module
    printf("Enabling UDP Interface on GERM...\n");
    rc = gige_reg_write(reg, 0x00000001, 0x1);
    if (rc != 0) {
        fprintf(stderr, "Error: %s\n", gige_strerr(rc));
    }

    /*printf("Reading Register...\n");
    rc = gige_reg_read(reg, 0x00000001, &value);
    printf("ReadVal: %x\n",value);
    if (rc != 0)
        fprintf(stderr, "Error: %s\n", gige_strerr(rc));*/

    while (1) {
      memset(filename,0,strlen(filename));
      printf("Waiting for Filename...\n");
      zmq_recv(responder, filename, sizeof(filename), 0);
      printf("ZMQ msg: Rcvd Base Filename: %s \n",filename);
      zmq_send(responder, "Received Filename", 17, 0);
      printf("Ready for Event Data...\n");

      //get the data from a frame
      uint64_t numwords = gige_data_recv(dat, evtdata);
      uint64_t numevents = (numwords-8)/4;
      uint64_t numoverflows = (ntohs(evtdata[numwords-4]) << 16 | ntohs(evtdata[numwords-3]));
      //printf("Numwords in Frame=%d\n",numwords);
      //printf("\n");

      //save to disk
      zmq_recv(responder, eofmsg, sizeof(eofmsg), 0);
      printf("ZMQ msg: %s\n", eofmsg);

      //print frame number (2nd word in packet)
      framenum =  ntohs(evtdata[2]) << 16 | ntohs(evtdata[3]);
      printf("Frame Number: %d\n", framenum);
      printf("Numevents in Frame = %" PRId64 "\n", numevents);
      printf("Events lost to Overflow: %" PRId64 "\n", numoverflows);
      //printf("EOF: %x\n",(ntohs(evtdata[numwords-2]) << 16 | ntohs(evtdata[numwords-1])));

      frame_md[0] = framenum;
      frame_md[1] = numevents;
      frame_md[2] = numoverflows;

      zmq_send(responder, frame_md, sizeof(frame_md), 0);
      strcat(filename,"_");
      sprintf(framestr,"%03d",framenum);
      strcat(filename,framestr);
      strcat(filename,".bin");
      filenamelen = strlen(filename);
      fp = fopen(filename, "w");
      gettimeofday(&tvBegin, NULL);
      printf("Saving File : %s\n",filename);
      fwrite(evtdata,numwords,sizeof(uint16_t),fp);
      gettimeofday(&tvEnd, NULL);
      printf("Wrote %4.2f MB to %s in %f sec\n", numwords*2/1e6, filename, (float)(time_elapsed(tvBegin, tvEnd)/1e6));
      fclose(fp);
      zmq_recv(responder, fwmsg, sizeof(fwmsg), 0);
      printf("ZMQ msg: %s\n", fwmsg);
      zmq_send(responder,filename, filenamelen, 0);

      printf("\n");

      }


    gige_reg_close(reg);
    return 0;
}
