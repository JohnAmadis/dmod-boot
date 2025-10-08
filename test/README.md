# Tests

This directory contains tests for the dmod-boot project.

## test_buffer_logic.py

A Python simulation test that validates the ring buffer logic:

- Variable-length entry allocation
- Buffer wraparound and oldest entry eviction
- Entry header parsing
- Memory efficiency calculations

### Running the test

```bash
python3 test/test_buffer_logic.py
```

All tests should pass with output showing:
- Basic write operations
- Buffer wraparound behavior
- Variable-length entry handling
- Memory efficiency comparison (new vs old design)
- Entry ID incrementing
- Large entry truncation
- Oldest entry eviction

This test ensures the C implementation logic is correct without requiring the ARM toolchain.
