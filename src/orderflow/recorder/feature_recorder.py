import csv
import os


class FeatureRecorder:

    def __init__(self, filename):

        self.filename = filename

        directory = os.path.dirname(filename)

        if directory:

            os.makedirs(directory, exist_ok=True)

        self.file = open(filename, "w", newline="", encoding="utf-8")

        self.writer = None

        self.count = 0

    def write(self, feature):

        if self.writer is None:

            self.writer = csv.DictWriter(self.file, fieldnames=list(feature.keys()))

            self.writer.writeheader()

        self.writer.writerow(feature)

        self.file.flush()

        self.count += 1

    def close(self):

        self.file.close()
