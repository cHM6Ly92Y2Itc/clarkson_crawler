import json
import requests
import os
import re
import pandas as pd
from datetime import timedelta
from datetime import datetime
import matplotlib.pylab as plt
import matplotlib.dates as mdates


class clarkson:
    def __init__(self) -> None:
        self.URL = "https://sin.clarksons.net/home/GetHomeLinksSearch?homeLinkType=2&page=1&pageSize=100&search="
        #指定数据文件保存目录
        self.data_path = ""
        #指定生成的图表目录
        self.graph_path = ""
        #自行设置代理,支持socks或http代理,如http://127.0.0.1:7890
        self.proxy = ""
        self.header = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0"
        }

    def get_data(self) -> list:

        #从html格式数据中提取数值
        def parser(s: str) -> int | float:
            s = s.replace(",", "")
            s = s.replace("(", "")
            s = s.replace(")", "")
            s = s.replace(" ", "")
            data = re.search(
                r'<b>\s*([0-9.]{0,32})\s*([a-zA-Z%$/]{0,100})\s*</b>', s)
            if data is None:
                print("parser error")
                os._exit(1)
            return float(
                data.group(1)) if data.group(2).count("$/day") < 1 else int(
                    data.group(1))

        #从网页获取json数据,并转换成dict
        #会根据self.proxy是否为空选择是否使用代理,若不使用代理有无法访问的可能
        try:
            if self.proxy != "":
                proxy = {"http": self.proxy, "https": self.proxy}
                data = json.loads(
                    requests.get(self.URL, headers=self.header,
                                 proxies=proxy).text)
            else:
                data = json.loads(
                    requests.get(self.URL, headers=self.header).text)
        except:
            print("request get error, retry without proxy ...")
            try:
                data = json.loads(
                    requests.get(self.URL, headers=self.header).text)
            except:
                print("request get error, exit")
                os._exit(1)

        return [
            parser(data["Results"][0]["Title"]),
            parser(data["Results"][1]["Title"]),
            parser(data["Results"][2]["Title"]),
            parser(data["Results"][3]["Title"]),
            parser(data["Results"][4]["Title"]),
            parser(data["Results"][5]["Title"])
        ]

    def check_update(self, label, lastdate: str, newdate: str, lastvalue,
                     newvalue, interval: int) -> tuple[bool, bool]:
        last = datetime.strptime(lastdate, r"%Y%m%d")
        new = datetime.strptime(newdate, r"%Y%m%d")
        td = timedelta(days=interval)
        ret1 = False
        ret2 = False
        if type(label) == list:
            if new - last >= td:
                print(
                    f"[Other data]lastdate: {lastdate} newdate: {newdate}, updating..."
                )
                ret1 = True
            else:
                print(
                    f"[Other data]lastdate: {lastdate} newdate: {newdate}, no update"
                )
            for i in range(0, len(lastvalue)):
                if lastvalue[i] != newvalue[i]:
                    print(
                        f"[{label[i]}]{lastvalue[i]} -> {newvalue[i]}, updating..."
                    )
                    ret2 = True
        else:
            if new - last >= td:
                print(
                    f"[{label}]lastdate: {lastdate} newdate: {newdate}, updating..."
                )
                ret1 = True
            else:
                print(
                    f"[{label}]lastdate: {lastdate} newdate: {newdate}, no update"
                )

            if lastvalue != newvalue:
                print(f"[{label}]{lastvalue} -> {newvalue}, updating...")
                ret2 = True

        return (ret1, ret2)

    def save_data(self) -> None:
        # 读取已保存数据
        congestion_idx = pd.read_csv(
            os.path.join(self.data_path, "container_port_congestion_idx.csv"))
        other_data = pd.read_csv(os.path.join(self.data_path, "clarkson.csv"))

        # 爬取新数据
        new = self.get_data()
        if new is None or len(new) == 0:
            print("get data error")
            os._exit(1)

        # 获取日期
        date = datetime.now().strftime("%Y%m%d")

        # 处理集装箱港口拥堵指数
        last_row = congestion_idx.iloc[-1].tolist()
        last_date = str(int(last_row[0]))
        last_value = last_row[1]
        update = self.check_update("congestion_idx", last_date, date,
                                   last_value, new[5], 1)
        if update[0]:
            new_df = pd.DataFrame(
                {
                    "date": int(date),
                    "container_port_congestion_idx": new[5]
                },
                index=[0])
            congestion_idx = pd.concat([congestion_idx, new_df],
                                       ignore_index=True)
            congestion_idx.to_csv(os.path.join(
                self.data_path, "container_port_congestion_idx.csv"),
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
                self.data_path, "container_port_congestion_idx.csv"),
                                  index=False)
        # 处理其他数据
        label = [
            "World Seaborne Trade", "World Seaborne Trade YoY",
            "ClarkSea Index", "Newbuild Price Index", "CO2 Emissions"
        ]
        last_row = other_data.iloc[-1].tolist()
        last_date = str(int(last_row[0]))
        last_value = last_row[1:]
        update = self.check_update(label, last_date, date, last_value,
                                   new[0:5], 7)
        if update[0]:
            new_df = pd.DataFrame(
                {
                    'date': [int(date)],
                    'world_seaborne_trade': [new[0]],
                    'growth': [new[1]],
                    'clarksea_idx': [new[2]],
                    'newbuild_price_idx': [new[3]],
                    'co2_emissions': [new[4]]
                },
                index=[0])
            other_data = pd.concat([other_data, new_df], ignore_index=True)
            other_data.to_csv(os.path.join(self.data_path, "clarkson.csv"),
                              index=False)
        elif update[1]:
            new_df = pd.DataFrame(
                {
                    'date': [int(last_date)],
                    'world_seaborne_trade': [new[0]],
                    'growth': [new[1]],
                    'clarksea_idx': [new[2]],
                    'newbuild_price_idx': [new[3]],
                    'co2_emissions': [new[4]]
                },
                index=[0])
            other_data.iloc[-1] = new_df
            other_data.to_csv(os.path.join(self.data_path, "clarkson.csv"),
                              index=False)

    def save_graph(self) -> None:
        # 读取已保存数据
        congestion_idx = pd.read_csv(
            os.path.join(self.data_path, "container_port_congestion_idx.csv"))
        other_data = pd.read_csv(os.path.join(self.data_path, "clarkson.csv"))

        date = [
            datetime.strptime(str(d), "%Y%m%d")
            for d in other_data["date"].tolist()
        ]
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
        ax1.plot(date,
                 other_data["world_seaborne_trade"],
                 color="black",
                 label="World Seaborne Trade Volume/bt")
        ax2.plot(date, other_data["growth"], color="blue", label="Yoy/%")
        fig.legend(loc="lower right",
                   frameon=True,
                   fontsize="large",
                   shadow=True,
                   facecolor="white",
                   edgecolor="black")
        plt.grid(visible=True)
        plt.savefig(os.path.join(self.graph_path, "world_seaborne_trade.png"))

        # 海运指数
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax1.set_title("ClarkSea Index")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("ClarkSea Index")
        ax1.plot(date,
                 other_data["clarksea_idx"],
                 color="black",
                 label="ClarkSea Index")
        plt.grid(visible=True)
        plt.savefig(os.path.join(self.graph_path, "clarksea_idx.png"))

        # 新造船指数
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax1.set_title("Newbuild Price Index")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Newbuild Price Index")
        ax1.plot(date,
                 other_data["newbuild_price_idx"],
                 color="black",
                 label="Newbuild Price Index")
        plt.grid(visible=True)
        plt.savefig(os.path.join(self.graph_path, "newbuild_price_idx.png"))

        # co2排放量
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax1.set_title("CO2 Emissions")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("CO2 Emissions")
        ax1.plot(date,
                 other_data['co2_emissions'],
                 color="black",
                 label="CO2 Emissions")
        plt.grid(visible=True)
        plt.savefig(os.path.join(self.graph_path, "CO2 Emissions.png"))

        # 集装箱港口拥堵指数
        date = [
            datetime.strptime(str(d), "%Y%m%d")
            for d in congestion_idx["date"].tolist()
        ]
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax1.set_title("Container Port Congestion Index/%")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Container Port Congestion Index")
        ax1.plot(date,
                 congestion_idx['container_port_congestion_idx'],
                 color="black",
                 label="Container Port Congestion Index")
        plt.grid(visible=True)
        plt.savefig(
            os.path.join(self.graph_path, "container_port_congestion_idx.png"))


if __name__ == "__main__":
    c = clarkson()
    print(f"{datetime.now()}: ------start------")
    c.save_data()
    c.save_graph()
    print(f"{datetime.now()}: ------end------")
