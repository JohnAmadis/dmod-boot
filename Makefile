# Makefile for dmod-boot
# Minimal embedded project for STM32 microcontrollers

# Target selection (STM32F746 or STM32F407)
TARGET ?= STM32F746

# Log ring buffer configuration
DMOD_LOG_TOTAL_SIZE ?= 8192
DMOD_LOG_MAX_ENTRY_SIZE ?= 512

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size
OBJDUMP = arm-none-eabi-objdump
NM = arm-none-eabi-nm

# Directories
SRC_DIR = src
INC_DIR = include
LINKER_DIR = linker
EXAMPLES_DIR = examples
BUILD_DIR = build
SCRIPTS_DIR = scripts

# Target-specific settings
ifeq ($(TARGET),STM32F746)
    LINKER_SCRIPT = $(LINKER_DIR)/STM32F746xG.ld
    STARTUP_SRC = $(SRC_DIR)/startup_stm32f746.c
    CPU = cortex-m7
    FPU = -mfpu=fpv5-sp-d16
    FLOAT_ABI = -mfloat-abi=hard
    OPENOCD_TARGET = target/stm32f7x.cfg
else ifeq ($(TARGET),STM32F407)
    LINKER_SCRIPT = $(LINKER_DIR)/STM32F407xG.ld
    STARTUP_SRC = $(SRC_DIR)/startup_stm32f407.c
    CPU = cortex-m4
    FPU = -mfpu=fpv4-sp-d16
    FLOAT_ABI = -mfloat-abi=hard
    OPENOCD_TARGET = target/stm32f4x.cfg
else
    $(error Invalid TARGET. Use STM32F746 or STM32F407)
endif

# OpenOCD settings
OPENOCD_INTERFACE = interface/stlink.cfg
OPENOCD = openocd

# Compiler flags
CFLAGS = -mcpu=$(CPU) -mthumb $(FPU) $(FLOAT_ABI)
CFLAGS += -Wall -Wextra -Werror
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -O2 -g
CFLAGS += -I$(INC_DIR)
CFLAGS += -DSTM32 -D$(TARGET)
CFLAGS += -DDMOD_LOG_TOTAL_SIZE=$(DMOD_LOG_TOTAL_SIZE)
CFLAGS += -DDMOD_LOG_MAX_ENTRY_SIZE=$(DMOD_LOG_MAX_ENTRY_SIZE)

# Linker flags
LDFLAGS = -mcpu=$(CPU) -mthumb $(FPU) $(FLOAT_ABI)
LDFLAGS += -T$(LINKER_SCRIPT)
LDFLAGS += -Wl,--gc-sections
LDFLAGS += -Wl,-Map=$(BUILD_DIR)/$(TARGET).map
LDFLAGS += --specs=nosys.specs
LDFLAGS += --specs=nano.specs

# Source files
SRCS = $(STARTUP_SRC) \
       $(SRC_DIR)/dmod_printf.c \
       $(EXAMPLES_DIR)/main.c

# Object files
OBJS = $(SRCS:%.c=$(BUILD_DIR)/%.o)

# Output files
ELF = $(BUILD_DIR)/$(TARGET).elf
BIN = $(BUILD_DIR)/$(TARGET).bin
HEX = $(BUILD_DIR)/$(TARGET).hex
ADDR_FILE = $(BUILD_DIR)/$(TARGET)_dmod_addresses.txt

# Default target
.PHONY: all
all: $(BIN) $(HEX) $(ADDR_FILE)
	@echo "Build complete for $(TARGET)"
	@$(SIZE) $(ELF)

# Create build directories
$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)/$(SRC_DIR)
	@mkdir -p $(BUILD_DIR)/$(EXAMPLES_DIR)

# Compile C files
$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	@echo "Compiling $<"
	@mkdir -p $(dir $@)
	@$(CC) $(CFLAGS) -c $< -o $@

# Link
$(ELF): $(OBJS)
	@echo "Linking $@"
	@$(CC) $(OBJS) $(LDFLAGS) -o $@

# Create binary file
$(BIN): $(ELF)
	@echo "Creating binary $@"
	@$(OBJCOPY) -O binary $< $@

# Create hex file
$(HEX): $(ELF)
	@echo "Creating hex $@"
	@$(OBJCOPY) -O ihex $< $@

# Extract addresses for debugging
$(ADDR_FILE): $(ELF)
	@echo "Extracting symbol addresses to $@"
	@echo "# dmod-boot Symbol Addresses for $(TARGET)" > $@
	@echo "# Generated: $$(date)" >> $@
	@echo "" >> $@
	@echo "DMOD_LOG_RING_ADDR=$$($(NM) $< | grep ' dmod_log_ring$$' | cut -d' ' -f1)" >> $@
	@echo "DMOD_LOG_RING_START=$$($(NM) $< | grep _dmod_log_ring_start | cut -d' ' -f1)" >> $@
	@echo "DMOD_LOG_RING_END=$$($(NM) $< | grep _dmod_log_ring_end | cut -d' ' -f1)" >> $@
	@echo "DMOD_LOG_TOTAL_SIZE=$(DMOD_LOG_TOTAL_SIZE)" >> $@
	@echo "DMOD_LOG_MAX_ENTRY_SIZE=$(DMOD_LOG_MAX_ENTRY_SIZE)" >> $@
	@echo "" >> $@
	@echo "Addresses saved to $@"

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts"
	@rm -rf $(BUILD_DIR)

# Build for STM32F746
.PHONY: stm32f746
stm32f746:
	@$(MAKE) TARGET=STM32F746

# Build for STM32F407
.PHONY: stm32f407
stm32f407:
	@$(MAKE) TARGET=STM32F407

# Build all targets
.PHONY: all-targets
all-targets: stm32f746 stm32f407

# Disassembly
.PHONY: disasm
disasm: $(ELF)
	@$(OBJDUMP) -d $< > $(BUILD_DIR)/$(TARGET).dis

# Install firmware on target
.PHONY: install
install: $(ELF)
	@echo "Installing firmware on $(TARGET)..."
	@$(OPENOCD) -f $(OPENOCD_INTERFACE) -f $(OPENOCD_TARGET) \
		-c "program $(ELF) verify reset exit"

# Connect to target with OpenOCD
.PHONY: connect
connect:
	@echo "Connecting to $(TARGET) with OpenOCD..."
	@echo "OpenOCD will start and wait for connections (GDB: port 3333, Telnet: port 4444)"
	@echo "Press Ctrl+C to stop OpenOCD"
	@$(OPENOCD) -f $(OPENOCD_INTERFACE) -f $(OPENOCD_TARGET)

# Monitor log output
.PHONY: monitor
monitor: $(ADDR_FILE)
	@echo "Starting log monitor for $(TARGET)..."
	@python3 $(SCRIPTS_DIR)/dmod_log_monitor.py --target $(TARGET)

# Run simulated OpenOCD for testing monitor script
.PHONY: test-monitor
test-monitor:
	@echo "Starting simulated OpenOCD server..."
	@echo "In another terminal, run:"
	@echo "  python3 scripts/dmod_log_monitor.py --port 4445 --addr-file test/simulated_addresses.txt"
	@python3 test/simulate_openocd.py

# Run tests
.PHONY: test
test:
	@echo "Running Python simulation tests..."
	@python3 test/test_buffer_logic.py
	@echo ""
	@echo "Running x86 native tests..."
	@cd test && $(MAKE) test

# Clean test artifacts
.PHONY: test-clean
test-clean:
	@cd test && $(MAKE) clean

# Help
.PHONY: help
help:
	@echo "dmod-boot Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make [TARGET=<target>]  - Build for specified target (default: STM32F746)"
	@echo "  make install            - Build and install firmware on target"
	@echo "  make connect            - Connect to target with OpenOCD"
	@echo "  make monitor            - Monitor log output from target"
	@echo "  make test               - Run all tests (Python + x86)"
	@echo "  make test-monitor       - Run simulated OpenOCD for testing"
	@echo "  make stm32f746          - Build for STM32F746"
	@echo "  make stm32f407          - Build for STM32F407"
	@echo "  make all-targets        - Build for all targets"
	@echo "  make clean              - Remove build artifacts"
	@echo "  make test-clean         - Remove test artifacts"
	@echo "  make disasm             - Generate disassembly"
	@echo "  make help               - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  DMOD_LOG_TOTAL_SIZE=$(DMOD_LOG_TOTAL_SIZE)       - Total size of log buffer in bytes"
	@echo "  DMOD_LOG_MAX_ENTRY_SIZE=$(DMOD_LOG_MAX_ENTRY_SIZE) - Maximum size of a single log entry"
	@echo ""
	@echo "Targets:"
	@echo "  STM32F746 - STM32F746 (Cortex-M7, 1MB Flash, 320KB RAM)"
	@echo "  STM32F407 - STM32F407 (Cortex-M4, 1MB Flash, 128KB RAM + 64KB CCM)"
	@echo ""
	@echo "OpenOCD Commands:"
	@echo "  make install            - Program firmware via OpenOCD"
	@echo "  make connect            - Start OpenOCD server for debugging"
	@echo "  make monitor            - Monitor debug logs via OpenOCD"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run all tests (Python simulation + x86 native)"
	@echo "  make test-monitor       - Run simulated OpenOCD for monitor script testing"
	@echo "  make test-clean         - Clean test build artifacts"
