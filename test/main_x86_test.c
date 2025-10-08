/*
 * main_x86_test.c - x86 test application for dmod-boot ring buffer
 * 
 * This standalone test allows testing the ring buffer logic on x86 without
 * requiring ARM hardware or toolchain.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>

/* Override configuration for testing */
#define DMOD_LOG_TOTAL_SIZE    2048
#define DMOD_LOG_MAX_ENTRY_SIZE    256

#include "../include/dmod_printf.h"

/* Note: dmod_log_ring is defined in dmod_printf.c, not here */

/* Helper function to dump ring buffer state */
void dump_ring_state(void)
{
    printf("\n=== Ring Buffer State ===\n");
    printf("Magic:      0x%08X %s\n", dmod_log_ring.magic, 
           dmod_log_ring.magic == DMOD_MAGIC_NUMBER ? "(OK)" : "(BAD!)");
    printf("Latest ID:  %u\n", dmod_log_ring.latest_id);
    printf("Flags:      0x%08X\n", dmod_log_ring.flags);
    printf("Head:       %u\n", dmod_log_ring.head_offset);
    printf("Tail:       %u\n", dmod_log_ring.tail_offset);
    printf("Buffer:     %u bytes\n", DMOD_LOG_TOTAL_SIZE);
    printf("========================\n\n");
}

/* Helper function to read and display all entries */
void read_all_entries(void)
{
    uint32_t current_offset = dmod_log_ring.tail_offset;
    uint32_t head_offset = dmod_log_ring.head_offset;
    int count = 0;
    
    printf("\n=== All Log Entries ===\n");
    
    while (current_offset != head_offset && count < 100) {
        /* Read entry header */
        uint32_t id = *(uint32_t*)&dmod_log_ring.buffer[current_offset];
        uint16_t length = *(uint16_t*)&dmod_log_ring.buffer[current_offset + 4];
        
        if (length > DMOD_LOG_MAX_ENTRY_SIZE) {
            printf("ERROR: Entry at offset %u has invalid length %u\n", current_offset, length);
            break;
        }
        
        printf("[%u] (offset=%u, len=%u): ", id, current_offset, length);
        
        /* Read and print message */
        uint32_t data_offset = current_offset + 6;
        for (uint16_t i = 0; i < length; i++) {
            uint8_t ch = dmod_log_ring.buffer[(data_offset + i) % DMOD_LOG_TOTAL_SIZE];
            putchar(ch);
        }
        
        /* Move to next entry */
        current_offset = (current_offset + 6 + length) % DMOD_LOG_TOTAL_SIZE;
        count++;
    }
    
    printf("=== Total entries: %d ===\n\n", count);
}

/* Test functions */
void test_basic_logging(void)
{
    printf("\n*** Test 1: Basic Logging ***\n");
    
    Dmod_Log_Init();
    dump_ring_state();
    
    Dmod_Printf("Hello, World!\n");
    Dmod_Printf("Test message %d\n", 42);
    Dmod_Printf("Hex: 0x%X\n", 0xDEADBEEF);
    
    dump_ring_state();
    read_all_entries();
}

void test_wraparound(void)
{
    printf("\n*** Test 2: Buffer Wraparound ***\n");
    
    Dmod_Log_Init();
    
    /* Fill buffer with many logs to force wraparound */
    for (int i = 0; i < 50; i++) {
        Dmod_Printf("Entry %d: This is a test message with some length\n", i);
    }
    
    dump_ring_state();
    read_all_entries();
}

void test_variable_length(void)
{
    printf("\n*** Test 3: Variable Length Entries ***\n");
    
    Dmod_Log_Init();
    
    Dmod_Printf("Short\n");
    Dmod_Printf("This is a much longer message with more content to test variable length allocation\n");
    Dmod_Printf("Mid\n");
    Dmod_Printf("Another long message: %s\n", "The quick brown fox jumps over the lazy dog");
    
    dump_ring_state();
    read_all_entries();
}

void test_buffer_clear(void)
{
    printf("\n*** Test 4: Buffer Clear ***\n");
    
    Dmod_Log_Init();
    
    Dmod_Printf("Before clear 1\n");
    Dmod_Printf("Before clear 2\n");
    
    printf("Before clear:\n");
    dump_ring_state();
    read_all_entries();
    
    Dmod_Log_Clear();
    
    printf("After clear:\n");
    dump_ring_state();
    
    Dmod_Printf("After clear 1\n");
    Dmod_Printf("After clear 2\n");
    
    printf("After new logs:\n");
    dump_ring_state();
    read_all_entries();
}

void test_large_entry(void)
{
    printf("\n*** Test 5: Large Entry Truncation ***\n");
    
    Dmod_Log_Init();
    
    char large_buffer[512];
    memset(large_buffer, 'X', sizeof(large_buffer) - 1);
    large_buffer[sizeof(large_buffer) - 1] = '\0';
    
    Dmod_Printf("Large entry: %s\n", large_buffer);
    
    dump_ring_state();
    read_all_entries();
}

int main(void)
{
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║         dmod-boot Ring Buffer x86 Test Suite                ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\nConfiguration:\n");
    printf("  DMOD_LOG_TOTAL_SIZE:      %u bytes\n", DMOD_LOG_TOTAL_SIZE);
    printf("  DMOD_LOG_MAX_ENTRY_SIZE:  %u bytes\n", DMOD_LOG_MAX_ENTRY_SIZE);
    printf("  Entry header size:        6 bytes (id=4, length=2)\n");
    printf("  Ring buffer address:      %p\n", (void*)&dmod_log_ring);
    printf("\n");
    
    test_basic_logging();
    test_variable_length();
    test_wraparound();
    test_buffer_clear();
    test_large_entry();
    
    printf("\n╔══════════════════════════════════════════════════════════════╗\n");
    printf("║                    All Tests Complete                       ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    
    return 0;
}
