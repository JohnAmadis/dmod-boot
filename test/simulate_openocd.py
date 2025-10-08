#!/usr/bin/env python3
"""
Memory simulator for testing dmod_log_monitor.py

This creates a simulated memory dump that matches the ring buffer format,
allowing us to test the monitor script without needing actual hardware.
"""

import struct
import socket
import threading
import time
import sys


class SimulatedMemory:
    """Simulates the ring buffer in memory"""
    
    def __init__(self, base_addr=0x20000000, total_size=8192, max_entry_size=512):
        self.base_addr = base_addr
        self.total_size = total_size
        self.max_entry_size = max_entry_size
        
        # Control structure: magic(4) + latest_id(4) + flags(4) + head_offset(4) + tail_offset(4)
        self.control_size = 20
        
        # Allocate memory
        self.memory = bytearray(self.control_size + total_size)
        
        # Initialize control structure
        self.set_u32(0, 0x444D4F44)  # magic
        self.set_u32(4, 0)            # latest_id
        self.set_u32(8, 0)            # flags
        self.set_u32(12, 0)           # head_offset
        self.set_u32(16, 0)           # tail_offset
        
        self.next_id = 1
    
    def set_u32(self, offset, value):
        """Set a 32-bit value at offset"""
        self.memory[offset:offset+4] = struct.pack('<I', value)
    
    def set_u16(self, offset, value):
        """Set a 16-bit value at offset"""
        self.memory[offset:offset+2] = struct.pack('<H', value)
    
    def get_u32(self, offset):
        """Get a 32-bit value from offset"""
        return struct.unpack('<I', self.memory[offset:offset+4])[0]
    
    def add_log_entry(self, message):
        """Add a log entry to the buffer"""
        data = message.encode('utf-8')
        length = len(data)
        
        if length > self.max_entry_size:
            length = self.max_entry_size
            data = data[:length]
        
        head = self.get_u32(12)
        tail = self.get_u32(16)
        
        entry_size = 6 + length  # header + data
        
        # Simple eviction: if not enough space, just wrap around
        # (simplified version - real one is more complex)
        if head + entry_size > self.total_size:
            # Wrap around
            head = 0
            tail = 0
        
        # Write entry header
        entry_offset = self.control_size + head
        self.set_u32(entry_offset, self.next_id)  # id
        self.set_u16(entry_offset + 4, length)     # length
        
        # Write data
        for i, byte in enumerate(data):
            self.memory[entry_offset + 6 + i] = byte
        
        # Update control structure
        self.set_u32(4, self.next_id)  # latest_id
        self.set_u32(12, (head + entry_size) % self.total_size)  # head_offset
        
        self.next_id += 1
    
    def read_bytes(self, address, size):
        """Read bytes from simulated memory"""
        offset = address - self.base_addr
        if offset < 0 or offset + size > len(self.memory):
            return None
        return bytes(self.memory[offset:offset+size])


class SimulatedOpenOCD:
    """Simulates OpenOCD telnet server"""
    
    def __init__(self, memory, host='localhost', port=4445):
        self.memory = memory
        self.host = host
        self.port = port
        self.running = False
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the simulated OpenOCD server"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        self.running = True
        
        self.thread = threading.Thread(target=self._serve)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"Simulated OpenOCD listening on {self.host}:{self.port}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server:
            self.server.close()
    
    def _serve(self):
        """Serve client connections"""
        while self.running:
            try:
                self.server.settimeout(1.0)
                client, addr = self.server.accept()
                print(f"Client connected from {addr}")
                self._handle_client(client)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error: {e}")
                break
    
    def _handle_client(self, client):
        """Handle a client connection"""
        try:
            # Send initial prompt
            client.send(b"> ")
            
            while self.running:
                client.settimeout(1.0)
                data = client.recv(1024)
                if not data:
                    break
                
                cmd = data.decode('utf-8').strip()
                response = self._handle_command(cmd)
                
                if response:
                    client.sendall(response.encode('utf-8'))
                client.sendall(b"> ")  # Prompt without newline before it
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Client error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            client.close()
    
    def _handle_command(self, cmd):
        """Handle an OpenOCD command"""
        print(f"Command received: {cmd}")
        if cmd.startswith('mdw '):
            # Parse: mdw 0xADDRESS COUNT
            parts = cmd.split()
            if len(parts) >= 3:
                try:
                    address = int(parts[1], 16)
                    count = int(parts[2])
                    print(f"  Reading {count} words from 0x{address:08x}")
                    
                    # Read memory
                    data = self.memory.read_bytes(address, count * 4)
                    if data:
                        print(f"  Got {len(data)} bytes")
                        # Format response like OpenOCD
                        response = []
                        for i in range(0, len(data), 16):  # Process 4 words at a time
                            addr = address + i
                            response.append(f"0x{addr:08x}:")
                            for j in range(i, min(i + 16, len(data)), 4):
                                word = struct.unpack('<I', data[j:j+4])[0]
                                response.append(f" {word:08x}")
                            response.append('\n')
                        result = ''.join(response)
                        print(f"  Response ({len(result)} chars): {result[:100]}...")
                        return result
                    else:
                        print(f"  No data returned")
                except Exception as e:
                    print(f"  Error: {e}")
                    return f"Error: {e}\r\n"
        
        print(f"  Unknown command")
        return f"Unknown command: {cmd}\r\n"


def main():
    """Main test function"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     Simulated OpenOCD Memory Server for Testing             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # Create simulated memory
    memory = SimulatedMemory(base_addr=0x20000224, total_size=8192, max_entry_size=512)
    
    # Add some test log entries
    print("Adding test log entries...")
    memory.add_log_entry("dmod-boot initialized\n")
    memory.add_log_entry("System starting...\n")
    memory.add_log_entry("Ring buffer debug output enabled\n\n")
    
    for i in range(5):  # Reduced from 10 to 5
        memory.add_log_entry(f"Counter: {i} (0x{i:X})\n")
    
    print(f"Added {memory.next_id - 1} log entries")
    print()
    
    # Start simulated OpenOCD server
    server = SimulatedOpenOCD(memory, port=4445)
    server.start()
    
    print("Ready for testing!")
    print()
    print("To test, run in another terminal:")
    print("  python3 scripts/dmod_log_monitor.py --port 4445 \\")
    print("    --addr-file test/simulated_addresses.txt")
    print()
    print("Press Ctrl+C to stop")
    
    try:
        # Keep adding logs periodically  
        counter = 5  # Start from 5 since we already added 0-4
        while True:
            time.sleep(2)  # Slower rate
            memory.add_log_entry(f"Counter: {counter} (0x{counter:X})\n")
            counter += 1
    except KeyboardInterrupt:
        print("\n\nStopping...")
        server.stop()


if __name__ == '__main__':
    sys.exit(main() or 0)
