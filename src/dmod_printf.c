/*
 * dmod_printf.c - Memory ring buffer based printf implementation for dmod-boot
 * 
 * Minimal printf implementation using a memory ring buffer for debugging output
 * without external libraries. Works across all architectures.
 */

#include "dmod_printf.h"
#include <stddef.h>

/* Ring buffer placed in special linker section */
__attribute__((section(".dmod_log_ring"))) dmod_log_ring_t dmod_log_ring;

/* Helper function prototypes */
static void print_to_buffer(char ch);
static void print_int(int32_t value);
static void print_uint(uint32_t value);
static void print_hex(uint32_t value, int uppercase);
static int strlen_local(const char *str);
static void flush_buffer(void);

/* Current buffer being built */
static char current_buffer[DMOD_LOG_BUFFER_SIZE];
static uint32_t current_length = 0;
static uint32_t next_id = 1;

void Dmod_Log_Init(void)
{
    uint32_t i;
    
    /* Initialize ring buffer control */
    dmod_log_ring.latest_id = 0;
    dmod_log_ring.write_index = 0;
    
    /* Clear all entries */
    for (i = 0; i < DMOD_LOG_ENTRIES; i++) {
        dmod_log_ring.entries[i].id = 0;
        dmod_log_ring.entries[i].length = 0;
    }
    
    /* Reset local state */
    current_length = 0;
    next_id = 1;
}

static void print_to_buffer(char ch)
{
    if (current_length < DMOD_LOG_BUFFER_SIZE - 1) {
        current_buffer[current_length++] = ch;
    }
}

static void flush_buffer(void)
{
    uint32_t i;
    uint32_t write_idx;
    
    if (current_length == 0) {
        return;
    }
    
    /* Get current write index */
    write_idx = dmod_log_ring.write_index;
    
    /* Copy data to ring buffer entry */
    dmod_log_ring.entries[write_idx].length = current_length;
    for (i = 0; i < current_length; i++) {
        dmod_log_ring.entries[write_idx].buffer[i] = current_buffer[i];
    }
    
    /* Null-terminate for convenience */
    if (current_length < DMOD_LOG_BUFFER_SIZE) {
        dmod_log_ring.entries[write_idx].buffer[current_length] = '\0';
    }
    
    /* Assign ID and update latest_id */
    dmod_log_ring.entries[write_idx].id = next_id;
    dmod_log_ring.latest_id = next_id;
    next_id++;
    
    /* Move to next entry (wrap around) */
    dmod_log_ring.write_index = (write_idx + 1) % DMOD_LOG_ENTRIES;
    
    /* Reset current buffer */
    current_length = 0;
}

static int strlen_local(const char *str)
{
    int len = 0;
    if (str == NULL) {
        return 0;
    }
    
    while (str[len]) {
        len++;
    }
    return len;
}

static void print_int(int32_t value)
{
    char buffer[12]; /* Enough for -2147483648 */
    int i = 0;
    int is_negative = 0;
    
    if (value < 0) {
        is_negative = 1;
        value = -value;
    }
    
    /* Handle 0 explicitly */
    if (value == 0) {
        print_to_buffer('0');
        return;
    }
    
    /* Extract digits in reverse order */
    while (value > 0) {
        buffer[i++] = '0' + (value % 10);
        value /= 10;
    }
    
    /* Print negative sign if needed */
    if (is_negative) {
        print_to_buffer('-');
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        print_to_buffer(buffer[--i]);
    }
}

static void print_uint(uint32_t value)
{
    char buffer[11]; /* Enough for 4294967295 */
    int i = 0;
    
    /* Handle 0 explicitly */
    if (value == 0) {
        print_to_buffer('0');
        return;
    }
    
    /* Extract digits in reverse order */
    while (value > 0) {
        buffer[i++] = '0' + (value % 10);
        value /= 10;
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        print_to_buffer(buffer[--i]);
    }
}

static void print_hex(uint32_t value, int uppercase)
{
    char buffer[9]; /* Enough for FFFFFFFF + null */
    int i = 0;
    const char *hex_chars = uppercase ? "0123456789ABCDEF" : "0123456789abcdef";
    
    /* Handle 0 explicitly */
    if (value == 0) {
        print_to_buffer('0');
        return;
    }
    
    /* Extract hex digits in reverse order */
    while (value > 0) {
        buffer[i++] = hex_chars[value & 0xF];
        value >>= 4;
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        print_to_buffer(buffer[--i]);
    }
}

static void print_string(const char *str)
{
    if (str == NULL) {
        str = "(null)";
    }
    
    while (*str) {
        print_to_buffer(*str++);
    }
}

int Dmod_Printf(const char *format, ...)
{
    va_list args;
    int count = 0;
    
    if (format == NULL) {
        return 0;
    }
    
    va_start(args, format);
    
    while (*format) {
        if (*format == '%') {
            format++;
            
            switch (*format) {
                case 'd':
                case 'i': {
                    int32_t val = va_arg(args, int32_t);
                    print_int(val);
                    break;
                }
                
                case 'u': {
                    uint32_t val = va_arg(args, uint32_t);
                    print_uint(val);
                    break;
                }
                
                case 'x': {
                    uint32_t val = va_arg(args, uint32_t);
                    print_hex(val, 0);
                    break;
                }
                
                case 'X': {
                    uint32_t val = va_arg(args, uint32_t);
                    print_hex(val, 1);
                    break;
                }
                
                case 'c': {
                    char ch = (char)va_arg(args, int);
                    print_to_buffer(ch);
                    count++;
                    break;
                }
                
                case 's': {
                    const char *str = va_arg(args, const char *);
                    print_string(str);
                    count += strlen_local(str);
                    break;
                }
                
                case '%': {
                    print_to_buffer('%');
                    count++;
                    break;
                }
                
                default:
                    /* Unknown format specifier, print as-is */
                    print_to_buffer('%');
                    print_to_buffer(*format);
                    count += 2;
                    break;
            }
            
            format++;
        } else {
            print_to_buffer(*format);
            format++;
            count++;
        }
    }
    
    va_end(args);
    
    /* Flush the buffer to ring */
    flush_buffer();
    
    return count;
}
