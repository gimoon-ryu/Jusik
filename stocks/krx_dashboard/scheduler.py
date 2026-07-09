from datetime import datetime, timedelta
from threading import Event, Thread

from .config import load_config
from .updater import run_update


class DailyScheduler:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.stop_event = Event()
        self.thread: Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _loop(self) -> None:
        last_run_keys: set[str] = set()
        while not self.stop_event.is_set():
            config = load_config(self.config_path)
            now = datetime.now()
            current_hm = now.strftime("%H:%M")
            today_key = now.strftime("%Y-%m-%d")
            for update_time in config.update_times:
                run_key = f"{today_key} {update_time}"
                if current_hm == update_time and run_key not in last_run_keys:
                    try:
                        run_update(self.config_path)
                    finally:
                        last_run_keys.add(run_key)
            self.stop_event.wait(20)


def next_update_label(update_times: list[str]) -> str:
    now = datetime.now()
    candidates = []
    for value in update_times:
        hour, minute = [int(part) for part in value.split(":")]
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return min(candidates).strftime("%Y-%m-%d %H:%M")

