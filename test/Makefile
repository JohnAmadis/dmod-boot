# Makefile for x86 test target
# This allows testing the ring buffer logic without ARM hardware

# Compiler for native x86/x64
CC = gcc
CFLAGS = -Wall -Wextra -O2 -g -I../include
CFLAGS += -DDMOD_LOG_TOTAL_SIZE=2048
CFLAGS += -DDMOD_LOG_MAX_ENTRY_SIZE=256
CFLAGS += -DDMOD_X86_TEST  # Flag to disable section attributes

# Source files
SRCS = main_x86_test.c ../src/dmod_printf.c
OBJS = $(SRCS:.c=.o)

# Output
TARGET = dmod_test_x86

# Default target
.PHONY: all
all: $(TARGET)
	@echo "Build complete. Run with: ./$(TARGET)"

# Link
$(TARGET): $(OBJS)
	@echo "Linking $@"
	@$(CC) $(OBJS) -o $@

# Compile
%.o: %.c
	@echo "Compiling $<"
	@$(CC) $(CFLAGS) -c $< -o $@

# Run tests
.PHONY: test
test: $(TARGET)
	@echo "Running x86 tests..."
	@./$(TARGET)

# Clean
.PHONY: clean
clean:
	@echo "Cleaning x86 test artifacts"
	@rm -f $(OBJS) $(TARGET)

# Help
.PHONY: help
help:
	@echo "dmod-boot x86 Test Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make        - Build x86 test executable"
	@echo "  make test   - Build and run tests"
	@echo "  make clean  - Remove build artifacts"
	@echo "  make help   - Show this help"
