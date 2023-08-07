import json
import requests
import re
import os
import shutil
from datetime import datetime
import matplotlib.pylab as plt


class clarkson:

    def __init__(self) -> None:
        self.URL = "https://sin.clarksons.net/home/GetHomeLinksSearch?homeLinkType=2&page=1&pageSize=100&search="
        #指定数据文件保存路径(可选,应当设置为文件路径,默认为工作目录下的clarkson.json文件)
        self.path = "clarkson.json"
        #指定生成的图表路径(可选,应当设置为目录路径,默认生成在工作目录)
        self.graph_path = "."
        #自行设置代理,如果不需要就把requests.get中的proxies参数去掉
        self.proxy = {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }
        self.header = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0"
        }

    def get_data(self) -> dict:
        xhr = requests.get(self.URL, headers=self.header, proxies=self.proxy)
        data = json.loads(xhr.text)
        return {
            "Date":
            datetime.now().strftime(r"%Y%m%d %H:%M:%S"),
            "World Seaborne Trade":
            self.parser(data["Results"][0]["Title"]),
            "World Seaborne Trade YoY":
            self.parser(data["Results"][1]["Title"]),
            "ClarkSea Index":
            self.parser(data["Results"][2]["Title"]),
            "Newbuild Price Index":
            self.parser(data["Results"][3]["Title"]),
            "CO2 Emissions":
            self.parser(data["Results"][4]["Title"]),
            "Container Port Congestion Index":
            self.parser(data["Results"][5]["Title"]),
        }

    def parser(self, s: str) -> dict:
        s = s.replace(",", "")
        s = s.replace("(", "")
        s = s.replace(")", "")
        s = s.replace(" ", "")
        data = re.search(r'<b>\s*([0-9.]{0,32})\s*([a-zA-Z%$/]{0,100})\s*</b>',
                         s)
        return {
            "value": float(data.group(1)),
            "unit": data.group(2) if data.group(2) != "" else "index"
        }

    def save_data(self) -> None:
        #如果文件不存在,则生成一个带空列表的文件
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

        #防止程序出bug,备份历史数据
        shutil.copyfile(self.path, self.path + ".bak")

        #读取旧数据
        with open(self.path, "r") as f:
            data = json.load(f)

        #更新数据并写回
        with open(self.path, "w") as f:
            data.append(self.get_data())
            json.dump(data, f, indent=4)

    def save_graph(self) -> None:
        with open(self.path, "r") as f:
            data = json.load(f)
        date = []
        World_Seaborne_Trade = []
        World_Seaborne_Trade_YoY = []
        ClarkSea_Index = []
        Newbuild_Price_Index = []
        CO2_Emissions = []
        Container_Port_Congestion_Index = []
        for d in data:
            date.append(d["Date"].split(" ")[0])
            World_Seaborne_Trade.append(d["World Seaborne Trade"]["value"])
            World_Seaborne_Trade_YoY.append(
                d["World Seaborne Trade YoY"]["value"])
            ClarkSea_Index.append(d["ClarkSea Index"]["value"])
            Newbuild_Price_Index.append(d["Newbuild Price Index"]["value"])
            CO2_Emissions.append(d["CO2 Emissions"]["value"])
            Container_Port_Congestion_Index.append(
                d["Container Port Congestion Index"]["value"])

        #生成其他数据的折线图
        def gen_graph(date: list, value: list, title: str, unit: str) -> None:
            plt.plot(date, value, "k.-", label=title + ": " + unit)
            plt.title(title)
            plt.xlabel("Date")
            plt.grid(True)
            plt.legend(loc="best", frameon=False)
            for x, y in zip(date, value):
                plt.annotate(str(y), xy=(x, y))

            plt.savefig(os.path.join(self.graph_path, title + ".png"))
            plt.close()

        d = data[0]

        gen_graph(date, ClarkSea_Index, "ClarkSea Index",
                  d["ClarkSea Index"]["unit"])
        gen_graph(date, Newbuild_Price_Index, "Newbuild Price Index",
                  d["Newbuild Price Index"]["unit"])
        gen_graph(date, CO2_Emissions, "CO2 Emissions",
                  d["CO2 Emissions"]["unit"])
        gen_graph(date, Container_Port_Congestion_Index,
                  "Container Port Congestion Index",
                  d["Container Port Congestion Index"]["unit"])

        #生成World Seaborne Trade折线图
        fig = plt.figure()
        ax1 = fig.subplots()
        ax1.set_ylabel("World Seaborne Trade/" +
                       d["World Seaborne Trade"]["unit"],
                       color="k")
        ax1.set_xlabel("Date")
        ax2 = ax1.twinx()
        ax2.set_ylabel("YoY/%", color="r")

        ax1.plot(date,
                 World_Seaborne_Trade,
                 "k.-",
                 label="World Seaborne Trade: " +
                 d["World Seaborne Trade"]["unit"])
        ax2.plot(date,
                 World_Seaborne_Trade_YoY,
                 "r.-",
                 label="World Seaborne Trade YoY: " +
                 d["World Seaborne Trade YoY"]["unit"])

        for x, y in zip(date, World_Seaborne_Trade):
            ax1.annotate(str(y), xy=(x, y))

        for x, y in zip(date, World_Seaborne_Trade_YoY):
            ax2.annotate(str(y), xy=(x, y))

        plt.grid(True)
        plt.title("World Seaborne Trade")

        plt.savefig(os.path.join(self.graph_path, "World Seaborne Trade.png"))
        plt.close()


if __name__ == "__main__":
    c = clarkson()
    #c.save_data()
    c.save_graph()