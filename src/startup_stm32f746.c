/*
 * startup_stm32f746.c - Startup code for STM32F746 microcontroller
 * 
 * Minimal startup code without external dependencies
 */

#include <stdint.h>

/* External symbols from linker script */
extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

/* Function prototypes */
void Reset_Handler(void);
void Default_Handler(void);
void NMI_Handler(void) __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void) __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void) __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void) __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")));

/* External main function */
extern int main(void);

/* Vector table */
__attribute__((section(".isr_vector")))
void (* const g_pfnVectors[])(void) = {
    (void (*)(void))((uint32_t)&_estack), /* Initial Stack Pointer */
    Reset_Handler,                         /* Reset Handler */
    NMI_Handler,                           /* NMI Handler */
    HardFault_Handler,                     /* Hard Fault Handler */
    MemManage_Handler,                     /* MPU Fault Handler */
    BusFault_Handler,                      /* Bus Fault Handler */
    UsageFault_Handler,                    /* Usage Fault Handler */
    0,                                      /* Reserved */
    0,                                      /* Reserved */
    0,                                      /* Reserved */
    0,                                      /* Reserved */
    SVC_Handler,                           /* SVCall Handler */
    DebugMon_Handler,                      /* Debug Monitor Handler */
    0,                                      /* Reserved */
    PendSV_Handler,                        /* PendSV Handler */
    SysTick_Handler,                       /* SysTick Handler */
    
    /* External Interrupts - STM32F746 specific */
    /* Add more interrupt handlers here as needed */
};

/**
 * @brief Reset Handler - Entry point after reset
 */
void Reset_Handler(void)
{
    uint32_t *src, *dst;
    
    /* Copy data segment from Flash to RAM */
    src = &_sidata;
    dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    
    /* Zero-fill BSS segment */
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }
    
    /* Call main */
    main();
    
    /* Infinite loop if main returns */
    while (1);
}

/**
 * @brief Default Handler for unused interrupts
 */
void Default_Handler(void)
{
    /* Infinite loop */
    while (1);
}
