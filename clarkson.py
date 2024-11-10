import json
import requests
import os
import re
import pandas as pd
from datetime import timedelta
from datetime import datetime
import matplotlib.pylab as plt
import matplotlib.dates as mdates
import logging

URL = "https://sin.clarksons.net/home/GetHomeLinksSearch?homeLinkType=2&page=1&pageSize=100&search="
# Get the directory of the current script
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(WORK_DIR, "log.txt")

# Configure logging
logging.basicConfig(filename=LOG_PATH,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
#指定数据文件保存目录
DATA_PATH = os.path.join(WORK_DIR, "data")
#指定生成的图表目录
GRAPH_PATH = os.path.join(WORK_DIR, "graph")
# Ensure directories exist
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(GRAPH_PATH, exist_ok=True)
#自行设置代理,支持socks或http代理,如http://127.0.0.1:7890
PROXY = "http://127.0.0.1:7890"
HEADER = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0"
}


# Log cleanup function to remove logs older than a month
def cleanup_logs():
    try:
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()

        one_month_ago = datetime.now() - timedelta(days=30)
        with open(LOG_PATH, 'w') as f:
            for line in lines:
                # Extract the date from each log line
                timestamp_str = line.split(" - ")[0]
                log_date = datetime.strptime(timestamp_str,
                                             '%Y-%m-%d %H:%M:%S,%f')
                # Write back lines that are newer than one month
                if log_date >= one_month_ago:
                    f.write(line)
    except Exception as e:
        logging.error(f"Error in cleanup_logs: {e}")


def get_data() -> list:

    #从html格式数据中提取数值
    def parser(s: str) -> float | int:
        s = s.replace(",", "")
        s = s.replace("(", "")
        s = s.replace(")", "")
        s = s.replace(" ", "")
        numbers = re.findall(r'(\d+(?:\.\d+)?)', s.replace(',', ''))
        if numbers is None:
            logging.error("parser error")
            os._exit(1)
        return float(numbers[0]) if s.count("$/day") < 1 else int(numbers[0])

    #从网页获取json数据,并转换成dict
    #会根据PROXY是否为空选择是否使用代理,若不使用代理有无法访问的可能
    try:
        if PROXY != "":
            proxy = {"http": PROXY, "https": PROXY}
            data = json.loads(
                requests.get(URL, headers=HEADER, proxies=proxy).text)
        else:
            data = json.loads(requests.get(URL, headers=HEADER).text)
    except:
        logging.warning("request get error, retry without proxy ...")
        try:
            data = json.loads(requests.get(URL, headers=HEADER).text)
        except:
            logging.error("request get error, exit")
            os._exit(1)

    return [
        parser(data["Results"][0]["Title"]),
        parser(data["Results"][1]["Title"]),
        parser(data["Results"][2]["Title"]),
        parser(data["Results"][3]["Title"]),
        parser(data["Results"][4]["Title"]),
        parser(data["Results"][5]["Title"])
    ]


def check_update(label, lastdate: str, newdate: str, lastvalue, newvalue,
                 interval: int) -> tuple[bool, bool]:
    last = datetime.strptime(lastdate, r"%Y%m%d")
    new = datetime.strptime(newdate, r"%Y%m%d")
    td = timedelta(days=interval)
    ret1 = False
    ret2 = False
    if type(label) == list:
        if new - last >= td:
            logging.info(
                f"[Other data]lastdate: {lastdate} newdate: {newdate}, updating..."
            )
            ret1 = True
        else:
            logging.info(
                f"[Other data]lastdate: {lastdate} newdate: {newdate}, no update"
            )
        for i in range(0, len(lastvalue)):
            if lastvalue[i] != newvalue[i]:
                logging.info(
                    f"[{label[i]}]{lastvalue[i]} -> {newvalue[i]}, updating..."
                )
                ret2 = True
    else:
        if new - last >= td:
            logging.info(
                f"[{label}]lastdate: {lastdate} newdate: {newdate}, updating..."
            )
            ret1 = True
        else:
            logging.info(
                f"[{label}]lastdate: {lastdate} newdate: {newdate}, no update")

        if lastvalue != newvalue:
            logging.info(f"[{label}]{lastvalue} -> {newvalue}, updating...")
            ret2 = True

    return (ret1, ret2)


def save_data() -> None:
    # 读取已保存数据
    congestion_idx = pd.read_csv(
        os.path.join(DATA_PATH, "container_port_congestion_idx.csv"))
    other_data = pd.read_csv(os.path.join(DATA_PATH, "clarkson.csv"))

    # 爬取新数据
    new = get_data()
    if new is None or len(new) == 0:
        logging.error("get data error")
        os._exit(1)

    # 获取日期
    date = datetime.now().strftime("%Y%m%d")

    # 处理集装箱港口拥堵指数
    last_row = congestion_idx.iloc[-1].tolist()
    last_date = str(int(last_row[0]))
    last_value = last_row[1]
    update = check_update("congestion_idx", last_date, date, last_value,
                          new[5], 1)
    if update[0]:
        new_df = pd.DataFrame(
            {
                "date": int(date),
                "container_port_congestion_idx": new[5]
            },
            index=[0])
        congestion_idx = pd.concat([congestion_idx, new_df], ignore_index=True)
        congestion_idx.to_csv(os.path.join(
            DATA_PATH, "container_port_congestion_idx.csv"),
                              index=False)
    elif update[1]:
        new_df = pd.DataFrame(
            {
                "date": int(last_date),
                "container_port_congestion_idx": new[5]
            },
            index=[0])
        congestion_idx.iloc[-1] = new_df
        congestion_idx.to_csv(os.path.join(
            DATA_PATH, "container_port_congestion_idx.csv"),
                              index=False)
    # 处理其他数据
    label = [
        "World Seaborne Trade", "World Seaborne Trade YoY", "ClarkSea Index",
        "Newbuild Price Index", "GHG Emissions"
    ]
    last_row = other_data.iloc[-1].tolist()
    last_date = str(int(last_row[0]))
    last_value = last_row[1:]
    update = check_update(label, last_date, date, last_value, new[0:5], 7)
    if update[0]:
        new_df = pd.DataFrame(
            {
                'date': [int(date)],
                'world_seaborne_trade': [new[0]],
                'growth': [new[1]],
                'clarksea_idx': [new[2]],
                'newbuild_price_idx': [new[3]],
                'ghg_emissions': [new[4]]
            },
            index=[0])
        other_data = pd.concat([other_data, new_df], ignore_index=True)
        other_data.to_csv(os.path.join(DATA_PATH, "clarkson.csv"), index=False)
    elif update[1]:
        new_df = pd.DataFrame(
            {
                'date': [int(last_date)],
                'world_seaborne_trade': [new[0]],
                'growth': [new[1]],
                'clarksea_idx': [new[2]],
                'newbuild_price_idx': [new[3]],
                'ghg_emissions': [new[4]]
            },
            index=[0])
        other_data.iloc[-1] = new_df
        other_data.to_csv(os.path.join(DATA_PATH, "clarkson.csv"), index=False)


def save_graph() -> None:
    # 读取已保存数据
    congestion_idx = pd.read_csv(
        os.path.join(DATA_PATH, "container_port_congestion_idx.csv"))
    other_data = pd.read_csv(os.path.join(DATA_PATH, "clarkson.csv"))

    # Convert date column to datetime objects
    other_data["date"] = pd.to_datetime(other_data["date"], format="%Y%m%d")

    # 设置x轴的主要刻度定位器和格式化器
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # 世界海运贸易量以及增长率
    fig, ax1 = plt.subplots(figsize=(20, 10))
    ax2 = ax1.twinx()
    ax1.set_title("World Seaborne Trade")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("World Seaborne Trade Volume/bt")
    ax2.set_ylabel("Yoy/%")
    # 量左轴, 增长率右轴
    ax1.plot(other_data["date"],
             other_data["world_seaborne_trade"],
             color="black",
             label="World Seaborne Trade Volume/bt")
    ax2.plot(other_data["date"],
             other_data["growth"],
             color="blue",
             label="Yoy/%")
    fig.legend(loc="lower right",
               frameon=True,
               fontsize="large",
               shadow=True,
               facecolor="white",
               edgecolor="black")
    plt.grid(visible=True)
    plt.savefig(os.path.join(GRAPH_PATH, "world_seaborne_trade.png"))

    # 海运指数
    fig, ax1 = plt.subplots(figsize=(20, 10))
    ax1.set_title("ClarkSea Index")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("ClarkSea Index")
    ax1.plot(other_data["date"],
             other_data["clarksea_idx"],
             color="black",
             label="ClarkSea Index")
    plt.grid(visible=True)
    plt.savefig(os.path.join(GRAPH_PATH, "clarksea_idx.png"))

    # 新造船指数
    fig, ax1 = plt.subplots(figsize=(20, 10))
    ax1.set_title("Newbuild Price Index")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Newbuild Price Index")
    ax1.plot(other_data["date"],
             other_data["newbuild_price_idx"],
             color="black",
             label="Newbuild Price Index")
    plt.grid(visible=True)
    plt.savefig(os.path.join(GRAPH_PATH, "newbuild_price_idx.png"))

    # ghg排放量
    fig, ax1 = plt.subplots(figsize=(20, 10))
    ax1.set_title("GHG Emissions")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("GHG Emissions")
    ax1.plot(other_data["date"],
             other_data['ghg_emissions'],
             color="black",
             label="GHG Emissions")
    plt.grid(visible=True)
    plt.savefig(os.path.join(GRAPH_PATH, "GHG Emissions.png"))

    # 集装箱港口拥堵指数
    # Convert date column to datetime objects
    congestion_idx["date"] = pd.to_datetime(congestion_idx["date"],
                                            format="%Y%m%d")

    fig, ax1 = plt.subplots(figsize=(20, 10))
    ax1.set_title("Container Port Congestion Index/%")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Container Port Congestion Index")
    ax1.plot(congestion_idx["date"],
             congestion_idx['container_port_congestion_idx'],
             color="black",
             label="Container Port Congestion Index")
    plt.grid(visible=True)
    plt.savefig(os.path.join(GRAPH_PATH, "container_port_congestion_idx.png"))


if __name__ == "__main__":
    logging.info("start")
    save_data()
    save_graph()
    cleanup_logs()
    logging.info("end")
