# dmod-boot Scripts

This directory contains utility scripts for working with dmod-boot.

## dmod_log_monitor.py

Python script for monitoring log output from the target microcontroller via OpenOCD.

### Requirements

- Python 3.x
- OpenOCD running with TCL server enabled

### Usage

```bash
# Basic usage (default: STM32F746)
python3 scripts/dmod_log_monitor.py

# Specify target
python3 scripts/dmod_log_monitor.py --target STM32F407

# Custom OpenOCD connection
python3 scripts/dmod_log_monitor.py --host 192.168.1.100 --port 6666

# Custom polling interval (default: 0.1 seconds)
python3 scripts/dmod_log_monitor.py --interval 0.5

# Use custom address file
python3 scripts/dmod_log_monitor.py --addr-file /path/to/addresses.txt
```

### How It Works

1. Reads the ring buffer address from `build/<TARGET>_dmod_addresses.txt`
2. Connects to OpenOCD's TCL server (default port 6666)
3. Polls the ring buffer's `latest_id` field for changes
4. When new entries are detected, reads and displays them
5. Continues monitoring until interrupted with Ctrl+C

### OpenOCD Setup

Make sure OpenOCD is running before starting the monitor:

```bash
# For STM32F746
openocd -f interface/stlink.cfg -f target/stm32f7x.cfg

# For STM32F407
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg
```

The script connects to:
- **TCL port**: 6666 (for sending commands)
- Not to be confused with the telnet port (4444) or GDB port (3333)

### Troubleshooting

**Problem**: `Failed to connect to OpenOCD`
- Ensure OpenOCD is running
- Check that the TCL server is enabled (default)
- Verify the host and port settings

**Problem**: `Could not load addresses`
- Build the firmware first with `make`
- Check that `build/<TARGET>_dmod_addresses.txt` exists

**Problem**: No output visible
- Verify the target is running
- Check that `Dmod_Printf()` is being called in your code
- Use OpenOCD's telnet interface to manually inspect memory
