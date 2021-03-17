# pyM3u8
Download m3u8 segments asynchronously, still work on decrypt problem

# Usage
python3 m3u8.py

**************************************************
碎片的保存路径, 默认./Download：
视频的保存路径, 默认./Complete：
是否清除碎片, 默认False：
url解析关键字, 默认ts：
保存片段格式, 默认ts：  
请输入合法的m3u8链接：

第一行是segmentTS保存的路径，没有会新建，如果里面有碎片请手动删除
第二行是最后合成的视频文件路径，没有会新建
第三行是下载完成后是否会删除Download文件夹以及所有segmentTS
第四行是下载segmentTS的url关键字，可以解析出下载链接的那种，是域名中'.'后面的特征，例如：https://puui.qpic.cn/newsapp_ls/0/13247123834/0  填 qpic即可
第五行是保存的片段格式后缀名，默认可不填
第六行是m3u8的地址，例如：https://www.baobuzz.com/m3u8/232134.m3u8

# Notice
如果下载到还剩几个片段就卡住了，是因为进程pool的workers进入死循环，重新运行一下即可。会断点续下。
