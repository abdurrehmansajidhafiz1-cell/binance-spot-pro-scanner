"""
Time utilities for formatting dual timestamps (Pakistan Standard Time PKT + UTC).
PKT is UTC+5.
"""
from datetime import datetime, timezone, timedelta
from typing import Union, Optional

PKT_OFFSET = timedelta(hours=5)


def get_current_utc() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_to_utc(dt_input: Union[datetime, str, int, float]) -> Optional[datetime]:
    """Parse various inputs (ISO string, unix ms, datetime) to timezone-aware UTC datetime."""
    if dt_input is None:
        return None
    if isinstance(dt_input, datetime):
        if dt_input.tzinfo is None:
            return dt_input.replace(tzinfo=timezone.utc)
        return dt_input.astimezone(timezone.utc)
    if isinstance(dt_input, (int, float)):
        # If timestamp in milliseconds
        if dt_input > 1e11:
            return datetime.fromtimestamp(dt_input / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(dt_input, tz=timezone.utc)
    if isinstance(dt_input, str):
        try:
            # Handle ISO strings like 2026-09-01T16:55:00
            clean_str = dt_input.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def format_dual_time(dt_input: Optional[Union[datetime, str, int, float]] = None) -> str:
    """
    Formats a datetime into dual timestamp:
    Example: '2026-09-01 21:55:00 PKT (16:55:00 UTC)'
    """
    utc_dt = parse_to_utc(dt_input) if dt_input is not None else get_current_utc()
    if utc_dt is None:
        return "N/A"
        
    pkt_dt = utc_dt + PKT_OFFSET
    
    pkt_str = pkt_dt.strftime("%Y-%m-%d %H:%M:%S PKT")
    utc_str = utc_dt.strftime("%H:%M:%S UTC")
    
    return f"{pkt_str} ({utc_str})"


def get_pkt_hour() -> int:
    """Returns current hour in PKT (0 to 23)."""
    utc_now = get_current_utc()
    pkt_now = utc_now + PKT_OFFSET
    return pkt_now.hour
