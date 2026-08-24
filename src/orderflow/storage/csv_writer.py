import csv
import os
from datetime import datetime


class CSVWriter:

    def __init__(self, filename):

        self.filename = filename

        exists = os.path.exists(filename)

        self.file = open(
            filename,
            "a",
            newline=""
        )

        self.writer = csv.writer(
            self.file
        )

        if not exists:
            self.writer.writerow(
                [
                    "timestamp",
                    "mid",
                    "microprice",
                    "micro_mid_diff",
                    "spread",
                    "obi1",
                    "obi5",
                    "obi10",
                ]
            )

    def write(
        self,
        mid,
        microprice,
        spread,
        obi1,
        obi5,
        obi10,
    ):

        self.writer.writerow(
            [
                datetime.utcnow().isoformat(),
                mid,
                microprice,
                microprice - mid,
                spread,
                obi1,
                obi5,
                obi10,
            ]
        )

        self.file.flush()


    def close(self):

        self.file.close()