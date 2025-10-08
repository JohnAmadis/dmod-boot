/*
 * dmod_printf.h - ITM-based printf implementation for dmod-boot
 * 
 * This provides a minimal printf implementation using ARM's Instrumentation
 * Trace Macrocell (ITM) for debugging output without external libraries.
 */

#ifndef DMOD_PRINTF_H
#define DMOD_PRINTF_H

#include <stdint.h>
#include <stdarg.h>

/* ITM Register Definitions */
#define ITM_BASE            0xE0000000UL
#define ITM_STIM0           (*(volatile uint32_t *)(ITM_BASE + 0x00))
#define ITM_TER             (*(volatile uint32_t *)(ITM_BASE + 0xE00))
#define ITM_TCR             (*(volatile uint32_t *)(ITM_BASE + 0xE80))

/* ITM Port 0 is used for standard output */
#define ITM_PORT_PRINTF     0

/**
 * @brief Initialize ITM for debug output
 * 
 * This function enables ITM stimulus port 0 for printf output.
 * Must be called before using Dmod_Printf.
 */
void Dmod_ITM_Init(void);

/**
 * @brief Send a character via ITM
 * 
 * @param ch Character to send
 */
void Dmod_ITM_SendChar(char ch);

/**
 * @brief Send a string via ITM
 * 
 * @param str Null-terminated string to send
 */
void Dmod_ITM_SendString(const char *str);

/**
 * @brief Printf implementation using ITM
 * 
 * Supports basic format specifiers:
 * - %d, %i: signed decimal integer
 * - %u: unsigned decimal integer
 * - %x: unsigned hexadecimal integer (lowercase)
 * - %X: unsigned hexadecimal integer (uppercase)
 * - %c: character
 * - %s: string
 * - %%: literal %
 * 
 * @param format Format string
 * @param ... Variable arguments
 * @return Number of characters written
 */
int Dmod_Printf(const char *format, ...);

#endif /* DMOD_PRINTF_H */
