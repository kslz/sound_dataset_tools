# -*- coding: utf-8 -*-
"""
    @Time : 2022/12/13 21:51
    @Author : 李子
    @Url : https://github.com/kslz
"""
import sqlite3


class MyDB():
    def __init__(self, path="db/data.db"):
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    def insert_from_srt(self, text, speaker, start, end, from_video):
        self.cur.execute(f"INSERT INTO info (text, speaker ,start ,end ,from_video) \
      VALUES ('{text}', '{speaker}','{start}','{end}','{from_video}')")

    def insert_csmsc(self, file_name, text):
        self.cur.execute(f"INSERT INTO info_csmsc (file_name ,text) \
      VALUES ('{file_name}', '{text}')")
        self.con.commit()

    def select_all(self):
        cursor = self.cur.execute("SELECT id, text, start, end ,from_video from info")
        return cursor

    def select_all_video(self):
        cursor = self.cur.execute("SELECT from_video from info GROUP BY from_video")
        return cursor

    def select_wav_text(self):
        cursor = self.cur.execute("SELECT id, file_name, text from info")
        return cursor

    def select_csmsc_text(self):
        cursor = self.cur.execute("SELECT id, file_name, text from info_csmsc")
        return cursor

    def select_csmsc_output(self):
        cursor = self.cur.execute("select id,text,pinyin,loudness_avg,speed from info where LENGTH(text)>6 and "
                                  "phone_score>70 and fluency_score>70 and integrity_score>90 and speed<5 order by id")
        return cursor

    def update_speed(self, id, speed):
        self.cur.execute(f"UPDATE info set speed = {speed} where id={id}")
        self.con.commit()

    def update_loudness(self, id, loudness):
        self.cur.execute(f"UPDATE info set loudness_avg = {loudness} where id={id}")
        self.con.commit()

    def update_csmsc_speed_loudness(self, id, speed, loudness):
        self.cur.execute(f"UPDATE info_csmsc set speed={speed},loudness_avg = {loudness} where id={id}")
        self.con.commit()

    def update_score(self, id, info_dict):
        self.cur.execute(f"UPDATE info_csmsc set phone_score = {info_dict['phone_score']},"
                         f"fluency_score = {info_dict['fluency_score']},"
                         f"integrity_score = {info_dict['integrity_score']},"
                         f"tone_score = {info_dict['tone_score']},"
                         f"total_score = {info_dict['total_score']} where id={id}")
        self.con.commit()

    def update_pinyin(self, id, pinyin):
        self.cur.execute(f"UPDATE info set pinyin = '{pinyin}' where id={id}")
        self.con.commit()
