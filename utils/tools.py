# -*- coding: utf-8 -*-
"""
    @Time : 2022/12/14 14:49
    @Author : 李子
    @Url : https://github.com/kslz
"""
import json
import os
import subprocess
import wave
from xml.dom.minidom import parse
import xml.dom.minidom

import pysrt
import textgrid
from pydub import silence, AudioSegment
from pydub.playback import play
from pysrt import SubRipFile

from utils.sqlitedb import MyDB


def mk_list_dirs(dir_list):
    for file_dir in dir_list:
        os.makedirs(file_dir, exist_ok=True)


def file_w(path, text, mode, encoding="UTF-8"):
    """
    用于向文件中写入

    :param path: 文件路径
    :param text: 要写入的数据
    :param mode: 写入模式 a为追加 w为覆写
    :param encoding: 文档编码格式

    """
    with open(path, mode, encoding=encoding) as f:
        f.write(text)


def get_all_files(path, need_file=None, no_file=None):
    """
    读取目录下的文件名，以列表形式返回路径

    :param path: 文件夹路径
    :param need_file: 需要的扩展名，如 .wav
    :param no_file: 需要排除的扩展名 如 .txt
    :return: 包含文件路径的列表
    """
    all_file = []
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            allpath = os.path.join(root, name)
            if need_file:
                if os.path.splitext(allpath)[1] != need_file:
                    continue
            if no_file:
                if os.path.splitext(allpath)[1] == no_file:
                    continue
            all_file.append(allpath)
    return all_file


def del_silence(mysound: AudioSegment, updb: int = 2, supplement: int = 50):
    """
    去除声音文件中的静音片段，会取开头10毫秒和结尾10毫秒计算平均响度再+updb（默认为2）
    作为音频的静音帧响度大小，低于这个响度的都会被排除，裁剪时开头和结尾会分别少裁剪
    supplement长度的音频（默认为50）当次总裁剪长度少于100毫秒时将跳过

    :param mysound: AudioSegment音频对象
    :param updb: 定义静音时提高的响度，默认为2
    :param supplement: 裁减补偿 默认为50
    :return: 裁剪静音后的AudioSegment音频对象
    """

    s = mysound[0:10] + mysound[-10:-1]
    jingyin = s.dBFS
    all_silence = silence.detect_silence(mysound, 10, jingyin + updb)
    while all_silence != []:
        if len(all_silence[-1]) <= supplement * 2:
            del all_silence[-1]
            continue
        cut_start = all_silence[-1][0] + supplement
        cut_end = all_silence[-1][1] - supplement
        if all_silence[-1][0] == 0:
            cut_start = 0
            mysound = mysound[cut_end:]
            del all_silence[-1]
            continue
        if all_silence[-1][1] == len(mysound):
            cut_end = len(mysound)
            mysound = mysound[:cut_start]
            del all_silence[-1]
            continue
        mysound = mysound[:cut_start] + mysound[cut_end:]
    return mysound


def del_silence_startend(mysound):
    """
    弃用
    去除声音文件中的静音片段，会取开头10毫秒和结尾10毫秒计算平均响度再+3作为音频的静音帧响度大小，低于这个响度的都会被排除
    :param mysound:
    :return:
    """
    s = mysound[0:10] + mysound[-10:-1]
    jingyin = s.dBFS
    all_silence = silence.detect_silence(mysound, 10, jingyin + 3)

    while all_silence != []:
        if all_silence[-1][-1] == len(mysound):
            del all_silence[-1]
            # print("跳过了尾静音")
            continue
        if all_silence[-1][0] == 0:
            del all_silence[-1]
            # print("跳过了头静音")
            continue
        mysound = mysound[:all_silence[-1][0]] + mysound[all_silence[-1][1]:]
        del all_silence[-1]
    return mysound


def del_huxi(mysound: AudioSegment, updb: int = 2, huxidb: int = -40):
    """
    去除音频中的呼吸声，会取开头10毫秒和结尾10毫秒计算平均响度再+updb（默认为2）
    作为音频的静音帧响度，寻找响度大于静音但小于huxidb（默认为-40）的音频片段
    并将其删除。

    :param mysound: AudioSegment音频对象
    :param updb: 定义静音时提高的响度，默认为2
    :param huxidb: 小于这个响度值的音频段会被定义为呼吸段
    :return: 裁剪静音后的AudioSegment音频对象
    """
    huxilist = []
    s = mysound[0:10] + mysound[-10:-1]
    jingyin = s.dBFS
    all_silence = silence.detect_nonsilent(mysound, 10, jingyin + 3)
    for voice in all_silence:
        huxi = []
        for time in range(voice[0], voice[1], 10):
            if mysound[time:time + 10].dBFS < -40:
                huxi.append(time)
            else:
                huxi = []
        if huxi == []:
            continue
        if huxi[-1] - huxi[0] <= 100:
            continue
        if mysound[voice[0]:huxi[0]].dBFS > mysound[huxi[0]:huxi[1]].dBFS:
            for i in range(huxi[0] + 20, huxi[0] + 100, 10):
                if mysound[i:i + 10].dBFS > mysound[i + 11:i + 20].dBFS:
                    huxi[0] = i
                else:
                    break
        if mysound[huxi[-1]:voice[1]].dBFS > mysound[huxi[0]:huxi[-1]].dBFS:
            for i in range(huxi[-1], huxi[-1] - 100):
                if mysound[i].dBFS > mysound[i - 1].dBFS:
                    huxi[i] = i
                else:
                    break
        if voice[1] - huxi[-1] <= 10:
            huxi[-1] = voice[-1]
        huxilist.append([huxi[0], huxi[-1]])
    while huxilist != []:
        mysound = mysound[:huxilist[-1][0]] + mysound[huxilist[-1][1]:]
        del huxilist[-1]
    return mysound


def wav2pcm(input_dir: str, out_dir: str):
    """
    将wav文件转换为pcm文件

    :param input_dir: 输入wav文件路径
    :param out_dir: 输出pcm文件路径
    """
    with open(input_dir, 'rb') as wavfile:
        wavfile.seek(44)
        # wavfile.read(44)
        ori_data = wavfile.read()  # 读出来是裸流bytes数据
        wavfile.close()
    with open(out_dir, 'wb') as pcmfile:
        pcmfile.write(ori_data)
        pcmfile.close()


def wav2pcm2(input_dir: str, out_dir: str, temp_dir: str):
    """
    将wav文件转换为pcm文件 且当音频长度小于3.1秒时通过在结尾添加静音片段，将音频延长至3.1秒

    :param input_dir: 输入wav文件路径
    :param out_dir: 输出pcm文件路径
    :param temp_dir: 临时文件存放路径
    :return:
    """

    os.makedirs(temp_dir, exist_ok=True)
    mysound = AudioSegment.from_file(input_dir)
    if len(mysound) < 3100:
        jingyinlen = 3100 - len(mysound)
        jingyin = AudioSegment.silent(jingyinlen, frame_rate=16000)
        mysound = mysound + jingyin
    temp_dir = os.path.join(temp_dir, os.path.basename(input_dir))
    mysound.export(temp_dir, format='wav')

    with open(temp_dir, 'rb') as wavfile:
        wavfile.seek(44)
        # wavfile.read(44)
        ori_data = wavfile.read()  # 读出来是裸流bytes数据
        wavfile.close()
    with open(out_dir, 'wb') as pcmfile:
        pcmfile.write(ori_data)
        pcmfile.close()


def pcm2wav(pcm_path, wav_path):
    """
    将pcm文件转换为wav文件 需按实际情况修改文件头

    :param pcm_path:
    :param wav_path:
    :return:
    """
    with open(pcm_path, 'rb') as pcmfile:
        pcmdata = pcmfile.read()
    with wave.open(wav_path, 'wb') as wavfile:
        wavfile.setparams((2, 2, 44100, 0, 'NONE', 'NONE'))
        wavfile.writeframes(pcmdata)


def wavto16kwav(input_file, output_file, sampling_rate='16000'):
    """
    使用FFMPEG修改wav文件的取样率（Sampling Rate）

    :param input_file: 输入wav文件路径
    :param output_file: 输出wav文件路径
    :param sampling_rate: 取样率 默认16000
    :return:
    """

    subprocess.run(['ffmpeg', '-y', '-f', 'wav', '-i', input_file, '-acodec', 'pcm_s16le', '-ac', '1', '-ar',
                    str(sampling_rate), '-bitexact', output_file])


def ise_ws(input_wav, textline, output_xml, appid, apisecret, apikey):
    """
    通过讯飞接口进行音频评测，并将返回的xml文件保存到本地，需自行填入鉴权信息
    注意：只支持采样率16k、位长16bit、单声道的wav或pcm音频（建议pcm）
    文档：https://www.xfyun.cn/doc/Ise/IseAPI.html

    :param input_wav: 音频文件路径
    :param textline: 音频对应文本
    :param output_xml: 输出xml存放路径
    :param appid: appid（请参考文档获取）
    :param apisecret: apisecret（请参考文档获取）
    :param apikey: apikey（请参考文档获取）
    """

    import websocket
    import datetime
    import hashlib
    import base64
    import hmac
    import json
    from urllib.parse import urlencode
    import time
    import ssl
    from wsgiref.handlers import format_date_time
    from datetime import datetime
    from time import mktime
    import _thread as thread

    STATUS_FIRST_FRAME = 0  # 第一帧的标识
    STATUS_CONTINUE_FRAME = 1  # 中间帧标识
    STATUS_LAST_FRAME = 2  # 最后一帧的标识

    #  BusinessArgs参数常量
    SUB = "ise"
    ENT = "cn_vip"
    # 中文题型：read_syllable（单字朗读，汉语专有）read_word（词语朗读）read_sentence（句子朗读）read_chapter(篇章朗读)
    # 英文题型：read_word（词语朗读）read_sentence（句子朗读）read_chapter(篇章朗读)simple_expression（英文情景反应）read_choice（英文选择题）topic（英文自由题）retell（英文复述题）picture_talk（英文看图说话）oral_translation（英文口头翻译）
    CATEGORY = "read_sentence"
    # 待评测文本 utf8 编码，需要加utf8bom 头
    TEXT = '\uFEFF' + textline

    # 直接从文件读取的方式
    # TEXT = '\uFEFF'+ open("cn/read_sentence_cn.txt","r",encoding='utf-8').read()

    class Ws_Param(object):
        # 初始化
        def __init__(self, APPID, APIKey, APISecret, AudioFile, Text):
            self.APPID = APPID
            self.APIKey = APIKey
            self.APISecret = APISecret
            self.AudioFile = AudioFile
            self.Text = Text

            # 公共参数(common)
            self.CommonArgs = {"app_id": self.APPID}
            # 业务参数(business)，更多个性化参数可在官网查看
            self.BusinessArgs = {"category": CATEGORY, "sub": SUB, "ent": ENT, "cmd": "ssb",
                                 "auf": "audio/L16;rate=16000",
                                 "aue": "raw", "text": self.Text, "ttp_skip": True, "aus": 1}

        # 生成url
        def create_url(self):
            # wws请求对Python版本有要求，py3.7可以正常访问，如果py版本请求wss不通，可以换成ws请求，或者更换py版本
            url = 'ws://ise-api.xfyun.cn/v2/open-ise'
            # 生成RFC1123格式的时间戳
            now = datetime.now()
            date = format_date_time(mktime(now.timetuple()))

            # 拼接字符串
            signature_origin = "host: " + "ise-api.xfyun.cn" + "\n"
            signature_origin += "date: " + date + "\n"
            signature_origin += "GET " + "/v2/open-ise " + "HTTP/1.1"
            # 进行hmac-sha256进行加密
            signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                     digestmod=hashlib.sha256).digest()
            signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

            authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
                self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
            authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
            # 将请求的鉴权参数组合为字典
            v = {
                "authorization": authorization,
                "date": date,
                "host": "ise-api.xfyun.cn"
            }
            # 拼接鉴权参数，生成url
            url = url + '?' + urlencode(v)

            # 此处打印出建立连接时候的url,参考本demo的时候，比对相同参数时生成的url与自己代码生成的url是否一致
            print("date: ", date)
            print("v: ", v)
            print('websocket url :', url)
            return url

    # 收到websocket消息的处理
    def on_message(ws, message):
        try:
            code = json.loads(message)["code"]
            sid = json.loads(message)["sid"]
            if code != 0:
                errMsg = json.loads(message)["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

            else:
                data = json.loads(message)["data"]
                status = data["status"]
                result = data["data"]
                if (status == 2):
                    xml = base64.b64decode(result)
                    # python在windows上默认用gbk编码，print时需要做编码转换，mac等其他系统自行调整编码
                    dxml = xml.decode("gbk")
                    print(dxml)
                    file_w(output_xml, dxml, "w")

        except Exception as e:
            print("receive msg,but parse exception:", e)

    # 收到websocket错误的处理
    def on_error(ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(ws):
        print("### closed ###")

    # 收到websocket连接建立的处理
    def on_open(ws):
        def run(*args):
            frameSize = 1280  # 每一帧的音频大小
            intervel = 0.04  # 发送音频间隔(单位:s)
            status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧

            with open(wsParam.AudioFile, "rb") as fp:
                while True:
                    buf = fp.read(frameSize)
                    # 文件结束
                    if not buf:
                        status = STATUS_LAST_FRAME
                    # 第一帧处理
                    # 发送第一帧音频，带business 参数
                    # appid 必须带上，只需第一帧发送
                    if status == STATUS_FIRST_FRAME:
                        d = {"common": wsParam.CommonArgs,
                             "business": wsParam.BusinessArgs,
                             "data": {"status": 0}}
                        d = json.dumps(d)
                        ws.send(d)
                        status = STATUS_CONTINUE_FRAME
                    # 中间帧处理
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {"business": {"cmd": "auw", "aus": 2, "aue": "raw"},
                             "data": {"status": 1, "data": str(base64.b64encode(buf).decode())}}
                        ws.send(json.dumps(d))
                    # 最后一帧处理
                    elif status == STATUS_LAST_FRAME:
                        d = {"business": {"cmd": "auw", "aus": 4, "aue": "raw"},
                             "data": {"status": 2, "data": str(base64.b64encode(buf).decode())}}
                        ws.send(json.dumps(d))
                        time.sleep(1)
                        break
                    # 模拟音频采样间隔
                    time.sleep(intervel)
            ws.close()

        thread.start_new_thread(run, ())

    # APPID、APISecret、APIKey信息在控制台——语音评测了（流式版）——服务接口认证信息处即可获取
    wsParam = Ws_Param(APPID=appid, APISecret=apisecret,
                       APIKey=apikey,
                       AudioFile=input_wav, Text=TEXT)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


def pingce_biaobei(file_path, text, output_path, access_token):
    """
    通过标贝接口进行音频评测，并将返回的json文件保存到本地，需自行填入鉴权信息
    注意：只支持采样率16k、位长16bit、单声道的pcm音频。
    标贝语音评测只支持3秒以上的音频，建议使用wav2pcm2()函数进行转换
    文档：https://www.data-baker.com/specs/file/eva_api_restful

    :param file_path: 音频文件路径
    :param text: 音频对应文本
    :param output_path: 输出json存放路径
    :param access_token: 鉴权信息（请参考文档获取）
    """

    import requests
    import base64

    with open(file_path, "rb") as f:
        # b64encode是编码，b64decode是解码
        base64_data = base64.b64encode(f.read())

    headers = {
        # Already added when you pass json= but not when you pass data=
        'Content-Type': 'application/json',
        'Host': 'openapi.data-baker.com'
    }

    json_data = {
        'access_token': access_token,
        'format': 'pcm',
        'txt': text,
        'lan': 'cn',
        'audio': str(base64_data).replace("b'", "").replace("'", ""),
    }

    response = requests.post('https://openapi.data-baker.com/cap/getCapScore', headers=headers, json=json_data)

    response_json = response.content.decode("utf-8")
    print(response_json)
    file_w(output_path, response_json, "w")


def get_score_from_xml(xml_path) -> dict:
    """
    通过读取讯飞语音评测返回的xml文件，获取分数信息

    :param xml_path: xml文件路径
    :return: dict格式的分数信息
    """
    DOMTree = xml.dom.minidom.parse(xml_path)
    collection = DOMTree.documentElement
    read_sentence = collection.getElementsByTagName("read_sentence")[1]
    phone_score = read_sentence.getAttribute("phone_score")
    fluency_score = read_sentence.getAttribute("fluency_score")
    integrity_score = read_sentence.getAttribute("integrity_score")
    tone_score = read_sentence.getAttribute("tone_score")
    total_score = read_sentence.getAttribute("total_score")
    if read_sentence.getAttribute("is_rejected") == "true":
        print(os.path.basename(xml_path))
    return {
        "phone_score": phone_score,
        "fluency_score": fluency_score,
        "integrity_score": integrity_score,
        "tone_score": tone_score,
        "total_score": total_score,
    }


def get_score_from_json(json_path) -> dict:
    """
    通过读取标贝语音评测返回的json文件，获取分数信息。
    注意：标贝分数信息不包含tone_score，且当读取到请求失败的json文件后返回的分数值都为0

    :param json_path: json文件路径
    :return: dict格式的分数信息
    """
    path = './data/'

    # 打开文件,r是读取,encoding是指定编码格式
    with open(json_path, 'r', encoding='utf-8') as fp:
        data = json.load(fp)

    if data['err_msg'] == 'SUCCESS':
        score_data = {
            "phone_score": data['result']['acc_score'],
            "fluency_score": data['result']['flu_score'],
            "integrity_score": data['result']['int_score'],
            "tone_score": 0,
            "total_score": data['result']['all_score'],
        }
    else:
        score_data = {
            "phone_score": 0,
            "fluency_score": 0,
            "integrity_score": 0,
            "tone_score": 0,
            "total_score": 0,
        }
    return score_data


def get_pinyin_from_json(json_path):
    """
    通过读取标贝语音评测返回的json文件，获取拼音信息。
    注意：标贝没有处理上声变调等情况，我觉得这没什么价值，建议改用paddlespeech的文本前端

    :param json_path: json文件路径
    :return: 本句话的拼音
    """
    # 打开文件,r是读取,encoding是指定编码格式
    with open(json_path, 'r', encoding='utf-8') as fp:
        data = json.load(fp)

    if data['err_msg'] == 'SUCCESS':
        pinyin_data = ""
        word_list = data['result']['word']
        for word in word_list:
            phone = word['phone'][0]['sym'] + word['phone'][1]['sym']
            if pinyin_data == "":
                pinyin_data = phone
            else:
                pinyin_data = pinyin_data + " " + phone
    else:
        pinyin_data = ""
    return pinyin_data.replace('_', "").replace('$0', '')


def get_textgrid_from_json(json_path, wav_path, textgrid_path):
    """
    通过读取标贝语音评测返回的json文件生成textgrid文件
    注意：因为标贝只支持3秒以上的音频，短音频需进过转换添加空白音频段才能正常识别，
    所以需要在此输入转换前的源音频段来获取音频的真正时长。

    :param json_path: json文件路径
    :param wav_path: 源wav文件路径
    :param textgrid_path: 输出textgrid文件路径
    """
    mysound = AudioSegment.from_file(wav_path)
    length = len(mysound) / 1000

    with open(json_path, 'r', encoding='utf-8') as fp:
        data = json.load(fp)

    if data['err_msg'] == 'SUCCESS':
        result = data['result']
        minTime = 0
        maxTime = length

    else:
        print(json_path)
        return

    # 读取音频文件给定最大时长
    tg = textgrid.TextGrid(minTime=minTime, maxTime=maxTime)
    # print(tg.__dict__)

    tier_words = textgrid.IntervalTier(name="words", minTime=minTime, maxTime=maxTime)  # 添加一层,命名为word层
    tier_phones = textgrid.IntervalTier(name="phones", minTime=minTime, maxTime=maxTime)  # 添加一层,命名为phone音素层

    if result['word'][0]['phone'][0]['start_time'] != 0:
        tier_words.addInterval(
            textgrid.Interval(minTime=0, maxTime=float(format(result['word'][0]['phone'][0]['start_time'], '.3f')),
                              mark='sil'))
        tier_phones.addInterval(
            textgrid.Interval(minTime=0, maxTime=float(format(result['word'][0]['phone'][0]['start_time'], '.3f')),
                              mark='sil'))

    # 添加分割线
    for word in result['word']:
        phone = word['phone'][0]['sym'] + word['phone'][1]['sym']

        phone_1 = word['phone'][0]['sym']
        phone_2 = word['phone'][1]['sym'].replace('_', "")
        phone_1_start = float(format(word['phone'][0]['start_time'], '.3f'))
        phone_1_end = float(format(word['phone'][0]['end_time'], '.3f'))
        phone_2_start = float(format(word['phone'][1]['start_time'], '.3f'))
        phone_2_end = float(format(word['phone'][1]['end_time'], '.3f'))
        if phone_1 == "$0":
            phone_1 = ""
            phone_2_start = phone_1_start
        phone_all = phone_1 + phone_2
        phone_all_start = phone_1_start
        phone_all_end = phone_2_end
        last_start_w = tier_words[-1].maxTime
        if phone_all_start - last_start_w > 0.1:
            last_start_w = phone_all_start
        last_start_p = tier_phones[-1].maxTime
        if phone_1_start - last_start_p > 0.1:
            last_start_p = phone_1_start
        if phone_all_end > maxTime:
            phone_all_end = maxTime
        if phone_2_end > maxTime:
            phone_2_end = maxTime
        tier_words.addInterval(textgrid.Interval(minTime=last_start_w, maxTime=phone_all_end, mark=phone_all))
        if phone_1 != "":
            tier_phones.addInterval(textgrid.Interval(minTime=last_start_p, maxTime=phone_1_end, mark=phone_1))
        last_start_p = tier_phones[-1].maxTime
        if phone_2_start - last_start_p > 0.1:
            last_start_p = phone_2_start
        tier_phones.addInterval(textgrid.Interval(minTime=last_start_p, maxTime=phone_2_end, mark=phone_2))

    if float(format(result['word'][-1]['phone'][1]['end_time'], '.3f')) < maxTime:
        tier_words.addInterval(
            textgrid.Interval(minTime=float(format(result['word'][-1]['phone'][1]['end_time'], '.3f')), maxTime=maxTime,
                              mark='sil'))
        tier_phones.addInterval(
            textgrid.Interval(minTime=float(format(result['word'][-1]['phone'][1]['end_time'], '.3f')), maxTime=maxTime,
                              mark='sil'))

    # 添加到tg对象中
    tg.tiers.append(tier_words)
    tg.tiers.append(tier_phones)

    # print(tg.__dict__)
    # 写入保存
    tg.write(textgrid_path)


def check_start_ok(start_time, mysound, dbfs=-50):
    """
    剪映生成的字幕开始位置经常过于靠后，此函数用于检查起始位置是否是静音帧，
    如果不是则向前寻找静音帧直到音频开头，静音帧标准默认为-50，请按需修改

    :param start_time: 字幕中本句的起始位置
    :param mysound: AudioSegment音频对象
    :param dbfs: 静音帧响度定义
    :return: 正确的开始时间
    """

    if mysound[start_time:start_time + 10].dBFS > dbfs:
        for new_start_time in range(start_time, 0, -10):
            if mysound[new_start_time:new_start_time + 10].dBFS < dbfs:
                return new_start_time - 10
    else:
        return start_time


def cut_long_end(end_time, mysound, dbfs=-50):
    """
    剪映生成的字幕结束位置经常过于靠后，此函数用于检查结束位置是否有过长的静音帧，
    如果是则向前寻找非静音帧直到音频开头，寻找到后会向后50毫秒作为补偿。
    默认静音帧响度标准为-50，请按需修改

    :param end_time: 字幕中本句的结束位置
    :param mysound: AudioSegment音频对象
    :param dbfs: 静音帧响度定义
    :return: 正确的结束时间
    """

    new_end_time = end_time
    for new_end_time in range(end_time, 0, -10):
        if mysound[new_end_time - 10:new_end_time].dBFS >= dbfs:
            break
    if new_end_time + 50 < end_time:
        return new_end_time + 50
    return end_time


def get_hebing(subs: SubRipFile, index, hebing_time=35):
    """
    剪映生成的字幕经常出现在很短的空隙中截断，导致两句之间没有间隔或间隔很小，
    本函数可以将这种零碎的字幕段合并成一个，并返回这段字幕的文字和结束的字幕节点

    :param subs: pysrt的SubRipFile对象
    :param index: 当前字幕节点
    :param hebing_time: 当两句字幕间隔小于这个值时合并这两个字幕，默认值为35，单位毫秒
    :return: 合并后这段字幕的文字 , 结束的字幕节点
    """
    text = ""
    for i in range(index, len(subs)):
        text += subs[i].text
        # if subs[i + 1].start.ordinal - subs[i].end.ordinal > hebing_time:
        #     return text, i
        try:
            if subs[i + 1].start.ordinal - subs[i].end.ordinal > hebing_time:
                return text, i
        except:
            return text, i


def cut_wav_by_srt(srt_path, wav_path, out_path, start_name: int = 1, minlen=0):
    """
    通过srt文件裁切音频文件

    :param srt_path: srt文件位置
    :param wav_path: 源音频文件位置
    :param out_path: 输出wav和标记文件位置
    :param start_name: 作为文件名的整数，裁出的音频段会以此为名然后逐渐递增
    :param minlen: 短于这个长度的字段会被跳过

    :return: 最后导出的文件名+1
    """
    mysound = AudioSegment.from_file(wav_path)
    # file_name = os.path.basename(srt_path)
    # file_name = os.path.splitext(file_name)[0]
    subs = pysrt.open(srt_path)
    # print_srt_text_length(subs)

    subs2 = []
    index = -1
    for i in range(len(subs)):
        # subs[i].text = fix_text(subs[i].text)
        # print(index)
        if i <= index:
            continue
        try:
            subs[i + 1]
        except:
            subs[i].start.ordinal = check_start_ok(subs[i].start.ordinal, mysound)
            subs[i].end.ordinal = cut_long_end(subs[i].end.ordinal, mysound)
            subs2.append(subs[i])
            break

        if subs[i + 1].start.ordinal - subs[i].end.ordinal > 35:
            subs[i].start.ordinal = check_start_ok(subs[i].start.ordinal, mysound)
            subs[i].end.ordinal = cut_long_end(subs[i].end.ordinal, mysound)
            subs2.append(subs[i])
        else:
            text, index = get_hebing(subs, i)
            line = subs[i]
            line.text = text
            line.end.ordinal = subs[index].end.ordinal
            line.start.ordinal = check_start_ok(line.start.ordinal, mysound)
            line.end.ordinal = cut_long_end(line.end.ordinal, mysound)
            subs2.append(line)
    os.makedirs(out_path, exist_ok=True)
    # i = 1
    labels = ""
    for sub in subs2:
        if len(sub.text) < minlen:
            continue
        mysound[sub.start.ordinal:sub.end.ordinal].export(os.path.join(out_path, str(start_name) + ".wav"),
                                                          format="wav")
        labels = labels + str(start_name) + "|" + sub.text + "\n"
        start_name += 1

    file_w(os.path.join(out_path, "labels.txt"), labels, "a")

    return start_name

    # add_to_dataset(mydb, subs2, file_name)
    # mydb.con.commit()
