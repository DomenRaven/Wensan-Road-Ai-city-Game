from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.tabtip import show_windows_touch_keyboard

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


class TouchKeyboardRequest(BaseModel):
    provider: str = Field(default="auto", description="auto | tabtip | sogou_hand")


@router.post("/touch-keyboard/show")
def show_touch_keyboard(body: TouchKeyboardRequest | None = None) -> dict[str, Any]:
    """Show touch keyboard · zh-CN IME + TabTip (搜狗软键盘无独立 exe)."""
    provider = body.provider if body else "auto"
    return show_windows_touch_keyboard(provider)
