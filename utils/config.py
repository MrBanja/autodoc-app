import functools
import pathlib

import yaml
from pydantic import BaseModel, SecretStr


class DataBaseConfig(BaseModel):
    host: str
    username: str
    password: SecretStr
    port: int
    database: str

    def uri(self, protocol: str = 'postgresql+asyncpg') -> str:
        return "{protocol}://{user}:{pwd}@{host}:{port}/{db}".format(
            protocol=protocol,
            user=self.username,
            pwd=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            db=self.database,
        )


class RabbitMQConfig(BaseModel):
    host: str
    username: str
    password: SecretStr
    vhost: str


class TelegramConfig(BaseModel):
    tg_token: str
    host: str
    port: int
    webhook: str


class AppConfig(BaseModel):
    migrate_to: str

    telegram: TelegramConfig
    db: DataBaseConfig
    rmq: RabbitMQConfig

    project_dir: pathlib.Path
    static_dir: pathlib.Path


@functools.lru_cache
def get_config() -> AppConfig:
    path_to_config = pathlib.Path(__file__).parent.parent.resolve() / 'config.yml'
    assert path_to_config.exists(), 'No Config file!'

    project_dir = pathlib.Path(__file__).parent.parent.resolve()
    static_dir = pathlib.Path(__file__).parent.parent.joinpath('static').resolve()

    with path_to_config.open('r') as fp:
        config = yaml.safe_load(fp)
        config['project_dir'] = project_dir
        config['static_dir'] = static_dir
        return AppConfig.parse_obj(config)
