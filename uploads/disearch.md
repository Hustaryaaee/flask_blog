dirsearch是一种高级的命令行工具，旨在对web服务器中的目录和文件进行暴力破解。

```none
git clone https://github.com/maurosoria/dirsearch.git
cd dirsearch
python3 dirsearch.py -u <URL> -e <EXTENSION>
```

也可以使用此别名直接发送到代理
`python3 /path/to/dirsearch/dirsearch.py --http-proxy=localhost:8080`

## 选项

```none
选项:
  -h, --help            显示此帮助消息并退出

  Mandatory:
    -u URL, --url=URL   URL目标
    
    -L URLLIST, --url-list=URLLIST
                        URL列表目标
                        
    -e EXTENSIONS, --extensions=EXTENSIONS
                        以逗号分隔的扩展列表（示例：php、asp）
                        
    -E, --extensions-list
                        使用公共扩展的预定义列表

  Dictionary Settings:
    -w WORDLIST, --wordlist=WORDLIST
                        自定义单词表（用逗号分隔）
    -l, --lowercase
    -f, --force-extensions
                        强制扩展每个单词表条目（如DirBuster）

  常规设置:
    -s DELAY, --delay=DELAY
                        请求之间的延迟（浮点数）
                        
    -r, --recursive     递归暴力
    
    -R RECURSIVE_LEVEL_MAX, --recursive-level-max=RECURSIVE_LEVEL_MAX
                        最大递归级别（子目录）（默认值：1[仅限根目录+1目录]）
                        
    --suppress-empty, --suppress-empty
    --scan-subdir=SCANSUBDIRS, --scan-subdirs=SCANSUBDIRS
                        扫描给定-u |--url的子目录（分开逗号）
                        
    --exclude-subdir=EXCLUDESUBDIRS, --exclude-subdirs=EXCLUDESUBDIRS
                        在递归过程中排除下列子目录扫描（用逗号分隔）
                        
    -t THREADSCOUNT, --threads=THREADSCOUNT
                        线程数
                        
    -x EXCLUDESTATUSCODES, --exclude-status=EXCLUDESTATUSCODES
                        排除状态代码，用逗号分隔（例如：301，500个）
                        
    --exclude-texts=EXCLUDETEXTS
                        用逗号分隔的文本排除响应(示例: "Not found", "Error")
                        
    --exclude-regexps=EXCLUDEREGEXPS
                        按regexp排除响应，用逗号分隔(示例： "Not foun[a-z]{1}", "^Error$")
                        
    -c COOKIE, --cookie=COOKIE
    
    --ua=USERAGENT, --user-agent=USERAGENT 
   						用户代理
   						
    -F, --follow-redirects 
    					--遵循重定向
    					
    -H HEADERS, --header=HEADERS 页眉，--页眉=页眉
                        要添加的标题 (example: --header "Referer:
                        example.com" --header "User-Agent: IE"
                        
    --random-agents, --random-user-agents 
    					随机代理，--随机用户代理

  连接设置:
    --timeout=TIMEOUT   连接超时
    
    --ip=IP             将名称解析为IP地址
    
    --proxy=HTTPPROXY, --http-proxy=HTTPPROXY
                        Http代理 (example: localhost:8080
                        
    --http-method=HTTPMETHOD
                        要使用的方法，默认值：GET，也可能是：HEAD；POST
                        
    --max-retries=MAXRETRIES
    					最大重试次数
    					
    -b, --request-by-hostname
                        默认情况下，dirsearch将通过IP请求速度。
						这将强制按主机名请求

 报告:
    --simple-report=SIMPLEOUTPUTFILE 简单输出文件
                        只找到路径
                        
    --plain-text-report=PLAINTEXTOUTPUTFILE 纯文本输出文件
                        找到带有状态代码的路径
                        
    --json-report=JSONOUTPUTFILE JSON输出文件
```

## 支持的操作系统

- Windows XP/7/8/10

- GNU/Linux

- MacOSX

- ## 特征

  - 多线程
  - 保持活跃的联系
  - 支持多种扩展（-e |-扩展asp，php）
  - 支持每种HTTP方法
  - 报告（纯文本，JSON）
  - 启发式检测无效网页
  - 递归暴力破解
  - 子目录暴力破解
  - 力扩展
  - HTTP代理支持
  - HTTP cookie和标头支持
  - 用户代理随机化
  - 批量处理
  - 请求延迟
  - 通过主机名强制请求的选项
  - 选择排除文字回复
  - 选择排除正则表达式的响应（例如：“ Not foun [az] {1}”））
  - 强制时从扩展名中删除点的选项（–nd，示例为％EXT％而不是example。％EXT％）
  - 仅显示响应长度范围为（–min和–max）的项目的选项
  - 可以将响应代码列入白名单（-i 200,500）
  - 可以将响应代码列入黑名单（-x 404,403）
  - 从控制台删除输出的选项（-q，将输出保留到文件）
  - 向文件名中添加不带点的自定义后缀的选项（-后缀.BAK，.old，例如。％EXT %% SUFFIX％）

## 关于词表

词典必须是文本文件。除了使用特殊词％EXT％以外，每一行都将按此方式处理，这将为作为参数传递的每个扩展名（-e | --extension）生成一个条目。

例：

- 例/
- 例如。％EXT％

传递扩展名“ asp”和“ aspx”将生成以下字典：

- 例/
- example.asp
- example.aspx

您也可以使用-f | --force-extensions切换以将扩展名附加到单词表中的每个单词（例如DirBuster）。

## 如何使用

一些使用dirsearch的示例-这些是最常见的参数。如果需要全部，只需使用“ -h”参数。

```none
python3 dirsearch.py -e php,txt,zip -u https://target
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --recursive -R 2
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --recursive -R 4 --scan-subdirs=/,/wp-content/,/wp-admin/
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --exclude-texts=This,AndThat
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt -H "User-Agent: IE"
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt -t 20
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --random-agents
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --json-report=reports/target.json
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --simple-report=reports/target-paths.txt
python3 dirsearch.py -e php,txt,zip -u https://target -w db/dicc.txt --plain-text-report=reports/target-paths-and-status.json
```

## 支持Docker

### 安装Docker Linux

安装Docker

```none
curl -fsSL https://get.docker.com | bash
```

> 要使用docker，您需要超级用户权限

### 建立映像目录搜寻

创建图像

```none
docker build -t "dirsearch:v0.3.8" .
```

> **dirsearch**这是图像的名称，而**v0.3.8**是版本

### 使用 dirsearch

用于

```none
docker run -it --rm "dirsearch:v0.3.8" -u target -e php,html,png,js,jpg
```

> 目标是站点或IP