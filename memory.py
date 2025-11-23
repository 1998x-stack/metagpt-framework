"""
记忆管理模块

该模块负责管理Agent的记忆系统，包括：
- 短期记忆：当前会话的消息历史
- 长期记忆：持久化的知识和经验
- 工作记忆：当前任务相关的上下文
- 记忆检索：基于相关性检索历史信息

遵循Google Style Guide和PEP 8规范
"""

from typing import List, Dict, Any, Optional, Callable
from collections import deque
from datetime import datetime
import json
from pathlib import Path

from messages import Message, MessageType, MessageChain


class ShortTermMemory:
    """
    短期记忆
    
    存储当前会话的消息历史，采用FIFO队列实现，自动淘汰过期消息
    
    Attributes:
        max_size: 最大容量
        messages: 消息队列
    """
    
    def __init__(self, max_size: int = 100):
        """
        初始化短期记忆
        
        Args:
            max_size: 最大消息数量
        """
        self.max_size = max_size
        self.messages: deque[Message] = deque(maxlen=max_size)
    
    def add(self, message: Message) -> None:
        """
        添加消息到短期记忆
        
        Args:
            message: 消息对象
        """
        self.messages.append(message)
    
    def get_recent(self, n: int = 10) -> List[Message]:
        """
        获取最近的n条消息
        
        Args:
            n: 消息数量
            
        Returns:
            消息列表
        """
        return list(self.messages)[-n:]
    
    def get_by_type(self, msg_type: MessageType) -> List[Message]:
        """
        按类型获取消息
        
        Args:
            msg_type: 消息类型
            
        Returns:
            匹配类型的消息列表
        """
        return [msg for msg in self.messages if msg.msg_type == msg_type]
    
    def get_by_sender(self, sender: str) -> List[Message]:
        """
        按发送者获取消息
        
        Args:
            sender: 发送者角色
            
        Returns:
            匹配发送者的消息列表
        """
        return [msg for msg in self.messages if msg.sender == sender]
    
    def search(self, predicate: Callable[[Message], bool]) -> List[Message]:
        """
        根据谓词搜索消息
        
        Args:
            predicate: 谓词函数
            
        Returns:
            匹配的消息列表
        """
        return [msg for msg in self.messages if predicate(msg)]
    
    def clear(self) -> None:
        """清空短期记忆"""
        self.messages.clear()
    
    def __len__(self) -> int:
        """返回消息数量"""
        return len(self.messages)
    
    def __iter__(self):
        """迭代器"""
        return iter(self.messages)


class LongTermMemory:
    """
    长期记忆
    
    存储持久化的知识和经验，支持保存和加载
    
    Attributes:
        storage_path: 存储路径
        knowledge_base: 知识库字典
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化长期记忆
        
        Args:
            storage_path: 存储文件路径
        """
        self.storage_path = storage_path
        self.knowledge_base: Dict[str, Any] = {}
        
        if storage_path and storage_path.exists():
            self.load()
    
    def add_knowledge(self, key: str, value: Any) -> None:
        """
        添加知识
        
        Args:
            key: 知识键
            value: 知识值
        """
        self.knowledge_base[key] = {
            "value": value,
            "created_at": datetime.now().isoformat(),
            "access_count": 0
        }
    
    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """
        获取知识
        
        Args:
            key: 知识键
            default: 默认值
            
        Returns:
            知识值
        """
        if key in self.knowledge_base:
            self.knowledge_base[key]["access_count"] += 1
            return self.knowledge_base[key]["value"]
        return default
    
    def update_knowledge(self, key: str, value: Any) -> None:
        """
        更新知识
        
        Args:
            key: 知识键
            value: 新的知识值
        """
        if key in self.knowledge_base:
            self.knowledge_base[key]["value"] = value
            self.knowledge_base[key]["updated_at"] = datetime.now().isoformat()
        else:
            self.add_knowledge(key, value)
    
    def remove_knowledge(self, key: str) -> None:
        """
        删除知识
        
        Args:
            key: 知识键
        """
        if key in self.knowledge_base:
            del self.knowledge_base[key]
    
    def has_knowledge(self, key: str) -> bool:
        """
        检查是否存在知识
        
        Args:
            key: 知识键
            
        Returns:
            是否存在
        """
        return key in self.knowledge_base
    
    def get_all_keys(self) -> List[str]:
        """
        获取所有知识键
        
        Returns:
            知识键列表
        """
        return list(self.knowledge_base.keys())
    
    def save(self) -> None:
        """保存长期记忆到文件"""
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
    
    def load(self) -> None:
        """从文件加载长期记忆"""
        if self.storage_path and self.storage_path.exists():
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
    
    def clear(self) -> None:
        """清空长期记忆"""
        self.knowledge_base.clear()
    
    def __len__(self) -> int:
        """返回知识数量"""
        return len(self.knowledge_base)


class WorkingMemory:
    """
    工作记忆
    
    存储当前任务相关的上下文信息
    
    Attributes:
        context: 上下文字典
    """
    
    def __init__(self):
        """初始化工作记忆"""
        self.context: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any) -> None:
        """
        设置上下文
        
        Args:
            key: 上下文键
            value: 上下文值
        """
        self.context[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取上下文
        
        Args:
            key: 上下文键
            default: 默认值
            
        Returns:
            上下文值
        """
        return self.context.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        批量更新上下文
        
        Args:
            data: 上下文数据字典
        """
        self.context.update(data)
    
    def remove(self, key: str) -> None:
        """
        删除上下文
        
        Args:
            key: 上下文键
        """
        if key in self.context:
            del self.context[key]
    
    def clear(self) -> None:
        """清空工作记忆"""
        self.context.clear()
    
    def has(self, key: str) -> bool:
        """
        检查是否存在上下文
        
        Args:
            key: 上下文键
            
        Returns:
            是否存在
        """
        return key in self.context
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            上下文字典
        """
        return self.context.copy()


class Memory:
    """
    记忆系统
    
    整合短期记忆、长期记忆和工作记忆，提供统一的记忆管理接口
    
    Attributes:
        short_term: 短期记忆
        long_term: 长期记忆
        working: 工作记忆
    """
    
    def __init__(
        self,
        short_term_size: int = 100,
        long_term_path: Optional[Path] = None
    ):
        """
        初始化记忆系统
        
        Args:
            short_term_size: 短期记忆容量
            long_term_path: 长期记忆存储路径
        """
        self.short_term = ShortTermMemory(max_size=short_term_size)
        self.long_term = LongTermMemory(storage_path=long_term_path)
        self.working = WorkingMemory()
    
    def add_message(self, message: Message) -> None:
        """
        添加消息到短期记忆
        
        Args:
            message: 消息对象
        """
        self.short_term.add(message)
    
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """
        获取最近的消息
        
        Args:
            n: 消息数量
            
        Returns:
            消息列表
        """
        return self.short_term.get_recent(n)
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[Message]:
        """
        按类型获取消息
        
        Args:
            msg_type: 消息类型
            
        Returns:
            消息列表
        """
        return self.short_term.get_by_type(msg_type)
    
    def search_messages(self, predicate: Callable[[Message], bool]) -> List[Message]:
        """
        搜索消息
        
        Args:
            predicate: 谓词函数
            
        Returns:
            匹配的消息列表
        """
        return self.short_term.search(predicate)
    
    def add_knowledge(self, key: str, value: Any) -> None:
        """
        添加知识到长期记忆
        
        Args:
            key: 知识键
            value: 知识值
        """
        self.long_term.add_knowledge(key, value)
    
    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """
        从长期记忆获取知识
        
        Args:
            key: 知识键
            default: 默认值
            
        Returns:
            知识值
        """
        return self.long_term.get_knowledge(key, default)
    
    def set_context(self, key: str, value: Any) -> None:
        """
        设置工作记忆上下文
        
        Args:
            key: 上下文键
            value: 上下文值
        """
        self.working.set(key, value)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        获取工作记忆上下文
        
        Args:
            key: 上下文键
            default: 默认值
            
        Returns:
            上下文值
        """
        return self.working.get(key, default)
    
    def get_all_context(self) -> Dict[str, Any]:
        """
        获取所有工作记忆上下文
        
        Returns:
            上下文字典
        """
        return self.working.to_dict()
    
    def clear_short_term(self) -> None:
        """清空短期记忆"""
        self.short_term.clear()
    
    def clear_working(self) -> None:
        """清空工作记忆"""
        self.working.clear()
    
    def save_long_term(self) -> None:
        """保存长期记忆"""
        self.long_term.save()
    
    def load_long_term(self) -> None:
        """加载长期记忆"""
        self.long_term.load()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取记忆系统摘要
        
        Returns:
            摘要字典
        """
        return {
            "short_term_size": len(self.short_term),
            "long_term_size": len(self.long_term),
            "working_context_keys": list(self.working.context.keys())
        }


if __name__ == "__main__":
    # 测试记忆模块
    print("=== Testing Memory Module ===\n")
    
    # 创建记忆系统
    memory = Memory(short_term_size=5, long_term_path=Path("test_memory.json"))
    
    # 测试短期记忆
    print("1. Testing Short-Term Memory:")
    for i in range(7):
        msg = Message(
            content=f"Message {i}",
            msg_type=MessageType.NOTIFICATION,
            sender="test"
        )
        memory.add_message(msg)
    
    recent = memory.get_recent_messages(5)
    print(f"Recent messages count: {len(recent)}")
    print(f"First message content: {recent[0].content}\n")
    
    # 测试长期记忆
    print("2. Testing Long-Term Memory:")
    memory.add_knowledge("api_key", "sk-test123")
    memory.add_knowledge("model", "gpt-4")
    print(f"API Key: {memory.get_knowledge('api_key')}")
    print(f"Knowledge count: {len(memory.long_term)}\n")
    
    # 测试工作记忆
    print("3. Testing Working Memory:")
    memory.set_context("current_file", "main.py")
    memory.set_context("task_status", "in_progress")
    print(f"Current file: {memory.get_context('current_file')}")
    print(f"All context: {memory.get_all_context()}\n")
    
    # 测试记忆摘要
    print("4. Memory Summary:")
    print(memory.get_summary())
    
    # 保存和加载
    memory.save_long_term()
    print("\n5. Long-term memory saved")
    
    # 清理测试文件
    test_file = Path("test_memory.json")
    if test_file.exists():
        test_file.unlink()
    
    print("\n=== Memory Module Test Completed ===")