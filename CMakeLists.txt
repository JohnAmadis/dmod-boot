# =====================================================================
#               DMOD Boot CMakeLists.txt
# =====================================================================
cmake_minimum_required(VERSION 3.10)

# ======================================================================
#               Configuration
# ======================================================================
set(TARGET "STM32F746xG" CACHE STRING "Target microcontroller")

# ======================================================================
#               Early DMOD Configuration (before project())
# ======================================================================
set(DMOD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lib/dmod")
include(configs/dmod-cfg.cmake)
include(configs/mcu/${TARGET}.cmake)

# Include toolchain configuration before project() to set compilers
include(${DMOD_DIR}/configs/arch/${DMBOOT_ARCH}/tools-cfg.cmake)

# ======================================================================
#               DMOD Boot Project Configuration
# ======================================================================
project(dmboot
    VERSION 1.0
    DESCRIPTION "DMOD Bootloader"
    LANGUAGES C CXX)

# ======================================================================
#               Subdirectories
# ======================================================================
add_subdirectory(lib)
add_subdirectory(inc)
add_subdirectory(src)

# ======================================================================
#               dmod-boot application
# ======================================================================
set(MODULE_NAME dmboot)

add_executable(${MODULE_NAME}.elf
    src/main.c
)

target_link_options(${MODULE_NAME}.elf
    PRIVATE 
        -T${CMAKE_CURRENT_SOURCE_DIR}/configs/arch/${DMBOOT_ARCH}/arch.ld
        -T${CMAKE_CURRENT_SOURCE_DIR}/configs/mcu/${DMBOOT_MCU_SERIES}/${DMBOOT_MCU_NAME}.ld
        -Wl,-Map=${MODULE_NAME}.map
)

target_link_libraries(${MODULE_NAME}.elf
    PRIVATE 
        dmod
        dmboot_inc
        dmboot_startup
)