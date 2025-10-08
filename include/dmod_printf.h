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
#ifndef DMOD_LOG_TOTAL_SIZE
#define DMOD_LOG_TOTAL_SIZE    8192
#endif

/* Maximum size of a single log message */
#ifndef DMOD_LOG_MAX_ENTRY_SIZE
#define DMOD_LOG_MAX_ENTRY_SIZE    512
#endif

/* Flag bits for commands/status */
#define DMOD_FLAG_CLEAR_BUFFER  0x00000001  /* Set to clear buffer, cleared after execution */

/**
 * @brief Log entry header structure
 * 
 * Each entry in the buffer has this header followed by the message data:
 * [entry_id(4)] [length(2)] [data(length)]
 * 
 * - id: Unique incrementing ID to detect new entries
 * - length: Actual length of the message data (max 65535 bytes)
 */
typedef struct {
    volatile uint32_t id;
    volatile uint16_t length;
} __attribute__((packed)) dmod_log_entry_header_t;

/**
 * @brief Ring buffer control structure
 * 
 * Contains:
 * - magic: Magic number for validation (0x444D4F44 = "DMOD")
 * - latest_id: Most recent log entry ID (for easy monitoring)
 * - flags: Command/status flags (bit 0: clear buffer)
 * - head_offset: Offset to the newest entry in the buffer
 * - tail_offset: Offset to the oldest entry in the buffer
 * - buffer: Variable-length entries stored here
 * 
 * Buffer layout: Entries are stored sequentially with their headers.
 * When the buffer wraps around, the oldest entries are overwritten.
 */
typedef struct {
    volatile uint32_t magic;
    volatile uint32_t latest_id;
    volatile uint32_t flags;
    volatile uint32_t head_offset;
    volatile uint32_t tail_offset;
    volatile uint8_t buffer[DMOD_LOG_TOTAL_SIZE];
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
 * @brief Clear the log ring buffer
 * 
 * Clears all log entries and resets the buffer to empty state.
 * Can be used to recover from buffer corruption or for re-synchronization.
 */
void Dmod_Log_Clear(void);

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
