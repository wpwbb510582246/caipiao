#!/usr/bin/python3

# -*- coding: utf-8 -*-
# @Author   : Grayson
# @Time     : 2021-03-05 10:17
# @Email    : weipengweibeibei@163.com
# @Description  : 通用工具类
import random
import smtplib
import time
from email.mime.text import MIMEText
from typing import List

import requests
from lxml import etree
from requests.adapters import HTTPAdapter

from constant import Constants
from util.MySqlUtils import *

# 获取日志实例
logger = LoggerUtils('CommonUtils').logger

# 获取requests对象
def get_requests():
    session = requests.Session()
    # 超时自动重试3次
    session.mount('http://', HTTPAdapter(max_retries=3))
    session.mount('https://', HTTPAdapter(max_retries=3))
    return session

# 根据 url 获取响应数据
def get_response(url):
    ua_header = {
        'User-Agent': 'Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14'
    }
    return get_requests().get(url, headers=ua_header, verify=False, timeout=60)

# 获取一个页面的源代码
def get_one_page(url, encode='utf-8'):
    if encode == None:
        encode = 'utf-8'
    response = get_response(url)
    response.encoding = encode
    if response.status_code == 200:
        return response.text
    return None

# 获取双色球中奖等级
def get_two_color_ball_jackpot_level(red_check_seq_len, blue_check_seq_len):
    jackpot_level = None
    # 一等奖: 7个号码相符(6个红色球号码和1个蓝色球号码)
    if red_check_seq_len + blue_check_seq_len == 7:
        jackpot_level = '一等奖'
    # 二等奖: 6个红色球号码相符
    elif red_check_seq_len == 6:
        jackpot_level = '二等奖'
    # 三等奖: 5个红色球号码和1个蓝色球号码相符
    elif red_check_seq_len == 5 and blue_check_seq_len == 1:
        jackpot_level = '三等奖'
    # 四等奖：5个红色球号码或4个红色球号码和1个蓝色球号码相符
    elif red_check_seq_len == 5 or (red_check_seq_len == 4 and blue_check_seq_len == 1):
        jackpot_level = '四等奖'
    # 五等奖: 4个红色球号码或3个红色球号码和1个蓝色球号码
    elif red_check_seq_len == 4 or (red_check_seq_len == 3 and blue_check_seq_len == 1):
        jackpot_level = '五等奖'
    # 六等奖: 1个蓝色球号码相符
    elif blue_check_seq_len == 1:
        jackpot_level = '六等奖'
    # 未中奖
    else:
        jackpot_level = '未中奖'
    return jackpot_level

# 检查彩票中奖情况(子方法)
def check_two_color_ball_jackpot_sub(conn, lottery_info, bet_info, draw_date):
    # 中奖情况id
    tcbli_id = lottery_info[0]
    # 目标红球号码
    target_red_seq = lottery_info[2]
    # 目标蓝球号码
    target_blue_seq = lottery_info[3]

    # 获取检查结果并写入数据库
    draw_date = draw_date.replace('-', '')
    subject = f'双色球中奖信息({draw_date}期)'
    content = '双色球中奖信息如下：\n'
    for i in range(0, len(bet_info)):
        bet_info_item = bet_info[i]
        # 获取检查结果
        tcb_id = bet_info_item[0]
        bet_req_seq = bet_info_item[1].decode('utf-8').split(Constants.NUM_SEPERATOR)
        bet_blue_seq = bet_info_item[2].decode('utf-8').split(Constants.NUM_SEPERATOR)
        # 红色球命中号码
        red_check_seq = set(bet_req_seq) & set(target_red_seq)
        red_check_seq_join = Constants.NUM_SEPERATOR.join(red_check_seq)
        # 红色球命中号码数
        red_check_seq_len = len(red_check_seq)
        # 蓝色球命中号码
        blue_check_seq = set(bet_blue_seq) & set(target_blue_seq)
        blue_check_seq_join = Constants.NUM_SEPERATOR.join(blue_check_seq)
        # 蓝色球命中号码数
        blue_check_seq_len = len(blue_check_seq)
        # 奖项等级
        jackpot_level = get_two_color_ball_jackpot_level(red_check_seq_len, blue_check_seq_len)
        logger.info(f'检查结果：{tcb_id}\t{red_check_seq_len}\t{red_check_seq}\t{blue_check_seq_len}\t{blue_check_seq}\t{jackpot_level}')
        content = f'{content}第{i+1}张彩票 -> 红球命中号码：{red_check_seq_join} 命中个数：{red_check_seq_len} 蓝球命中号码：{blue_check_seq_join} 命中个数：{blue_check_seq_len} 中奖等级：{jackpot_level}\n'

        # 将检查结果写入数据库
        logger.info('将检查结果写入数据库')
        sql = 'insert into two_color_ball_res (tcb_id, tcbli_id, red_check_seq, red_check_seq_len, blue_check_seq, blue_check_seq_len, jackpot_level, create_time) values(%s, %s, %s, %s, %s, %s, %s, %s)'
        val = (tcb_id, tcbli_id, red_check_seq_join, red_check_seq_len, blue_check_seq_join, blue_check_seq_len, jackpot_level, get_current_time())
        add(conn, sql, val)

    # 发送邮件
    send_mail(subject, content)


# 获取所投注的双色球号码
def get_two_color_ball(conn, periods):
    sql = f"select id, red_num, blue_num from two_color_ball where periods='{periods}';"
    res = query(conn, sql)
    return res

# 获取最新一期双色球中奖情况
def get_latest_two_color_ball_lottery_info(conn):
    # 1.解析最新一期双色球中奖情况
    logger.info('解析最新一期双色球中奖情况')
    html = get_one_page(Constants.TWO_COLOR_BALL_API_URL)
    html = etree.HTML(html)
    html = html.xpath('//*[@id="tdata"]/tr[1]')[0]
    # 期号
    issue_num = (int)(html.xpath('./td[1]/text()')[0])
    # 红球号码
    red_seq = [
        html.xpath('./td[2]/text()')[0],
        html.xpath('./td[3]/text()')[0],
        html.xpath('./td[4]/text()')[0],
        html.xpath('./td[5]/text()')[0],
        html.xpath('./td[6]/text()')[0],
        html.xpath('./td[7]/text()')[0]
    ]
    red_seq_join = Constants.NUM_SEPERATOR.join(red_seq)
    # 蓝球号码
    blue_seq = [
        html.xpath('./td[8]/text()')[0]
    ]
    blue_seq_join = Constants.NUM_SEPERATOR.join(blue_seq)
    # 奖池奖金
    prize_pool_bonus = (str)(html.xpath('./td[10]/text()')[0].replace(',', ''))
    # 一等奖注数
    first_prize_bet_num = (str)(html.xpath('./td[11]/text()')[0])
    # 一等奖奖金
    first_prize_bonus = (str)(html.xpath('./td[12]/text()')[0].replace(',', ''))
    # 二等奖注数
    second_prize_bet_num = (str)(html.xpath('./td[13]/text()')[0])
    # 二等奖奖金
    second_prize_bonus = (str)(html.xpath('./td[14]/text()')[0].replace(',', ''))
    # 总投注额
    total_bet = (str)(html.xpath('./td[15]/text()')[0].replace(',', ''))
    # 开奖日期
    draw_date = (str)(html.xpath('./td[16]/text()')[0])
    logger.info(f'{issue_num}\t{red_seq_join}\t{blue_seq_join}\t{prize_pool_bonus}\t{first_prize_bet_num}\t{first_prize_bonus}\t{second_prize_bet_num}\t{second_prize_bonus}\t{total_bet}\t{draw_date}')

    # 2.将最新一期双色球中奖情况存入数据库
    logger.info('将最新一期双色球中奖情况存入数据库')
    logger.info('将最新一期双色球中奖情况存入数据库')
    sql = 'insert into two_color_ball_lottery_info (issue_num, red_seq, blue_seq, prize_pool_bonus, first_prize_bet_num, first_prize_bonus, second_prize_bet_num, second_prize_bonus, total_bet, draw_date, create_time) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
    val = (issue_num, red_seq_join, blue_seq_join, prize_pool_bonus, first_prize_bet_num, first_prize_bonus, second_prize_bet_num, second_prize_bonus, total_bet, draw_date, get_current_time())
    add(conn, sql, val)

    # 3.查询最新一期双色球中奖情况的id
    sql = f"select id from two_color_ball_lottery_info where issue_num='{issue_num}' order by id desc limit 1"
    res = query(conn, sql)
    tcbli_id = res[0][0]
    logger.info(f'查询最新一期双色球中奖情况的id: {tcbli_id}')
    val2 = (tcbli_id, issue_num, red_seq, blue_seq, prize_pool_bonus, first_prize_bet_num, first_prize_bonus, second_prize_bet_num, second_prize_bonus, total_bet, draw_date, get_current_time())

    # 返回数据
    return val2


# 检查彩票中奖情况
def check_two_color_ball_jackpot():
    logger.info('开始：检查彩票中奖情况')

    # 1.获取 MySQL 实例
    logger.info('1.获取 MySQL 实例')
    conn = connect(Constants.DATABASE_NAME)

    # 2.获取最新一期中奖情况
    logger.info('2.获取最新一期中奖情况')
    lottery_info = get_latest_two_color_ball_lottery_info(conn)
    draw_date = lottery_info[10]

    # 3.获取所投注的双色球号码
    logger.info('3.获取所投注的双色球号码')
    bet_info = get_two_color_ball(conn, draw_date)

    # 4.检查彩票中奖情况(子方法)
    logger.info('4.检查彩票中奖情况(子方法)')
    check_two_color_ball_jackpot_sub(conn, lottery_info, bet_info, draw_date)

    logger.info('结束：检查彩票中奖情况')


# 获取当前日期（YYYYMMDD）
def get_current_date2():
    return get_format_time(format="%Y%m%d")

# 获取当前日期（YYYY-MM-DD）
def get_current_date():
    return get_format_time(format="%Y-%m-%d")

# 获取当前时间
def get_current_time():
    return get_format_time()

# 获取指定格式的时间
def get_format_time(format="%Y-%m-%d %H:%M:%S", tmp_time=time.localtime()):
    return time.strftime(format, tmp_time)

# 从数组中随机取出一个元素，并返回取出该元素后的数组
def pick_one(arr: list):
    if (len(arr) > 0):
        index = random.randint(0, len(arr) - 1)
        item = arr[index]
        del arr[index]
        logger.info(f'item:{item} arr:{arr}')
        time.sleep(random.randint(0, 60))
        return item, arr
    logger.error(f'List is empty!')
    sys.exit(-1)

# 生成双色球号码(版本2)
def generate_two_color_ball_v2():
    # 获取 MySQL 实例
    conn = connect(Constants.DATABASE_NAME)
    # 红球最大号码
    max_red_num = 33
    # 生成的红球数量
    gen_red_num = 6
    # 蓝球最大号吗
    max_blue_num = 16
    # 生成的蓝球数量
    gen_blue_num = 1

    # 生成彩票
    current_date = get_current_date()
    current_date2 = get_current_date2()
    subject = f'双色球({current_date2}期)'
    content = '双色球号码信息如下：\n'
    for i in range(0, Constants.CAIPIAO_NUM):
        # 生成红球号码
        tmp_red_seq = [i for i in range(1, max_red_num + 1)]
        red_seq = []
        while(len(red_seq) < gen_red_num):
            item, tmp_red_seq = pick_one(tmp_red_seq)
            red_seq.append(item)
        red_seq.sort()
        # 生成蓝球号码
        tmp_blue_seq = [i for i in range(1, max_blue_num + 1)]
        blue_seq = []
        while(len(blue_seq) < gen_blue_num):
            item, tmp_blue_seq = pick_one(tmp_blue_seq)
            blue_seq.append(item)
        blue_seq.sort()
        logger.info(f"第{i + 1}张彩票号码为 -> 红球：{red_seq} 蓝球：{blue_seq}")
        content = f'{content}第{i + 1}张彩票号码为 -> 红球：{red_seq} 蓝球：{blue_seq}\n'
        # 存入数据库
        sql = 'insert into two_color_ball (red_num, blue_num, periods, generate_time) values(%s, %s, %s, %s)'
        val = (Constants.NUM_SEPERATOR.join(red_seq), Constants.NUM_SEPERATOR.join(blue_seq), current_date, get_current_time())
        add(conn, sql, val)
    # 发送邮件
    send_mail(subject, content)

# 生成双色球号码
def generate_two_color_ball():
    # 获取 MySQL 实例
    conn = connect(Constants.DATABASE_NAME)
    # 红球最大号码
    max_red_num = 33
    # 生成的红球数量
    gen_red_num = 6
    # 蓝球最大号吗
    max_blue_num = 16
    # 生成的蓝球数量
    gen_blue_num = 1

    # 生成彩票
    current_date = get_current_date()
    current_date2 = get_current_date2()
    subject = f'彩票号码(双色球) - {current_date2}期'
    content = '彩票号码信息如下：\n'
    for i in range(0, Constants.CAIPIAO_NUM):
        # 生成红球号码
        tmp_red_seq = [i for i in range(1, max_red_num + 1)]
        red_seq = random.sample(tmp_red_seq, gen_red_num)
        red_seq.sort()
        # 生成蓝球号码
        tmp_blue_seq = [i for i in range(1, max_blue_num + 1)]
        blue_seq = random.sample(tmp_blue_seq, gen_blue_num)
        blue_seq.sort()
        logger.info(f"第{i + 1}张彩票号码为 -> 红球：{red_seq} 蓝球：{blue_seq}")
        content = f'{content}第{i + 1}张彩票号码为 -> 红球：{red_seq} 蓝球：{blue_seq}\n'
        # 存入数据库
        sql = 'insert into two_color_ball (red_num, blue_num, periods, generate_time) values(%s, %s, %s, %s)'
        val = (Constants.NUM_SEPERATOR.join(red_seq), Constants.NUM_SEPERATOR.join(blue_seq), current_date, get_current_time())
        add(conn, sql, val)
    # 发送邮件
    send_mail(subject, content)

# 发送邮件
def send_mail(subject, content):
    # 设置服务器所需信息
    # 163邮箱服务器地址
    mail_host = 'mail_host'
    # 163用户名
    mail_user = 'mail_user'
    # 密码(部分邮箱为授权码)
    mail_pass = 'mail_pass'
    # 邮件发送方邮箱地址
    sender = 'sender'
    # 邮件接受方邮箱地址，注意需要[]包裹，这意味着你可以写多个邮件地址群发
    receivers = ['receivers']

    # 设置email信息
    # 邮件内容设置
    message = MIMEText(content, 'plain', 'utf-8')
    # 邮件主题
    message['Subject'] = subject
    # 发送方信息
    message['From'] = sender
    # 接受方信息
    message['To'] = receivers[0]

    # 登录并发送邮件
    try:
        smtpObj = smtplib.SMTP()
        # 连接到服务器
        smtpObj.connect(mail_host, 25)
        # 登录到服务器
        smtpObj.login(mail_user, mail_pass)
        # 发送
        smtpObj.sendmail(
            sender, receivers, message.as_string())
        # 退出
        smtpObj.quit()
        logger.info(f'邮件发送成功')
    except smtplib.SMTPException as e:
        logger.error(f'邮件发送失败: {e}')
