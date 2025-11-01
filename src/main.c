#include "dmod.h"
#include "dmlog.h"

extern void* __logs_start__;
extern void* __logs_end__;

void delay(int cycles)
{
    for(volatile int i = 0; i < cycles; i++);
}

int main(int argc, char** argv) 
{
    void* logs_start = &__logs_start__;
    void* logs_end = &__logs_end__;
    dmlog_index_t  logs_size = (dmlog_index_t)((uintptr_t)logs_end - (uintptr_t)logs_start);
    
    dmlog_ctx_t ctx = dmlog_create(logs_start, logs_size);

    while(1)
    {
        dmlog_puts(ctx, "Hello, DMLoG!");
        delay(1000000);
    }
    return 0;
}