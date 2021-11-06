import subprocess

from mock.sdk import API_Processor
from mock.sdk import UpipeEntities
import os

schema_folder = os.path.join("..", "schema")


def dump_schema(api_def, file_name):
    file_path = os.path.join(schema_folder, file_name)
    model_schema = api_def.schema_json(indent=2)
    schema_file = open(file_path, "w")
    schema_file.write(model_schema)
    schema_file.close()


def generate_ts_interface(file_name, interface_name):
    schema_path = os.path.join(file_name)
    interface_dir = os.path.join("..", "..", "pipeview", "src", "models", "interfaces")
    interface_path = os.path.join(interface_dir, interface_name)
    cmd = f"quicktype --just-types -s schema {schema_path} -o {interface_path}"
    print(cmd)
    subprocess.call(cmd, shell=True)
    # os.system(cmd)


if __name__ == "__main__":
    entity_name = "UpipeEntities"
    schema_output_name = f"{entity_name}.json"
    ts_interface_name = f"{entity_name}.d.ts"
    dump_schema(UpipeEntities, schema_output_name)
    generate_ts_interface(schema_output_name, ts_interface_name)
    pass
