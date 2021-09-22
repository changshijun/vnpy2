import multiprocessing
from time import sleep
from datetime import datetime, time
from logging import INFO

from vnpy.event import EventEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.engine import MainEngine

from vnpy.gateway.ctp import CtpGateway
from vnpy.gateway.xtp import XtpGateway
from vnpy.app.cta_strategy import CtaEngine
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.cta_strategy.base import EVENT_CTA_LOG

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True

# CTP接口连接设置
ctp_setting = {
    "用户名": "161xxx",
    "密码": "****************",
    "经纪商代码": "9999",
    "交易服务器": "180.168.146.187:10101",
    "行情服务器": "180.168.146.187:10111",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "产品信息": ""
}

# XTP接口连接设置
xtp_setting = {
    "账号": "53191000xxx",
    "密码": "********",
    "客户号": "1",
    "行情地址": "120.27.164.138",
    "行情端口": "6002",
    "交易地址": "120.27.164.69",
    "交易端口": "6001",
    "行情协议": "TCP",
    "授权码": "*****************************************"
}

# CTA策略信息
class_name = "DoubleMaStrategy"
strategy_name = "DM_rb2109"
vt_symbol = "rb2109.SHFE"
"""
class_name = "DemoMaStrategy"
strategy_name = "DM_601990"
vt_symbol = "601990.SSE"
"""
strategy_setting = {
    "fast_window": 5,
    "slow_window": 10
}

# Chinese futures market trading period (day/night)
DAY_START = time(8, 45)
DAY_END = time(20, 43)

NIGHT_START = time(20, 45)
NIGHT_END = time(2, 45)

def check_trading_period():
    """"""
    current_time = datetime.now().time()

    trading = False
    if (
        (current_time >= DAY_START and current_time <= DAY_END)
        or (current_time >= NIGHT_START)
        or (current_time <= NIGHT_END)
    ):
        trading = True

    return trading

def run_child():
    """
    Running in the child process.
    """
    SETTINGS["log.file"] = True

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # main_engine.add_gateway(XtpGateway)
    main_engine.add_gateway(CtpGateway)
    main_engine.add_app(CtaStrategyApp)
    main_engine.write_log("主引擎创建成功")

    log_engine = main_engine.get_engine("log")
    event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
    main_engine.write_log("注册日志事件监听")

    # main_engine.connect(xtp_setting, "XTP")
    # main_engine.write_log("连接XTP接口")

    main_engine.connect(ctp_setting, "CTP")
    main_engine.write_log("连接CTP接口")

    sleep(10)

    # 创建CTA策略引擎
    cta_engine = CtaEngine(main_engine, event_engine)

    # 初始化CTA策略引擎, 会依次调用init_rqdata(), load_strategy_class()等函数
    cta_engine.init_engine()

    # 创建属于我们自己的策略，首次创建成功后会将参数写入到C:\Users\Administrator\.vntrader文件夹下的cta_strategy_setting.json文件内
    if strategy_name not in cta_engine.strategies:
        main_engine.write_log(f"创建{strategy_name}策略")
        cta_engine.add_strategy(class_name, strategy_name, vt_symbol, strategy_setting)
    else:
        cta_engine.update_strategy_setting(strategy_name, strategy_setting)

    # 初始化刚创建的策略
    cta_engine.init_strategy(strategy_name)

    # 留有足够的时间来进行策略初始化
    sleep(10)

    # 启动刚创建的策略
    cta_engine.start_strategy(strategy_name)

    # cta_engine.init_all_strategies()

    # sleep(60)
    # main_engine.write_log("CTA策略全部初始化")

    # cta_engine.start_all_strategies()
    # main_engine.write_log("CTA策略全部启动")

    print("正在交易中...")

    while True:
        sleep(1)

def run_parent():
    """
    Running in the parent process.
    """
    print("启动CTA策略守护父进程")

    child_process = None

    while True:
        trading = check_trading_period()

        # Start child process in trading period
        if trading and child_process is None:
            print("启动子进程")
            child_process = multiprocessing.Process(target=run_child)
            child_process.start()
            print("子进程启动成功")

        # 非记录时间则退出子进程
        if not trading and child_process is not None:
            if not child_process.is_alive():
                child_process = None
                print("子进程关闭成功")

        sleep(5)


if __name__ == "__main__":
    run_parent()
