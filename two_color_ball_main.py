#!/usr/bin/python3  

# -*- coding: utf-8 -*-
# @Author   : Grayson
# @Time     : 2021-03-05 09:35
# @Email    : weipengweibeibei@163.com
# @Description  : 彩票号码生成器

from apscheduler.schedulers.blocking import BlockingScheduler

from util.CommonUtils import generate_two_color_ball_v2, \
    check_two_color_ball_jackpot, LoggerUtils

# 获取日志实例
logger = LoggerUtils('main').logger

if __name__ == '__main__':
    logger.info('程序启动')

    # 每周二、周四、周日0:00生成双色球号码
    logger.info('添加定时任务：每周二、周四、周日0:00生成双色球号码')
    scheduler = BlockingScheduler()
    scheduler.add_job(generate_two_color_ball_v2, 'cron', day_of_week='0,2,4', hour='0')

    # 每周二、周四、周日22:00检查彩票中奖情况
    logger.info('添加定时任务：每周二、周四、周日22:00检查彩票中奖情况')
    scheduler.add_job(check_two_color_ball_jackpot, 'cron', day_of_week='0,2,4', hour='22')

    # 启动定时任务
    logger.info('定时任务启动')
    scheduler.start()

    logger.info('程序结束')