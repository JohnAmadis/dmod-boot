/*
 * dmod_printf.c - Memory ring buffer based printf implementation for dmod-boot
 * 
 * Minimal printf implementation using a memory ring buffer for debugging output
 * without external libraries. Works across all architectures.
 */

#include "dmod_printf.h"
#include <stddef.h>

/* Ring buffer placed in special linker section */
#ifdef DMOD_X86_TEST
/* For x86 testing, don't use special section */
dmod_log_ring_t dmod_log_ring;
#else
/* For embedded targets, place in special linker section */
__attribute__((section(".dmod_log_ring"))) dmod_log_ring_t dmod_log_ring;
#endif

/* Helper function prototypes */
static void print_to_buffer(char ch);
static void print_int(int32_t value);
static void print_uint(uint32_t value);
static void print_hex(uint32_t value, int uppercase);
static int strlen_local(const char *str);
static void flush_buffer(void);
static uint32_t get_free_space(uint32_t head, uint32_t tail);
static void write_entry(const char *data, uint32_t length);

/* Current buffer being built */
static char current_buffer[DMOD_LOG_MAX_ENTRY_SIZE];
static uint32_t current_length = 0;
static uint32_t next_id = 1;

void Dmod_Log_Init(void)
{
    uint32_t i;
    
    /* Initialize ring buffer control */
    dmod_log_ring.magic = DMOD_MAGIC_NUMBER;
    dmod_log_ring.latest_id = 0;
    dmod_log_ring.flags = 0;
    dmod_log_ring.head_offset = 0;
    dmod_log_ring.tail_offset = 0;
    
    /* Clear buffer */
    for (i = 0; i < DMOD_LOG_TOTAL_SIZE; i++) {
        dmod_log_ring.buffer[i] = 0;
    }
    
    /* Reset local state */
    current_length = 0;
    next_id = 1;
}

void Dmod_Log_Clear(void)
{
    uint32_t i;
    
    /* Reset control fields */
    dmod_log_ring.latest_id = 0;
    dmod_log_ring.head_offset = 0;
    dmod_log_ring.tail_offset = 0;
    dmod_log_ring.flags = 0;
    
    /* Clear buffer */
    for (i = 0; i < DMOD_LOG_TOTAL_SIZE; i++) {
        dmod_log_ring.buffer[i] = 0;
    }
    
    /* Reset local state */
    current_length = 0;
    next_id = 1;
}

static void print_to_buffer(char ch)
{
    if (current_length < DMOD_LOG_MAX_ENTRY_SIZE - 1) {
        current_buffer[current_length++] = ch;
    }
}

static uint32_t get_free_space(uint32_t head, uint32_t tail)
{
    if (head >= tail) {
        return DMOD_LOG_TOTAL_SIZE - (head - tail);
    } else {
        return tail - head;
    }
}

static void write_entry(const char *data, uint32_t length)
{
    uint32_t i;
    uint32_t head = dmod_log_ring.head_offset;
    uint32_t tail = dmod_log_ring.tail_offset;
    uint32_t entry_total_size = sizeof(dmod_log_entry_header_t) + length;
    dmod_log_entry_header_t header;
    
    /* Check for clear buffer command */
    if (dmod_log_ring.flags & DMOD_FLAG_CLEAR_BUFFER) {
        Dmod_Log_Clear();
        head = 0;
        tail = 0;
    }
    
    /* Set busy flag to indicate write in progress */
    dmod_log_ring.flags |= DMOD_FLAG_BUSY;
    
    /* If entry is too large, truncate it */
    if (length > DMOD_LOG_MAX_ENTRY_SIZE) {
        length = DMOD_LOG_MAX_ENTRY_SIZE;
        entry_total_size = sizeof(dmod_log_entry_header_t) + length;
    }
    
    /* Make space if needed by advancing tail (removing old entries) */
    while (get_free_space(head, tail) < entry_total_size + 1) {
        /* Read the entry at tail to get its size */
        dmod_log_entry_header_t old_header;
        
        /* Read old entry header */
        for (i = 0; i < sizeof(dmod_log_entry_header_t); i++) {
            ((uint8_t*)&old_header)[i] = dmod_log_ring.buffer[(tail + i) % DMOD_LOG_TOTAL_SIZE];
        }
        
        /* Advance tail past this entry */
        tail = (tail + sizeof(dmod_log_entry_header_t) + old_header.length) % DMOD_LOG_TOTAL_SIZE;
        
        /* Safety check - if tail catches head or buffer seems corrupted, reset */
        /* Note: tail == head should only occur if buffer is corrupted, not during normal operation */
        /* because we check free space before writing and always keep at least 1 byte free */
        if (tail == head || old_header.length > DMOD_LOG_MAX_ENTRY_SIZE) {
            tail = 0;
            head = 0;
            break;
        }
    }
    
    /* Prepare header with magic number */
    header.magic = DMOD_ENTRY_MAGIC_NUMBER;
    header.id = next_id;
    header.length = (uint16_t)length;
    
    /* Write header to buffer */
    for (i = 0; i < sizeof(dmod_log_entry_header_t); i++) {
        dmod_log_ring.buffer[(head + i) % DMOD_LOG_TOTAL_SIZE] = ((uint8_t*)&header)[i];
    }
    head = (head + sizeof(dmod_log_entry_header_t)) % DMOD_LOG_TOTAL_SIZE;
    
    /* Write data to buffer */
    for (i = 0; i < length; i++) {
        dmod_log_ring.buffer[(head + i) % DMOD_LOG_TOTAL_SIZE] = data[i];
    }
    head = (head + length) % DMOD_LOG_TOTAL_SIZE;
    
    /* Update control structure */
    dmod_log_ring.head_offset = head;
    dmod_log_ring.tail_offset = tail;
    dmod_log_ring.latest_id = next_id;
    next_id++;
    
    /* Clear busy flag - write complete */
    dmod_log_ring.flags &= ~DMOD_FLAG_BUSY;
}

static void flush_buffer(void)
{
    if (current_length == 0) {
        return;
    }
    
    /* Write entry to ring buffer */
    write_entry(current_buffer, current_length);
    
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
