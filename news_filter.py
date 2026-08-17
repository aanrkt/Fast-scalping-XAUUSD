"""Economic news filter to protect against high-impact volatility spikes."""
from datetime import datetime, timezone
from typing import List, Dict

class NewsFilter:
    def __init__(self, pre_news_buffer_mins: int = 30, post_news_buffer_mins: int = 30):
        self.pre_buffer = pre_news_buffer_mins * 60
        self.post_buffer = post_news_buffer_mins * 60
        self.events: List[Dict] = []

    def load_events(self, mock_events: List[Dict] = None):
        """Loads events. Integrate with ForexFactory/ForexLive JSON API or mock data."""
        self.events = mock_events or []

    def is_news_blocked(self, check_time: datetime = None) -> bool:
        """Returns True if within the high-impact news no-trade window."""
        now = (check_time or datetime.now(timezone.utc)).timestamp()
        for event in self.events:
            if event.get("impact") == "HIGH" and event.get("currency") in ["USD", "ALL"]:
                event_ts = event["timestamp"]
                if (event_ts - self.pre_buffer) <= now <= (event_ts + self.post_buffer):
                    return True
        return False

    def is_imminent_news(self, check_time: datetime = None, window_mins: int = 15) -> bool:
        """Checks if high-impact news is happening within `window_mins`."""
        now = (check_time or datetime.now(timezone.utc)).timestamp()
        target_window = window_mins * 60
        for event in self.events:
            if event.get("impact") == "HIGH" and event.get("currency") in ["USD", "ALL"]:
                event_ts = event["timestamp"]
                if 0 <= (event_ts - now) <= target_window:
                    return True
        return False
