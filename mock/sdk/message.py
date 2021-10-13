def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


class Message:
    header_size = 10
    footer_size = 10

    def __init__(self, data):
        self.data = data
        self.data_size = len(self.data)

    def write_to_buffer(self, buffer, address):
        buffer[address] = 1
        size_bytes = self.data_size.to_bytes(4, 'big')
        buffer[address + 1:address + 5] = size_bytes
        data_start = address + self.header_size
        data_end = data_start + self.data_size
        buffer[data_start:data_end] = self.data
        buffer[address] = 2
        return self.size

    @staticmethod
    def from_buffer(buffer, address):
        # size = int.from_bytes(buffer[1], 'big')
        m = Message(buffer[address + Message.header_size:Message.header_size])
        return m

    @property
    def size(self):
        return self.header_size + len(self.data) + self.footer_size


class MessageMemory:
    def __init__(self, data):
        self.data = data


class Block:
    ...


class MemoryBlock:
    def __init__(self, block):
        self.block = block

    def read_u8(self, address):
        return self.block.buf[address]

    def write_u8(self, address, value):
        self.block[address] = value

    def write_bytes(self, address, byte_arr):
        self.block.buf[address:address + len(byte_arr)] = byte_arr
