"""알림 시스템 (Phase 4-1, F-5.1).

본 패키지는 ``SignalLogic``/``SentimentEngine`` 의 결과를 사용자에게
텔레그램으로 푸시한다. 핵심 컴포넌트는 다음과 같다.

- :class:`TelegramClient`        : 텔레그램 Bot HTTP API 호출 + 3회 재시도 (T-043)
- :class:`NotificationManager`   : BUY/SELL 시그널 → 메시지 변환 + 발송 (T-041)
- :class:`SentimentAlertWatcher` : 감성 점수 ±30pt 급변 감지 (T-042)
"""

from .manager import NotificationManager, NotificationRecord, NotificationResult
from .sentiment_alert import SentimentAlertWatcher
from .telegram_client import TelegramClient, TelegramSendError

__all__ = [
    "TelegramClient",
    "TelegramSendError",
    "NotificationManager",
    "NotificationResult",
    "NotificationRecord",
    "SentimentAlertWatcher",
]
