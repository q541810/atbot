import os
import sys
import importlib.util
import toml
from packaging import version

class PluginManager:
    """插件管理器，用于加载和管理插件"""
    
    def __init__(self, plugin_dir=None, current_version=None):
        """初始化插件管理器
        
        Args:
            plugin_dir: 插件目录，默认为当前脚本所在目录下的plugin文件夹
            current_version: 当前程序版本，用于检查插件兼容性
        """
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plugin')
        
        self.plugin_dir = plugin_dir
        self.current_version = current_version
        self.plugins = {}
        self.actions = {}
    
    def load_plugins(self):
        """加载所有插件"""
        if not os.path.exists(self.plugin_dir):
            print(f"警告: 插件目录不存在: {self.plugin_dir}")
            return
        
        # 遍历插件目录
        for plugin_folder in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, plugin_folder)
            
            # 检查是否是目录
            if not os.path.isdir(plugin_path):
                continue
            
            # 检查是否存在config.toml和plugin.py
            config_file = os.path.join(plugin_path, 'config.toml')
            plugin_file = os.path.join(plugin_path, 'plugin.py')
            
            if not os.path.exists(config_file) or not os.path.exists(plugin_file):
                print(f"警告: 插件 {plugin_folder} 缺少必要文件")
                continue
            
            # 加载插件配置
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = toml.load(f)
            except Exception as e:
                print(f"错误: 无法读取插件配置文件 {config_file}: {e}")
                continue
            
            # 检查插件是否启用
            if not config.get('plugin', {}).get('enabled', False):
                print(f"插件 {config.get('plugin', {}).get('name', plugin_folder)} 未启用，跳过加载")
                continue
            
            # 检查版本兼容性
            if self.current_version and 'min_version' in config.get('plugin', {}):
                min_version = config['plugin']['min_version']
                # 简单的字符串比较，而不是使用version.parse
                if self.current_version != min_version:
                    print(f"警告: 插件 {config.get('plugin', {}).get('name', plugin_folder)} 需要版本 {min_version}，当前版本为 {self.current_version}")
                    print("但仍将尝试加载该插件")
            
            # 加载插件模块
            try:
                # 动态导入插件模块
                spec = importlib.util.spec_from_file_location(f"plugin_{plugin_folder}", plugin_file)
                plugin_module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = plugin_module
                spec.loader.exec_module(plugin_module)
                
                # 保存插件信息
                plugin_name = config.get('plugin', {}).get('name', plugin_folder)
                self.plugins[plugin_name] = {
                    'module': plugin_module,
                    'config': config,
                    'path': plugin_path
                }
                
                # 注册插件动作
                self._register_actions(plugin_name, config, plugin_module)
                
                print(f"成功加载插件: {plugin_name} v{config.get('plugin', {}).get('version', '未知')}")
                print(f"插件介绍: {config.get('plugin', {}).get('introduce', '无介绍')}")
            except Exception as e:
                print(f"错误: 加载插件 {plugin_folder} 失败: {e}")
    
    def _register_actions(self, plugin_name, config, plugin_module):
        """注册插件动作"""
        # 遍历所有action配置
        for key in config:
            if key.startswith('action'):
                action_config = config[key]
                if 'key_word' in action_config and 'def_name' in action_config:
                    key_words = action_config['key_word']
                    func_name = action_config['def_name']
                    parameter = action_config.get('parameter', None)
                    parameter_quantity = action_config.get('parameter_quantity', 0)
                    
                    # 检查函数是否存在
                    if hasattr(plugin_module, func_name):
                        func = getattr(plugin_module, func_name)
                        whitelist = action_config.get('whitelist', None)
                        # 为每个关键词注册动作
                        for key_word in key_words:
                            self.actions[key_word] = {
                                'plugin': plugin_name,
                                'function': func,
                                'parameter': parameter,
                                'parameter_quantity': parameter_quantity,
                                'whitelist': whitelist
                            }
                    else:
                        print(f"警告: 插件 {plugin_name} 中找不到函数 {func_name}")
    
    def handle_message(self, message, **kwargs):
        """处理消息，检查是否触发插件动作
        
        Args:
            message: 消息内容
            **kwargs: 其他参数，将传递给插件函数
        
        Returns:
            bool: 是否有插件处理了消息
        """
        # 检查消息是否触发任何动作
        for key_word, action in self.actions.items():
            if key_word in message:
                func = action['function']
                parameter = action['parameter']
                parameter_quantity = action.get('parameter_quantity', 0)
                whitelist = action.get('whitelist', None)
                
                # 检查白名单权限
                if whitelist is not None:
                    user_id = kwargs.get('user_id')
                    if user_id is None or user_id not in whitelist:
                        print(f"用户 {user_id} 没有权限使用插件动作: {key_word}")
                        return False
                
                try:
                    # 提取参数（如果需要）
                    if parameter or parameter_quantity > 0:
                        if parameter == "message_id":
                            # 对于message_id参数，优先使用引用的消息ID
                            target_message_id = None
                            if "reply_message_id" in kwargs and kwargs["reply_message_id"]:
                                target_message_id = kwargs["reply_message_id"]
                                print(f"使用引用的消息ID: {target_message_id}")
                            elif "message_id" in kwargs:
                                # 如果没有引用消息，尝试从消息中提取ID
                                param_text = message.split(key_word, 1)[1].strip()
                                if param_text:
                                    target_message_id = param_text
                                    print(f"从消息中提取的消息ID: {target_message_id}")
                                else:
                                    target_message_id = kwargs["message_id"]
                            
                            if target_message_id:
                                func(target_message_id, **{k: v for k, v in kwargs.items() if k not in ["message_id", "reply_message_id", "user_id"]})
                            else:
                                print(f"警告: 插件需要message_id参数，但未提供")
                                return False
                        else:
                            # 其他参数从消息中提取
                            param_text = message.split(key_word, 1)[1].strip()
                            if parameter_quantity > 0:
                                # 根据parameter_quantity分割参数
                                if parameter_quantity == 1:
                                    func(param_text, **{k: v for k, v in kwargs.items() if k in ["group_id"]})
                                elif parameter_quantity >= 2:
                                    # 分割参数，最多分割parameter_quantity个部分
                                    params = param_text.split(None, parameter_quantity - 1)
                                    # 确保参数数量正确
                                    while len(params) < parameter_quantity:
                                        params.append("")
                                    # 对于多参数函数，group_id通常作为位置参数传递，不作为关键字参数
                                    # 将group_id插入到适当位置（通常是第二个参数）
                                    group_id = kwargs.get('group_id')
                                    if group_id is not None:
                                        params.insert(1, group_id)  # 在第二个位置插入group_id
                                    func(*params)
                            else:
                                func(**{k: v for k, v in kwargs.items() if k in ["group_id"]})
                    else:
                        # 对于没有参数的函数，只传递group_id
                        func(**{k: v for k, v in kwargs.items() if k in ["group_id"]})
                    return True
                except Exception as e:
                    print(f"错误: 执行插件动作失败: {e}")
        
        return False
    
    def get_plugin_info(self):
        """获取所有已加载插件的信息"""
        info = []
        for name, plugin in self.plugins.items():
            config = plugin['config']
            info.append({
                'name': name,
                'version': config.get('plugin', {}).get('version', '未知'),
                'introduce': config.get('plugin', {}).get('introduce', '无介绍'),
                'actions': [k for k in self.actions if self.actions[k]['plugin'] == name]
            })
        return info

# 创建全局插件管理器实例
plugin_manager = None

def initialize_plugin_manager(current_version=None):
    """初始化插件管理器"""
    global plugin_manager
    plugin_manager = PluginManager(current_version=current_version)
    plugin_manager.load_plugins()
    return plugin_manager