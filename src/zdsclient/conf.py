import os
import yaml


class Settings(object):
    config = None
    base_dir = None

    def __init__(self):
        self.config = {}
        self.base_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
        ))

    def load(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(self.base_dir, 'config.yml')

        with open(config_file, 'r') as _config:
            self.config.update(yaml.safe_load(_config))

        return self.config


settings = Settings()