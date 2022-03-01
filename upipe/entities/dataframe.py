import json
import pickle
from enum import IntEnum
from typing import List, Type, Union, Dict
import uuid
import numpy as np
from pydantic import BaseModel

__all__ = ['DType', 'DataFrame', 'DataField']


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
    CUSTOM_TYPE_START = 100  # all ids above this type are user generated, TBD dynamic
    CUSTOM_TYPE_END = 200  # all ids above this type are user generated, TBD dynamic


class DataFrameBaseType(BaseModel):

    @staticmethod
    def from_byte_array(arr: bytearray):
        data = pickle.loads(arr)
        return data

    @staticmethod
    def to_byte_array(data):
        data_bytes = pickle.dumps(data)
        return data_bytes

    class Config:
        arbitrary_types_allowed = True
        validate_all = False


class TypeHandler:
    def __init__(self, type_id: int, model_definition: Type[DataFrameBaseType]):
        if type_id > MAX_TYPE_ID:
            raise IndexError(f"Custom type id must be between {DType.CUSTOM_TYPE_START} to {DType.CUSTOM_TYPE_END}")
        self.model = model_definition.construct(_fields_set=None, **{})
        self.type_id = type_id

    def from_byte_array(self, arr: bytearray):
        return self.model.from_byte_array(arr)

    def to_byte_array(self, data):
        return self.model.to_byte_array(data)

    @property
    def members(self):
        return self.model.schema()['properties'].keys()


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


def int_size(d_type: DType):
    if d_type == DType.U8:
        return 1
    if d_type == DType.U16:
        return 2
    if d_type == DType.U32:
        return 4
    if d_type == DType.U64:
        return 8
    raise ValueError("Data type has no fixed size")


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
            datum_type = get_data_type(datum)
            datum_byte_array = data_to_byte_arr(datum, datum_type)
            datum_size = len(datum_byte_array)
            datum_header_array = datum_type.to_bytes(1, "little") + datum_size.to_bytes(4, "little")
            data_arr += datum_header_array + datum_byte_array
    elif type_handlers[d_type]:
        data_arr = type_handlers[d_type].to_byte_array(data)
    else:
        data_arr = data.to_bytes(int_size(d_type), "little")
    return data_arr


def data_from_byte_arr(arr: bytearray, d_type: DType = None):
    data = None
    if d_type == DType.U8:
        data = int.from_bytes(arr, "little")
    elif d_type == DType.U16:
        data = int.from_bytes(arr, "little")
    elif d_type == DType.U32:
        data = int.from_bytes(arr, "little")
    elif d_type == DType.U64:
        data = int.from_bytes(arr, "little")
    elif d_type == DType.JSON:
        data = json.loads(arr.decode("utf-8"))
    elif d_type == DType.TUPLE:
        data = tuple(json.loads(arr.decode("utf-8")))
    elif d_type == DType.STR:
        data = arr.decode("utf-8")
    elif d_type == DType.ARRAY:
        data = []
        arr_size = len(arr)
        current_datum_index = 0
        while current_datum_index + 5 < arr_size:  # 5 is header size, 1 type, for datum size
            datum_type = DType(arr[current_datum_index])
            current_datum_index += 1
            datum_size = int.from_bytes(arr[current_datum_index:current_datum_index + 4], "little")
            current_datum_index += 4
            datum_bytes = arr[current_datum_index:current_datum_index + datum_size]
            data.append(data_from_byte_arr(datum_bytes, datum_type))
            current_datum_index += datum_size
    elif type_handlers[d_type]:
        data = type_handlers[d_type].from_byte_array(arr)
    else:
        raise LookupError(f"No matching data type was registered:{d_type} ")
    return data


NEXT_CUSTOM_TYPE_ID = DType.CUSTOM_TYPE_START
MAX_TYPE_ID = DType.CUSTOM_TYPE_END
type_handlers: List[Union[TypeHandler, None]] = [None for _ in range(MAX_TYPE_ID)]


def _allocate_new_type():
    global NEXT_CUSTOM_TYPE_ID, MAX_TYPE_ID
    new_type = NEXT_CUSTOM_TYPE_ID
    NEXT_CUSTOM_TYPE_ID += 1
    if new_type > MAX_TYPE_ID:
        raise IndexError("Max type definition list reached")
    return new_type


def register_data_type(d_model: Type[DataFrameBaseType], d_type=None):
    if d_type and type_handlers[d_type]:
        raise FileExistsError(f"type id {d_type} already registered")
    if not d_type:
        d_type = _allocate_new_type()
    handler = TypeHandler(d_type, d_model)
    type_handlers[d_type] = handler


def _register_builtin_types():
    register_data_type(DataFrameBaseType, DType.ND_ARR)


_built_in_register_done = False

if not _built_in_register_done:
    _register_builtin_types()
    _built_in_register_done = True


class DataField:

    def __init__(self, key: str, value, d_type: DType = None):
        if d_type is None:
            d_type = get_data_type(value)
        self.key = key
        self.value = value
        self.d_type = d_type

    @property
    def byte_arr(self):
        arr = bytearray(2)
        arr[0] = self.d_type
        key_bytes = bytearray(self.key.encode('utf-8'))
        arr[1] = len(key_bytes)
        arr.extend(key_bytes)
        value_bytes = data_to_byte_arr(self.value, self.d_type)
        value_size = len(value_bytes)
        arr.extend(value_size.to_bytes(4, "little"))
        arr.extend(value_bytes)
        return arr

    @staticmethod
    def from_byte_arr(arr: bytearray):
        d_type = DType(arr[0])
        key_size = arr[1]
        key_start = 2
        key_bytes = arr[key_start:key_start + key_size]
        key = key_bytes.decode("utf-8")
        key_end = key_start + key_size
        value_size = int.from_bytes(arr[key_end:key_end + 4], "little")
        value_start = key_end + 4
        value_bytes = arr[value_start:value_start + value_size]
        field = DataField(key, data_from_byte_arr(value_bytes, d_type), d_type)
        return field

    @property
    def size(self):
        return len(self.byte_arr)


class DataFrame:
    """
    d  - default data field
    pip - frame pipline id
    last - marks no more frames are expected
    """
    reserved_keys = ['d', 'pid', 'last']
    MAX_FIELD_LIMIT = 255

    def __init__(self, data=None):
        self.fields: Dict[str, DataField] = dict()
        if data is not None:
            self.fields['d'] = DataField('d', data)  # "d" is special key, the default key

    def add_field(self, key, value):
        f = DataField(key, value)
        self._add_field(f)

    def init_pipe_execution(self, key, value):
        f = DataField(key, value)
        self._add_field(f)

    def _add_field(self, field: DataField, allow_reserve=False):
        if field.key in self.reserved_keys and not allow_reserve:
            raise KeyError(f"{field.key} is a reserved field key name")
        if len(self.fields) > DataFrame.MAX_FIELD_LIMIT:
            raise KeyError(f"Maximum frame fields limit reached: {len(self.fields)} ")
        self.fields[field.key] = field

    @staticmethod
    def from_byte_arr(arr: bytearray):
        frame = DataFrame()
        fields_num = arr[0]
        next_field_index = 1
        while next_field_index < len(arr):
            field_start = next_field_index + 4  # first 4 bytes hold field size
            field_size_bytes = arr[next_field_index:field_start]
            field_size = int.from_bytes(field_size_bytes, "little")
            field_bytes = arr[field_start:field_start + field_size]
            f = DataField.from_byte_arr(field_bytes)
            frame._add_field(f, True)
            next_field_index = next_field_index + 4 + field_size
        return frame

    @property
    def data(self):
        if self.fields_number == 0:
            raise ValueError("Trying to access empty frame data")
        if 'd' in self.fields:
            return self.fields['d'].value
        for key in self.fields:
            if key in self.reserved_keys:
                continue
            return self.fields[key].value
        raise ValueError("Not supported")

    @property
    def last(self):
        if 'last' not in self.fields:
            return None
        return self.fields['last'].value

    @last.setter
    def last(self, flag: bool):
        if not flag:
            self.fields.pop('last', None)
            return
        self.fields['last'] = DataField('last', 1, DType.U8)

    @property
    def pipe_execution_id(self):
        if 'pid' not in self.fields:
            return None
        return self.fields['pid'].value

    @staticmethod
    def encode_field_to_byte_arr(f: DataField):
        arr = bytearray(0)
        field_bytes = f.byte_arr
        field_size = len(field_bytes)
        arr.extend(field_size.to_bytes(4, "little"))
        arr.extend(field_bytes)
        return arr

    def to_byte_arr(self):
        arr = bytearray(1)
        arr[0] = self.fields_number
        for key in self.fields:
            f = self.fields[key]
            arr.extend(self.encode_field_to_byte_arr(f))
        return arr

    @property
    def fields_number(self):
        return len(self.fields)

    def set_pipe_exe_id(self, _id=None):
        if _id is None:
            _id = uuid.uuid4().__str__()
        self.fields['pid'] = DataField('pid', _id)
