import os
import subprocess
from pathlib import Path
import json
import argparse


TARGET_BITRATE = [
    "6000k", "10000k", "14000k", "18000k", "22000k",
]

RAW_FILES = [
    "pedestrian_area_1080p25.y4m",
    # "riverbed_1080p25.y4m",
    # "rush_hour_1080p25.y4m",
]

# ENCODER = "hevc_nvenc"
ENCODER = "libx265"


class EncodingAndMeasure:
    def __init__(self, args):
        self.args = args
        self.output_path = args.output

    def encode(self, bitrate, raw_file, encoded_file):
        try:
            cmd = f'ffmpeg -y -i {raw_file} -c:v {ENCODER} -b:v {bitrate} {encoded_file}'
            subprocess.check_call(cmd, shell=True)
        except Exception as e:
            print("Error: {}".format(e))

    def __get_candidate_files(self, target_path):
        path = Path(target_path)
        candidate_files = path.glob("*.y4m")
        return candidate_files

    def run(self):
        candidate_files = self.__get_candidate_files(self.args.path)
        encoded_files = []
        for raw_file in candidate_files:
            for br in TARGET_BITRATE:
                target_file = os.path.join(self.output_path, f'{raw_file.stem}_{format(br)}.mp4')
                encoded_files.append(target_file)
                self.encode(br, raw_file, target_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='encoded and measure tool',
    )

    parser.add_argument("-p", "--path", required=True, help="set target path")
    parser.add_argument("-o", "--output", default=".", help="set output path")
    args = parser.parse_args()

    tool = EncodingAndMeasure(args)
    tool.run()