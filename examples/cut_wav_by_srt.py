# -*- coding: utf-8 -*-
"""
    @Time : 2022/12/29 11:14
    @Author : 李子
    @Url : https://github.com/kslz
"""
import add_path

from utils.tools import *


def main(srt_files="./files/input", wav_files="./files/input2", output_path="./files/output", minilen: int = 0):
    """
    假设这样一种场景，你有一组srt字幕文件和一组wav音频文件，两者一一对应且文件名除了后缀以外都相同
    比如 a.srt,b.srt... a.wav,b.wav... 。你需要通过srt文件裁切对应的wav文件
    srt文件默认存放的路径为 "./files/input"
    wav文件默认存放的路径为 "./files/input2"
    裁切后文件默认存放的路径为 "./files/output"

    :param srt_files: srt文件存放路径
    :param wav_files: wav文件存放路径
    :param output_path: 裁切后的文件的输出路径
    :param minilen: 如果一句话的文字长度短于这个值则会被跳过
    """

    file_name = 1
    srt_list = get_all_files(srt_files)
    for srt_path in srt_list:
        wav_path = srt_path.replace(srt_files, wav_files).replace(".srt", ".wav")
        file_name = cut_wav_by_srt(srt_path, wav_path, output_path, file_name, minilen)


if __name__ == "__main__":
    main(minilen=6)

    # 完整参数示例：
    # main(srt_files="./files/input", wav_files="./files/input2", output_path="./files/output", minilen=6)
