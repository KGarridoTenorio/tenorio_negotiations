from datetime import datetime

FORMAT = "%Y-%m-%d %H:%M:%S"


def now_datetime() -> str:
    return datetime.now().strftime(FORMAT)


def get_start_time(player: 'Player') -> datetime:
    return datetime.strptime(player.time_start, FORMAT)
