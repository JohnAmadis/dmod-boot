#!/bin/bash
# Script to extract symbol addresses from ELF file

ELF_FILE=$1
TARGET=$2
DMOD_LOG_TOTAL_SIZE=$3
DMOD_LOG_MAX_ENTRY_SIZE=$4
OUTPUT_FILE=$5

echo "# dmod-boot Symbol Addresses for ${TARGET}" > "${OUTPUT_FILE}"
echo "# Generated: $(date)" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Extract addresses (use || true to not fail if symbol not found)
arm-none-eabi-nm "${ELF_FILE}" | grep ' dmod_log_ring$' | cut -d' ' -f1 | xargs -I {} echo "DMOD_LOG_RING_ADDR={}" >> "${OUTPUT_FILE}" || true
arm-none-eabi-nm "${ELF_FILE}" | grep _dmod_log_ring_start | cut -d' ' -f1 | xargs -I {} echo "DMOD_LOG_RING_START={}" >> "${OUTPUT_FILE}" || true
arm-none-eabi-nm "${ELF_FILE}" | grep _dmod_log_ring_end | cut -d' ' -f1 | xargs -I {} echo "DMOD_LOG_RING_END={}" >> "${OUTPUT_FILE}" || true

echo "DMOD_LOG_TOTAL_SIZE=${DMOD_LOG_TOTAL_SIZE}" >> "${OUTPUT_FILE}"
echo "DMOD_LOG_MAX_ENTRY_SIZE=${DMOD_LOG_MAX_ENTRY_SIZE}" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
