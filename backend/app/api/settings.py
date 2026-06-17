"""Settings API — user-configurable app settings."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingsResponse, SettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_setting(db: Session, key: str) -> str:
    """Get a setting value by key, or empty string if not found."""
    record = db.query(Setting).filter(Setting.key == key).first()
    return record.value if record and record.value else ""


def _upsert_setting(db: Session, key: str, value: str) -> None:
    """Insert or update a setting."""
    record = db.query(Setting).filter(Setting.key == key).first()
    if record:
        record.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    """Get all user-configurable settings."""
    return SettingsResponse(
        domain_url=_get_setting(db, "domain_url"),
        password_length=int(_get_setting(db, "password_length") or "8"),
        qr_code_visible=_get_setting(db, "qr_code_visible").lower() != "false",
    )


@router.put("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
) -> SettingsResponse:
    """Update user-configurable settings."""
    _upsert_setting(db, "domain_url", payload.domain_url.strip())
    _upsert_setting(db, "password_length", str(payload.password_length))
    _upsert_setting(db, "qr_code_visible", str(payload.qr_code_visible).lower())
    return SettingsResponse(
        domain_url=payload.domain_url.strip(),
        password_length=payload.password_length,
        qr_code_visible=payload.qr_code_visible,
    )
