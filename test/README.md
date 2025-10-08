# Tests

This directory contains tests for the dmod-boot project.

## test_buffer_logic.py

A Python simulation test that validates the ring buffer logic:

- Variable-length entry allocation
- Buffer wraparound and oldest entry eviction
- Entry header parsing
- Memory efficiency calculations

### Running the test

```bash
python3 test/test_buffer_logic.py
```

All tests should pass with output showing:
- Basic write operations
- Buffer wraparound behavior
- Variable-length entry handling
- Memory efficiency comparison (new vs old design)
- Entry ID incrementing
- Large entry truncation
- Oldest entry eviction

This test ensures the C implementation logic is correct without requiring the ARM toolchain.

## x86 Test Target (main_x86_test.c)

A standalone x86 test application that compiles and runs the actual C code on the host system.
This allows testing the ring buffer implementation without ARM hardware or toolchain.

### Building and Running

```bash
cd test
make test
```

Or manually:

```bash
cd test
make
./dmod_test_x86
```

### What it Tests

The x86 test suite validates:
- Basic logging operations
- Variable-length entries
- Buffer wraparound and oldest entry eviction
- Buffer clear functionality
- Large entry truncation
- Visual output showing ring buffer state and all entries

### Configuration

The x86 test uses smaller buffer sizes for faster testing:
- `DMOD_LOG_TOTAL_SIZE`: 2048 bytes
- `DMOD_LOG_MAX_ENTRY_SIZE`: 256 bytes

These can be adjusted in `test/Makefile`.

### Why x86 Testing?

Benefits of having an x86 test target:
1. **No ARM toolchain required** - Tests on the development host
2. **Faster iteration** - Quick compile and run cycles
3. **Standard debugging tools** - Use gdb, valgrind, etc.
4. **CI/CD friendly** - Easy to integrate into automated testing
5. **Target independent** - Validates core logic without hardware dependencies

This makes the repository truly target-independent as requested.

