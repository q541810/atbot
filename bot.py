import asyncio
import websockets
import os
import time
import re
from log import info,debug,warning,error
from llm.if_module import llm_if
from llm.send_message import llm_send_message
from read_config import load_adapter_config,load_bot_config,load_adaptive_model_config
from type_analysis import parse_msg
from data.read_the_username import 替换消息中的at
from llm.Image_recognition import 图片识别

# 加载配置
adapter_config = load_adapter_config()
bot_config = load_bot_config()
adaptive_model_config = load_adaptive_model_config()
host = adapter_config['napcat_server']['host']
port = adapter_config['napcat_server']['port']
bot_name = bot_config['bot']['bot的名字']  # "麦麦"
bot_qq = bot_config['bot']['bot的qq号']    # 385487834
reply_interest = bot_config['bot']['回复兴趣']  # 0.5
# 提示词将通过personality配置动态生成
maxtoken = bot_config['model']['replyer_1']['maxtoken']
回复模型_url = adaptive_model_config['回复模型_url']
回复模型_key = adaptive_model_config['回复模型_key']
回复模型_model = adaptive_model_config['回复模型_model']
判断模型_url = adaptive_model_config['判断模型_url']
判断模型_key = adaptive_model_config['判断模型_key']
判断模型_model = adaptive_model_config['判断模型_model']
图片模型_url = adaptive_model_config['图片模型_url']
图片模型_key = adaptive_model_config['图片模型_key']
图片模型_model = adaptive_model_config['图片模型_model']
图片模型_switch = adaptive_model_config['图片模型_switch']

# 群聊频率限制
group_last_call_time = {}

# 群聊上下文记录
group_context = {}  # 存储每个群聊的消息历史
消息记录长度 = bot_config['bot']['消息记录长度']  # 从配置文件读取消息记录长度

personality_core = bot_config['personality']['personality_core']
personality_side = bot_config['personality']['personality_side']
identity = bot_config['personality']['identity']

提示词 = (f"# 核心人格\n{personality_core}\n---\n# 侧面人格\n{personality_side}\n---\n# 固定身份\n{identity}")

第一次连接=True

async def main():
    global 第一次连接
    uri = f"ws://{host}:{port}/"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                if 第一次连接:
                    info(f"已连接到 {uri}")
                    第一次连接=False
                else:
                    info(f"重新连接到 {uri}")
                async for message in websocket:
                     parsed = parse_msg(message)
                     if parsed is None:
                         continue
                     
                     消息类型, 消息内容, 群号, 人名 = parsed
                      
                     # 检查群号是否在白名单中
                     if 群号 not in adapter_config['chat']['group_list']:
                         continue  # 如果群号不在白名单中，跳过处理，等待下一条消息
                     if 消息类型=="图片":
                         if 图片模型_switch:
                            try:
                                图片描述 = await 图片识别(消息内容, 图片模型_key, 图片模型_url, 图片模型_model)
                                消息内容 = f"[图片:{图片描述}]"
                                info(f"图片描述: {图片描述}")
                            except Exception as e:
                                error(f"图片识别出错: {e}")
                                消息内容 = "[图片]"
                         else:
                             消息内容 = "[图片]"
                     elif 消息类型=="文件":
                         消息内容=f"[文件]"
              
                     被艾特 = False
                     # 只要消息中包含 @后跟5~12位数字，就执行一次替换（可能有多个@数字会统一处理）
                     # 处理 @QQ -> @昵称 并判断是否被@
                     try:
                         if re.search(r"@\d{5,12}", 消息内容):
                             消息内容 = await 替换消息中的at(消息内容, host, port, bot_qq=bot_qq, bot_name=bot_name, 群号=群号)
                     except Exception as e:
                         warning(f"处理@用户名时出错: {e}")
                     被艾特 = f"@{bot_name}" in 消息内容
                     # 为每个群聊维护独立的上下文记录
                     if 群号 not in group_context:
                         group_context[群号] = []  # 初始化该群的消息历史
                     # 添加当前消息到群聊上下文（格式："用户名: 消息内容"）
                     current_message = f"{人名}: {消息内容}"
                     group_context[群号].append(current_message)
                     
                     # 保持消息历史长度不超过配置的限制
                     if len(group_context[群号]) > 消息记录长度:
                         group_context[群号] = group_context[群号][-消息记录长度:]  # 保留最新的N条消息
                      
                     if 消息类型!="文字":
                        if 消息类型=="图片":
                            回复=False
                            info(f"收到来自{群号}的{人名}的消息: {消息内容}。")
                     else:
                         回复=True
                     #触发事件:回复
                     if 回复:
                         最近五条 = "\n".join(group_context.get(群号, [])[-5:])
                         if 被艾特:
                             兴趣 = 10
                             info("被@,兴趣度改为10")
                         else:
                             兴趣 = await llm_if((f"""{人名}发了消息:{消息内容}"""), bot_name, bot_qq, 判断模型_url, 判断模型_key, 判断模型_model, 消息内容, 提示词, 消息记录=最近五条)
                             if 兴趣 == "error:0":
                                 warning("判断错误0:判断模型返回值为空")
                             elif 兴趣 == "error:1":
                                 warning("判断错误1:ValueError")
                         info(f"收到来自{群号}的{人名}消息: {消息内容}。兴趣度:{兴趣}")
                         if isinstance(兴趣, (int, float)) and 兴趣>=reply_interest:
                             # 检查群聊频率限制（每4秒最多调用一次）
                             current_time = time.time()
                             if 群号 in group_last_call_time:
                                 time_diff = current_time - group_last_call_time[群号]
                                 if time_diff < 6.0:  # 4秒内不允许重复调用
                                     info(f"群{群号}频率限制：距离上次调用仅{time_diff:.1f}秒，跳过本次回复")
                                     continue
                             
                             # 更新最后调用时间
                             group_last_call_time[群号] = current_time
                             
                             async def 回复群消息():
                                 try:
                                     # 使用该群的完整消息历史作为上下文
                                     群消息历史 = "\n".join(group_context[群号])
                                     单条完整消息=f"{人名}发了: {消息内容}"
                                     回复内容=await llm_send_message(消息历史=[群消息历史],单条完整消息=单条完整消息,那个人的名字=人名,bot名字=bot_name,提示词=提示词,群号=群号,napcat_host=host,napcat_port=port,api_url=回复模型_url,api_key=回复模型_key,模型=回复模型_model,是否发至群里=True,最大token=maxtoken)
                                     debug(f"发给判断模型的消息历史:{群消息历史}")
                                     # 将bot的回复也添加到群聊上下文中
                                     if 回复内容:
                                         bot_message = f"{bot_name}: {回复内容}"
                                         group_context[群号].append(bot_message)
                                         # 再次检查长度限制
                                         if len(group_context[群号]) > 消息记录长度:
                                             group_context[群号] = group_context[群号][-消息记录长度:]
                                 except Exception as e:
                                    if str(e).isdigit() and 9 <= len(str(e)) <= 10:
                                        pass  # 如果是9-10位数字则忽略
                                    else:
                                        error(f"回复模型出错: {e}")
                             asyncio.create_task(回复群消息())
                            
        except websockets.exceptions.ConnectionClosed:
            warning("WebSocket连接已关闭，尝试重新连接...")
            await asyncio.sleep(5)  # 等待5秒后重新连接
        except Exception as e:
            error(f"连接出错: {e}，尝试重新连接...")
            await asyncio.sleep(5)  # 等待5秒后重新连接
            
# 示例使用
if __name__ == "__main__":
    # 这里可以调用你的函数
    try:
        print("当前版本:beta0.4.0")
        print("启动中.....")
        asyncio.run(main())
    except KeyboardInterrupt:
        info("接收到中断信号，正在关闭...")
    except Exception as e:
        error(f"应用程序运行出错: {e}")
    finally:
        info("应用程序已退出")
