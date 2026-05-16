"""텔레그램 Bot HTTP API 클라이언트 (T-043, F-5.1.1, UC-05 §E1).

> "텔레그램 API 전송 실패: 최대 3회 재시도 후 실패 시 시스템 로그에 오류를 기록한다."

설계
----
- 외부 의존성을 최소화하기 위해 ``python-telegram-bot`` 대신 ``requests`` 로
  Telegram Bot REST API (https://api.telegram.org) 를 직접 호출한다.
  → ``python-telegram-bot`` 20.x 는 async-only 라 동기 환경에서 사용 시
    asyncio.run() 등 별도 처리가 필요해 단순 HTTP 호출이 더 깔끔하다.
- 토큰/chat_id 는 ``Settings`` 에서만 주입받아 하드코딩을 차단한다(.env 활용).
- 모든 실패는 ``TelegramSendError`` 로 일원화하고, 호출자가 적재/재시도
  횟수를 결정할 수 있도록 ``send`` 는 1회 시도/예외 전파 모드와
  ``send_with_retry`` 는 ``max_retries`` 까지 자동 재시도하는 모드를 분리.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..config import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

_TELEGRAM_BASE = "https://api.telegram.org"


class TelegramSendError(RuntimeError):
    """Telegram API 호출 실패 도메인 예외."""


class TelegramClient:
    """Telegram Bot 메시지 전송 클라이언트.

    Parameters
    ----------
    bot_token / chat_id:
        직접 주입 가능. 미지정 시 ``Settings.telegram_bot_token / telegram_chat_id``.
    timeout:
        HTTP 타임아웃(초). 미지정 시 ``Settings.http_timeout_seconds``.
    max_retries:
        ``send_with_retry`` 의 시도 횟수 상한. PRD/UC-05 §E1 의 "최대 3회".
    backoff_seconds:
        재시도 간 대기. 단순 선형 backoff (i * backoff_seconds).
    """

    def __init__(
        self,
        *,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._bot_token = (bot_token if bot_token is not None else self._settings.telegram_bot_token).strip()
        self._chat_id = (chat_id if chat_id is not None else self._settings.telegram_chat_id).strip()
        self._timeout = int(timeout if timeout is not None else self._settings.http_timeout_seconds)
        retries_value = max_retries if max_retries is not None else self._settings.notify_max_retries
        self._max_retries = max(1, int(retries_value))
        backoff_value = (
            backoff_seconds if backoff_seconds is not None else self._settings.notify_backoff_seconds
        )
        self._backoff_seconds = max(0.0, float(backoff_value))

    # ------------------------------------------------------------------ properties
    @property
    def is_configured(self) -> bool:
        """봇 토큰과 chat_id 가 모두 설정되어 있는가."""
        return bool(self._bot_token) and bool(self._chat_id)

    @property
    def max_retries(self) -> int:
        return self._max_retries

    # ------------------------------------------------------------------ low-level
    def _build_url(self, method: str) -> str:
        return f"{_TELEGRAM_BASE}/bot{self._bot_token}/{method}"

    def send(
        self,
        text: str,
        *,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
    ) -> dict:
        """단일 시도로 메시지를 전송한다. 실패 시 ``TelegramSendError`` 전파."""
        if not text or not text.strip():
            raise TelegramSendError("메시지 본문이 비어 있습니다.")
        if not self.is_configured:
            raise TelegramSendError(
                "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되지 않았습니다 (.env 확인)."
            )

        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover - 의존성 미설치 환경
            raise TelegramSendError("'requests' 패키지가 필요합니다.") from exc

        url = self._build_url("sendMessage")
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "disable_web_page_preview": bool(disable_web_page_preview),
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = requests.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise TelegramSendError(f"Telegram 네트워크 오류: {exc}") from exc

        # Telegram 은 200 + JSON {"ok": true|false} 로 응답한다.
        try:
            data = response.json()
        except ValueError as exc:
            raise TelegramSendError(
                f"Telegram 응답 JSON 파싱 실패 (status={response.status_code})"
            ) from exc

        if response.status_code >= 400 or not data.get("ok"):
            description = data.get("description") or f"status={response.status_code}"
            raise TelegramSendError(f"Telegram API 오류: {description}")

        return data

    def send_with_retry(
        self,
        text: str,
        *,
        parse_mode: Optional[str] = None,
    ) -> dict:
        """최대 ``max_retries`` 회까지 재시도하며 메시지 전송.

        Returns
        -------
        dict
            성공한 ``send`` 응답.

        Raises
        ------
        TelegramSendError
            모든 시도가 실패한 경우. ``last_error`` 메시지 포함.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self.send(text, parse_mode=parse_mode)
            except TelegramSendError as exc:
                last_exc = exc
                _LOGGER.warning(
                    "텔레그램 발송 실패 (attempt %d/%d): %s",
                    attempt, self._max_retries, exc,
                )
                if attempt < self._max_retries and self._backoff_seconds > 0:
                    time.sleep(self._backoff_seconds * attempt)
        # 모든 시도 실패
        message = (
            f"텔레그램 발송이 {self._max_retries}회 모두 실패했습니다: "
            f"{last_exc!s}" if last_exc else "텔레그램 발송 실패"
        )
        _LOGGER.error(message)
        raise TelegramSendError(message)
