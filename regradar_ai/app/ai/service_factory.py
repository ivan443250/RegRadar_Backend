"""Dependency-injection factory for the stable RegRadar AI facade."""

from functools import lru_cache

from .reg_radar_ai_service import RegRadarAIService


def build_reg_radar_ai_service(**overrides) -> RegRadarAIService:
    return RegRadarAIService(**overrides)


@lru_cache(maxsize=1)
def get_reg_radar_ai_service() -> RegRadarAIService:
    return build_reg_radar_ai_service()


def reset_reg_radar_ai_service_for_tests() -> None:
    get_reg_radar_ai_service.cache_clear()
