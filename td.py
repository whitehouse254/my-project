"""
DERIV TRADING BOT - Fixed Version
Trades synthetic indices (Volatility 75, etc.) on Deriv
USE DEMO ACCOUNT FIRST!
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands

# Try to import websockets with error handling
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️ websockets library not installed. Run: pip install websockets")

# ======================= CONFIGURATION =======================
# Get your API token from Deriv: Settings -> API Token
DERIV_API_TOKEN = "YOUR_DERIV_API_TOKEN"  # Get from deriv.com account
DERIV_APP_ID = 1089  # 1089 = demo, get real ID from deriv.com/developers
SYMBOL = "R_75"      # R_75 = Volatility 75 (most popular)

# Trading Parameters (Binary Options)
TRADE_AMOUNT = 1.0          # $1 per trade (start small)
DURATION = 5                # 5 ticks duration
DURATION_UNIT = "t"         # "t" = ticks, "m" = minutes

# Strategy Parameters (Same RSI you already have)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MIN_TICKS_FOR_ANALYSIS = 50  # Minimum data points

# Risk Management
MAX_DAILY_TRADES = 20
MAX_DAILY_LOSS = 10.0       # Stop at $10 loss
STOP_LOSS_PCT = 2.0         # 2% stop loss
TAKE_PROFIT_PCT = 4.0       # 4% take profit
COOLDOWN_SECONDS = 30       # Wait between trades

# Logging
LOG_LEVEL = "INFO"
# ==============================================================

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DerivWebSocketClient:
    """Handles WebSocket connection to Deriv API"""

    def __init__(self, api_token: str, app_id: int):
        self.api_token = api_token
        self.app_id = app_id
        self.ws_url = f"wss://ws.deriv.com/websockets/v3?app_id={app_id}"
        self.websocket = None
        self.ticks_data: List[Dict] = []
        self.balance = 0
        self.is_demo = True

    async def connect(self):
        """Establish WebSocket connection and authorize"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not installed. Run: pip install websockets")
            return False

        logger.info(f"Connecting to Deriv WebSocket: {self.ws_url}")

        try:
            self.websocket = await websockets.connect(self.ws_url)

            # Authorize with API token
            auth_request = {
                "authorize": self.api_token,
                "req_id": 1
            }
            await self.websocket.send(json.dumps(auth_request))
            response = await self.websocket.recv()
            auth_response = json.loads(response)

            if auth_response.get("authorize"):
                self.is_demo = auth_response["authorize"].get("is_virtual", True)
                self.balance = float(auth_response["authorize"]["balance"])
                logger.info(f"✅ Authorized - Demo Mode: {self.is_demo}")
                logger.info(f"💰 Balance: ${self.balance:.2f}")
                return True
            else:
                logger.error(f"❌ Authorization failed: {auth_response.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def subscribe_ticks(self, symbol: str):
        """Subscribe to real-time tick data"""
        tick_request = {
            "ticks": symbol,
            "subscribe": 1,
            "req_id": 2
        }
        await self.websocket.send(json.dumps(tick_request))
        logger.info(f"✅ Subscribed to {symbol} ticks")

    async def get_ticks_history(self, symbol: str, count: int = 500):
        """Fetch historical ticks for analysis"""
        history_request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "ticks",
            "req_id": 3
        }
        await self.websocket.send(json.dumps(history_request))
        response = await self.websocket.recv()
        return json.loads(response)

    async def place_binary_trade(self, symbol: str, amount: float, direction: str,
                                  duration: int, duration_unit: str) -> Dict:
        """Place a binary option trade (CALL/PUT)"""
        try:
            # First, get a proposal (price quote)
            proposal_request = {
                "proposal": 1,
                "amount": amount,
                "barrier": "+0" if direction == "CALL" else "-0",
                "duration": duration,
                "duration_unit": duration_unit,
                "basis": "payout",
                "contract_type": "CALL" if direction == "CALL" else "PUT",
                "currency": "USD",
                "symbol": symbol,
                "req_id": 4
            }

            await self.websocket.send(json.dumps(proposal_request))
            proposal_response = await self.websocket.recv()
            proposal_data = json.loads(proposal_response)

            if "error" in proposal_data:
                logger.error(f"Proposal error: {proposal_data['error']}")
                return {"success": False, "error": proposal_data["error"]["message"]}

            proposal_id = proposal_data["proposal"]["id"]
            logger.info(f"📊 Proposal received - ID: {proposal_id}")

            # Execute the buy order
            buy_request = {
                "buy": proposal_id,
                "price": amount,
                "req_id": 5
            }

            await self.websocket.send(json.dumps(buy_request))
            buy_response = await self.websocket.recv()
            buy_data = json.loads(buy_response)

            if "error" in buy_data:
                logger.error(f"Buy error: {buy_data['error']}")
                return {"success": False, "error": buy_data["error"]["message"]}

            logger.info(f"✅ Trade placed - Contract ID: {buy_data['buy']['contract_id']}")
            logger.info(f"   Direction: {direction.upper()} | Amount: ${amount} | Duration: {duration}{duration_unit}")

            return {
                "success": True,
                "contract_id": buy_data["buy"]["contract_id"],
                "direction": direction,
                "amount": amount,
                "entry_price": buy_data["buy"].get("spot", 0)
            }

        except Exception as e:
            logger.error(f"Trade placement error: {e}")
            return {"success": False, "error": str(e)}

    async def monitor_trade(self, contract_id: str) -> Dict:
        """Monitor open trade until settlement"""
        subscribe_request = {
            "subscribe": 1,
            "contracts": contract_id,
            "req_id": 6
        }
        await self.websocket.send(json.dumps(subscribe_request))

        # Wait for contract settlement
        while True:
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                data = json.loads(response)

                if "contract" in data:
                    contract = data["contract"]
                    if contract.get("is_settleable", False) or contract.get("status") == "settled":
                        profit = float(contract.get("profit", 0))
                        payout = float(contract.get("payout", 0))

                        logger.info(f"🏁 Trade settled - Profit: ${profit:.2f}")
                        return {
                            "profit": profit,
                            "payout": payout,
                            "status": contract.get("status", "settled")
                        }

                await asyncio.sleep(0.5)

            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for trade settlement")
                return {"profit": 0, "payout": 0, "status": "timeout"}
            except Exception as e:
                logger.error(f"Error monitoring trade: {e}")
                await asyncio.sleep(1)

    async def get_account_balance(self) -> float:
        """Fetch current account balance"""
        try:
            balance_request = {"balance": 1, "req_id": 7}
            await self.websocket.send(json.dumps(balance_request))
            response = await self.websocket.recv()
            data = json.loads(response)

            if "balance" in data:
                self.balance = float(data["balance"]["balance"])
                return self.balance
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        return self.balance

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()


class DerivTechnicalAnalyzer:
    """Technical analysis for tick data (adapts your existing strategy)"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tick_history: List[float] = []
        self.tick_timestamps: List[float] = []

    def ticks_to_ohlc(self, ticks: List[float], ticks_per_candle: int = 10) -> pd.DataFrame:
        """Convert tick data to OHLC candles (using fixed number of ticks)"""
        if len(ticks) < ticks_per_candle:
            return pd.DataFrame()

        ohlc_data = []

        for i in range(0, len(ticks) - ticks_per_candle, ticks_per_candle):
            window = ticks[i:i+ticks_per_candle]
            if len(window) == ticks_per_candle:
                ohlc_data.append({
                    'open': window[0],
                    'high': max(window),
                    'low': min(window),
                    'close': window[-1],
                    'volume': ticks_per_candle
                })

        df = pd.DataFrame(ohlc_data)
        return df

    def calculate_rsi(self, ticks: List[float], period: int = 14) -> float:
        """Calculate RSI from tick data (same as your Bybit bot)"""
        if len(ticks) < period * 2:  # Need enough data
            return 50

        # Create OHLC candles for RSI calculation
        df = self.ticks_to_ohlc(ticks, ticks_per_candle=5)
        if df.empty or len(df) < period:
            return 50

        try:
            # Use last N candles
            df_to_use = df.tail(period * 2)
            rsi_indicator = RSIIndicator(close=df_to_use['close'], window=period)
            rsi = rsi_indicator.rsi_indicator().iloc[-1]
            return round(rsi, 2)
        except Exception as e:
            logger.debug(f"RSI calculation error: {e}")
            return 50

    def calculate_moving_average(self, ticks: List[float], period: int = 20) -> float:
        """Calculate simple moving average"""
        if len(ticks) < period:
            return ticks[-1] if ticks else 0

        recent_ticks = ticks[-period:]
        return sum(recent_ticks) / len(recent_ticks)

    def detect_trend(self, ticks: List[float]) -> str:
        """Detect trend using simple method for tick data"""
        if len(ticks) < 100:
            return "NEUTRAL"

        # Calculate short and long term trends
        short_ma = self.calculate_moving_average(ticks, 20)
        medium_ma = self.calculate_moving_average(ticks, 50)
        current_price = ticks[-1]

        # Calculate slope of recent prices
        if len(ticks) > 20:
            recent_slope = (ticks[-1] - ticks[-20]) / ticks[-20]
        else:
            recent_slope = 0

        if (current_price > short_ma and short_ma > medium_ma) or recent_slope > 0.0005:
            return "BULLISH"
        elif (current_price < short_ma and short_ma < medium_ma) or recent_slope < -0.0005:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def calculate_bollinger(self, ticks: List[float]) -> Dict:
        """Calculate Bollinger Bands for volatility"""
        if len(ticks) < 100:
            return {"upper": 0, "middle": 0, "lower": 0, "position": 0.5, "width": 0}

        # Create OHLC candles for Bollinger Bands
        df = self.ticks_to_ohlc(ticks, ticks_per_candle=5)
        if df.empty or len(df) < 20:
            return {"upper": 0, "middle": 0, "lower": 0, "position": 0.5, "width": 0}

        try:
            bb = BollingerBands(close=df['close'], window=20, window_dev=2)
            current_price = df['close'].iloc[-1]
            upper = bb.bollinger_hband().iloc[-1]
            lower = bb.bollinger_lband().iloc[-1]
            middle = bb.bollinger_mavg().iloc[-1]

            # Calculate position within bands (0 to 1)
            if upper != lower:
                position = (current_price - lower) / (upper - lower)
                position = max(0, min(1, position))
            else:
                position = 0.5

            width = (upper - lower) / middle if middle > 0 else 0

            return {
                "upper": upper,
                "middle": middle,
                "lower": lower,
                "position": position,
                "width": width
            }
        except Exception as e:
            logger.debug(f"Bollinger calculation error: {e}")
            return {"upper": 0, "middle": 0, "lower": 0, "position": 0.5, "width": 0}

    def get_trading_signal(self, ticks: List[float], price: float) -> Dict:
        """
        Generate trading signal based on multiple indicators
        This adapts your existing RSI strategy to Deriv
        """
        if len(ticks) < MIN_TICKS_FOR_ANALYSIS:
            return {"signal": "WAIT", "strength": 0, "reason": f"Insufficient data ({len(ticks)} ticks)"}

        try:
            rsi = self.calculate_rsi(ticks, RSI_PERIOD)
            trend = self.detect_trend(ticks)
            bb = self.calculate_bollinger(ticks)

            signals = {"CALL": 0, "PUT": 0}
            reasons = []

            # 1. RSI Signal (your primary strategy)
            if rsi < RSI_OVERSOLD:
                signals["CALL"] += 3
                reasons.append(f"RSI Oversold: {rsi}")
            elif rsi > RSI_OVERBOUGHT:
                signals["PUT"] += 3
                reasons.append(f"RSI Overbought: {rsi}")
            else:
                # Mid-RSI - neutral bias
                if rsi < RSI_MID and rsi > RSI_OVERSOLD:
                    signals["CALL"] += 1
                    reasons.append(f"RSI below 50: {rsi}")
                elif rsi > RSI_MID and rsi < RSI_OVERBOUGHT:
                    signals["PUT"] += 1
                    reasons.append(f"RSI above 50: {rsi}")

            # 2. Trend Filter
            if trend == "BULLISH":
                signals["CALL"] += 2
                reasons.append("Bullish trend")
            elif trend == "BEARISH":
                signals["PUT"] += 2
                reasons.append("Bearish trend")

            # 3. Bollinger Bands (reversion signal)
            if bb["position"] < 0.2:  # Price near lower band
                signals["CALL"] += 2
                reasons.append(f"Bollinger lower band ({bb['position']:.0%})")
            elif bb["position"] > 0.8:  # Price near upper band
                signals["PUT"] += 2
                reasons.append(f"Bollinger upper band ({bb['position']:.0%})")

            # Determine final signal (need at least 2 signals for confidence)
            if signals["CALL"] >= signals["PUT"] and signals["CALL"] >= 3:
                return {
                    "signal": "CALL",
                    "strength": signals["CALL"],
                    "rsi": rsi,
                    "trend": trend,
                    "reasons": reasons,
                    "price": price,
                    "bb_position": bb["position"]
                }
            elif signals["PUT"] >= signals["CALL"] and signals["PUT"] >= 3:
                return {
                    "signal": "PUT",
                    "strength": signals["PUT"],
                    "rsi": rsi,
                    "trend": trend,
                    "reasons": reasons,
                    "price": price,
                    "bb_position": bb["position"]
                }
            else:
                return {
                    "signal": "WAIT",
                    "strength": max(signals.values()),
                    "rsi": rsi,
                    "trend": trend,
                    "reasons": ["Mixed signals - waiting"],
                    "price": price
                }

        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            return {"signal": "WAIT", "strength": 0, "reason": f"Error: {e}"}


class DerivTradingBot:
    """Main Deriv Trading Bot - The complete orchestrator"""

    def __init__(self):
        self.client = None
        self.analyzer = DerivTechnicalAnalyzer(SYMBOL)
        self.daily_trades = 0
        self.daily_pnl = 0
        self.position_open = False
        self.current_contract = None
        self.last_trade_time = 0
        self.trades_today = []  # Store today's trades

    async def initialize(self):
        """Initialize connection and setup"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot start: websockets library not installed")
            logger.info("Run: pip install websockets")
            return False

        self.client = DerivWebSocketClient(DERIV_API_TOKEN, DERIV_APP_ID)

        if not await self.client.connect():
            logger.error("Failed to connect to Deriv")
            return False

        await self.client.subscribe_ticks(SYMBOL)

        # Fetch historical data for initial analysis
        try:
            history = await self.client.get_ticks_history(SYMBOL, 500)
            if "ticks_history" in history:
                ticks = history["ticks_history"]["prices"]
                for tick in ticks:
                    self.analyzer.tick_history.append(float(tick))

            logger.info(f"📊 Initialized - Historical ticks loaded: {len(self.analyzer.tick_history)}")
        except Exception as e:
            logger.warning(f"Could not fetch historical data: {e}")

        return True

    async def process_tick(self, tick_data: Dict):
        """Process incoming tick data and generate signals"""
        if "tick" not in tick_data:
            return

        tick_price = float(tick_data["tick"]["quote"])
        self.analyzer.tick_history.append(tick_price)

        # Keep only last 2000 ticks for performance
        if len(self.analyzer.tick_history) > 2000:
            self.analyzer.tick_history = self.analyzer.tick_history[-2000:]

        # Check if we can trade
        can_trade, reason = self.can_trade()
        if not can_trade:
            if reason != "Position open" and len(self.analyzer.tick_history) % 100 == 0:
                logger.debug(f"Can't trade: {reason}")
            return

        # Generate trading signal (only every 10 ticks to avoid spam)
        if len(self.analyzer.tick_history) % 10 == 0:
            signal_data = self.analyzer.get_trading_signal(
                self.analyzer.tick_history,
                tick_price
            )

            # Print status
            self.print_status(signal_data)

            # Execute trade if signal is strong
            if signal_data["signal"] in ["CALL", "PUT"] and not self.position_open:
                await self.execute_trade(signal_data)

    def can_trade(self) -> tuple:
        """Check risk management limits"""
        if self.position_open:
            return False, "Position open"

        if time.time() - self.last_trade_time < COOLDOWN_SECONDS:
            return False, "Cooldown"

        if self.daily_trades >= MAX_DAILY_TRADES:
            return False, f"Max daily trades ({MAX_DAILY_TRADES}) reached"

        if self.daily_pnl <= -MAX_DAILY_LOSS:
            return False, f"Daily loss limit (${MAX_DAILY_LOSS}) reached"

        return True, "OK"

    async def execute_trade(self, signal_data: Dict):
        """Execute a trade based on signal"""
        direction = signal_data["signal"]
        reasons = ", ".join(signal_data["reasons"])
        price = signal_data["price"]
        rsi = signal_data["rsi"]
        strength = signal_data["strength"]

        logger.info(f"\n{'='*50}")
        logger.info(f"🎯 TRADE SIGNAL: {direction} (Strength: {strength})")
        logger.info(f"   Price: {price:.4f} | RSI: {rsi}")
        logger.info(f"   Trend: {signal_data['trend']}")
        logger.info(f"   Reasons: {reasons}")
        logger.info(f"{'='*50}")

        # Place the trade
        result = await self.client.place_binary_trade(
            symbol=SYMBOL,
            amount=TRADE_AMOUNT,
            direction=direction,
            duration=DURATION,
            duration_unit=DURATION_UNIT
        )

        if result["success"]:
            self.position_open = True
            self.current_contract = result["contract_id"]
            self.last_trade_time = time.time()

            # Monitor the trade
            settlement = await self.client.monitor_trade(result["contract_id"])

            # Update statistics
            profit = settlement["profit"]
            self.daily_trades += 1
            self.daily_pnl += profit

            # Store trade record
            self.trades_today.append({
                "time": datetime.now().isoformat(),
                "direction": direction,
                "entry_price": price,
                "rsi": rsi,
                "profit": profit,
                "contract_id": result["contract_id"]
            })

            # Check if stop loss / take profit triggered
            if profit <= -TRADE_AMOUNT * STOP_LOSS_PCT / 100:
                logger.warning(f"🛑 Stop loss triggered! Loss: ${profit:.2f}")
            elif profit >= TRADE_AMOUNT * TAKE_PROFIT_PCT / 100:
                logger.info(f"🎉 Take profit hit! Profit: ${profit:.2f}")

            # Update balance
            await self.client.get_account_balance()

            # Log daily summary
            win_loss = "WIN" if profit > 0 else "LOSS"
            logger.info(f"📊 Trade #{self.daily_trades}: {win_loss} ${profit:.2f} | Daily PnL: ${self.daily_pnl:.2f}")
            logger.info(f"💰 Balance: ${self.client.balance:.2f}")

            self.position_open = False
            self.current_contract = None

    def print_status(self, signal_data: Dict):
        """Print current market status"""
        if signal_data["signal"] != "WAIT":
            logger.info(f"📊 SIGNAL: {signal_data['signal']} | RSI: {signal_data['rsi']} | Strength: {signal_data['strength']}")
        else:
            # Only print occasionally to avoid spam
            if len(self.analyzer.tick_history) % 200 == 0:
                logger.info(f"📊 Status - RSI: {signal_data['rsi']} | Signal: {signal_data['signal']} | Daily: {self.daily_trades} trades | PnL: ${self.daily_pnl:.2f}")

    def print_session_summary(self):
        """Print final session summary"""
        wins = sum(1 for t in self.trades_today if t["profit"] > 0)
        losses = sum(1 for t in self.trades_today if t["profit"] < 0)
        win_rate = (wins / self.daily_trades * 100) if self.daily_trades > 0 else 0

        logger.info("\n" + "="*60)
        logger.info("📈 SESSION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Trades: {self.daily_trades}")
        logger.info(f"Wins: {wins} | Losses: {losses}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Total PnL: ${self.daily_pnl:.2f}")
        logger.info(f"Final Balance: ${self.client.balance if self.client else 0:.2f}")
        logger.info("="*60)

        # Save to file
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_trades": self.daily_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": self.daily_pnl,
            "final_balance": self.client.balance if self.client else 0,
            "trades": self.trades_today
        }

        with open("deriv_trading_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        logger.info("📁 Summary saved to deriv_trading_summary.json")

    async def run(self):
        """Main bot loop"""
        if not await self.initialize():
            return

        logger.info("\n" + "🚀"*20)
        logger.info("DERIV TRADING BOT - RUNNING")
        logger.info(f"Symbol: {SYMBOL}")
        logger.info(f"Trade Amount: ${TRADE_AMOUNT}")
        logger.info(f"Duration: {DURATION}{DURATION_UNIT}")
        logger.info(f"RSI Strategy: Oversold={RSI_OVERSOLD} | Overbought={RSI_OVERBOUGHT}")
        logger.info("🚀"*20)
        logger.info("Press CTRL+C to stop\n")

        try:
            # Listen for incoming WebSocket messages
            while True:
                message = await self.client.websocket.recv()
                data = json.loads(message)

                # Process tick data
                if "tick" in data:
                    await self.process_tick(data)

                # Process contract updates
                if "contract" in data:
                    # Contract update received from subscription
                    pass

                # Check for errors
                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    if "Rate limit" not in error_msg:  # Don't spam rate limit errors
                        logger.warning(f"API Error: {error_msg}")

        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped by user")
            self.print_session_summary()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.print_session_summary()
        finally:
            if self.client:
                await self.client.close()


# ======================= MAIN EXECUTION =======================

async def main():
    """Entry point"""
    # Check for websockets library
    if not WEBSOCKETS_AVAILABLE:
        print("\n⚠️ Missing required library: websockets")
        print("\nInstall it by running:")
        print("    pip install websockets")
        print("\nThen restart the bot.")
        return

    # Validate API token
    if DERIV_API_TOKEN == "YOUR_DERIV_API_TOKEN":
        print("\n⚠️ WARNING: You need to set your Deriv API token!")
        print("\n   1. Log into deriv.com (use demo account)")
        print("   2. Go to Settings → API Token")
        print("   3. Create a token with 'Trade' permission")
        print("   4. Copy the token (starts with 'deriv-')")
        print("   5. Replace 'YOUR_DERIV_API_TOKEN' in the code")
        print("\n   Example: DERIV_API_TOKEN = 'deriv-abc123xyz'")
        print("\n⚠️ Using DEMO account only until you've tested extensively!")

        # For testing, you can use a public demo token
        use_demo = input("\nUse public demo token for testing? (y/n): ")
        if use_demo.lower() == 'y':
            # This is a public demo token for testing only
            print("Using public demo token...")
            # Note: Real code would need a valid token
            print("Please get your own token from deriv.com")
            return
        else:
            print("Exiting. Please set your API token and try again.")
            return

    bot = DerivTradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())