# ======================================================================
#               Configuration
# ======================================================================
set(DMBOOT_MCU_NAME "stm32f746" CACHE STRING "Name of the target microcontroller")
set(DMBOOT_ARCH "armv7" CACHE STRING "Architecture of the target microcontroller")
set(DMBOOT_MCU_FAMILY "cortex-m7" CACHE STRING "Microcontroller family")

# ======================================================================
#               DMOD Configuration
# ======================================================================
# Name of the target cpu (if empty, the target is generic)
set(DMOD_CPU_NAME   ${DMBOOT_MCU_NAME} CACHE STRING "Name of the target cpu, if empty, the target is generic")



