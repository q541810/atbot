# atbot
一个写插件究极简单的qqbot，同时专注于在qq水群~~~（大概吧）（注：beta0.4.0 已重构所有代码，增加了新功能，插件系统暂时废弃）
# atBot 部署指南

### 交流群：
_群号:1019465737_

## 项目简介

atBot 是一个基于 OneBot 协议的 QQ 机器人，支持智能回复、表情包\图片识别、@消息处理等功能。

## 环境要求

- Python 3.11+
- NapCat QQ 或其他支持 OneBot 协议的框架
- 网络连接（用于访问 AI 模型 API）
- 一个良好的脑子
- 一个liunx/~~mac~~/windows的电脑
## 部署步骤

### 1. 准备工作

#### 1.1 确定python版本
```bash
python3 -V
```
若显示Python 3.11或以上，那么就开始下一步
(如果你安装了但是显示没有此命令，请重新安装python并在安装过程中勾选PATH)
#### 1.2 下载项目文件
```bash
git clone https://github.com/q541810/atbot.git
```
#### 1.3 安装依赖库
```bash
pip install websockets toml openai requests dotenv packaging websocket-client
```
（这里遇到的问题比较多，报错了不会的建议去问ai或者在群里问）
## 恭喜🎉，现在的主程序部分已经好了，继续进行下一步吧
## 2.1安装napcatqq(其他onebot协议的也行)
根据https://napneko.github.io/guide/boot/Shell 的教程安装napcat
## 2.2登录并配置napcat
首先，访问http://127.0.0.1:6099/webui/
然后登录(默认密码为"napcat"(不带双引号))
使用qq扫码登录后根据图文教程操作:
<img width="1169" height="753" alt="image" src="https://github.com/user-attachments/assets/0167e4ba-2f06-402b-a3eb-0f03a9a582c6" />
<img width="671" height="756" alt="image" src="https://github.com/user-attachments/assets/8342cde9-1964-4c60-8968-4325034fa11c" />
## 3.1启动！
好了，恭喜你，你已经完成了最基本的部署操作，接下来就去编辑atbot/config文件下的三个配置文件吧
填写后我们就可以进入atbot这个目录使用python3 bot.py这段命令启动啦

~~没经验，写的有不好之处不好求别喷~~
