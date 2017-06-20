#include <zmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include <sys/mman.h>
//#include "zhelpers.h"
#include <math.h>
#include <fcntl.h>


#define CMD_REG_READ  0
#define CMD_REG_WRITE 1
#define CMD_START_DMA 2

#define FIFODATAREG 24
#define FIFORDCNTREG 25
#define FIFOCNTRLREG 26

#define FRAMEACTIVEREG 52
#define FRAMENUMREG 54
#define FRAMELENREG 53

volatile unsigned int *fpgabase;  //mmap'd fpga registers
int databuf[65536];
int evttot;
int dbg_lvl=0;
int lkuptbl[512];

/*****************************************
* fifo_enable
*  FIFO Control Register
*     bit 0 = enable
*     bit 1 = testmode
*     bit 2 = rst
******************************************/
void fifo_enable()
{
   int rdback, newval;

   //read current value of register
   rdback = fpgabase[FIFOCNTRLREG];
   newval = rdback | 0x1;
   fpgabase[FIFOCNTRLREG] = newval;

}

/*****************************************
* fifo_disable
*  FIFO Control Register
*     bit 0 = enable
*     bit 1 = testmode
*     bit 2 = rst
******************************************/
void fifo_disable()
{
   int rdback, newval;

   //read current value of register
   rdback = fpgabase[FIFOCNTRLREG];
   newval = rdback & 0x60;
   fpgabase[FIFOCNTRLREG] = newval;

}


/******************************************
* fifo reset
*  FIFO Control Register
*     bit 0 = enable
*     bit 1 = testmode
*     bit 2 = rst
******************************************/
void fifo_reset()
{
   int rdback, newval;

   //read current value of register
   rdback = fpgabase[FIFOCNTRLREG];
   newval = rdback | 0x4;
   //set reset high
   fpgabase[FIFOCNTRLREG] = newval;
   //set reset low
   newval = rdback & 0x3;
   fpgabase[FIFOCNTRLREG] = newval;


}

/*****************************************
* check_framestatus
*    Check is frame is Active
******************************************/
int check_framestatus()
{

   //read current value of register
   return fpgabase[FRAMEACTIVEREG];

}

/*****************************************
* get_framenum
*   Read the current frame Number
*   Framenumber is incremented by FPGA at end of frame
*
******************************************/
int get_framenum()
{

   //read current value of register
   return fpgabase[FRAMENUMREG];

}


/*****************************************
* get_framelen
*   Read the current frame length
*   Counter is 25MHz, so 40ns period
*
******************************************/
float get_framelen()
{

   //read current value of register
   return fpgabase[FRAMELENREG] / 25000000.0;

}


/*****************************************
*   Write Register
*
******************************************/
void write_reg(int addr, int val)
{

   fpgabase[addr >> 2] = val;
   printf("Write Reg: Addr=0x%x  Val=0x%x\n",addr,val);

}

/*****************************************
*   Read Register
*
******************************************/
int read_reg(int addr)
{
   int rdback;

   rdback = fpgabase[addr >> 2];
   printf("Read Reg: Addr=0x%x  Val=0x%x\n",addr,rdback);
   return rdback;
}



/*****************************************
* fifo_numwords
*  Reads back number of words in fifo
******************************************/
int fifo_numwords()
{

   return fpgabase[FIFORDCNTREG];

}


/*****************************************
* fifo_getdata
*  Reads back number of words in fifo
******************************************/
int fifo_getdata(int len, int *data)
{

   int i;


   for (i=0;i<len;i++) {
      data[i] = fpgabase[FIFODATAREG];
      //printf("i=%d\t0x%x\t0x%x\t0x%x\t0x%x\n",i,data[0],data[1],data[2],data[3]);
   }


   return 0;

}


/*******************************************
* mmap fpga register space
* returns pointer fpgabase
*
********************************************/
void mmap_fpga()
{
   int fd;

   fd = open("/dev/mem",O_RDWR|O_SYNC);
   if (fd < 0) {
      printf("Can't open /dev/mem\n");
      exit(1);
   }

   fpgabase = (unsigned int *) mmap(0,255,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0x43C00000);

   if (fpgabase == NULL) {
      printf("Can't map FPGA space\n");
      exit(1);
   }

}



/******************************************
* Event Rate Thread
*
*  Prints out the event rate
*******************************************/
void *event_rate()
{
    int evttotprev;
    int evtrate;

    while (1) {
       evtrate = evttot - evttotprev;
       evttot = evttotprev;
       printf("Event Rate : %d\n", evtrate);
       sleep(1);
    }
}

/*******************************************
* Event Publish
*
*   Thread which handles checking if there
*   is data in the fifo, and if so sends it out
*   to the client
*******************************************/
void *event_publish(void *args)
{

    int i, fulladdr, chipnum, channel, pd, td, ts, ts_prev, addr, newaddr;
    void *context = zmq_ctx_new();
    void *publisher = zmq_socket(context, ZMQ_PUB);

    int rc = zmq_bind(publisher,"tcp://*:5556");
    assert (rc == 0);
    zmq_msg_t  topic, msg;
    int numwords, prevframestat, framestat, curframenum;
    float evtrate, framelen;


    printf("Starting Data Thread...\n");
    framestat = 0;
    curframenum = get_framenum();
    evttot = 0;

    while (1) {
        prevframestat = framestat;
        framestat = check_framestatus();
        //printf("PrevFrameStat=%d\tFrameStatus=%d\n",prevframestat,framestat);
        if (framestat == 1) {
           if ((prevframestat == 0) && (framestat == 1))
              printf("Frame Started...\n");
           numwords = fifo_numwords();
           if (numwords > 0) {
              if (numwords > 10000)
                printf("Event Rate kinda too high...   Numwords in FIFO: %d\n",numwords);
              fifo_getdata(numwords,databuf);
              evttot += numwords/2;
              if (dbg_lvl == 1) {
                 for (i=0;i<numwords;i=i+2) {
                  fulladdr = (databuf[i] & 0x7FC00000) >> 22;
                  //newaddr = lkuptbl[addr];
		  //databuf[i] = (databuf[i] & ~0x7FC00000) | (newaddr << 22);
                  chipnum = (databuf[i] & 0x78000000) >> 27;
                  channel = (databuf[i] & 0x07C00000) >> 22;
                  pd = (databuf[i] & 0xFFF);
                  td = (databuf[i] & 0x3FF000) >> 12;
                  ts_prev = ts;
                  ts = (databuf[i+1] & 0x1FFFFFFF);

                  if (ts > ts_prev + 19)
                    printf("\n");
                  printf("ASIC: %4d   Chan: %4d   PD: %4d   TD: %4d   Timestamp: %d\n",
				chipnum,channel,pd,td,ts);
                  }
              }
              zmq_msg_init_size(&topic,4);
              memcpy(zmq_msg_data(&topic), "data", 4);
              zmq_msg_send(&topic,publisher,ZMQ_SNDMORE);

              zmq_msg_init_size(&msg,numwords*4);
              memcpy(zmq_msg_data(&msg), databuf, numwords*4);
              int size = zmq_msg_send(&msg,publisher,0);
              //printf("Bytes Sent: %d\n",size);
              //printf("\n\n");

              zmq_msg_close(&msg);
           }
        }
        else
            if ((prevframestat == 1) && (framestat == 0)) {
                printf("Frame Complete...\n");
                framelen = get_framelen();
                evtrate = evttot / framelen;

                printf("Total Events in Frame=%d\t Rate=%.1f\n",evttot,evtrate);
                evttot = 0;
                zmq_msg_init_size(&topic,4);
                memcpy(zmq_msg_data(&topic), "meta", 4);
                zmq_msg_send(&topic,publisher,ZMQ_SNDMORE);

                zmq_msg_init_size(&msg,4);
                curframenum = get_framenum();
                memcpy(zmq_msg_data(&msg), &curframenum, 4);
                int size = zmq_msg_send(&msg,publisher,0);
                //printf("Bytes Sent: %d\n",size);
                //printf("\n\n");

                zmq_msg_close(&msg);
             }

        usleep(2000);

    }

    pthread_exit(NULL);
}





/*******************************************
* Read Address lookup table File and store
* values
*
*
*******************************************/
void read_addrlkuptbl(int * lkuptbl, char * fileptr)
{
    FILE *f;
    char line[100];
    int linenum;
    int realaddr, virtaddr;
    int quad, asic, pixel;

    printf("Opening File : %s\n",fileptr);

    linenum=0;
    f = fopen(fileptr,"r");
    if (f == NULL) {
       printf("File not Found\n");
       exit(1);
    }

   while (fgets(line, 80, f) != NULL) {
     printf("%s",line);

     sscanf(line,"%d %d %d %d %d", &virtaddr, &realaddr, &quad, &asic, &pixel);
     //printf("realAddr=%d\n",realaddr);
     //lkuptbl[linenum] = realaddr;
     lkuptbl[realaddr] = linenum ;
     linenum++;
     if (linenum > 512) {
        printf("File too long...\n");
        exit(1);
        }
      }

   close((int)f);
}


/********************************************************
*  Main
*
********************************************************/
int main (int argc, char *argv[] )
{
    pthread_t evt_thread_pid, evtrate_thread_pid;
    int cmdbuf[3];
    int nbytes;
    void *context = zmq_ctx_new();
    void *responder = zmq_socket(context, ZMQ_REP);
    int rc = zmq_bind(responder, "tcp://*:5555");
    assert (rc == 0);
    char *configFilePtr, configFile[40];
    configFilePtr = configFile;

    int threadargs=0;
    int cmd, addr, value;
    int i;

    //if (argc < 3) {
    //   printf("Usage: %s [0,1] 0=no_dbg 1=full_dbg  lkuptable\n",argv[0]);
    //   exit(1);
    //}

    if (argc < 2) {
       printf("Usage: %s [0,1] 0=no_dbg 1=full_dbg \n",argv[0]);
       exit(1);
    }




    dbg_lvl = atoi(argv[1]);
    if (dbg_lvl == 0)
       printf("Starting Zserver with no debug messages\n");
    else
       printf("Starting Zserver with full debug messages\n");

    //configFilePtr = argv[2];
    //printf("Opening Lookup table: %s\n",configFilePtr);

    //initialize lkuptable to some impossible address
    for (i=0;i<512;i++)
        lkuptbl[i] = 400;

    //read_addrlkuptbl(lkuptbl,configFilePtr);


    mmap_fpga();

    fifo_disable();
    fifo_reset();
    fifo_enable();

    //start the event data publisher thread
    pthread_create(&evt_thread_pid, NULL, event_publish, (void *)threadargs);

    pthread_create(&evtrate_thread_pid, NULL, event_rate, NULL);

    while (1) {
        if ((nbytes = zmq_recv(responder, cmdbuf, sizeof(int)*3, 0)) < 0) {
            break;
        }
        printf("recv: %i bytes, %x %x %x\n", nbytes, cmdbuf[0], cmdbuf[1], cmdbuf[2]);
        cmd = cmdbuf[0];
        addr = cmdbuf[1];
        value = cmdbuf[2];

        switch (cmd) {
            case CMD_REG_READ:
                // do read register
                value = read_reg(addr);
                cmdbuf[2] = value;
		zmq_send(responder, cmdbuf, sizeof(cmdbuf), 0);
                break;

            case CMD_REG_WRITE:
                // do write
                write_reg(addr, value);
                zmq_send(responder, cmdbuf, sizeof(cmdbuf), 0);
                break;

            default:
                cmdbuf[0] = 0xdead;
                cmdbuf[1] = 0xdead;
                cmdbuf[2] = 0xdead;
                zmq_send(responder, cmdbuf, sizeof(cmdbuf), 0);
                break;

        }

    }
    return 0;
}
