import os
from datetime import datetime
import pandas as pd


class DataframeCache:
    def __init__(self, cache_file_location: str = "/tmp/") -> None:
        pass

    def write_cache(self, df: pd.DataFrame) -> None:
        dt = datetime.now()
        formatted_string = dt.strftime("%Y_%m_%d_%H_%M")
        filename = f'fin_screen_{formatted_string}.csv'
        pass

    def load_cache(self) -> None:
        pass