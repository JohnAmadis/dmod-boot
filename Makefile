# Makefile for dmod-boot
# Minimal embedded project for STM32 microcontrollers

# Target selection (STM32F746 or STM32F407)
TARGET ?= STM32F746

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size
OBJDUMP = arm-none-eabi-objdump

# Directories
SRC_DIR = src
INC_DIR = include
LINKER_DIR = linker
EXAMPLES_DIR = examples
BUILD_DIR = build

# Target-specific settings
ifeq ($(TARGET),STM32F746)
    LINKER_SCRIPT = $(LINKER_DIR)/STM32F746xG.ld
    STARTUP_SRC = $(SRC_DIR)/startup_stm32f746.c
    CPU = cortex-m7
    FPU = -mfpu=fpv5-sp-d16
    FLOAT_ABI = -mfloat-abi=hard
else ifeq ($(TARGET),STM32F407)
    LINKER_SCRIPT = $(LINKER_DIR)/STM32F407xG.ld
    STARTUP_SRC = $(SRC_DIR)/startup_stm32f407.c
    CPU = cortex-m4
    FPU = -mfpu=fpv4-sp-d16
    FLOAT_ABI = -mfloat-abi=hard
else
    $(error Invalid TARGET. Use STM32F746 or STM32F407)
endif

# Compiler flags
CFLAGS = -mcpu=$(CPU) -mthumb $(FPU) $(FLOAT_ABI)
CFLAGS += -Wall -Wextra -Werror
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -O2 -g
CFLAGS += -I$(INC_DIR)
CFLAGS += -DSTM32 -D$(TARGET)

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

# Default target
.PHONY: all
all: $(BIN) $(HEX)
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

# Help
.PHONY: help
help:
	@echo "dmod-boot Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make [TARGET=<target>]  - Build for specified target (default: STM32F746)"
	@echo "  make stm32f746          - Build for STM32F746"
	@echo "  make stm32f407          - Build for STM32F407"
	@echo "  make all-targets        - Build for all targets"
	@echo "  make clean              - Remove build artifacts"
	@echo "  make disasm             - Generate disassembly"
	@echo "  make help               - Show this help message"
	@echo ""
	@echo "Targets:"
	@echo "  STM32F746 - STM32F746 (Cortex-M7, 1MB Flash, 320KB RAM)"
	@echo "  STM32F407 - STM32F407 (Cortex-M4, 1MB Flash, 128KB RAM + 64KB CCM)"
