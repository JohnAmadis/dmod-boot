# CMakeLists.txt for x86 test target
# This allows testing the ring buffer logic without ARM hardware
cmake_minimum_required(VERSION 3.15)

project(dmod-test-x86 C)

# Compiler for native x86/x64
set(CMAKE_C_COMPILER gcc)

# Compiler flags
set(CMAKE_C_FLAGS "-Wall -Wextra -O2 -g")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DDMOD_LOG_TOTAL_SIZE=2048")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DDMOD_LOG_MAX_ENTRY_SIZE=256")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DDMOD_X86_TEST")  # Flag to disable section attributes

# Include directories
include_directories(../include)

# Source files
set(SOURCES
    main_x86_test.c
    ../src/dmod_printf.c
)

# Create executable
add_executable(dmod_test_x86 ${SOURCES})

# Custom target to run tests
add_custom_target(run-test
    COMMAND ./dmod_test_x86
    DEPENDS dmod_test_x86
    COMMENT "Running x86 tests..."
)

# Print build configuration
message(STATUS "Building x86 test target")
