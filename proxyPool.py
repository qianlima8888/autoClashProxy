import yaml
import argparse
import os

import sys
sys.path.append('.')

from processProxy import *
from autoPush import *
from clash import *

def parserSourceUrl(sourceFile):
    print(f"从{sourceFile}解析出以下有效的url:")
    allUrls = open(sourceFile, encoding='utf8').read().strip().splitlines()
    allUrl = []
    for url in allUrls:
        if (url.strip().startswith("#") or url.strip().startswith("//")): #删除注释
            continue
        if (url.isspace() or len(url) == 0): #删除空行
            continue
        if(url not in allUrl): #删除重复url
            allUrl.append(url)
            print(url)

    print("解析完成，共获得{}个有效url".format(len(allUrl)))
    return allUrl

parser = argparse.ArgumentParser()
parser.add_argument("--urlfile", type=str, default="source.url", help="指定下载clash订阅链接的文件")
parser.add_argument("--push", action='store_true', help="将生成的clash配置文件上传至github")
parser.add_argument("--retry", type=int, default=5, help="失败后重试的次数。默认数值为5次")
parser.add_argument("--noDownload", action='store_true', help="不下载公开节点，使用本地配置文件")

createClash = parser.add_mutually_exclusive_group(required=True)
createClash.add_argument("--local", action='store_true', help="处理本地配置文件，生成clash配置文件。")
createClash.add_argument("--download", action='store_true', help="下载公开的订阅文件，生成clash配置文件。")
createClash.add_argument("--update", action='store_true', help="对所有节点进行延迟测试后，生成配置文件。")

args = parser.parse_args()
profile = clashConfig()

if(args.noDownload and args.local):
    print("error: argument --noDownload: not allowed with argument --local")
    sys.exit(1)

if(args.noDownload and args.download):
    print("error: argument --noDownload: not allowed with argument --download")
    sys.exit(1)

bNoDownload = args.noDownload
proxies = None
configPath = f"{os.getcwd()}/{profile.file}"

#处理本地的clash配置文件，删除里面不符合要求的节点，生成配置文件。
if (args.local or bNoDownload):
    print(f"开始处理配置文件：{profile.file}。")
    proxies = yaml.load(open(profile.file, encoding='utf8').read(), Loader=yaml.FullLoader)["proxies"]
    bNoDownload = True

#如果没有指定noDownload，会根据urlfile从网上下载节点。删除里面不符合要求的节点，生成配置文件。
if ((args.download or args.update) and (not bNoDownload)):
    print("开始下载公开节点。")
    sources = parserSourceUrl(args.urlfile)
    proxies = getProxyFromSource(sources, profile.requestsProxy)

proxies = processNodes(proxies)
bSuccess = profile.creatConfig(proxies)

if (args.update):
    if (bSuccess and profile.clash.loadConfig(configPath, args.retry)): #
        bSuccess = False
        proxies = yaml.load(open(profile.file, encoding='utf8').read(), Loader=yaml.FullLoader)["proxies"]
        proxies = removeTimeoutProxy(proxies, profile) #对配置文件中的节点进行延迟测试，删除延迟不符合要求的节点。
        bSuccess = profile.creatConfig(proxies)
        if (bSuccess):
            profile.clash.loadConfig(configPath, args.retry) #延迟测试结束，加载最终生成的配置文件
    else:
        bSuccess = False

    if (not bSuccess):
        print("配置文件更新失败")

if (bSuccess and args.push):
    pushFile(profile.file, args.retry)