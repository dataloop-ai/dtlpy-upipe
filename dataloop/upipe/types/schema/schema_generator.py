import subprocess

from upipe.types import UPipeEntityType, UPipeMessageType, PipeActionType, PipeExecutionStatus, \
    ProcessorExecutionStatus, ResourceType
from upipe.types.framework import UpipeEntities
from upipe.types.performance import MetricType, PerformanceMetricUnitType
import os

schema_folder = os.path.join("..", "schema")


def getTsEnumStr(enum):
    enum_str = f'export enum {enum.__name__} ' + '{\n'
    for s in enum:
        enum_str += f'    {s.name} = {s.value}' + ',\n'
    enum_str += '}\n'
    return enum_str


def getTsClassStaticEnumStr(cls):
    enum_static_props = [v for v, m in vars(cls).items() if not (v.startswith('_') or callable(m))]
    enum_str = f'export enum {cls.__name__} ' + '{\n'
    for s in enum_static_props:
        enum_str += f'    {s} = \'{cls.__dict__[s]}\'' + ',\n'
    enum_str += '}\n'
    return enum_str


def line_prepender(filename, line):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n')
        f.write('\n' + content)


def line_appender(filename, line):
    with open(filename, 'a') as f:
        f.write(line.rstrip('\r\n') + '\n')


def dump_schema(api_def, file_name):
    file_path = os.path.join(schema_folder, file_name)
    model_schema = api_def.schema_json(indent=2)
    schema_file = open(file_path, "w")
    schema_file.write(model_schema)
    schema_file.close()
    return file_path


def generate_ts_interface(file_name, interface_name):
    schema_path = os.path.join(file_name)
    interface_dir = os.path.join("..", "..", "pipeview", "src", "models", "defs")
    interface_path = os.path.join(interface_dir, interface_name)
    cmd = f"quicktype --just-types -s schema {schema_path} -o {interface_path}"
    print(cmd)
    subprocess.call(cmd, shell=True)
    # os.system(cmd)
    return interface_path


if __name__ == "__main__":
    # entities
    entity_name = "UpipeEntities"
    schema_output_name = f"{entity_name}.json"
    ts_interface_name = f"{entity_name}.ts"
    schema_file_path = dump_schema(UpipeEntities, schema_output_name)
    interface_path = generate_ts_interface(schema_output_name, ts_interface_name)
    line_prepender(interface_path, "/* *********** Interfaces *************** */")
    # linter rules
    linter_disable = ['/* eslint-disable @typescript-eslint/no-unused-vars */',
                      '/* eslint-disable @typescript-eslint/no-explicit-any */',
                      '/* eslint-disable camelcase */',
                      '/* eslint-disable no-multi-spaces */',
                      '/* eslint-disable no-use-before-define */']

    for ln in linter_disable:
        line_prepender(interface_path, ln)
    line_prepender(interface_path, "/* *********** Linter rules *************** */")

    # enums
    line_appender(interface_path, "/* *********** Int Enums *************** */")
    line_appender(interface_path, getTsEnumStr(ProcessorExecutionStatus))
    line_appender(interface_path, getTsEnumStr(PipeExecutionStatus))
    line_appender(interface_path, getTsEnumStr(UPipeEntityType))
    line_appender(interface_path, getTsEnumStr(UPipeMessageType))
    line_appender(interface_path, getTsEnumStr(PipeActionType))
    # static classes
    line_appender(interface_path, "/* *********** Str enums *************** */")
    line_appender(interface_path, getTsClassStaticEnumStr(ResourceType))
    line_appender(interface_path, getTsClassStaticEnumStr(MetricType))
    line_appender(interface_path, getTsClassStaticEnumStr(PerformanceMetricUnitType))
    os.unlink(schema_file_path)
