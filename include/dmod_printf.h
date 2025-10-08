/*
 * dmod_printf.h - Memory ring buffer based printf implementation for dmod-boot
 * 
 * This provides a minimal printf implementation using a memory ring buffer
 * for debugging output without external libraries. Works across all architectures.
 */

#ifndef DMOD_PRINTF_H
#define DMOD_PRINTF_H

#include <stdint.h>
#include <stdarg.h>

#ifndef DMOD_MAGIC_NUMBER
#define DMOD_MAGIC_NUMBER    0x444D4F44  /* 'DMOD' */
#endif

/* Configuration - can be overridden by Makefile */
#ifndef DMOD_LOG_ENTRIES
#define DMOD_LOG_ENTRIES    128
#endif

#ifndef DMOD_LOG_BUFFER_SIZE
#define DMOD_LOG_BUFFER_SIZE    256
#endif

/**
 * @brief Log entry structure in the ring buffer
 * 
 * Each entry contains:
 * - id: Unique incrementing ID to detect new entries
 * - length: Actual length of the message
 * - buffer: Message data
 */
typedef struct {
    volatile uint32_t id;
    volatile uint32_t length;
    volatile char buffer[DMOD_LOG_BUFFER_SIZE];
} dmod_log_entry_t;

/**
 * @brief Ring buffer control structure
 * 
 * Contains:
 * - latest_id: Most recent log entry ID (for easy monitoring)
 * - write_index: Current write position in the ring
 * - entries: Array of log entries
 */
typedef struct {
    volatile uint32_t magic;          
    volatile uint32_t latest_id;
    volatile uint32_t write_index;
    dmod_log_entry_t entries[DMOD_LOG_ENTRIES];
} dmod_log_ring_t;

/* External ring buffer defined in linker script */
extern dmod_log_ring_t dmod_log_ring;

/**
 * @brief Initialize the log ring buffer
 * 
 * Must be called before using Dmod_Printf.
 */
void Dmod_Log_Init(void);

/**
 * @brief Printf implementation using memory ring buffer
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
