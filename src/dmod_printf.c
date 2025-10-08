/*
 * dmod_printf.c - ITM-based printf implementation for dmod-boot
 * 
 * Minimal printf implementation using ARM's Instrumentation Trace Macrocell (ITM)
 * for debugging output without external libraries.
 */

#include "dmod_printf.h"
#include <stddef.h>

/* Helper function prototypes */
static void print_int(int32_t value);
static void print_uint(uint32_t value);
static void print_hex(uint32_t value, int uppercase);
static int strlen_local(const char *str);

void Dmod_ITM_Init(void)
{
    /* Enable ITM stimulus port 0 */
    ITM_TER |= (1UL << ITM_PORT_PRINTF);
}

void Dmod_ITM_SendChar(char ch)
{
    /* Wait until ITM port is ready */
    while (!(ITM_STIM0 & 1UL));
    
    /* Send character to ITM stimulus port 0 */
    ITM_STIM0 = (uint8_t)ch;
}

void Dmod_ITM_SendString(const char *str)
{
    if (str == NULL) {
        return;
    }
    
    while (*str) {
        Dmod_ITM_SendChar(*str++);
    }
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
        Dmod_ITM_SendChar('0');
        return;
    }
    
    /* Extract digits in reverse order */
    while (value > 0) {
        buffer[i++] = '0' + (value % 10);
        value /= 10;
    }
    
    /* Print negative sign if needed */
    if (is_negative) {
        Dmod_ITM_SendChar('-');
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        Dmod_ITM_SendChar(buffer[--i]);
    }
}

static void print_uint(uint32_t value)
{
    char buffer[11]; /* Enough for 4294967295 */
    int i = 0;
    
    /* Handle 0 explicitly */
    if (value == 0) {
        Dmod_ITM_SendChar('0');
        return;
    }
    
    /* Extract digits in reverse order */
    while (value > 0) {
        buffer[i++] = '0' + (value % 10);
        value /= 10;
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        Dmod_ITM_SendChar(buffer[--i]);
    }
}

static void print_hex(uint32_t value, int uppercase)
{
    char buffer[9]; /* Enough for FFFFFFFF + null */
    int i = 0;
    const char *hex_chars = uppercase ? "0123456789ABCDEF" : "0123456789abcdef";
    
    /* Handle 0 explicitly */
    if (value == 0) {
        Dmod_ITM_SendChar('0');
        return;
    }
    
    /* Extract hex digits in reverse order */
    while (value > 0) {
        buffer[i++] = hex_chars[value & 0xF];
        value >>= 4;
    }
    
    /* Print digits in correct order */
    while (i > 0) {
        Dmod_ITM_SendChar(buffer[--i]);
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
                    Dmod_ITM_SendChar(ch);
                    count++;
                    break;
                }
                
                case 's': {
                    const char *str = va_arg(args, const char *);
                    if (str) {
                        Dmod_ITM_SendString(str);
                        count += strlen_local(str);
                    } else {
                        Dmod_ITM_SendString("(null)");
                        count += 6;
                    }
                    break;
                }
                
                case '%': {
                    Dmod_ITM_SendChar('%');
                    count++;
                    break;
                }
                
                default:
                    /* Unknown format specifier, print as-is */
                    Dmod_ITM_SendChar('%');
                    Dmod_ITM_SendChar(*format);
                    count += 2;
                    break;
            }
            
            format++;
        } else {
            Dmod_ITM_SendChar(*format);
            format++;
            count++;
        }
    }
    
    va_end(args);
    return count;
}
