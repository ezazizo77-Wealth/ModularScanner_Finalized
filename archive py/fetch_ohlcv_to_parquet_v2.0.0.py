"""
fetch_ohlcv_to_parquet_v2.0.0.py
Version: 2.0.0
Author: A-Team (Aziz + Amy)

🔍 Description:
Fetches OHLCV data from Binance for selected symbols and timeframes, storing results
in Parquet format. Includes styled CLI, config parsing, logging, and error tracking.

✨ Features:
- CLI powered by `typer` with config path as argument
- Styled terminal output via `rich`
- Logs output to both console and file (fetch.log)
- Reuses ccxt client with rate limiting
- Tracks skipped symbols with error breakdown
"""

import ccxt
import pandas as pd
import typer
import yaml
import time
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import track
from rich import print
import logging

app = typer.Typer()
console = Console()

OUTPUT_DIR = Path("ohlcv_parquet")
LOG_FILE = "fetch.log"
OUTPUT_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Reusable ccxt exchange client
exchange = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 20000,
    'options': {'defaultType': 'spot'}
})


def fetch_symbols(config):
    if config["fetcher"].get("use_test_symbols", False):
        console.print("🧪 [yellow]TEST MODE[/yellow]: Using fixed symbol list")
        return config["fetcher"].get("test_symbols", [])

    console.print("🌐 [cyan]LIVE MODE[/cyan]: Fetching active USDT spot pairs from Binance")
    markets = exchange.load_markets()
    return [
        s for s, m in markets.items()
        if s.endswith('/USDT') and m.get('spot') and m.get('active', False)
           and not any(x in s for x in ['UP/', 'DOWN/', 'BULL/', 'BEAR/'])
    ]


def fetch_ohlcv(symbol, tf, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        return df
    except Exception as e:
        logging.error(f"{symbol} [{tf}] fetch error: {e}")
        return None


def save_to_parquet(df, tf):
    file_path = OUTPUT_DIR / f"ohlcv_{tf}.parquet"
    df.to_parquet(file_path, engine="pyarrow", index=True)


@app.command()
def main(config_path: str = "fetch.config.yaml"):
    if not Path(config_path).exists():
        console.print(f"[red]❌ Config not found: {config_path}[/red]")
        raise typer.Exit(code=1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    timeframes = config["fetcher"]["timeframes"]
    lookback = config["fetcher"]["data_limit"]
    delay = config["fetcher"].get("delay_between_requests", 0.1)

    start = time.time()
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    console.print(f"\n🕰️ [bold]Job started:[/bold] {timestamp} UTC")
    logging.info(f"Job started at {timestamp} UTC")

    symbols = fetch_symbols(config)
    console.print(f"🔁 [bold]{len(symbols)}[/bold] symbols x [bold]{len(timeframes)}[/bold] timeframes")
    logging.info(f"Symbols: {len(symbols)} | Timeframes: {timeframes}")

    for tf in timeframes:
        console.print(f"\n⏳ [blue]Timeframe:[/blue] {tf}")
        collected = []
        skipped_errors = 0
        skipped_short = 0

        for symbol in track(symbols, description=f"[{tf}] Fetching..."):
            df = fetch_ohlcv(symbol, tf, lookback)
            if df is None:
                skipped_errors += 1
                continue
            if len(df) < lookback:
                skipped_short += 1
                continue
            df.set_index(['symbol', 'timestamp'], inplace=True)
            collected.append(df)
            if delay and delay > 0:
                time.sleep(delay)

        if collected:
            full_df = pd.concat(collected)
            save_to_parquet(full_df, tf)
            console.print(f"[green]✅ Saved:[/green] {len(full_df)} rows → ohlcv_{tf}.parquet")
            logging.info(f"Saved {len(full_df)} rows to ohlcv_{tf}.parquet")
        else:
            console.print(f"[yellow]⚠️ No data saved for {tf}[/yellow]")
            logging.warning(f"No data saved for {tf}")

        console.print(f"ℹ️ Skipped in [bold]{tf}[/bold] → errors: {skipped_errors}, insufficient: {skipped_short}")
        logging.info(f"Skipped for {tf} | Errors: {skipped_errors} | Short: {skipped_short}")

    end = time.time()
    duration = round(end - start)
    console.print(f"\n⏱️ Finished in [bold]{duration // 60}m {duration % 60}s[/bold]")
    logging.info(f"Job ended. Duration: {duration}s")


if __name__ == "__main__":
    app()