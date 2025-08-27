# atbot

一个写插件究极简单的qqbot，同时专注于在qq水群~~~（大概吧）（注：beta0.4.0 已重构所有代码，增加了新功能，插件系统暂时废弃）

# atBot 部署指南u

## 项目简介

atBot 是一个基于 OneBot 协议的 QQ 机器人，支持智能回复、表情包\图片识别、@消息处理等功能。

# 部署

## 环境要求

- Python 3.11+
- NapCat QQ 或其他支持 OneBot 协议的框架
- 网络连接（用于访问 AI 模型 API）
- 一个良好的脑子
- 一个liunx/windows的电脑

### 确定python版本

```bash
python -V
```

若显示Python 3.11或以上，那么就开始下一步
(如果你安装了但是显示没有此命令，请重新安装python并在安装过程中勾选PATH)
## 使用uv工具部署

### 克隆项目

```bash
git clone https://github.com/q541810/atbot.git
cd atbot
```

### 安装uv
```bash
pip install uv
```
### 使用uv安装依赖
```bash
uv sync
```

*安装完成*
## Python直接部署（传统方法）
## 【注：若您已经使用了uv部署，请跳过python直接部署的步骤，开始安装napcat】
### 下载项目文件

```bash
git clone https://github.com/q541810/atbot.git
```

### 创建虚拟环境

```bash
python -m venv .venv
```

### 激活虚拟环境安装依赖

```bash
# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate

# 激活虚拟环境 (Windows PowerShell)
.\.venv\Scripts\activate
```

### 安装依赖

```bash
pip3 install -r requirements.txt
```

*安装完成*

## 恭喜🎉，现在的主程序部分已经好了，继续进行下一步吧

### 安装napcatqq(其他onebot协议的也行)
根据<https://napneko.github.io/guide/boot/Shell> 的教程安装napcat

### 登录并配置napcat

首先，访问<http://127.0.0.1:6099/webui/>
然后登录(默认密码为"napcat"(不带双引号))
使用qq扫码登录后根据图文教程操作:
![image](https://github.com/user-attachments/assets/0167e4ba-2f06-402b-a3eb-0f03a9a582c6)
![image](https://github.com/user-attachments/assets/8342cde9-1964-4c60-8968-4325034fa11c)

## 启动

启动：
若您使用了uv部署方法，请使用:

```bash
uv run bot.py

```
若是传统的python直接部署的方法，请你使用:

```bash
python bot.py
```

或

*交流群*

群号:1019465737
~~没经验，写的有不好之处不好求别喷~~
