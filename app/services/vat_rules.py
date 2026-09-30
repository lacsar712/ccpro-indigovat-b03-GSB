"""染缸状态业务规则。

电位达标判定集中在本模块：改状态入口、展开区达标条文、可染色图例张数、
状态筛可见缸数四处共用同一套口径，不得各自重写阈值比较。
"""

from decimal import Decimal
from typing import Optional

from app.models import DipLot, Vat

READY_REDOX_THRESHOLD_MV = Decimal("-500")


class VatRuleError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def redox_ready(latest: Optional[DipLot]) -> bool:
    """电位达标唯一口径：最新浸染批次 redoxMv 已填且 <= -500 mV。

    读数缺失或高于阈值一律为否。改状态入口与展开区达标条文都调这里；
    图例张数与状态筛只认状态字段（经改状态入口写入），不重复此判定。
    """
    return (
        latest is not None
        and latest.redoxMv is not None
        and Decimal(latest.redoxMv) <= READY_REDOX_THRESHOLD_MV
    )


def assert_can_mark_ready(latest: Optional[DipLot]) -> None:
    """不能将染缸标为 ready，除非最新浸染批次 redoxMv 已填且 <= -500。"""
    if not redox_ready(latest):
        raise VatRuleError(
            "无法设为可染色：最新浸染批次的氧化还原电位为空或高于 -500 mV。"
        )


def validate_vat_status_change(vat: Vat, new_status: str, latest: Optional[DipLot]) -> None:
    if new_status == Vat.STATUS_READY:
        assert_can_mark_ready(latest)
