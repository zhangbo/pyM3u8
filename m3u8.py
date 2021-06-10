#!/usr/bin/env python
# encoding: utf-8
import requests, sys, os, platform, time
import re
from Crypto.Cipher import AES
import multiprocessing
from retrying import retry
from retrying import RetryError

requests.packages.urllib3.disable_warnings()

class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    MOVE_UP = '\033[F'
    FLUSH_LINE = '\033[K'

    @staticmethod
    def failed(s):
        return Color.colorize(s, Color.BOLD + Color.RED)

    @staticmethod
    def success(s):
        return Color.colorize(s, Color.GREEN)
    @staticmethod
    def colorize(s, color):
        """Formats the given string with the given color"""
        return color + s + Color.END if Color.tty() else s
    @staticmethod
    def tty():
        """Returns true if running in a real terminal (as opposed to being piped or redirected)"""
        return sys.stdout.isatty()
    @staticmethod
    def moveup():
        sys.stdout.write(Color.MOVE_UP)
    @staticmethod
    def flushline():
        sys.stdout.write(Color.FLUSH_LINE)


class M3u8:
    '''
     This is a main Class, the file contains all documents.
     One document contains paragraphs that have several sentences
     It loads the original file and converts the original file to new content
     Then the new content will be saved by this class
    '''
    def __init__(self):
        '''
        Initial the custom file by self
        '''
        self.encrypt = False
        self.encryptKey = ""
        self.saveSuffix = "ts"
        self.parseSegment = "ts"
        self.attributePattern = re.compile(r'''((?:[^,"']|"[^"]*"|'[^']*')+)''')
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"
        }

    def formatter(self):
        print("*" * 50)
        return self

    def checkUrl(self, url):
        '''
        Determine if it is a available link of m3u8
        :return: bool
        '''
        if len(url) <= 0 :
            return False
        elif not url.startswith('http'):
            return False
        else:
            return True

    def parse(self, url):
        '''
        Analyze a link of m3u8
        :param url: string, the link need to analyze
        :return: list
        '''
        container = list()
        response = self.request(url, None).text.split('\n')
        for ts in response:
            if (".%s" % (self.parseSegment)) in ts:
                if self.containsSegment(container, ts):
                    continue
                container.append(ts)
            if '#EXT-X-KEY:' in ts:
                self.encrypt = True
                container.append(ts)
        return container

    def containsSegment(self, lst: [], url) -> bool:
        if lst == None or len(lst) == 0:
            return False
        return url in lst

    def getEncryptKey(self, url, line):
        '''
        Access to the secret key
        :param url: string, Access to the secret key by the url
        :return: string
        '''
        params = self.attributePattern.split(line.replace('#EXT-X-KEY:', ''))[1::2]
        keyStr = ''
        for param in params:
            name, value = param.split('=', 1)
            if name == "URI":
                quotes = ('"', "'")
                if value.startswith(quotes) and value.endswith(quotes):
                    keyStr = value[1:-1]
        finalUrl = keyStr if keyStr.startswith("http") else "{}{}".format(url, keyStr)
        encryptKey = self.request(finalUrl, None).content
        return encryptKey

    def aesDecode(self, data, key):
        '''
        Decode the data
        :param data: stream, the data need to decode
        :param key: secret key
        :return: decode the data
        '''
        crypt = AES.new(key, AES.MODE_CBC, key)
        plain_text = crypt.decrypt(data)
        return plain_text.rstrip(b'\0')

    def download(self, queue, sort, file, downPath, url, failed):
        '''
        Download the debris of video
        :param queue: the queue
        :param sort: which number debris
        :param file: the link of debris
        :param downPath: the path to save debris
        :param url: the link of m3u8
        :return: None
        '''
        queue.put(file)
        domainUrl = '/'.join(url.split("/")[:3])

        if file[:1] == '/':
            # root path
            baseUrl = domainUrl
            baseUrl += file
            baseUrl = '/'.join(baseUrl.split("/")[:-1])
        else:
            baseUrl = '/'.join(url.split("/")[:-1])
            
        if not file.startswith("http"):
            if file[:1] == '/':
                file = domainUrl + file
            else:
                file = baseUrl + '/' +file

        debrisName = "{}/{}.{}".format(downPath, sort, self.saveSuffix)
        offset = 0
        if not os.path.exists(debrisName):
            try:
                response = self.request(file, None)
                data = response.content
                if self.encrypt:
                    data = self.aesDecode(response.content, self.encryptKey)
                offset = self.skipPNGLength(data)
                if offset == 0:
                    offset = self.skipBMPLength(data)
            except (RetryError, requests.exceptions.RequestException) as e:
                failed.append(queue.get(file))
                return
            with open(debrisName, "wb") as f:
                f.write(data[offset:])
                f.flush()
        queue.get(file)

    def skipBMPLength(sekf, data: bytes) -> int:
        bmpHeaderStart = b'\x42\x4d'
        if data[:2] != bmpHeaderStart:
            return 0
        return int.from_bytes(data[10:14], byteorder='little', signed=False)

    def skipPNGLength(self, data: bytes) -> int:
        pngHeaderPattern = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
        pngEndPattern = b'\x00\x00\x00\x00\x49\x45\x4E\x44\xAE\x42\x60\x82'
        if data[:8] != pngHeaderPattern:
            return 0
        offset = 8
        while offset < len(data) - 12:
            if data[offset:offset + len(pngEndPattern)] == pngEndPattern:
                return offset + len(pngEndPattern)
            offset += 1
        return offset

    def progressBar(self, targets, failed):
        total = len(targets)
        print('---一共{}个碎片...'.format(total))
        finished = 0
        while True:
            for debrisName in targets:
                if os.path.exists(debrisName):
                    finished += 1
                    targets.remove(debrisName)
                print(Color.success("%d / %d" % (finished, total)) + " " * 5 + Color.failed("failed: %d" % (len(failed))))
                if finished + len(failed) < total:
                    Color.moveup()
            if finished + len(failed) == total:
                break

    def status_code_is_not_success(response):
        return response.status_code != 200

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_result=status_code_is_not_success)
    def request(self, url, params):
        response = requests.get(url, params=params, headers=self.headers, timeout=10, verify=False)
        # assert response.status_code == 200
        return response

    def mergefiles(self, downPath, savePath, saveName, clearDebris):
        sys = platform.system()
        if sys == "Windows":
            os.system("copy /b {}/*.ts {}/{}.{}".format(downPath, savePath, saveName, self.saveSuffix))
            if clearDebris:
                os.system("rmdir /s/q {}".format(downPath))
        else:
            os.system("cat {}/*.{}>{}/{}.{}".format(downPath, self.saveSuffix, savePath, saveName, self.saveSuffix))
            if clearDebris:
                os.system("rm -rf {}".format(downPath))

    def run(self):
        '''
        program entry, Input basic information
        '''
        downPath = str(input("碎片的保存路径, 默认./Download：")) or "./Download"
        savePath = str(input("视频的保存路径, 默认./Complete：")) or "./Complete"
        clearDebris = bool(input("是否清除碎片, 默认False：")) or False
        self.parseSegment = str(input("url解析关键字, 默认ts：")) or "ts"
        self.saveSuffix = str(input("保存片段格式, 默认ts：")) or "ts"

        while True:
            url = str(input("请输入合法的m3u8链接："))
            if self.checkUrl(url):
                break

        # create a not available folder
        if not os.path.exists(downPath):
            os.mkdir(downPath)

        if not os.path.exists(savePath):
            os.mkdir(savePath)

        # start analyze a link of m3u8
        print('---正在分析链接...')
        container = self.parse(url)
        print('---链接分析成功...')

        # run processing to do something
        print('---进程开始运行...')
        po = multiprocessing.Pool(30)
        queue = multiprocessing.Manager().Queue()
        targets = multiprocessing.Manager().list() # 本地没有的资源集合
        failed = multiprocessing.Manager().list() # 失败的资源集合
        size = 0
        if self.encrypt:
            baseUrl = '/'.join(url.split("/")[:3])
            self.encryptKey = self.getEncryptKey(baseUrl, container[0])
        for file in container:
            sort = str(size).zfill(5)
            debrisName = "{}/{}.{}".format(downPath, sort, self.saveSuffix)
            if not os.path.exists(debrisName):
                po.apply_async(self.download, args=(queue, sort, file, downPath, url, failed,))
                targets.append(debrisName)
            size += 1
        po.close()
        self.progressBar(targets, failed)
        print('---进程运行结束...')
        if len(failed) > 0:
            print('---失败资源...')
            print(failed)
            return
        # handler debris
        sys = platform.system()
        saveName = time.strftime("%Y%m%d_%H%M%S", time.localtime())

        print('---文件合并清除...')
        self.mergefiles(downPath, savePath, saveName, clearDebris)
        print('---合并清除完成...')
        print('---任务下载完成...')

if __name__ == "__main__":
    M3u8().formatter().run()