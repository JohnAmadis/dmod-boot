/*
 * main.c - Example application for dmod-boot
 * 
 * Simple example demonstrating ring buffer based debug output
 */

#include "dmod_printf.h"

/* Simple delay function */
static void delay(volatile uint32_t count)
{
    while (count--);
}

int main(void)
{
    uint32_t counter = 0;
    
    /* Initialize log ring buffer */
    Dmod_Log_Init();
    
    /* Print startup message */
    Dmod_Printf("dmod-boot initialized\n");
    Dmod_Printf("System starting...\n");
    Dmod_Printf("Ring buffer debug output enabled\n\n");
    
    /* Main loop */
    while (1) {
        Dmod_Printf("Counter: %u (0x%X)\n", counter, counter);
        counter++;
        
        /* Delay between prints */
        delay(1000000);
    }
    
    return 0;
}
