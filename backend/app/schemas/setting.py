"""Schemas for user-configurable settings."""

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    domain_url: str = ""
    password_length: int = 8
    qr_code_visible: bool = True


class SettingsUpdate(BaseModel):
    domain_url: str = ""
    password_length: int = 8
    qr_code_visible: bool = True
