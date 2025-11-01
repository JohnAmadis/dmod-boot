# =====================================================================
#               DMOD Boot CMakeLists.txt
# =====================================================================
cmake_minimum_required(VERSION 3.10)

# ======================================================================
#               DMOD Boot Project Configuration
# ======================================================================
project(dmboot
    VERSION 1.0
    DESCRIPTION "DMOD Bootloader"
    LANGUAGES C CXX)

# ======================================================================
#               Configuration
# ======================================================================
set(TARGET "STM32F746xG" CACHE STRING "Target microcontroller")

# ======================================================================
#               DMOD Configuration
# ======================================================================
set(DMOD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lib/dmod")
include(configs/dmod-cfg.cmake)
include(configs/mcu/${TARGET}.cmake)

# ======================================================================
#               Subdirectories
# ======================================================================
add_subdirectory(lib)
add_subdirectory(inc)
add_subdirectory(src)