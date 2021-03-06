# 注：该策略仅供参考和学习，不保证收益。

# !/usr/bin/env python
# -*- coding: utf-8 -*-

# 策略代码总共分为三大部分，1)PARAMS变量 2)initialize函数 3)handle_data函数
# 请根据指示阅读。或者直接点击运行回测按钮，进行测试，查看策略效果。

# 策略名称：MACD指标策略
# 策略详细介绍：https://wequant.io/study/strategy.macd.html
# 关键词：指数平滑移动均线、多空头预测。
# 方法：
# 1)利用talib库计算MACD值
# 2)MACD柱>0时买入，MACD柱<0时卖出

import numpy as np
import talib

# 阅读1，首次阅读可跳过:
# PARAMS用于设定程序参数，回测的起始时间、结束时间、滑点误差、初始资金和持仓。
# 可以仿照格式修改，基本都能运行。如果想了解详情请参考新手学堂的API文档。
PARAMS = {
    "start_time": "2015-01-01 00:00:00",
    "end_time": "2017-07-01 00:00:00",
    "commission": 0.002,  # 此处设置交易佣金
    "slippage": 0.001,  # 此处设置交易滑点
    "account_initial": {"huobi_cny_cash": 100000,
                      "huobi_cny_btc": 0},
}


# 阅读2，遇到不明白的变量可以跳过，需要的时候回来查阅:
# initialize函数是两大核心函数之一（另一个是handle_data），用于初始化策略变量。
# 策略变量包含：必填变量，以及非必填（用户自己方便使用）的变量
def initialize(context):
    # 设置回测频率, 可选："1m", "5m", "15m", "30m", "60m", "4h", "1d", "1w"
    context.frequency = "1d"
    # 设置回测基准, 比特币："huobi_cny_btc", 莱特币："huobi_cny_ltc", 以太坊："huobi_cny_eth"
    context.benchmark = "huobi_cny_btc"
    # 设置回测标的, 比特币："huobi_cny_btc", 莱特币："huobi_cny_ltc", 以太坊："huobi_cny_eth"
    context.security = "huobi_cny_btc"

    # 设置使用talib计算MACD的参数
    # 短期EMA平滑天数
    context.user_data.short_window = 12
    # 长期EMA平滑天数
    context.user_data.long_window = 26
    # DEA线平滑天数
    context.user_data.macd_window = 5
    # 历史数据要足够长，才能够拿到收敛的MACD
    context.user_data.longest_history = 100


# 阅读3，策略核心逻辑：
# handle_data函数定义了策略的执行逻辑，按照frequency生成的bar依次读取并执行策略逻辑，直至程序结束。
# handle_data和bar的详细说明，请参考新手学堂的解释文档。
def handle_data(context):
    # 获取历史数据, 取后longest_history根bar
    hist = context.data.get_price(context.security, count=context.user_data.longest_history, frequency="1d")
    if len(hist.index) < context.user_data.longest_history:
        context.log.warn("bar的数量不足, 等待下一根bar...")
        return

    # 历史收盘价
    prices = np.array(hist["close"])
    # 初始化买入卖出信号
    long_signal_triggered = False
    short_signal_triggered = False

    try:
        # talib计算MACD，返回三个数组，分别为DIF, DEA和MACD的值
        macd_tmp = talib.MACD(prices, fastperiod=context.user_data.short_window, slowperiod=context.user_data.long_window, signalperiod=context.user_data.macd_window)
        # 获取MACD值
        macd_hist = macd_tmp[2]
        # 获取最新一个MACD的值
        macd = macd_hist[-1]
        context.log.info("当前MACD为: %s" % macd)
    except:
        context.log.error("计算MACD出错...")
        return

    # macd大于0时，产生买入信号
    if macd > 0:
        long_signal_triggered = True
    # macd小于0时，产生卖出信号
    elif macd < 0:
        short_signal_triggered = True

    # 有卖出信号，且持有仓位，则市价单全仓卖出
    if short_signal_triggered:
        context.log.info("MACD小于0，产生卖出信号")
        if context.account.huobi_cny_btc >= HUOBI_CNY_BTC_MIN_ORDER_QUANTITY:
            # 卖出信号，且不是空仓，则市价单全仓清空
            context.log.info("正在卖出 %s" % context.security)
            context.log.info("卖出数量为 %s" % context.account.huobi_cny_btc)
            context.order.sell_limit(context.security, quantity=str(context.account.huobi_cny_btc), price=str(prices[-1]*0.98))
        else:
            context.log.info("仓位不足，无法卖出")
    # 有买入信号，且持有现金，则市价单全仓买入
    elif long_signal_triggered:
        context.log.info("MACD大于0，产生买入信号")
        if context.account.huobi_cny_cash >= HUOBI_CNY_BTC_MIN_ORDER_CASH_AMOUNT:
            # 买入信号，且持有现金，则市价单全仓买入
            context.log.info("正在买入 %s" % context.security)
            context.log.info("下单金额为 %s 元" % context.account.huobi_cny_cash)
            context.order.buy_limit(context.security, quantity=str(context.account.huobi_cny_cash/prices[-1]*0.98), price=str(prices[-1]*1.02))
        else:
            context.log.info("现金不足，无法下单")
    else:
        context.log.info("无交易信号，进入下一根bar")