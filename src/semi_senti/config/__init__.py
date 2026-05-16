"""런타임 설정 로딩 및 검증.

외부 모듈은 다음과 같이 사용한다::

    from semi_senti.config import get_settings

    settings = get_settings()
    print(settings.sqlite_path)
"""

from .settings import PROJECT_ROOT, Settings, get_settings

__all__ = ["Settings", "get_settings", "PROJECT_ROOT"]
