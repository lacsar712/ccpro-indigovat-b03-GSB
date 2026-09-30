"""染缸状态业务规则。

电位达标口径全应用只有一处：``evaluate_ready_gate``。
以下四处必须复用同一套口径，禁止各自另写阈值：

1. 改状态入口（``assert_can_mark_ready`` / ``validate_vat_status_change``）；
2. 展开区达标条文（后端 payload 的 ``potentialReady`` / ``readyGateReason``）；
3. 可染色图例张数（只数 ``Vat.status == ready`` 的缸，条文亮灯不算）；
4. 状态筛为「可染色」后的可见缸集（同样只认状态字段）。

注意区分两个概念：

- ``evaluate_ready_gate`` 是**读数派生**结论（最新批次电位够不够）；
- ``Vat.status`` 是**持久化状态字段**。

条文亮「是」不等于状态已 ready；登记浸染批次也绝不能据此静默改写状态字段。
"""

from decimal import Decimal
from typing import NamedTuple, Optional

from app.models import DipLot, Vat

# 「可染色」电位门槛：最新批次氧化还原电位须 <= -500 mV
READY_GATE_MV = Decimal("-500")


class ReadyGateResult(NamedTuple):
    ok: bool
    reason: str


def evaluate_ready_gate(latest: Optional[DipLot]) -> ReadyGateResult:
    """判定最新浸染批次电位是否达到「可染色」门槛。

    口径（唯一来源）：最新批次存在、``redoxMv`` 已填、且 ≤ -500 mV。
    读数缺失或高于 -500 mV 一律判否，并给出原因。
    """
    if latest is None:
        return ReadyGateResult(False, "尚无浸染批次")
    if latest.redoxMv is None:
        return ReadyGateResult(False, "最新批次电位读数缺失")
    if Decimal(latest.redoxMv) > READY_GATE_MV:
        return ReadyGateResult(
            False,
            f"最新批次电位 {latest.redoxMv} mV，高于门槛 {READY_GATE_MV} mV",
        )
    return ReadyGateResult(
        True,
        f"最新批次电位 {latest.redoxMv} mV，不高于 {READY_GATE_MV} mV",
    )


class VatRuleError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def assert_can_mark_ready(latest: Optional[DipLot]) -> None:
    """改状态入口：读数不达标则拒绝把缸标为 ready。与达标条文同一口径。"""
    result = evaluate_ready_gate(latest)
    if not result.ok:
        raise VatRuleError(f"无法设为可染色：{result.reason}。")


def validate_vat_status_change(vat: Vat, new_status: str, latest: Optional[DipLot]) -> None:
    if new_status == Vat.STATUS_READY:
        assert_can_mark_ready(latest)
