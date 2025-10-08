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

## Simulated OpenOCD Testing (simulate_openocd.py)

A simulated OpenOCD server that creates a virtual memory environment matching the ring buffer format.
This allows testing the Python monitor script (`dmod_log_monitor.py`) without needing actual hardware or OpenOCD.

### Running the Simulator

In one terminal:

```bash
cd test
python3 simulate_openocd.py
```

In another terminal:

```bash
python3 scripts/dmod_log_monitor.py --port 4445 --addr-file test/simulated_addresses.txt
```

### What it Tests

The simulated OpenOCD environment validates:
- OpenOCD telnet protocol handling
- Memory read commands (`mdw`)
- Ring buffer control structure parsing
- Variable-length entry reading
- Monitor script's ability to decode and display logs
- Continuous log monitoring with new entries

### How it Works

1. **Memory Simulation**: Creates a byte array matching the ring buffer structure
2. **OpenOCD Protocol**: Implements a subset of OpenOCD's telnet commands
3. **Live Updates**: Continuously adds new log entries to simulate a running system
4. **Network Server**: Listens on port 4445 (to avoid conflicts with real OpenOCD on 4444)

### Configuration

Edit `test/simulated_addresses.txt` to adjust:
- Ring buffer address
- Total buffer size
- Max entry size

Edit `test/simulate_openocd.py` to adjust:
- Initial log messages
- Rate of new log generation
- Buffer configuration

### Benefits

- **End-to-end testing** - Validates the entire monitor→OpenOCD→target chain
- **No hardware needed** - Test without STM32 boards
- **Reproducible** - Same behavior every time
- **Fast debugging** - Add print statements to see protocol details
- **Integration testing** - Validates monitor script with realistic OpenOCD responses

This completes the target-independent testing infrastructure as requested.


