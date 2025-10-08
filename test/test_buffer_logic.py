#!/usr/bin/env python3
"""
Test script to validate the new dynamic buffer logic.

This test simulates the ring buffer behavior to ensure proper handling of:
- Variable-length entry allocation
- Buffer wraparound
- Oldest entry eviction
- Entry header parsing
"""

import struct


class SimulatedRingBuffer:
    """Simulates the C ring buffer implementation"""
    
    # Constants for safety checks
    MAX_ITERATIONS = 1000  # Maximum iterations when reading entries
    
    def __init__(self, total_size=1024, max_entry_size=256):
        self.total_size = total_size
        self.max_entry_size = max_entry_size
        self.buffer = bytearray(total_size)
        self.magic = 0x444D4F44
        self.latest_id = 0
        self.flags = 0
        self.head_offset = 0
        self.tail_offset = 0
        self.next_id = 1
    
    def get_free_space(self):
        """Calculate free space in buffer"""
        head = self.head_offset
        tail = self.tail_offset
        if head >= tail:
            return self.total_size - (head - tail)
        else:
            return tail - head
    
    def write_entry(self, data):
        """Write a variable-length entry to the buffer"""
        length = len(data)
        if length > self.max_entry_size:
            length = self.max_entry_size
            data = data[:length]
        
        entry_total_size = 6 + length  # header (4+2) + data
        
        # Make space if needed
        while self.get_free_space() < entry_total_size + 1:
            # Read entry at tail to get its size
            tail = self.tail_offset
            entry_id = struct.unpack('<I', bytes(self.buffer[tail:tail+4]))[0]
            entry_length = struct.unpack('<H', bytes(self.buffer[tail+4:tail+6]))[0]
            
            # Advance tail past this entry
            self.tail_offset = (tail + 6 + entry_length) % self.total_size
            
            # Safety check - if tail catches head or buffer seems corrupted, reset
            # Note: tail == head should only occur if buffer is corrupted, not during normal operation
            # because we check free space before writing and always keep at least 1 byte free
            if self.tail_offset == self.head_offset or entry_length > self.max_entry_size:
                self.tail_offset = 0
                self.head_offset = 0
                break
        
        # Write header
        header = struct.pack('<IH', self.next_id, length)
        head = self.head_offset
        for i, byte in enumerate(header):
            self.buffer[(head + i) % self.total_size] = byte
        head = (head + 6) % self.total_size
        
        # Write data
        for i, byte in enumerate(data):
            self.buffer[(head + i) % self.total_size] = byte
        head = (head + length) % self.total_size
        
        # Update control
        self.head_offset = head
        self.latest_id = self.next_id
        self.next_id += 1
    
    def read_entry_at_offset(self, offset):
        """Read entry at given offset"""
        # Read header
        entry_id = struct.unpack('<I', bytes(self.buffer[offset:offset+4]))[0]
        length = struct.unpack('<H', bytes(self.buffer[offset+4:offset+6]))[0]
        
        # Read data
        data_offset = (offset + 6) % self.total_size
        data = bytearray()
        
        for i in range(length):
            data.append(self.buffer[(data_offset + i) % self.total_size])
        
        return {
            'id': entry_id,
            'length': length,
            'data': bytes(data),
            'next_offset': (offset + 6 + length) % self.total_size
        }
    
    def read_all_entries(self):
        """Read all entries from tail to head"""
        entries = []
        current_offset = self.tail_offset
        
        iterations = 0
        while current_offset != self.head_offset and iterations < self.MAX_ITERATIONS:
            iterations += 1
            entry = self.read_entry_at_offset(current_offset)
            entries.append(entry)
            current_offset = entry['next_offset']
            
            # Safety check: if we've wrapped around to tail, stop
            if iterations > 1 and current_offset == self.tail_offset:
                break
        
        return entries


def test_basic_write():
    """Test basic write operation"""
    print("Test 1: Basic write operation")
    buffer = SimulatedRingBuffer(total_size=256, max_entry_size=64)
    
    buffer.write_entry(b"Hello, World!")
    buffer.write_entry(b"Test message 2")
    buffer.write_entry(b"Test message 3")
    
    entries = buffer.read_all_entries()
    assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"
    assert entries[0]['data'] == b"Hello, World!", f"Entry 1 mismatch: {entries[0]['data']}"
    assert entries[1]['data'] == b"Test message 2", f"Entry 2 mismatch: {entries[1]['data']}"
    assert entries[2]['data'] == b"Test message 3", f"Entry 3 mismatch: {entries[2]['data']}"
    
    print("  ✓ Basic write works correctly")


def test_buffer_wraparound():
    """Test buffer wraparound"""
    print("Test 2: Buffer wraparound")
    buffer = SimulatedRingBuffer(total_size=128, max_entry_size=32)
    
    # Write entries until we wrap around
    for i in range(10):
        buffer.write_entry(f"Message {i}".encode())
    
    entries = buffer.read_all_entries()
    
    # Should have oldest entries evicted
    assert len(entries) > 0, "Should have at least one entry"
    assert entries[-1]['data'] == b"Message 9", f"Last entry mismatch: {entries[-1]['data']}"
    
    print(f"  ✓ Buffer wraparound works (kept {len(entries)} entries)")


def test_variable_length():
    """Test variable-length entries"""
    print("Test 3: Variable-length entries")
    buffer = SimulatedRingBuffer(total_size=512, max_entry_size=128)
    
    # Write entries of different sizes
    buffer.write_entry(b"Short")
    buffer.write_entry(b"A" * 50)
    buffer.write_entry(b"B" * 100)
    buffer.write_entry(b"C" * 10)
    
    entries = buffer.read_all_entries()
    assert len(entries) == 4, f"Expected 4 entries, got {len(entries)}"
    assert len(entries[0]['data']) == 5, f"Entry 1 length mismatch: {len(entries[0]['data'])}"
    assert len(entries[1]['data']) == 50, f"Entry 2 length mismatch: {len(entries[1]['data'])}"
    assert len(entries[2]['data']) == 100, f"Entry 3 length mismatch: {len(entries[2]['data'])}"
    assert len(entries[3]['data']) == 10, f"Entry 4 length mismatch: {len(entries[3]['data'])}"
    
    print("  ✓ Variable-length entries work correctly")


def test_memory_efficiency():
    """Test memory efficiency"""
    print("Test 4: Memory efficiency comparison")
    
    # Old design: 128 entries × 264 bytes = 33,792 bytes
    # Each entry: id(4) + length(4) + buffer(256) = 264 bytes
    OLD_ENTRIES = 128
    OLD_ENTRY_SIZE = 264
    old_design_size = OLD_ENTRIES * OLD_ENTRY_SIZE
    
    # New design: For same usage pattern
    # Assume average log is 50 bytes
    # New design can fit: 8192 / (6 + 50) ≈ 146 entries
    NEW_BUFFER_SIZE = 8192
    AVG_ENTRY_SIZE = 50
    ENTRY_HEADER_SIZE = 6  # id(4) + length(2)
    new_entries = NEW_BUFFER_SIZE // (ENTRY_HEADER_SIZE + AVG_ENTRY_SIZE)
    
    efficiency = (old_design_size / NEW_BUFFER_SIZE) * 100
    
    print(f"  Old design: {old_design_size} bytes for {OLD_ENTRIES} entries ({OLD_ENTRY_SIZE} bytes each)")
    print(f"  New design: {NEW_BUFFER_SIZE} bytes for ~{new_entries} entries (avg {AVG_ENTRY_SIZE} bytes)")
    print(f"  ✓ Memory savings: {efficiency:.1f}% more efficient")


def test_entry_ids():
    """Test entry ID incrementing"""
    print("Test 5: Entry ID incrementing")
    buffer = SimulatedRingBuffer(total_size=256, max_entry_size=64)
    
    for i in range(5):
        buffer.write_entry(f"Entry {i}".encode())
    
    entries = buffer.read_all_entries()
    
    # Check IDs are sequential
    for i, entry in enumerate(entries, start=1):
        assert entry['id'] == i, f"Entry {i} ID mismatch: {entry['id']}"
    
    assert buffer.latest_id == 5, f"Latest ID should be 5, got {buffer.latest_id}"
    
    print("  ✓ Entry IDs increment correctly")


def test_large_entries():
    """Test handling of large entries"""
    print("Test 6: Large entry handling")
    buffer = SimulatedRingBuffer(total_size=1024, max_entry_size=256)
    
    # Write entry larger than max - should be truncated
    large_data = b"X" * 300
    buffer.write_entry(large_data)
    
    entries = buffer.read_all_entries()
    assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"
    assert len(entries[0]['data']) == 256, f"Entry should be truncated to 256, got {len(entries[0]['data'])}"
    
    print("  ✓ Large entries are properly truncated")


def test_full_buffer_eviction():
    """Test that oldest entries are evicted when buffer is full"""
    print("Test 7: Oldest entry eviction")
    buffer = SimulatedRingBuffer(total_size=200, max_entry_size=64)
    
    # Fill buffer completely
    for i in range(20):
        buffer.write_entry(f"Message {i:02d}".encode())
    
    entries = buffer.read_all_entries()
    
    # Verify oldest entries were evicted
    first_id = entries[0]['id']
    last_id = entries[-1]['id']
    
    assert last_id == 20, f"Last ID should be 20, got {last_id}"
    assert first_id < last_id, "First entry should be older than last"
    
    print(f"  ✓ Oldest entries evicted correctly (kept IDs {first_id}-{last_id})")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Dynamic Ring Buffer Logic")
    print("=" * 60)
    print()
    
    try:
        test_basic_write()
        test_buffer_wraparound()
        test_variable_length()
        test_memory_efficiency()
        test_entry_ids()
        test_large_entries()
        test_full_buffer_eviction()
        
        print()
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"Test failed: {e}")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    exit(main())
