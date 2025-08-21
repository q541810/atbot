import re
from typing import List, Tuple, Optional

class AtParser:
    def __init__(self):
        # CQ码格式的@匹配：[CQ:at,qq=123456]
        self.cq_at_pattern = re.compile(r'\[CQ:at,qq=(\d+)\]')
        # 普通@格式匹配：@123456
        self.normal_at_pattern = re.compile(r'@(\d{5,12})')
    
    def extract_at_users(self, message: str) -> List[int]:
        """从消息中提取所有被@的用户QQ号"""
        at_users = []
        
        # 提取CQ码格式的@
        cq_matches = self.cq_at_pattern.findall(message)
        for qq in cq_matches:
            try:
                at_users.append(int(qq))
            except ValueError:
                continue
        
        # 提取普通@格式
        normal_matches = self.normal_at_pattern.findall(message)
        for qq in normal_matches:
            try:
                qq_int = int(qq)
                if qq_int not in at_users:  # 避免重复
                    at_users.append(qq_int)
            except ValueError:
                continue
        
        return at_users
    
    def replace_at_with_names(self, message: str, user_fetcher) -> str:
        """将消息中的@QQ号替换为昵称"""
        result = message
        
        # 替换CQ码格式的@
        def replace_cq_at(match):
            qq = match.group(1)
            try:
                user_id = int(qq)
                # 这里需要根据消息来源确定group_id
                display_name = user_fetcher.get_user_display_name(user_id)
                return f"@{display_name}"
            except ValueError:
                return match.group(0)  # 保持原样
        
        result = self.cq_at_pattern.sub(replace_cq_at, result)
        
        # 替换普通@格式
        def replace_normal_at(match):
            qq = match.group(1)
            try:
                user_id = int(qq)
                display_name = user_fetcher.get_user_display_name(user_id)
                return f"@{display_name}"
            except ValueError:
                return match.group(0)  # 保持原样
        
        result = self.normal_at_pattern.sub(replace_normal_at, result)
        
        return result
    

    
    def has_at_content(self, message: str) -> bool:
        """检查消息是否包含@内容"""
        return bool(self.cq_at_pattern.search(message) or self.normal_at_pattern.search(message))
    
    def get_at_info(self, message: str) -> List[Tuple[str, int]]:
        """获取@信息列表，返回(原始@文本, QQ号)的元组列表"""
        at_info = []
        
        # 获取CQ码格式的@信息
        for match in self.cq_at_pattern.finditer(message):
            try:
                qq = int(match.group(1))
                at_info.append((match.group(0), qq))
            except ValueError:
                continue
        
        # 获取普通@格式的@信息
        for match in self.normal_at_pattern.finditer(message):
            try:
                qq = int(match.group(1))
                at_info.append((match.group(0), qq))
            except ValueError:
                continue
        
        return at_info