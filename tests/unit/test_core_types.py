"""
Unit tests for core types and protocols.
Testing that protocols work correctly and type aliases are valid.
"""

from datetime import UTC, datetime

from src.core.enums import ActionType, PositionType, Symbol
from src.core.models.position import Position, Trade
from src.core.protocols import IPosition, ITrade, PositionDict, PriceDict


class TestProtocolCompliance:
    """Test that concrete implementations satisfy the protocols."""

    def test_position_implements_iposition_protocol(self) -> None:
        """Test that Position class correctly implements IPosition protocol."""
        # Arrange
        position = Position(
            symbol=Symbol.BTC,
            size=float("1.0"),
            entry_price=float("50000.0"),
            leverage=float("10.0"),
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),
        )

        # Act & Assert - verify all protocol attributes exist
        assert hasattr(position, "symbol")
        assert hasattr(position, "size")
        assert hasattr(position, "entry_price")
        assert hasattr(position, "leverage")
        assert hasattr(position, "timestamp")
        assert hasattr(position, "position_type")
        assert hasattr(position, "margin_used")

        # Verify protocol methods exist and work
        assert hasattr(position, "unrealized_pnl")
        assert hasattr(position, "is_liquidation_risk")
        assert hasattr(position, "position_value")

        # Test method calls
        pnl = position.unrealized_pnl(float("52000.0"))
        assert isinstance(pnl, float)

        risk = position.is_liquidation_risk(float("45000.0"), float("0.05"))
        assert isinstance(risk, bool)

        value = position.position_value(float("52000.0"))
        assert isinstance(value, float)

    def test_trade_implements_itrade_protocol(self) -> None:
        """Test that Trade class correctly implements ITrade protocol."""
        # Arrange
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.BUY,
            quantity=1.0,
            price=50000.0,
            leverage=10.0,
            fee=25.0,
            position_type=PositionType.LONG,
            pnl=0.0,
            margin_used=5000.0,
        )

        # Act & Assert - verify all protocol attributes exist
        assert hasattr(trade, "timestamp")
        assert hasattr(trade, "symbol")
        assert hasattr(trade, "quantity")
        assert hasattr(trade, "price")
        assert hasattr(trade, "leverage")
        assert hasattr(trade, "fee")
        assert hasattr(trade, "pnl")
        assert hasattr(trade, "margin_used")

        # Verify protocol methods exist and work
        assert hasattr(trade, "notional_value")
        notional = trade.notional_value()
        assert isinstance(notional, float)
        assert notional == 50000.0  # 1.0 * 50000.0

    def test_iposition_protocol_type_checking(self) -> None:
        """Test that IPosition protocol enables proper type checking."""
        # Arrange
        position = Position(
            symbol=Symbol.ETH,
            size=float("5.0"),
            entry_price=float("3000.0"),
            leverage=float("5.0"),
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=float("3000.0"),
        )

        # Act - function that accepts IPosition protocol
        def process_position(pos: IPosition) -> float:
            return pos.unrealized_pnl(float("3100.0"))

        # Assert - Position should work as IPosition
        result = process_position(position)
        assert isinstance(result, float)

    def test_itrade_protocol_type_checking(self) -> None:
        """Test that ITrade protocol enables proper type checking."""
        # Arrange
        trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.ETH,
            action=ActionType.SELL,
            quantity=2.0,
            price=3000.0,
            leverage=3.0,
            fee=18.0,
            position_type=PositionType.LONG,
            pnl=500.0,
            margin_used=0.0,
        )

        # Act - function that accepts ITrade protocol
        def process_trade(t: ITrade) -> float:
            return t.notional_value()

        # Assert - Trade should work as ITrade
        result = process_trade(trade)
        assert result == 6000.0  # 2.0 * 3000.0


class TestTypeAliases:
    """Test type aliases are correctly defined and usable."""

    def test_price_dict_type_alias(self) -> None:
        """Test PriceDict type alias works correctly."""
        # Arrange & Act
        prices: PriceDict = {
            Symbol.BTC: float("50000.0"),
            Symbol.ETH: float("3000.0"),
        }

        # Assert - should work as dict[Symbol, float]
        assert isinstance(prices, dict)
        assert Symbol.BTC in prices
        assert prices[Symbol.BTC] == float("50000.0")
        assert prices[Symbol.ETH] == float("3000.0")

    def test_position_dict_type_alias(self) -> None:
        """Test PositionDict type alias works correctly."""
        # Arrange
        btc_position = Position(
            symbol=Symbol.BTC,
            size=float("1.0"),
            entry_price=float("50000.0"),
            leverage=float("10.0"),
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=float("5000.0"),
        )

        eth_position = Position(
            symbol=Symbol.ETH,
            size=5.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=3000.0,
        )

        # Act
        positions: PositionDict = {
            Symbol.BTC: btc_position,
            Symbol.ETH: eth_position,
        }

        # Assert - should work as dict[Symbol, IPosition]
        assert isinstance(positions, dict)
        assert Symbol.BTC in positions
        assert Symbol.ETH in positions
        assert positions[Symbol.BTC] == btc_position
        assert positions[Symbol.ETH] == eth_position

    def test_type_aliases_in_function_signatures(self) -> None:
        """Test that type aliases work in function signatures."""

        # Arrange
        def calculate_portfolio_value(positions: PositionDict, prices: PriceDict) -> float:
            """Example function using type aliases."""
            total_value = float("0.0")
            for symbol, position in positions.items():
                if symbol in prices:
                    total_value += position.position_value(prices[symbol])
            return total_value

        btc_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=1.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=50000.0,
        )

        positions: PositionDict = {Symbol.BTC: btc_position}
        prices: PriceDict = {Symbol.BTC: float("52000.0")}

        # Act
        result = calculate_portfolio_value(positions, prices)

        # Assert
        assert isinstance(result, float)
        assert result > 0


class TestProtocolContractVerification:
    """Test that protocols enforce the expected contracts."""

    def test_iposition_protocol_method_contracts(self) -> None:
        """Test that IPosition methods behave as expected."""
        # Arrange
        long_position = Position(
            symbol=Symbol.BTC,
            size=1.0,
            entry_price=50000.0,
            leverage=10.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.LONG,
            margin_used=5000.0,
        )

        short_position = Position(
            symbol=Symbol.ETH,
            size=2.0,
            entry_price=3000.0,
            leverage=5.0,
            timestamp=datetime.now(UTC),
            position_type=PositionType.SHORT,
            margin_used=1200.0,
        )

        # Act & Assert - unrealized_pnl contract
        long_pnl_profit = long_position.unrealized_pnl(
            float("52000.0")
        )  # Price up = profit for long
        long_pnl_loss = long_position.unrealized_pnl(float("48000.0"))  # Price down = loss for long

        short_pnl_profit = short_position.unrealized_pnl(
            float("2800.0")
        )  # Price down = profit for short
        short_pnl_loss = short_position.unrealized_pnl(float("3200.0"))  # Price up = loss for short

        assert long_pnl_profit > 0
        assert long_pnl_loss < 0
        assert short_pnl_profit > 0
        assert short_pnl_loss < 0

        # position_value contract
        long_value = long_position.position_value(float("52000.0"))
        short_value = short_position.position_value(float("2800.0"))

        assert long_value > 0
        assert short_value > 0  # Value should always be positive (absolute position value)

    def test_itrade_protocol_method_contracts(self) -> None:
        """Test that ITrade methods behave as expected."""
        # Arrange
        small_trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.BTC,
            action=ActionType.BUY,
            quantity=0.1,
            price=50000.0,
            leverage=1.0,
            fee=5.0,
            position_type=PositionType.LONG,
            pnl=0.0,
            margin_used=5000.0,
        )

        large_trade = Trade(
            timestamp=datetime.now(UTC),
            symbol=Symbol.ETH,
            action=ActionType.SELL,
            quantity=10.0,
            price=3000.0,
            leverage=5.0,
            fee=30.0,
            position_type=PositionType.SHORT,
            pnl=1000.0,
            margin_used=6000.0,
        )

        # Act & Assert - notional_value contract
        small_notional = small_trade.notional_value()
        large_notional = large_trade.notional_value()

        assert small_notional == 5000.0  # 0.1 * 50000
        assert large_notional == 30000.0  # 10.0 * 3000
        assert large_notional > small_notional
