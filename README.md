# dmod-boot

Dynamic Modules (dMOD) bootloader - A minimalistic embedded project for STM32 microcontrollers.

## Overview

dmod-boot is a minimal bootloader framework designed for embedded systems, specifically targeting STM32 ARM Cortex-M microcontrollers. It provides a clean, dependency-free foundation for dynamic module loading without relying on external libraries like STM32Cube.

### Key Features

- **No External Dependencies**: Pure bare-metal implementation without STM32Cube or other HAL libraries
- **ITM Debug Output**: Built-in printf implementation using ARM's Instrumentation Trace Macrocell (ITM)
- **Multiple Architecture Support**: Linker scripts and startup code for various STM32 families
- **Minimal Footprint**: Optimized for size and efficiency
- **Easy to Extend**: Clean structure for adding support for additional microcontrollers

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
│   ├── dmod_printf.c      # ITM-based printf implementation
│   ├── startup_stm32f746.c # Startup code for STM32F746
│   └── startup_stm32f407.c # Startup code for STM32F407
├── include/               # Header files
│   └── dmod_printf.h     # Printf API definitions
├── linker/               # Linker scripts
│   ├── STM32F746xG.ld   # Linker script for STM32F746
│   └── STM32F407xG.ld   # Linker script for STM32F407
├── examples/             # Example applications
│   └── main.c           # Simple example with ITM output
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

- OpenOCD or ST-Link utilities for flashing
- GDB for debugging
- Serial Wire Viewer (SWV) compatible debugger for ITM output

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

## Using ITM Debug Output

The project uses ARM's Instrumentation Trace Macrocell (ITM) for debug output, providing a non-intrusive way to output debug information without blocking the CPU.

### API Usage

```c
#include "dmod_printf.h"

int main(void) {
    // Initialize ITM
    Dmod_ITM_Init();
    
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

### Viewing ITM Output

To view ITM output, you need a debugger that supports Serial Wire Viewer (SWV):

1. **OpenOCD** with SWO/SWV enabled
2. **ST-Link Utility** with SWV viewer
3. **Segger J-Link** with RTT Viewer
4. **GDB** with appropriate ITM configuration

Example OpenOCD configuration:
```
# Enable ITM on stimulus port 0
tpiu config internal itm.log uart off 168000000
itm port 0 on
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
- **DTCM RAM**: 0x20000000 - 0x2000FFFF (64KB)
- **ITCM RAM**: 0x00000000 - 0x00003FFF (16KB)

### STM32F407xG

- **Flash**: 0x08000000 - 0x080FFFFF (1MB)
- **RAM**: 0x20000000 - 0x2001FFFF (128KB)
- **CCM RAM**: 0x10000000 - 0x1000FFFF (64KB)

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
- [ARM ITM Documentation](https://developer.arm.com/documentation/ddi0403/latest/)

## Troubleshooting

### Build Issues

**Problem**: `arm-none-eabi-gcc: command not found`
- **Solution**: Install the ARM GCC toolchain (see Prerequisites)

**Problem**: Linker errors about undefined references
- **Solution**: Ensure all source files are included in the Makefile

### Debugging Issues

**Problem**: No ITM output visible
- **Solution**: Ensure your debugger supports SWV and ITM port 0 is enabled

**Problem**: Program crashes or doesn't start
- **Solution**: Verify the correct linker script is used for your target MCU
