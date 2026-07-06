from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.tabtip import (
    hide_windows_touch_keyboard,
    show_windows_touch_keyboard,
    warm_windows_touch_keyboard,
)

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


class TouchKeyboardRequest(BaseModel):
    provider: str = Field(default="auto", description="auto | tabtip | sogou_hand")


@router.post("/touch-keyboard/show")
def show_touch_keyboard(body: TouchKeyboardRequest | None = None) -> dict[str, Any]:
    """Show touch keyboard · zh-CN IME + TabTip (搜狗软键盘无独立 exe)."""
    provider = body.provider if body else "auto"
    return show_windows_touch_keyboard(provider)


@router.post("/touch-keyboard/hide")
def hide_touch_keyboard() -> dict[str, Any]:
    """Hide TabTip touch keyboard when visible."""
    return hide_windows_touch_keyboard()


@router.post("/touch-keyboard/warm")
def warm_touch_keyboard() -> dict[str, Any]:
    """Pre-start TabTip process for faster first show on kiosk."""
    return warm_windows_touch_keyboard()
