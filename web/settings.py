#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DOMAIN: str = None

    SECRET_KEY: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    DATA_PATH: Optional[str] = None

    MAIL_USERNAME: str = None
    MAIL_PASSWORD: str = None
    MAIL_FROM: str = None
    MAIL_PORT: int = 0
    MAIL_SERVER: str = None
    MAIL_FROM_NAME: str = None
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    class Config:
        env_file = '../.env'


settings = Settings()
