import csv
import os



class SignalRecorder:


    def __init__(
        self,
        filename="data/signals.csv"
    ):


        directory = os.path.dirname(
            filename
        )


        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )


        self.file = open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        )


        self.writer = csv.DictWriter(

            self.file,

            fieldnames=[
                "timestamp",
                "signal",
                "strength",
                "reason",
                "mid"
            ]

        )


        self.writer.writeheader()



    def write(
        self,
        signal,
        feature
    ):


        self.writer.writerow(

            {

                "timestamp":
                    signal.timestamp,


                "signal":
                    signal.side.value,


                "strength":
                    signal.strength,


                "reason":
                    signal.reason,


                "mid":
                    feature["mid"]

            }

        )


        self.file.flush()



    def close(self):

        self.file.close()