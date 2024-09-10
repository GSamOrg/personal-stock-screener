import os
from datetime import datetime
import pandas as pd


class DataframeCache:
    cache_dt_format: str = "%Y_%m_%d_%H_%M"

    def __init__(
        self, cache_file_location: str = "/tmp/", cache_stale_days: int = 60
    ) -> None:
        self.cache_file_location = cache_file_location
        self.cache_stale_days = cache_stale_days

    def write_cache(self, df: pd.DataFrame) -> None:
        dt = datetime.now()
        formatted_string = dt.strftime(self.cache_dt_format)
        filename = f"{formatted_string}_fin_screen.csv"
        file_full_path = os.path.join(self.cache_file_location, filename)
        df.to_csv(file_full_path, index=False)

    def _check_file_is_cache(self, filename: str) -> bool:
        if filename.endswith(".csv") and "fin_screen" in filename:
            return True
        else:
            return False

    def _get_cache_files(self) -> list[str]:
        cache_files = sorted(
            [
                os.path.join(self.cache_file_location, f)
                for f in os.listdir(self.cache_file_location)
                if self._check_file_is_cache(f)
            ],
        )
        return cache_files

    def load_cache(self) -> pd.DataFrame:
        cache_files = self._get_cache_files()
        return pd.read_csv(cache_files[-1])

    def is_stale(self) -> bool:
        cache_files = self._get_cache_files()
        if len(cache_files) == 0:
            return True
        else:
            latest_cache = cache_files[-1]
            latest_cache_date = datetime.strptime(
                latest_cache.split("fin_screen")[0].split('/')[-1][:-1], self.cache_dt_format
            )

            if (datetime.now() - latest_cache_date).days > self.cache_stale_days:
                return True
            else:
                return False
