# dmod-boot Scripts

This directory contains utility scripts for working with dmod-boot.

## dmod_log_monitor.py

Python script for monitoring log output from the target microcontroller via OpenOCD in real-time.

### Quick Start

Use the integrated Makefile commands for the easiest experience:

```bash
# Start OpenOCD server (in one terminal)
make connect

# Monitor logs (in another terminal)
make monitor
```

### Manual Usage

For advanced usage or custom configurations:

```bash
# Basic usage (default: STM32F746)
python3 scripts/dmod_log_monitor.py

# Specify target
python3 scripts/dmod_log_monitor.py --target STM32F407

# Enable debug logging
python3 scripts/dmod_log_monitor.py --debug

# Custom OpenOCD connection
python3 scripts/dmod_log_monitor.py --host 192.168.1.100 --port 4444

# Custom polling interval (default: 0.1 seconds)
python3 scripts/dmod_log_monitor.py --interval 0.05

# Use custom address file
python3 scripts/dmod_log_monitor.py --addr-file /path/to/addresses.txt
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--target` | STM32F746 | Target microcontroller (STM32F746, STM32F407) |
| `--host` | localhost | OpenOCD host address |
| `--port` | 4444 | OpenOCD telnet port |
| `--interval` | 0.1 | Polling interval in seconds |
| `--addr-file` | auto | Path to address file (auto-detected from target) |
| `--debug` | disabled | Enable detailed debug logging |

### Requirements

- **Python 3.x**
- **OpenOCD** running with telnet server enabled
- **Built firmware** (for address file generation)

### How It Works

The script implements a sophisticated ring buffer monitoring system:

1. **Address Resolution**: Reads ring buffer address from `build/<TARGET>_dmod_addresses.txt`
2. **OpenOCD Connection**: Connects to OpenOCD's telnet server (port 4444)
3. **Magic Number Validation**: Verifies ring buffer integrity using magic number `0x444D4F44` ("DMOD")
4. **Smart Polling**: Monitors the `latest_id` field for changes to detect new log entries
5. **Race Condition Handling**: Uses retry logic to handle concurrent firmware writes
6. **Ring Buffer Wrapping**: Correctly handles when the ring buffer wraps around
7. **Real-time Display**: Shows new log messages as they arrive

### Ring Buffer Structure

The script reads a memory structure with:

```c
typedef struct {
    volatile uint32_t magic;           // 0x444D4F44 ("DMOD")
    volatile uint32_t latest_id;       // Most recent log entry ID
    volatile uint32_t flags;           // Command/status flags (bit 0: clear buffer)
    volatile uint32_t head_offset;     // Offset to newest entry
    volatile uint32_t tail_offset;     // Offset to oldest entry
    volatile uint8_t buffer[8192];     // Variable-length entries
} dmod_log_ring_t;

typedef struct {
    volatile uint32_t id;              // Unique entry ID
    volatile uint16_t length;          // Message length
    // followed by message data (variable length)
} __attribute__((packed)) dmod_log_entry_header_t;
```

The new design uses a single fixed-size buffer with variable-length entries, which is much more memory-efficient than the old fixed-size entry approach.

### OpenOCD Setup

#### Automatic (Recommended)

```bash
make connect
```

#### Manual Setup

```bash
# For STM32F746
openocd -f interface/stlink.cfg -f target/stm32f7x.cfg

# For STM32F407
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg
```

The script connects to OpenOCD's **telnet port (4444)**, not to be confused with:
- **GDB port (3333)**: For debugging with GDB
- **TCL port (6666)**: For TCL scripts

### Debug Mode

Enable debug logging to see detailed monitoring information:

```bash
python3 scripts/dmod_log_monitor.py --debug
```

Debug output includes:
- Memory read operations and results
- Ring buffer state changes
- Entry parsing details
- Magic number validation
- Race condition detection

### Example Output

Normal operation:
```
Loading addresses from build/STM32F746_dmod_addresses.txt
Ring buffer address: 0x20000124
Total buffer size: 8192 bytes
Max entry size: 512 bytes

Connecting to OpenOCD at localhost:4444...
Connected to OpenOCD

Monitoring dmod-boot log ring buffer at 0x20000124
Buffer size: 8192 bytes, max entry: 512 bytes
Press Ctrl+C to stop

Starting from log ID: 1234, head: 1024, tail: 0
dmod-boot initialized
System starting...
Ring buffer debug output enabled

Counter: 1235 (0x4D3)
Counter: 1236 (0x4D4)
Counter: 1237 (0x4D5)
...
```

With debug enabled:
```
2024-10-08 14:30:15 - __main__ - DEBUG - latest_id changed from 1234 to 1235
2024-10-08 14:30:15 - __main__ - DEBUG - Found new entries, reading from tail 0 to head 1024
2024-10-08 14:30:15 - __main__ - DEBUG - Reading entry at offset 0: id=1235, length=22
Counter: 1235 (0x4D3)
```

### Manual Memory Inspection

You can also manually inspect the ring buffer using OpenOCD's telnet interface:

```bash
# Connect to OpenOCD telnet
telnet localhost 4444

# Read ring buffer control structure (magic, latest_id, flags, head_offset, tail_offset)
mdw 0x20000124 5

# Read buffer data at specific offset
mdw 0x20000138 32

# Halt target for stable reading
halt
mdw 0x20000124 10
resume
```

### Performance Tuning

For high-frequency logging, adjust the polling interval:

```bash
# Faster polling (higher CPU usage)
python3 scripts/dmod_log_monitor.py --interval 0.01

# Slower polling (lower CPU usage)
python3 scripts/dmod_log_monitor.py --interval 0.5
```

### Troubleshooting

#### Connection Issues

**Problem**: `Failed to connect to OpenOCD at localhost:4444`
- **Solution**: Ensure OpenOCD is running with `make connect`
- **Check**: `telnet localhost 4444` should connect successfully
- **Alternative**: Try different port with `--port 6666` if using TCL interface

**Problem**: `Connection closed by foreign host`
- **Solution**: OpenOCD may have crashed or been restarted
- **Fix**: Restart OpenOCD with `make connect`

#### Address/Build Issues

**Problem**: `Could not load addresses from build/STM32F746_dmod_addresses.txt`
- **Solution**: Build the firmware first with `make`
- **Check**: Verify the file exists and contains `DMOD_LOG_RING_ADDR=...`

**Problem**: `Error parsing addresses`
- **Solution**: Rebuild firmware - address file may be corrupted
- **Command**: `make clean && make`

#### Memory/Target Issues

**Problem**: `Failed to read ring buffer control after 3 attempts`
- **Cause**: Target may be halted, crashed, or memory not accessible
- **Solutions**:
  - Resume target: `echo "resume" | nc localhost 4444`
  - Reset target: `echo "reset" | nc localhost 4444`
  - Check target power and connections

**Problem**: `Invalid magic number`
- **Cause**: Ring buffer not initialized or memory corruption
- **Solutions**:
  - Ensure `Dmod_Log_Init()` is called in firmware
  - Reset and reflash: `make install`
  - Check if target is running the correct firmware

**Problem**: No log output visible
- **Causes**: Target not calling `Dmod_Printf()`, or ring buffer full
- **Solutions**:
  - Verify firmware is calling `Dmod_Printf()`
  - Check if target is stuck in a loop
  - Use debug mode: `--debug` to see internal monitoring state

#### Performance Issues

**Problem**: High CPU usage
- **Solution**: Increase polling interval: `--interval 0.5`

**Problem**: Logs appear delayed
- **Solution**: Decrease polling interval: `--interval 0.01`
- **Note**: Very fast polling may impact OpenOCD performance

### Advanced Features

#### Custom Address Files

For non-standard builds or custom linker scripts:

```bash
python3 scripts/dmod_log_monitor.py --addr-file custom_addresses.txt
```

Address file format:
```
# Comments start with #
DMOD_LOG_RING_ADDR=0x20000124
DMOD_LOG_TOTAL_SIZE=8192
DMOD_LOG_MAX_ENTRY_SIZE=512
```

#### Remote OpenOCD

Monitor targets connected to remote OpenOCD instances:

```bash
python3 scripts/dmod_log_monitor.py --host 192.168.1.100 --port 4444
```

#### Integration with Development Tools

The script can be integrated into IDEs or development workflows:

```bash
# Run in background and log to file
python3 scripts/dmod_log_monitor.py > debug.log 2>&1 &

# Use with grep for filtering
python3 scripts/dmod_log_monitor.py | grep "ERROR"

# Timestamped logging
python3 scripts/dmod_log_monitor.py | while read line; do
    echo "$(date): $line"
done
```
