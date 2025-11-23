"""
消息数据结构模块

该模块定义了MetaGPT框架中使用的消息数据结构，包括：
- Message: 基础消息类
- StructuredMessage: 结构化消息类
- MessageType: 消息类型枚举
- 消息序列化和反序列化功能

遵循Google Style Guide和PEP 8规范
"""

from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import uuid


class MessageType(Enum):
    """消息类型枚举类"""
    REQUIREMENT = "requirement"  # 需求消息
    PRD = "prd"  # 产品需求文档
    DESIGN = "design"  # 系统设计
    TASKS = "tasks"  # 任务列表
    CODE = "code"  # 代码
    TEST = "test"  # 测试
    REVIEW = "review"  # 审查
    FEEDBACK = "feedback"  # 反馈
    QUESTION = "question"  # 问题
    ANSWER = "answer"  # 回答
    NOTIFICATION = "notification"  # 通知


@dataclass
class Message:
    """
    基础消息类
    
    Attributes:
        id: 消息唯一标识符
        content: 消息内容
        msg_type: 消息类型
        sender: 发送者角色
        receiver: 接收者角色（可选）
        metadata: 元数据字典
        created_at: 创建时间
        parent_id: 父消息ID（用于消息链）
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    msg_type: MessageType = MessageType.NOTIFICATION
    sender: str = ""
    receiver: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果msg_type是字符串，转换为MessageType
        if isinstance(self.msg_type, str):
            self.msg_type = MessageType(self.msg_type)
        
        # 如果created_at是字符串，转换为datetime
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            消息字典
        """
        data = asdict(self)
        data['msg_type'] = self.msg_type.value
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        从字典创建消息对象
        
        Args:
            data: 消息字典
            
        Returns:
            Message实例
        """
        return cls(**data)
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        从JSON字符串创建消息对象
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Message实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据
        
        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 元数据键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self.metadata.get(key, default)
    
    def is_for(self, receiver: str) -> bool:
        """
        检查消息是否发送给指定接收者
        
        Args:
            receiver: 接收者角色
            
        Returns:
            是否发送给指定接收者
        """
        return self.receiver is None or self.receiver == receiver
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Message(id={self.id[:8]}..., "
            f"type={self.msg_type.value}, "
            f"sender={self.sender}, "
            f"receiver={self.receiver})"
        )


@dataclass
class StructuredMessage(Message):
    """
    结构化消息类
    
    用于传递结构化的文档内容（如PRD、设计文档等）
    
    Attributes:
        document_type: 文档类型
        sections: 文档章节字典
        format_version: 格式版本
    """
    document_type: str = ""
    sections: Dict[str, Any] = field(default_factory=dict)
    format_version: str = "1.0"
    
    def add_section(self, section_name: str, content: Any) -> None:
        """
        添加文档章节
        
        Args:
            section_name: 章节名称
            content: 章节内容
        """
        self.sections[section_name] = content
    
    def get_section(self, section_name: str, default: Any = None) -> Any:
        """
        获取文档章节
        
        Args:
            section_name: 章节名称
            default: 默认值
            
        Returns:
            章节内容
        """
        return self.sections.get(section_name, default)
    
    def has_section(self, section_name: str) -> bool:
        """
        检查是否包含指定章节
        
        Args:
            section_name: 章节名称
            
        Returns:
            是否包含章节
        """
        return section_name in self.sections
    
    def get_all_sections(self) -> List[str]:
        """
        获取所有章节名称
        
        Returns:
            章节名称列表
        """
        return list(self.sections.keys())
    
    def to_markdown(self) -> str:
        """
        转换为Markdown格式
        
        Returns:
            Markdown格式的文档内容
        """
        lines = [f"# {self.document_type}\n"]
        
        for section_name, content in self.sections.items():
            lines.append(f"## {section_name}\n")
            
            if isinstance(content, dict):
                for key, value in content.items():
                    lines.append(f"**{key}**: {value}\n")
            elif isinstance(content, list):
                for item in content:
                    lines.append(f"- {item}\n")
            else:
                lines.append(f"{content}\n")
            
            lines.append("\n")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            消息字典
        """
        data = super().to_dict()
        data['document_type'] = self.document_type
        data['sections'] = self.sections
        data['format_version'] = self.format_version
        return data


class MessageBuilder:
    """
    消息构建器
    
    使用Builder模式简化消息创建过程
    """
    
    def __init__(self):
        """初始化构建器"""
        self._message_data: Dict[str, Any] = {}
        self._message_class: Type[Message] = Message
    
    def with_type(self, msg_type: MessageType) -> 'MessageBuilder':
        """
        设置消息类型
        
        Args:
            msg_type: 消息类型
            
        Returns:
            构建器实例
        """
        self._message_data['msg_type'] = msg_type
        return self
    
    def with_content(self, content: str) -> 'MessageBuilder':
        """
        设置消息内容
        
        Args:
            content: 消息内容
            
        Returns:
            构建器实例
        """
        self._message_data['content'] = content
        return self
    
    def with_sender(self, sender: str) -> 'MessageBuilder':
        """
        设置发送者
        
        Args:
            sender: 发送者角色
            
        Returns:
            构建器实例
        """
        self._message_data['sender'] = sender
        return self
    
    def with_receiver(self, receiver: Optional[str]) -> 'MessageBuilder':
        """
        设置接收者
        
        Args:
            receiver: 接收者角色
            
        Returns:
            构建器实例
        """
        self._message_data['receiver'] = receiver
        return self
    
    def with_metadata(self, metadata: Dict[str, Any]) -> 'MessageBuilder':
        """
        设置元数据
        
        Args:
            metadata: 元数据字典
            
        Returns:
            构建器实例
        """
        self._message_data['metadata'] = metadata
        return self
    
    def with_parent(self, parent_id: str) -> 'MessageBuilder':
        """
        设置父消息ID
        
        Args:
            parent_id: 父消息ID
            
        Returns:
            构建器实例
        """
        self._message_data['parent_id'] = parent_id
        return self
    
    def as_structured(self, document_type: str) -> 'MessageBuilder':
        """
        构建结构化消息
        
        Args:
            document_type: 文档类型
            
        Returns:
            构建器实例
        """
        self._message_class = StructuredMessage
        self._message_data['document_type'] = document_type
        return self
    
    def with_section(self, section_name: str, content: Any) -> 'MessageBuilder':
        """
        添加文档章节（仅用于结构化消息）
        
        Args:
            section_name: 章节名称
            content: 章节内容
            
        Returns:
            构建器实例
        """
        if 'sections' not in self._message_data:
            self._message_data['sections'] = {}
        self._message_data['sections'][section_name] = content
        return self
    
    def build(self) -> Message:
        """
        构建消息对象
        
        Returns:
            消息实例
        """
        return self._message_class(**self._message_data)


class MessageChain:
    """
    消息链
    
    用于跟踪和管理相关消息的链式结构
    """
    
    def __init__(self, root_message: Optional[Message] = None):
        """
        初始化消息链
        
        Args:
            root_message: 根消息
        """
        self.messages: List[Message] = []
        if root_message:
            self.messages.append(root_message)
    
    def add_message(self, message: Message) -> None:
        """
        添加消息到链中
        
        Args:
            message: 消息对象
        """
        self.messages.append(message)
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[Message]:
        """
        按类型获取消息
        
        Args:
            msg_type: 消息类型
            
        Returns:
            匹配类型的消息列表
        """
        return [msg for msg in self.messages if msg.msg_type == msg_type]
    
    def get_messages_by_sender(self, sender: str) -> List[Message]:
        """
        按发送者获取消息
        
        Args:
            sender: 发送者角色
            
        Returns:
            匹配发送者的消息列表
        """
        return [msg for msg in self.messages if msg.sender == sender]
    
    def get_latest_message(self, msg_type: Optional[MessageType] = None) -> Optional[Message]:
        """
        获取最新消息
        
        Args:
            msg_type: 消息类型（可选）
            
        Returns:
            最新消息，如果不存在返回None
        """
        if msg_type:
            filtered = self.get_messages_by_type(msg_type)
            return filtered[-1] if filtered else None
        return self.messages[-1] if self.messages else None
    
    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """
        根据ID获取消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息对象，如果不存在返回None
        """
        for msg in self.messages:
            if msg.id == message_id:
                return msg
        return None
    
    def get_children(self, parent_id: str) -> List[Message]:
        """
        获取指定消息的子消息
        
        Args:
            parent_id: 父消息ID
            
        Returns:
            子消息列表
        """
        return [msg for msg in self.messages if msg.parent_id == parent_id]
    
    def __len__(self) -> int:
        """返回消息数量"""
        return len(self.messages)
    
    def __iter__(self):
        """迭代器"""
        return iter(self.messages)


if __name__ == "__main__":
    # 测试消息模块
    print("=== Testing Messages Module ===\n")
    
    # 测试基础消息
    print("1. Creating basic message:")
    msg1 = Message(
        content="Create a todo app",
        msg_type=MessageType.REQUIREMENT,
        sender="user",
        receiver="product_manager"
    )
    print(msg1)
    print(f"JSON: {msg1.to_json()}\n")
    
    # 测试消息构建器
    print("2. Using MessageBuilder:")
    msg2 = (MessageBuilder()
            .with_type(MessageType.PRD)
            .with_content("Product Requirements Document")
            .with_sender("product_manager")
            .with_receiver("architect")
            .with_metadata({"priority": "high", "deadline": "2024-01-01"})
            .build())
    print(msg2)
    print()
    
    # 测试结构化消息
    print("3. Creating structured message:")
    prd_msg = (MessageBuilder()
               .as_structured("Product Requirements Document")
               .with_type(MessageType.PRD)
               .with_sender("product_manager")
               .with_section("Goals", ["Goal 1", "Goal 2", "Goal 3"])
               .with_section("User Stories", ["Story 1", "Story 2"])
               .build())
    print(prd_msg)
    print(f"\nMarkdown:\n{prd_msg.to_markdown()}")
    
    # 测试消息链
    print("4. Testing message chain:")
    chain = MessageChain(msg1)
    chain.add_message(msg2)
    chain.add_message(prd_msg)
    print(f"Chain length: {len(chain)}")
    print(f"Latest PRD: {chain.get_latest_message(MessageType.PRD)}")
    
    print("\n=== Messages Module Test Completed ===")