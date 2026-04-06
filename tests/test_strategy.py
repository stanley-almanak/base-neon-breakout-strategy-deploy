import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategy import BaseNeonBreakoutStrategy


@pytest.fixture
def config() -> dict:
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as file:
        return json.load(file)


@pytest.fixture
def strategy(config: dict) -> BaseNeonBreakoutStrategy:
    return BaseNeonBreakoutStrategy(
        config=config,
        chain="base",
        wallet_address="0x" + "1" * 40,
    )


def build_market(
    rsi: Decimal,
    percent_b: float,
    bandwidth: float,
    quote_usd: Decimal,
    base_usd: Decimal,
    base_units: Decimal,
) -> MagicMock:
    market = MagicMock()

    rsi_data = MagicMock()
    rsi_data.value = rsi
    market.rsi.return_value = rsi_data

    bb_data = MagicMock()
    bb_data.percent_b = percent_b
    bb_data.bandwidth = bandwidth
    market.bollinger_bands.return_value = bb_data

    quote_balance = MagicMock()
    quote_balance.balance_usd = quote_usd
    quote_balance.balance = quote_usd

    base_balance = MagicMock()
    base_balance.balance_usd = base_usd
    base_balance.balance = base_units

    market.balance.side_effect = lambda token: quote_balance if token == "USDC" else base_balance
    market.price.return_value = Decimal("2500")
    return market


class TestBaseNeonBreakoutStrategy:
    def test_breakout_generates_buy_swap(self, strategy: BaseNeonBreakoutStrategy) -> None:
        market = build_market(
            rsi=Decimal("62"),
            percent_b=0.95,
            bandwidth=0.03,
            quote_usd=Decimal("500"),
            base_usd=Decimal("0"),
            base_units=Decimal("0"),
        )

        result = strategy.decide(market)

        assert result is not None
        assert getattr(result, "intent_type", None).value == "SWAP"
        assert result.from_token == "USDC"
        assert result.to_token == "WETH"

    def test_exit_generates_sell_swap(self, strategy: BaseNeonBreakoutStrategy) -> None:
        strategy._previous_bandwidth = 0.02
        market = build_market(
            rsi=Decimal("44"),
            percent_b=0.15,
            bandwidth=0.022,
            quote_usd=Decimal("100"),
            base_usd=Decimal("300"),
            base_units=Decimal("0.12"),
        )

        result = strategy.decide(market)

        assert result is not None
        assert getattr(result, "intent_type", None).value == "SWAP"
        assert result.from_token == "WETH"
        assert result.to_token == "USDC"

    def test_supports_teardown(self, strategy: BaseNeonBreakoutStrategy) -> None:
        assert strategy.supports_teardown() is True

    def test_status_contains_core_fields(self, strategy: BaseNeonBreakoutStrategy) -> None:
        status = strategy.get_status()

        assert status["strategy"] == "base_neon_breakout"
        assert status["chain"] == "base"
        assert status["protocol"] == "aerodrome"
