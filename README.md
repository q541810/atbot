# atbot
一个写插件究极简单的qqbot，同时专注于在qq水群~~~（大概吧）
# atBot 部署指南

## 项目简介

atBot 是一个基于 OneBot 协议的 QQ 机器人，支持智能回复、表情包识别、@消息处理等功能。

## 环境要求

- Python 3.11+
- NapCat QQ 或其他支持 OneBot 协议的框架
- 网络连接（用于访问 AI 模型 API）
- 一个良好的脑子
- 一个win/mac/windows的电脑(我还没试过esp32开发板，但理论上可行的说)
## 部署步骤

### 1. 准备工作

#### 1.1 克隆或下载项目
```bash
# 创建文件夹并进入
mkdir atbot
cd atbot
```
#### 1.2 确定python版本
```bash
python3 -V
```
若显示Python 3.11或以上，那么就开始下一步
(如果你安装了但是显示没有此命令，请重新安装python并在安装过程中勾选PATH)
#### 1.3 安装依赖库
```bash
pip install websockets toml openai requests dotenv packaging websocket-client
```
（这里遇到的问题比较多，报错了不会的建议去问ai）
## 恭喜🎉，现在的主程序部分已经好了，继续进行下一步吧
## 2.1安装napcatqq(其他onebot协议的也行)
根据https://napneko.github.io/guide/boot/Shell的教程安装napcat
## 2.2登录并配置napcat
首先，访问http://127.0.0.1:6099/webui/
然后登录(默认密码为"napcat"(不带双引号))
使用qq扫码登录后根据图文教程操作:
<img width="1169" height="753" alt="image" src="https://github.com/user-attachments/assets/0167e4ba-2f06-402b-a3eb-0f03a9a582c6" />
<img width="671" height="756" alt="image" src="https://github.com/user-attachments/assets/8342cde9-1964-4c60-8968-4325034fa11c" />
## 3.1启动！
好了，恭喜你，你已经完成了最基本的部署操作，接下来就去编辑atbot目录下的bot_config.toml吧（配置文件，必填的地方我都加上了"!!!!!"这5个感叹号以方便分辨（可以用来ctrl+f查询））
填写后我们就可以进入atbot这个目录使用python3 demo.py这段命令启动啦
# 交流群：
点击链接加入群聊【atbot1群】：https://qm.qq.com/q/QTbAS9HUSk
群号:1019465737
