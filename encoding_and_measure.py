import os
import subprocess
from pathlib import Path
import json
import argparse
import pandas as pd


TARGET_BITRATE = [
    "6000k", "10000k", "14000k", "18000k", "22000k",
]

# ENCODER = "hevc_nvenc"
ENCODER = "libx265"

FFMPEG_PATH = "../resource/ffmpeg"
VMAF_MODEL = "model/vmaf_v0.6.1.json"
UVQ_PATH = "../uvq"

class EncodingAndMeasure:
    def __init__(self, args):
        self.args = args
        self.output_path = args.output
        self.test_result = []

    def __encode(self, bitrate, raw_file, encoded_file):

        try:
            cmd = f'ffmpeg -y -loglevel 0 -i {raw_file} -c:v {ENCODER} -b:v {bitrate} {encoded_file}'
            subprocess.check_call(cmd, shell=True)
        except Exception as e:
            print("Error: {}".format(e))

    def __get_candidate_files(self, target_path):
        path = Path(target_path)
        return list(path.glob("*.y4m"))

    def __parse_result(self, target_name, result_file, uvq_score):
        try:
            new_result = {}
            new_result['target_name'] = Path(target_name).name
            new_result['uvq_score'] = round(float(uvq_score), 3)

            with open(result_file) as f:
                json_data = json.load(f)

            ffmpeg_measure_result = json_data['pooled_metrics']
            new_result['psnr_y'] = round(ffmpeg_measure_result['psnr_y']['mean'], 3)
            new_result['ms_ssim'] = round(ffmpeg_measure_result['float_ms_ssim']['mean'], 5)
            new_result['vmaf'] = round(ffmpeg_measure_result['vmaf']['mean'], 2)
            self.test_result.append(new_result)
        except Exception as e:
            print("Parse result Error: {}".format(e))

    def __measure(self, src, dst, vmaf_model):
        print(f"[Measuring] {dst}")
        dst_path_file = Path(dst)
        result_file = dst_path_file.with_suffix(".json")
        cmd_ffmpeg_vmaf = f'{FFMPEG_PATH} -y -loglevel 0 -i {src} -i {dst} -filter_complex "[0:v]setpts=PTS-STARTPTS[distorted];[1:v]setpts=PTS-STARTPTS[reference];[distorted][reference]'
        cmd_ffmpeg_vmaf += f'libvmaf=log_path={result_file}:log_fmt=json:model=path={vmaf_model}:n_threads=18:feature='
        cmd_ffmpeg_vmaf += f"'name=psnr|name=float_ms_ssim'"
        cmd_ffmpeg_vmaf += f'" -f null -'
        subprocess.check_call(cmd_ffmpeg_vmaf, shell=True)

        cmd_uvq = f'python3 {os.path.join(UVQ_PATH, "uvq_inference.py")} {dst}'
        out = subprocess.check_output(cmd_uvq, shell=True).decode('utf-8').replace('\r', '').replace('\n', '')

        self.__parse_result(dst, result_file, out)


    def __write_result_to_csv(self):
        df = pd.DataFrame(self.test_result)
        df.to_csv(os.path.join(self.output_path, "result.csv"), index=False)

    def run(self):
        candidate_files = self.__get_candidate_files(self.args.path)
        encoded_files = []

        total_cases = len(candidate_files) * len(TARGET_BITRATE)
        idx = 1
        for raw_file in candidate_files:
            for br in TARGET_BITRATE:
                print(f"==== {idx}/{total_cases} ====")
                target_file = os.path.join(self.output_path, f'{raw_file.stem}_{format(br)}.mp4')
                encoded_files.append(target_file)
                self.__encode(br, raw_file, target_file)
                self.__measure(raw_file, target_file, VMAF_MODEL)
                idx += 1

        self.__write_result_to_csv()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='encoded and measure tool',
    )

    parser.add_argument("-p", "--path", required=True, help="set target path")
    parser.add_argument("-o", "--output", default=".", help="set output path")
    args = parser.parse_args()

    tool = EncodingAndMeasure(args)
    tool.run()