from enum import IntEnum


def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


class DType(IntEnum):
    U8 = 1
    U16 = 2
    U32 = 3
    U64 = 4


class DataFrame:
    def __init__(self, data, d_type: DType):
        self.d_type = d_type
        self.byte_arr_data = self.data_to_byte_arr(data, self.size)

    @staticmethod
    def data_to_byte_arr(data, size):
        return data.to_bytes(size, "little")

    @staticmethod
    def data_from_byte_arr(arr: bytearray, d_type: DType):
        data = None
        if d_type == DType.U8:
            data = int.from_bytes(arr, "little")
        if d_type == DType.U16:
            data = int.from_bytes(arr, "little")
        if d_type == DType.U32:
            data = int.from_bytes(arr, "little")
        if d_type == DType.U64:
            data = int.from_bytes(arr, "little")
        return data

    @staticmethod
    def from_byte_arr(arr: bytearray, d_type: DType):
        return DataFrame(DataFrame.data_from_byte_arr(arr, d_type), d_type)

    @property
    def data(self):
        return self.data_from_byte_arr(self.byte_arr_data, self.d_type)

    @property
    def size(self):
        if self.d_type == DType.U8:
            return 1
        if self.d_type == DType.U16:
            return 2
        if self.d_type == DType.U32:
            return 4
        if self.d_type == DType.U64:
            return 8


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
