import os

config_path = 'config.ini'
from configparser import ConfigParser
import uuid


class NodeConfig:
    def __init__(self):
        self.config = ConfigParser()
        if not os.path.exists(config_path):
            self.config['MACHINE_INFO'] = {'id': str(uuid.uuid4())}
            self._commit()
        else:
            self.config.read(config_path)

    def _commit(self):
        with open(config_path, 'w') as f:
            self.config.write(f)

    @property
    def machine_id(self):
        return self.config.get('MACHINE_INFO', 'id')


node_config = NodeConfig()
