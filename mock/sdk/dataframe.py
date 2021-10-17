import io
from enum import IntEnum
import json


def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


class DType(IntEnum):
    U8 = 1
    U16 = 2
    U32 = 3
    U64 = 4
    STR = 5
    JSON = 6


class DataFrame:
    def __init__(self, data, d_type: DType = None):
        if not d_type:
            self.d_type = DataFrame.get_data_type(data)
        else:
            self.d_type = d_type
        self.byte_arr_data = self.data_to_byte_arr(data, self.d_type)

    @staticmethod
    def get_data_type(data):
        if isinstance(data, int):
            return DType.U32
        if isinstance(data, str):
            return DType.STR
        if is_jsonable(data):  # always keep last, slower than others
            return DType.JSON

    @staticmethod
    def data_to_byte_arr(data, d_type: DType = None):
        if d_type == DType.JSON:
            data_arr = bytearray(bytes(json.dumps(data), encoding='utf-8'))
        elif d_type == DType.STR:
            data_arr = bytearray(data.encode('utf-8'))
        else:
            data_arr = data.to_bytes(DataFrame.data_type_size(d_type), "little")
        return data_arr

    @staticmethod
    def data_type_size(d_type: DType):
        if d_type == DType.U8:
            return 1
        if d_type == DType.U16:
            return 2
        if d_type == DType.U32:
            return 4
        if d_type == DType.U64:
            return 8
        raise ValueError("Data type has no fixed size")

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
        if d_type == DType.JSON:
            data = json.load(io.BytesIO(arr))
        if d_type == DType.STR:
            data = arr.decode("utf-8")
        return data

    @staticmethod
    def from_byte_arr(arr: bytearray, d_type: DType):
        return DataFrame(DataFrame.data_from_byte_arr(arr, d_type))

    @property
    def data(self):
        return self.data_from_byte_arr(self.byte_arr_data, self.d_type)

    @property
    def size(self):
        if self.d_type == DType.JSON:
            return len(self.byte_arr_data)
        if self.d_type == DType.STR:
            return len(self.byte_arr_data)
        return self.data_type_size(self.d_type)
