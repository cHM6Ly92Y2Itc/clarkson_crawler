import json
import requests
import os
import re
import shutil
from datetime import datetime
import matplotlib.pylab as plt


class clarkson:

    def __init__(self) -> None:
        self.URL = "https://sin.clarksons.net/home/GetHomeLinksSearch?homeLinkType=2&page=1&pageSize=100&search="
        #指定数据文件保存路径(可选,应当设置为文件路径,默认为工作目录下的clarkson.json文件)
        self.data_path = "clarkson.json"
        #指定生成的图表路径(可选,应当设置为目录路径,默认生成在工作目录)
        self.graph_path = "."
        #自行设置代理,支持socks或http代理,如http://127.0.0.1:7890
        self.proxy = ""
        self.header = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.0.0"
        }
        #数据文件模板
        self.template = """
        {
            "World Seaborne Trade": {
                "unit":"bt",
                "data":[]
            },
            "World Seaborne Trade YoY": {
                "unit":"%",
                "data":[]
            },
            "ClarkSea Index": {
                "unit":"$/day",
                "data":[]
            },
            "Newbuild Price Index": {
                "unit":"index",
                "data":[]
            },
            "CO2 Emissions": {
                "unit":"Million Tonnes",
                "data":[]
            },
            "Container Port Congestion Index": {
                "unit":"%",
                "data":[]
            }
        }
        """

    def get_data(self) -> dict:

        #从html格式数据中提取数值
        def parser(s: str, date: str) -> dict:
            s = s.replace(",", "")
            s = s.replace("(", "")
            s = s.replace(")", "")
            s = s.replace(" ", "")
            data = re.search(
                r'<b>\s*([0-9.]{0,32})\s*([a-zA-Z%$/]{0,100})\s*</b>', s)
            return {
                "date":
                date,
                "value":
                float(data.group(1))
                if data.group(2).count("$/day") < 1 else int(data.group(1))
            }

        #从网页获取json数据,并转换成dict
        #会根据self.proxy是否为空选择是否使用代理,若不使用代理有无法访问的可能
        if self.proxy != "":
            proxy = {"http": self.proxy, "https": self.proxy}
            data = json.loads(
                requests.get(self.URL, headers=self.header,
                             proxies=proxy).text)
        else:
            data = json.loads(requests.get(self.URL, headers=self.header).text)

        date = datetime.now().strftime(r"%Y%m%d %H:%M:%S")
        return {
            "World Seaborne Trade":
            parser(data["Results"][0]["Title"], date),
            "World Seaborne Trade YoY":
            parser(data["Results"][1]["Title"], date),
            "ClarkSea Index":
            parser(data["Results"][2]["Title"], date),
            "Newbuild Price Index":
            parser(data["Results"][3]["Title"], date),
            "CO2 Emissions":
            parser(data["Results"][4]["Title"], date),
            "Container Port Congestion Index":
            parser(data["Results"][5]["Title"], date),
        }

    def save_data(self) -> None:
        #如果数据文件不存在,自动生成数据文件并写入模板
        if not os.path.exists(self.data_path):
            with open(self.data_path, "w") as f:
                f.write(self.template)

        #防止程序出bug,备份历史数据
        shutil.copyfile(self.data_path, self.data_path + ".bak")

        #读取旧数据
        with open(self.data_path, "r") as f:
            old = json.load(f)

        #更新数据并写回
        #只有港口拥堵指数每天更新,其余只在周六更新
        with open(self.data_path, "w") as f:
            new = self.get_data()
            if datetime.now().strftime(r"%a") == "Sat":
                for key, value in new.items():
                    old[key]["data"].append(value)
            else:
                old["Container Port Congestion Index"]["data"].append(
                    new["Container Port Congestion Index"])
            json.dump(old, f, indent=4)

    def save_graph(self) -> None:

        #格式化日期,每月和每年只完整显示一次
        #输入[20230101,20230102,20230201,20230202]
        #输出[20230101,02,0201,02]
        def date_format(date: list) -> list:
            #上次处理的年
            year = ""
            #上次处理的月
            month = ""
            ret = []
            for d in date:
                if d[0:4] == year and d[4:6] == month:
                    ret.append(d[6:])
                elif d[0:4] == year:
                    month = d[4:6]
                    ret.append(d[4:])
                else:
                    year = d[0:4]
                    month = d[4:6]
                    ret.append(d)
            return ret

        #生成折线图
        def gen_graph(date: list, value: list, title: str, unit: str) -> None:
            #为了使图表x轴不过于拥挤,使用了截短的日期,但这会导致x轴出现重复值导致图表出错
            #故使用一个等长的元素不重复列表xmask替代日期作为x轴的值,并使用xsticks函数将日期作为label替代原x轴的值显示在x轴上
            #从而解决此问题
            xmask = []
            for i in range(32, len(date) + 32):
                xmask.append(str(i))
            plt.plot(xmask, value, "k.-", label=title + ": " + unit)
            plt.title(title)
            plt.xlabel("Date")
            plt.grid(True)
            plt.legend(loc="best", frameon=False)
            for x, y in zip(xmask, value):
                plt.annotate(str(y),
                             xy=(x, y),
                             textcoords='data',
                             va='baseline',
                             ha='right')
            plt.tight_layout()
            plt.xticks(xmask, date, rotation=-30)
            plt.savefig(os.path.join(self.graph_path, title + ".png"),
                        bbox_inches='tight')
            plt.close()

        #读取并提取数据
        with open(self.data_path, "r") as f:
            data = json.load(f)

        for key, value in data.items():
            #World Seaborne Trade需要特殊处理,其他可以统一处理
            if key != "World Seaborne Trade" and key != "World Seaborne Trade YoY":
                date = []
                values = []
                unit = value["unit"]
                for i in value["data"]:
                    date.append(i["date"].split(" ")[0])
                    values.append(i["value"])
                date = date_format(date)
                gen_graph(date, values, key, unit)

        #处理World Seaborne Trade数据

        date1 = []
        value1 = []
        unit1 = data["World Seaborne Trade"]["unit"]

        date2 = []
        value2 = []
        unit2 = data["World Seaborne Trade YoY"]["unit"]

        for item in data["World Seaborne Trade"]["data"]:
            date1.append(item["date"].split(" ")[0])
            value1.append(item["value"])
        date1 = date_format(date1)

        for item in data["World Seaborne Trade YoY"]["data"]:
            date2.append(item["date"].split(" ")[0])
            value2.append(item["value"])
        date2 = date_format(date2)

        xmask1 = []
        xmask2 = []
        for i in range(32, len(date1) + 32):
            xmask1.append(str(i))
        for i in range(32, len(date2) + 32):
            xmask2.append(str(i))

        #画图
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
        fig.suptitle("World Seaborne Trade")
        ax1.plot(xmask1,
                 value1,
                 "k.-",
                 label="World Seaborne Trade" + ": " + unit1)
        ax1.set_ylabel("value/bt")
        for x, y in zip(xmask1, value1):
            ax1.annotate(str(y),
                         xy=(x, y),
                         textcoords='data',
                         va='baseline',
                         ha='right')
        ax1.grid(True)

        ax2.plot(xmask2, value2, "k.-", label="YoY" + ": " + unit2)
        ax2.set_xlabel("Date")
        ax2.set_ylabel("YoY/%")
        for x, y in zip(xmask2, value2):
            ax2.annotate(str(y),
                         xy=(x, y),
                         textcoords='data',
                         va='baseline',
                         ha='right')
        ax2.grid(True)

        plt.xticks(xmask2, date2, rotation=-30)
        fig.tight_layout()
        fig.savefig(os.path.join(self.graph_path,
                                 "World Seaborne Trade" + ".png"),
                    bbox_inches='tight')


if __name__ == "__main__":
    c = clarkson()
    c.save_data()
    c.save_graph()