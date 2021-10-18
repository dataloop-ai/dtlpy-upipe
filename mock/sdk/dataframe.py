import io
from enum import IntEnum
import json
import numpy as np

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
    ARRAY = 7
    TUPLE = 8
    ND_ARR = 9
    CUSTOM = 100 #all ids above this type are user generated, TBD dynamic



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
        if isinstance(data, list):
            return DType.ARRAY
        if isinstance(data, tuple):
            return DType.TUPLE
        if isinstance(data, np.ndarray):
            return DType.ND_ARR
        if is_jsonable(data):  # always keep last, slower than others
            return DType.JSON

    @staticmethod
    def data_to_byte_arr(data, d_type: DType = None):
        if d_type == DType.JSON:
            data_arr = bytearray(bytes(json.dumps(data), encoding='utf-8'))
        elif d_type == DType.STR:
            data_arr = bytearray(data.encode('utf-8'))
        elif d_type == DType.TUPLE:
            data_arr = bytearray(bytes(json.dumps(data), encoding='utf-8'))
        elif d_type == DType.ARRAY:
            data_arr = bytearray()
            for datum in data:
                datum_type = DataFrame.get_data_type(datum)
                datum_byte_array = DataFrame.data_to_byte_arr(datum, datum_type)
                datum_size = len(datum_byte_array)
                datum_header_array = datum_type.to_bytes(1, "little") + datum_size.to_bytes(4, "little")
                data_arr += datum_header_array + datum_byte_array
        elif d_type == DType.ND_ARR:
            pass
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
            data = json.loads(arr.decode("utf-8"))
        if d_type == DType.TUPLE:
            data = tuple(json.loads(arr.decode("utf-8")))
        if d_type == DType.STR:
            data = arr.decode("utf-8")
        if d_type == DType.ARRAY:
            data = []
            arr_size = len(arr)
            current_datum_index = 0
            while current_datum_index + 5 < arr_size:  # 5 is header size, 1 type, for datum size
                datum_type = arr[current_datum_index]
                current_datum_index += 1
                datum_size = int.from_bytes(arr[current_datum_index:current_datum_index + 4], "little")
                current_datum_index += 4
                datum_bytes=arr[current_datum_index:current_datum_index + datum_size]
                data.append(DataFrame.data_from_byte_arr(datum_bytes,datum_type))
                current_datum_index += datum_size
        return data

    @staticmethod
    def from_byte_arr(arr: bytearray, d_type: DType):
        return DataFrame(DataFrame.data_from_byte_arr(arr, d_type))

    @property
    def data(self):
        return self.data_from_byte_arr(self.byte_arr_data, self.d_type)

    @property
    def size(self):
        return len(self.byte_arr_data)
