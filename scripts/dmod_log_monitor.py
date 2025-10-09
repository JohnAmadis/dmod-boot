#!/usr/bin/env python3
"""
dmod_log_monitor.py - Monitor dmod-boot log ring buffer via OpenOCD

This script connects to OpenOCD and reads the memory ring buffer to display
log messages from the target microcontroller.

Usage:
    python3 scripts/dmod_log_monitor.py [options]

Options:
    --target TARGET     Target name (STM32F746 or STM32F407), default: STM32F746
    --host HOST         OpenOCD host, default: localhost
    --port PORT         OpenOCD telnet port, default: 4444
    --interval SECONDS  Polling interval in seconds, default: 0.1
    --addr-file FILE    Address file path, default: build/TARGET_dmod_addresses.txt
    --debug             Enable debug logging
"""

import socket
import time
import sys
import argparse
import struct
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class OpenOCDClient:
    def __init__(self, host='localhost', port=4444):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        """Connect to OpenOCD telnet server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Telnet server sends initial prompt - read it
            self.sock.recv(4096)  # Always consume initial prompt
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OpenOCD at {self.host}:{self.port}: {e}")
            return False
    
    def send_command(self, cmd):
        """Send command to OpenOCD and get response"""
        if not self.sock:
            return None
        
        try:
            # Send command
            self.sock.sendall((cmd + '\n').encode())
            
            # Read response until we get the prompt
            response = b''
            prompt = b'> '
            
            while True:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                
                # Check if we got the prompt (may be at the end)
                if prompt in response:
                    # Remove the prompt and everything after it
                    prompt_pos = response.rfind(prompt)
                    response = response[:prompt_pos]
                    break
                
                # Safety check
                if len(response) > 32768:
                    break
            
            return response.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    def read_memory(self, address, size):
        """Read memory from target"""
        # mdw reads in words (4 bytes), so we need to round up
        words_needed = (size + 3) // 4  # Round up to next word boundary
        cmd = f"mdw 0x{address:08x} {words_needed}"
        response = self.send_command(cmd)
        if not response:
            logger.debug(f"No response from OpenOCD for command: {cmd}")
            return None
        
        # Parse response - format: "0xADDRESS: VALUE VALUE ..."
        # Values are in hex but without 0x prefix
        words = []
        
        # Clean up the response - remove null bytes and normalize line endings
        cleaned_response = response.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
        lines = cleaned_response.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lines containing memory data with format "0xADDRESS: VALUE VALUE ..."
            if ':' in line and '0x' in line and 'mdw' not in line.lower():
                try:
                    # Split by colon and get the values part
                    addr_part, values_part = line.split(':', 1)
                    values = values_part.strip().split()
                    
                    for value in values:
                        value = value.strip()
                        # Values are hex strings without 0x prefix, should be 8 chars
                        if value and len(value) == 8:
                            try:
                                words.append(int(value, 16))
                            except ValueError:
                                continue
                except (IndexError, ValueError):
                    continue
        
        # Convert words to bytes (little endian)
        data = b''
        for word in words:
            data += struct.pack('<I', word)
        
        return data[:size] if len(data) >= size else None

    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()
            self.sock = None


class DmodLogMonitor:
    def __init__(self, client, ring_addr, ring_control_size, total_size, max_entry_size, expected_magic, max_startup_entries=100):
        self.client = client
        self.ring_addr = ring_addr
        self.ring_control_size = ring_control_size
        self.total_size = total_size
        self.max_entry_size = max_entry_size
        self.expected_magic = expected_magic
        self.max_startup_entries = max_startup_entries
        self.last_id = 0
        
    def read_ring_control(self):
        """Read ring buffer control structure"""
        data = self.client.read_memory(self.ring_addr, self.ring_control_size)
        if not data or len(data) < self.ring_control_size:
            return None
            
        magic, latest_id, flags, head_offset, tail_offset = struct.unpack('<IIIII', data)
        
        # Check magic number
        if magic != self.expected_magic:
            # Try one more time
            time.sleep(0.001)
            data = self.client.read_memory(self.ring_addr, self.ring_control_size)
            if not data or len(data) < self.ring_control_size:
                return None
            magic, latest_id, flags, head_offset, tail_offset = struct.unpack('<IIIII', data)
            
            if magic != self.expected_magic:
                return None
        
        # Validate the values
        if latest_id < 0xFFFFFF00 and head_offset < self.total_size and tail_offset < self.total_size:
            return {
                'latest_id': latest_id,
                'flags': flags,
                'head_offset': head_offset,
                'tail_offset': tail_offset
            }
        
        return None
    
    def read_entry_at_offset(self, offset):
        """Read a single log entry at given offset in the buffer"""
        # Read entry header (6 bytes: id(4) + length(2))
        header_size = 6
        buffer_start = self.ring_addr + self.ring_control_size
        entry_addr = buffer_start + offset
        
        # Read header
        header_data = self.client.read_memory(entry_addr, header_size)
        
        if not header_data or len(header_data) < header_size:
            return None
        
        entry_id, length = struct.unpack('<IH', header_data)
        logger.debug(f"Reading entry at offset {offset}: id={entry_id}, length={length}")
        
        if length > self.max_entry_size:
            logger.debug(f"Entry at offset {offset}: length {length} too big (max {self.max_entry_size})")
            return None
        
        # Read message data
        # Handle wraparound if needed
        data_offset = (offset + header_size) % self.total_size
        data_addr = buffer_start + data_offset
        
        # Check if data wraps around
        if data_offset + length <= self.total_size:
            # No wraparound
            message_data = self.client.read_memory(data_addr, length)
        else:
            # Wraparound: read in two parts
            first_part_len = self.total_size - data_offset
            second_part_len = length - first_part_len
            
            first_part = self.client.read_memory(data_addr, first_part_len)
            second_part = self.client.read_memory(buffer_start, second_part_len)
            
            if not first_part or not second_part:
                return None
            message_data = first_part + second_part
        
        if not message_data or len(message_data) < length:
            return None
        
        return {
            'id': entry_id,
            'length': length,
            'message': message_data.decode('utf-8', errors='replace'),
            'next_offset': (offset + header_size + length) % self.total_size
        }
    
    def read_entries_from_tail(self, tail_offset, head_offset, start_id):
        """Read all entries from tail to head"""
        entries = []
        current_offset = tail_offset
        
        # Safety counter to prevent infinite loops
        max_iterations = 1000
        iterations = 0
        
        # Progress indicator for large reads
        last_progress_time = 0
        import time
        
        while current_offset != head_offset and iterations < max_iterations:
            iterations += 1
            
            # Show progress for slow operations (every 50 entries or 2 seconds)
            if iterations % 50 == 0 or (time.time() - last_progress_time) > 2:
                logger.info(f"Reading entry {iterations}...")
                last_progress_time = time.time()
            
            entry = self.read_entry_at_offset(current_offset)
            
            if not entry:
                logger.debug(f"Failed to read entry at offset {current_offset}")
                break
            
            if entry['id'] >= start_id:
                entries.append(entry)
            
            current_offset = entry['next_offset']
            
            # Safety check: if we've wrapped around past head, stop
            if iterations > 1 and current_offset == tail_offset:
                break
        
        return entries

    def monitor(self, interval=0.1):
        """Monitor log ring buffer continuously"""
        print(f"Monitoring dmod-boot log ring buffer at 0x{self.ring_addr:08x}")
        print(f"Buffer size: {self.total_size} bytes, max entry: {self.max_entry_size} bytes")
        print("Press Ctrl+C to stop\n")
        
        # Initialize - start from current position to avoid reading old entries
        control = self.read_ring_control()
        if control is None:
            print("Failed to read ring buffer control")
            return
        
        self.last_id = control['latest_id']
        print(f"Starting from log ID: {self.last_id}, head: {control['head_offset']}, tail: {control['tail_offset']}")
        
        # Read and display all existing entries on startup
        if self.last_id > 0 and control['tail_offset'] != control['head_offset']:
            # Limit how many old entries we display on startup to avoid long delays
            # Only show the most recent entries
            max_startup_entries = self.max_startup_entries
            start_id = max(1, self.last_id - max_startup_entries + 1)
            
            if start_id > 1:
                print(f"Reading existing log entries (showing last {max_startup_entries})...\n")
            else:
                print("Reading existing log entries...\n")
            
            logger.debug(f"Reading entries from tail, filtering for id >= {start_id}")
            entries = self.read_entries_from_tail(control['tail_offset'], control['head_offset'], start_id)
            
            logger.debug(f"Found {len(entries)} entries to display")
            
            for entry in entries:
                print(entry['message'], end='')
                # Flush output to ensure it's visible immediately
                import sys
                sys.stdout.flush()
            
            if entries:
                print()  # Extra newline after existing entries
        
        try:
            while True:
                control = self.read_ring_control()
                
                if control is None:
                    time.sleep(interval)
                    continue
                
                latest_id = control['latest_id']
                
                # Debug: print current state
                if latest_id != self.last_id:
                    logger.debug(f"latest_id changed from {self.last_id} to {latest_id}")
                
                # Check if there are new entries
                if latest_id > self.last_id:
                    logger.debug(f"Found new entries, reading from tail {control['tail_offset']} to head {control['head_offset']}")
                    
                    # Read all entries from tail to head, filtering by ID
                    start_id = self.last_id + 1
                    entries = self.read_entries_from_tail(control['tail_offset'], control['head_offset'], start_id)
                    
                    # Print entries in order
                    for entry in entries:
                        print(entry['message'], end='')
                    
                    self.last_id = latest_id
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")


def load_addresses(addr_file):
    """Load addresses from file"""
    if not Path(addr_file).exists():
        return None
    
    addresses = {}
    with open(addr_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                addresses[key] = value
    
    return addresses


def main():
    parser = argparse.ArgumentParser(
        description='Monitor dmod-boot log ring buffer via OpenOCD'
    )
    parser.add_argument('--target', default='STM32F746',
                        choices=['STM32F746', 'STM32F407'],
                        help='Target name (default: STM32F746)')
    parser.add_argument('--host', default='localhost',
                        help='OpenOCD host (default: localhost)')
    parser.add_argument('--port', type=int, default=4444,
                        help='OpenOCD telnet port (default: 4444)')
    parser.add_argument('--interval', type=float, default=0.1,
                        help='Polling interval in seconds (default: 0.1)')
    parser.add_argument('--addr-file', default=None,
                        help='Address file path (default: build/TARGET_dmod_addresses.txt)')
    parser.add_argument('--max-startup-entries', type=int, default=100,
                        help='Maximum number of old entries to show on startup (default: 100)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.ERROR,
            format='%(levelname)s: %(message)s'
        )
    
    # Determine address file path
    if args.addr_file:
        addr_file = args.addr_file
    else:
        addr_file = f'build/{args.target}_dmod_addresses.txt'
    
    # Load addresses
    print(f"Loading addresses from {addr_file}")
    addresses = load_addresses(addr_file)
    
    if not addresses:
        print(f"Error: Could not load addresses from {addr_file}")
        print("Please build the firmware first with 'make'")
        return 1
    
    # Parse addresses
    try:
        ring_addr = int(addresses['DMOD_LOG_RING_ADDR'], 16)
        total_size = int(addresses['DMOD_LOG_TOTAL_SIZE'])
        max_entry_size = int(addresses['DMOD_LOG_MAX_ENTRY_SIZE'])
    except (KeyError, ValueError) as e:
        print(f"Error parsing addresses: {e}")
        return 1
    
    print(f"Ring buffer address: 0x{ring_addr:08x}")
    print(f"Total buffer size: {total_size} bytes")
    print(f"Max entry size: {max_entry_size} bytes")
    print()
    
    # Connect to OpenOCD
    client = OpenOCDClient(args.host, args.port)
    print(f"Connecting to OpenOCD at {args.host}:{args.port}...")
    
    if not client.connect():
        print("Make sure OpenOCD is running with TCL server enabled")
        print("Example: openocd -f interface/stlink.cfg -f target/stm32f7x.cfg")
        return 1
    
    print("Connected to OpenOCD\n")
    
    # Calculate sizes and create monitor
    ring_control_size = 20  # magic (4) + latest_id (4) + flags (4) + head_offset (4) + tail_offset (4)
    expected_magic = 0x444D4F44  # 'DMOD'
    
    monitor = DmodLogMonitor(
        client, ring_addr, ring_control_size, total_size, 
        max_entry_size, expected_magic, args.max_startup_entries
    )
    
    try:
        monitor.monitor(args.interval)
    finally:
        client.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
