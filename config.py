from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    """Класс для подключения токенов."""
    bot_token: SecretStr
    creator_id: SecretStr
    group_id: SecretStr
    pay_token: SecretStr
    proxy: SecretStr
    model_config = SettingsConfigDict(env_file='.env',
                                      env_file_encoding='utf-8')


config = Settings()
