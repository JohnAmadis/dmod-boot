# dmod-boot

Dynamic Modules (dMOD) bootloader - A minimalistic embedded project for STM32 microcontrollers.

## Overview

dmod-boot is a minimal bootloader framework designed for embedded systems, specifically targeting STM32 ARM Cortex-M microcontrollers. It provides a clean, dependency-free foundation for dynamic module loading without relying on external libraries like STM32Cube.

### Key Features

- **No External Dependencies**: Pure bare-metal implementation without STM32Cube or other HAL libraries
- **Memory Ring Buffer Debug Output**: Built-in printf implementation using a memory ring buffer - works across all architectures
- **Multiple Architecture Support**: Linker scripts and startup code for various STM32 families
- **Minimal Footprint**: Optimized for size and efficiency
- **Easy to Extend**: Clean structure for adding support for additional microcontrollers
- **OpenOCD Integration**: Python script for monitoring logs via OpenOCD

## Supported Targets

Currently supported STM32 families:

| Target | MCU Family | Core | Flash | RAM | FPU |
|--------|------------|------|-------|-----|-----|
| STM32F746 | STM32F7 | Cortex-M7 | 1MB | 320KB | FPv5-SP-D16 |
| STM32F407 | STM32F4 | Cortex-M4 | 1MB | 128KB + 64KB CCM | FPv4-SP-D16 |

## Project Structure

```
dmod-boot/
├── src/                    # Source files
│   ├── dmod_printf.c      # Ring buffer based printf implementation
│   ├── startup_stm32f746.c # Startup code for STM32F746
│   └── startup_stm32f407.c # Startup code for STM32F407
├── include/               # Header files
│   └── dmod_printf.h     # Printf API definitions
├── linker/               # Linker scripts
│   ├── STM32F746xG.ld   # Linker script for STM32F746
│   └── STM32F407xG.ld   # Linker script for STM32F407
├── examples/             # Example applications
│   └── main.c           # Simple example with ring buffer output
├── scripts/              # Utility scripts
│   └── dmod_log_monitor.py # OpenOCD log monitoring script
├── Makefile             # Build system
└── README.md           # This file
```

## Prerequisites

### Required Tools

- **ARM GCC Toolchain**: `arm-none-eabi-gcc` and related tools
  - Ubuntu/Debian: `sudo apt-get install gcc-arm-none-eabi`
  - macOS: `brew install arm-none-eabi-gcc`
  - Windows: Download from [ARM Developer](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm)

- **Make**: Build automation tool
  - Usually pre-installed on Linux/macOS
  - Windows: Install via MSYS2 or use WSL

### Optional Tools (for debugging)

- **Python 3**: For log monitoring script
- **OpenOCD**: For flashing and debugging
- **GDB**: For debugging
- **ST-Link** utilities as alternative to OpenOCD

## Building

### Build for STM32F746

```bash
make TARGET=STM32F746
# or
make stm32f746
```

### Build for STM32F407

```bash
make TARGET=STM32F407
# or
make stm32f407
```

### Build All Targets

```bash
make all-targets
```

### Configure Ring Buffer Size

You can customize the ring buffer configuration using Makefile variables:

```bash
# Build with custom ring buffer settings
make TARGET=STM32F746 DMOD_LOG_ENTRIES=256 DMOD_LOG_BUFFER_SIZE=512

# Default values:
# DMOD_LOG_ENTRIES=128       (number of log entries)
# DMOD_LOG_BUFFER_SIZE=256   (bytes per entry buffer)
```

### Clean Build Artifacts

```bash
make clean
```

### View Help

```bash
make help
```

## Output Files

After building, the following files will be generated in the `build/` directory:

- `<TARGET>.elf` - ELF executable with debug symbols
- `<TARGET>.bin` - Raw binary file for flashing
- `<TARGET>.hex` - Intel HEX format file
- `<TARGET>.map` - Linker map file showing memory layout
- `<TARGET>_dmod_addresses.txt` - Ring buffer addresses for debugging

## Using Memory Ring Buffer Debug Output

The project uses a memory ring buffer for debug output, providing a non-intrusive way to log messages that works across all architectures (not ARM-specific like ITM).

### API Usage

```c
#include "dmod_printf.h"

int main(void) {
    // Initialize log ring buffer
    Dmod_Log_Init();
    
    // Use printf-like formatting
    Dmod_Printf("Hello, World!\n");
    Dmod_Printf("Counter: %d\n", 42);
    Dmod_Printf("Hex: 0x%X\n", 0xDEADBEEF);
    
    while (1) {
        // Your code here
    }
    
    return 0;
}
```

### Supported Format Specifiers

- `%d`, `%i` - Signed decimal integer
- `%u` - Unsigned decimal integer
- `%x` - Unsigned hexadecimal (lowercase)
- `%X` - Unsigned hexadecimal (uppercase)
- `%c` - Character
- `%s` - String
- `%%` - Literal percent sign

### Ring Buffer Structure

The ring buffer consists of:
- **latest_id**: Most recent log entry ID (uint32_t) - easy to monitor for new logs
- **write_index**: Current write position (uint32_t)
- **entries**: Array of log entries, each containing:
  - **id**: Unique incrementing ID for the entry
  - **length**: Actual message length
  - **buffer**: Message data

### Monitoring Logs via OpenOCD

A Python script is provided to monitor logs in real-time via OpenOCD:

1. **Start OpenOCD** with your target:
```bash
# For STM32F746
openocd -f interface/stlink.cfg -f target/stm32f7x.cfg

# For STM32F407
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg
```

2. **Run the monitoring script** (in a separate terminal):
```bash
# Monitor STM32F746 logs
python3 scripts/dmod_log_monitor.py --target STM32F746

# Monitor STM32F407 logs
python3 scripts/dmod_log_monitor.py --target STM32F407

# With custom OpenOCD connection
python3 scripts/dmod_log_monitor.py --host localhost --port 6666 --interval 0.1
```

The script will:
- Read the ring buffer address from `build/<TARGET>_dmod_addresses.txt`
- Connect to OpenOCD's TCL server
- Poll the ring buffer for new log entries
- Display messages in real-time

### Manual Memory Inspection

You can also manually inspect the ring buffer using OpenOCD or GDB:

```bash
# In OpenOCD telnet interface (port 4444)
# Read ring buffer address from build/<TARGET>_dmod_addresses.txt
mdw 0x20000124 10    # Read latest_id and write_index
mdw 0x2000012c 66    # Read first entry (264 bytes = 66 words)
```

## Flashing the Firmware

### Using OpenOCD

```bash
openocd -f interface/stlink.cfg -f target/stm32f7x.cfg \
    -c "program build/STM32F746.elf verify reset exit"
```

### Using ST-Link

```bash
st-flash write build/STM32F746.bin 0x08000000
```

## Extending the Project

### Adding a New Target

1. Create a linker script in `linker/` directory (e.g., `STM32F103xB.ld`)
2. Create a startup file in `src/` directory (e.g., `startup_stm32f103.c`)
3. Add the new target to the Makefile
4. Update this README with the new target information

### Adding Features

The minimal design makes it easy to add features:

- **GPIO Control**: Add GPIO initialization and control functions
- **UART Communication**: Implement UART drivers
- **Timers**: Add timer configuration and interrupts
- **DMA**: Implement DMA transfers for efficient data movement

## Memory Layout

### STM32F746xG

- **Flash**: 0x08000000 - 0x080FFFFF (1MB)
- **RAM**: 0x20000000 - 0x2004FFFF (320KB)
  - Log ring buffer placed at start of RAM (configurable size)
- **DTCM RAM**: 0x20000000 - 0x2000FFFF (64KB)
- **ITCM RAM**: 0x00000000 - 0x00003FFF (16KB)

### STM32F407xG

- **Flash**: 0x08000000 - 0x080FFFFF (1MB)
- **RAM**: 0x20000000 - 0x2001FFFF (128KB)
  - Log ring buffer placed at start of RAM (configurable size)
- **CCM RAM**: 0x10000000 - 0x1000FFFF (64KB)

### Ring Buffer Memory Usage

With default configuration:
- **Entries**: 128
- **Buffer size per entry**: 256 bytes
- **Total size**: ~33.8 KB (8 bytes control + 128 × 264 bytes)

## Contributing

Contributions are welcome! Please feel free to submit pull requests for:

- Additional STM32 family support
- Bug fixes
- Documentation improvements
- New features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [dmod](https://github.com/JohnAmadis/dmod) - Dynamic modules library for embedded architectures

## References

- [ARM Cortex-M7 Technical Reference Manual](https://developer.arm.com/documentation/ddi0489/latest/)
- [STM32F7 Reference Manual](https://www.st.com/resource/en/reference_manual/dm00124865.pdf)
- [STM32F4 Reference Manual](https://www.st.com/resource/en/reference_manual/dm00031020.pdf)
- [OpenOCD User's Guide](http://openocd.org/doc/html/index.html)

## Troubleshooting

### Build Issues

**Problem**: `arm-none-eabi-gcc: command not found`
- **Solution**: Install the ARM GCC toolchain (see Prerequisites)

**Problem**: Linker errors about undefined references
- **Solution**: Ensure all source files are included in the Makefile

**Problem**: Ring buffer takes too much RAM
- **Solution**: Reduce `DMOD_LOG_ENTRIES` or `DMOD_LOG_BUFFER_SIZE` in the Makefile

### Debugging Issues

**Problem**: Cannot connect to OpenOCD
- **Solution**: Make sure OpenOCD is running with TCL server enabled (port 6666)
- Check: `telnet localhost 4444` should connect to OpenOCD

**Problem**: No log output visible in monitor script
- **Solution**: Verify the target is running and calling `Dmod_Printf()`
- Check the ring buffer address in `build/<TARGET>_dmod_addresses.txt`
- Verify OpenOCD can read target memory

**Problem**: Program crashes or doesn't start
- **Solution**: Verify the correct linker script is used for your target MCU
- Check that ring buffer size doesn't exceed available RAM
