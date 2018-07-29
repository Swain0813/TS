#合并TS文件
# dirs = "D:/Program Files (x86)/Thunder Network/Network/TS/"
# mp4 = "D:/Program Files (x86)/Thunder Network/Network/mp4/"
# coding=utf-8
import asyncio
import multiprocessing
import os
import re
import time
from math import floor
from multiprocessing import Manager
import aiohttp
import requests
from lxml import html
import threading
# from src.my_lib import retry
# from src.my_lib import time_statistics

def time_statistics(fun):
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = fun(*args, **kwargs)
        t1 = time.time()
        print("Total time running %s: %s seconds" % (fun.__name__, str(t1 - t0)))
        return result

    return function_timer


def retry(retries=3):
    def _retry(fun):
        def wrapper(*args, **kwargs):
            for _ in range(retries):
                try:
                    return fun(*args, **kwargs)
                except Exception as e:
                    print("@", fun.__name__, "->", e)

        return wrapper

    return _retry

class M3U8Download:
    _path = "D:/Program Files (x86)/Thunder Network/Network/mp4/"  # 本地文件路径
    _url_seed = None  # 资源所在链接前缀
    _target_url = {}  # 资源任务目标字典
    _mode = ""
    _headers = {"User-agent": "Mozilla/5.0"}  # 浏览器代理
    _target_num = 100

    def __init__(self):
        self._ml = Manager().list()  # 进程通信列表
        if not os.path.exists(self._path):  # 检测本地目录存在否
            os.makedirs(self._path)
        exec_str = r'chcp 65001'
        os.system(exec_str)  # 先切换utf-8输出,防止控制台乱码

    def sniffing(self, url):
        self._url = url
        print("开始嗅探...")
        try:
            r = requests.get(self._url)  # 访问嗅探网址,获取网页信息
        except:
            print("嗅探失败,网址不正确")
            os.system("pause")
        else:
            tree = html.fromstring(r.content)
            # print('==='+tree)
            try:
                # source_url = tree.xpath('//video//source/@src')[0]  # 嗅探资源控制文件链接,这里只针对一个资源控制文件
                source_url = 'https://m3u8.cdnpan.com/bzjeAH24.m3u8'  # 嗅探资源控制文件链接,这里只针对一个资源控制文件
                # self._url_seed = re.split("/\w+\.m3u8", source_url)[0]  # 从资源控制文件链接解析域名
            except:
                print("嗅探失败,未发现资源")
                os.system("pause")
            else:
                self.analysis(source_url)

    def analysis(self, source_url):
        try:
            self._url_seed = re.split("/\w+\.m3u8", source_url)[0]  # 从资源控制文件链接解析域名
            with requests.get(source_url) as r:  # 访问资源控制文件,获得资源信息
                src = re.split("\n*#.+\n", r.text)  # 解析资源信息
                for sub_src in src:  # 将资源地址储存到任务字典
                    if sub_src:
                        # self._target_url[sub_src] = self._url_seed + "/" + sub_src
                        self._target_url[sub_src] =sub_src
        except Exception as e:
            print("资源无法成功解析", e)
            os.system("pause")
        else:
            self._target_num = len(self._target_url)
            print("sniffing success!!!,found", self._target_num, "url.")
            # self._mode = input(
            #     "1:-> 单进程(Low B)\n2:-> 多进程+多线程(网速开始biubiu飞起!)\n3:-> 多进程+协程(最先进的并发!!!)\n")
            self._mode = '3'

            if self._mode == "1":
                for path, url in self._target_url.items():
                    self._download(path, url)
            elif self._mode == "2" or self._mode == "3":
                self._multiprocessing()

    def _multiprocessing(self, processing_num=4):  # 多进程,多线程
        target_list = {}  # 进程任务字典,储存每个进程分配的任务
        pool = multiprocessing.Pool(processes=processing_num)  # 开启进程池
        i = 0  # 任务分配标识
        for path, url in self._target_url.items():  # 分配进程任务
            target_list[path] = url
            i += 1
            if i % 10 == 0 or i == len(self._target_url):  # 每个进程分配十个任务
                if self._mode == "2":
                    pool.apply_async(self._sub_multithreading, kwds=target_list)  # 使用多线程驱动方法
                else:
                    pool.apply_async(self._sub_coroutine, kwds=target_list)  # 使用协程驱动方法
                target_list = {}
        pool.close()  # join函数等待所有子进程结束
        pool.join()  # 调用join之前，先调用close函数，否则会出错。执行完close后不会有新的进程加入到pool
        while True:
            if self._judge_over():
                self._combine()
                break

    def _sub_multithreading(self, **kwargs):
        for path, url in kwargs.items():  # 根据进程任务开启线程
            t = threading.Thread(target=self._download, args=(path, url,))
            t.start()

    @retry()
    def _download(self, path, url):  # 同步下载方法
        # with requests.get(url, headers=self._headers) as r:
        with requests.get(url) as r:
            if r.status_code == 200:
                # print('_download========'+self._path + path.split('/').pop())
                with open(self._path + path.split('/').pop(), "wb")as file:
                    file.write(r.content)
                self._ml.append(0)  # 每成功一个就往进程通信列表增加一个值
                percent = '%.2f' % (len(self._ml) / self._target_num * 100)
                print(len(self._ml), ": ", path, "->OK", "\tcomplete:", percent, "%") # 显示下载进度
            else:
                print("+++"+path, r.status_code, r.reason)

    def _sub_coroutine(self, **kwargs):
        tasks = []
        for path, url in kwargs.items():  # 根据进程任务创建协程任务列表
            tasks.append(asyncio.ensure_future(self._async_download(path, url)))
        loop = asyncio.get_event_loop()  # 创建异步事件循环
        loop.run_until_complete(asyncio.wait(tasks))  # 注册任务列表

    async def _async_download(self, path, url):  # 异步下载方法
        # print('_async_download========' + self._path + path.split('/').pop())
        async with aiohttp.ClientSession() as session:
            # async with session.get(url, headers=self._headers) as resp:
            async with session.get(url, headers=self._headers) as resp:
                try:
                    assert resp.status == 200, "E"  # 断言状态码为200,否则抛异常,触发重试装饰器
                    # print('---path---'+path.split('/').pop())
                    with open(self._path + path.split('/').pop(), "wb")as file:
                        file.write(await resp.read())
                except Exception as e:
                    print(e)
                else:
                    self._ml.append(0)  # 每成功一个就往进程通信列表增加一个值
                    percent = '%.2f' % (len(self._ml) / self._target_num * 100)
                    print(len(self._ml), ": ", path, "->OK", "\tcomplete:", percent, "%") # 显示下载进度

    def _combine(self):  # 组合资源方法
        try:
            print("开始组合资源...")
            identification = str(floor(time.time()))
            exec_str = r'copy /b  "' + self._path + r'*.ts" "' + self._path + 'video' + identification + '.mp4"'
            os.system(exec_str)  # 使用cmd命令将资源整合
            exec_str = r'del  "' + self._path + r'*.ts"'
            os.system(exec_str)  # 删除原来的文件
        except:
            print("资源组合失败")
        else:
            print("资源组合成功!")

    def _judge_over(self):  # 判断是否全部下载完成
        if len(self._ml) == len(self._target_url):
            return True
        return False


@time_statistics
def app():
    multiprocessing.freeze_support()
    url = 'https://m3u8.cdnpan.com/YOTZa9bq.m3u8'
    m3u8 = M3U8Download()
    m3u8.sniffing(url)
    # m3u8.analysis(url)


if __name__ == "__main__":
    app()

