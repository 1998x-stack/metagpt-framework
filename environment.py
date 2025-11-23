"""
环境模块 - 共享消息池

该模块实现MetaGPT的核心通信机制：
- SharedMessagePool: 共享消息池
- 发布-订阅机制
- 消息过滤和路由
- 消息持久化

遵循Google Style Guide和PEP 8规范
"""

from typing import List, Dict, Any, Optional, Callable, Set
from collections import defaultdict
import threading
from pathlib import Path
import json

from messages import Message, MessageType
from logger import get_logger


logger = get_logger(__name__)


class MessageFilter:
    """
    消息过滤器
    
    用于定义订阅条件，支持多种过滤方式
    """
    
    def __init__(
        self,
        msg_types: Optional[List[MessageType]] = None,
        senders: Optional[List[str]] = None,
        receivers: Optional[List[str]] = None,
        custom_filter: Optional[Callable[[Message], bool]] = None
    ):
        """
        初始化消息过滤器
        
        Args:
            msg_types: 感兴趣的消息类型列表
            senders: 感兴趣的发送者列表
            receivers: 感兴趣的接收者列表
            custom_filter: 自定义过滤函数
        """
        self.msg_types = set(msg_types) if msg_types else set()
        self.senders = set(senders) if senders else set()
        self.receivers = set(receivers) if receivers else set()
        self.custom_filter = custom_filter
    
    def match(self, message: Message) -> bool:
        """
        检查消息是否匹配过滤条件
        
        Args:
            message: 消息对象
            
        Returns:
            是否匹配
        """
        # 如果所有条件都未设置，匹配所有消息
        if not (self.msg_types or self.senders or self.receivers or self.custom_filter):
            return True
        
        # 检查消息类型
        if self.msg_types and message.msg_type not in self.msg_types:
            return False
        
        # 检查发送者
        if self.senders and message.sender not in self.senders:
            return False
        
        # 检查接收者
        if self.receivers and message.receiver not in self.receivers:
            return False
        
        # 执行自定义过滤
        if self.custom_filter and not self.custom_filter(message):
            return False
        
        return True


class Subscriber:
    """
    订阅者
    
    表示一个订阅了消息池的角色
    
    Attributes:
        name: 订阅者名称
        filter: 消息过滤器
        callback: 消息回调函数
    """
    
    def __init__(
        self,
        name: str,
        message_filter: MessageFilter,
        callback: Optional[Callable[[Message], None]] = None
    ):
        """
        初始化订阅者
        
        Args:
            name: 订阅者名称
            message_filter: 消息过滤器
            callback: 消息接收回调
        """
        self.name = name
        self.filter = message_filter
        self.callback = callback
        self.received_messages: List[Message] = []
    
    def notify(self, message: Message) -> None:
        """
        通知订阅者有新消息
        
        Args:
            message: 消息对象
        """
        if self.filter.match(message):
            self.received_messages.append(message)
            
            if self.callback:
                try:
                    self.callback(message)
                except Exception as e:
                    logger.error(f"Error in callback for {self.name}: {e}")
    
    def get_unread_messages(self, clear: bool = True) -> List[Message]:
        """
        获取未读消息
        
        Args:
            clear: 是否清空已读消息
            
        Returns:
            未读消息列表
        """
        messages = self.received_messages.copy()
        if clear:
            self.received_messages.clear()
        return messages
    
    def clear_messages(self) -> None:
        """清空消息"""
        self.received_messages.clear()


class SharedMessagePool:
    """
    共享消息池
    
    实现发布-订阅机制，支持多Agent之间的异步通信
    
    Attributes:
        messages: 所有消息列表
        subscribers: 订阅者字典
        lock: 线程锁（保证线程安全）
    """
    
    def __init__(self, enable_persistence: bool = False, storage_path: Optional[Path] = None):
        """
        初始化共享消息池
        
        Args:
            enable_persistence: 是否启用持久化
            storage_path: 存储路径
        """
        self.messages: List[Message] = []
        self.subscribers: Dict[str, Subscriber] = {}
        self.lock = threading.Lock()
        self.enable_persistence = enable_persistence
        self.storage_path = storage_path
        
        # 统计信息
        self.stats = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_sender": defaultdict(int)
        }
        
        logger.info("SharedMessagePool initialized")
    
    def publish(self, message: Message) -> None:
        """
        发布消息到共享池
        
        Args:
            message: 消息对象
        """
        with self.lock:
            # 添加消息到池中
            self.messages.append(message)
            
            # 更新统计信息
            self.stats["total_messages"] += 1
            self.stats["messages_by_type"][message.msg_type.value] += 1
            self.stats["messages_by_sender"][message.sender] += 1
            
            # 通知所有订阅者
            for subscriber in self.subscribers.values():
                subscriber.notify(message)
            
            # 持久化
            if self.enable_persistence:
                self._persist_message(message)
            
            logger.debug(
                f"Message published: type={message.msg_type.value}, "
                f"sender={message.sender}, receiver={message.receiver}"
            )
    
    def subscribe(
        self,
        name: str,
        message_filter: Optional[MessageFilter] = None,
        callback: Optional[Callable[[Message], None]] = None
    ) -> Subscriber:
        """
        订阅消息池
        
        Args:
            name: 订阅者名称
            message_filter: 消息过滤器
            callback: 消息回调函数
            
        Returns:
            订阅者对象
        """
        with self.lock:
            if message_filter is None:
                message_filter = MessageFilter()  # 订阅所有消息
            
            subscriber = Subscriber(name, message_filter, callback)
            self.subscribers[name] = subscriber
            
            logger.info(f"Subscriber '{name}' registered")
            
            return subscriber
    
    def unsubscribe(self, name: str) -> None:
        """
        取消订阅
        
        Args:
            name: 订阅者名称
        """
        with self.lock:
            if name in self.subscribers:
                del self.subscribers[name]
                logger.info(f"Subscriber '{name}' unregistered")
    
    def get_messages(
        self,
        msg_type: Optional[MessageType] = None,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        查询消息
        
        Args:
            msg_type: 消息类型过滤
            sender: 发送者过滤
            receiver: 接收者过滤
            limit: 返回消息数量限制
            
        Returns:
            匹配的消息列表
        """
        with self.lock:
            filtered_messages = self.messages
            
            # 应用过滤条件
            if msg_type:
                filtered_messages = [m for m in filtered_messages if m.msg_type == msg_type]
            
            if sender:
                filtered_messages = [m for m in filtered_messages if m.sender == sender]
            
            if receiver:
                filtered_messages = [m for m in filtered_messages if m.receiver == receiver]
            
            # 应用数量限制
            if limit:
                filtered_messages = filtered_messages[-limit:]
            
            return filtered_messages
    
    def get_latest_message(
        self,
        msg_type: Optional[MessageType] = None,
        sender: Optional[str] = None
    ) -> Optional[Message]:
        """
        获取最新消息
        
        Args:
            msg_type: 消息类型过滤
            sender: 发送者过滤
            
        Returns:
            最新消息，如果不存在返回None
        """
        messages = self.get_messages(msg_type=msg_type, sender=sender, limit=1)
        return messages[0] if messages else None
    
    def get_subscriber_messages(self, name: str, clear: bool = True) -> List[Message]:
        """
        获取订阅者的未读消息
        
        Args:
            name: 订阅者名称
            clear: 是否清空已读消息
            
        Returns:
            未读消息列表
        """
        with self.lock:
            if name not in self.subscribers:
                return []
            
            return self.subscribers[name].get_unread_messages(clear=clear)
    
    def clear(self) -> None:
        """清空消息池"""
        with self.lock:
            self.messages.clear()
            for subscriber in self.subscribers.values():
                subscriber.clear_messages()
            
            # 重置统计信息
            self.stats = {
                "total_messages": 0,
                "messages_by_type": defaultdict(int),
                "messages_by_sender": defaultdict(int)
            }
            
            logger.info("Message pool cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            return {
                "total_messages": self.stats["total_messages"],
                "messages_in_pool": len(self.messages),
                "active_subscribers": len(self.subscribers),
                "messages_by_type": dict(self.stats["messages_by_type"]),
                "messages_by_sender": dict(self.stats["messages_by_sender"])
            }
    
    def _persist_message(self, message: Message) -> None:
        """
        持久化消息
        
        Args:
            message: 消息对象
        """
        if not self.storage_path:
            return
        
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 追加写入模式
            with open(self.storage_path, 'a', encoding='utf-8') as f:
                f.write(message.to_json() + '\n')
        
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")
    
    def load_messages(self, storage_path: Optional[Path] = None) -> int:
        """
        从文件加载消息
        
        Args:
            storage_path: 存储路径（可选，默认使用初始化时的路径）
            
        Returns:
            加载的消息数量
        """
        path = storage_path or self.storage_path
        if not path or not path.exists():
            return 0
        
        count = 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        message = Message.from_json(line)
                        self.messages.append(message)
                        count += 1
            
            logger.info(f"Loaded {count} messages from {path}")
            return count
        
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")
            return 0
    
    def __len__(self) -> int:
        """返回消息池中的消息数量"""
        return len(self.messages)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"SharedMessagePool("
            f"messages={len(self.messages)}, "
            f"subscribers={len(self.subscribers)})"
        )


if __name__ == "__main__":
    # 测试环境模块
    print("=== Testing Environment Module ===\n")
    
    # 创建共享消息池
    pool = SharedMessagePool(enable_persistence=False)
    
    # 创建订阅者
    print("1. Creating subscribers:")
    
    # Product Manager订阅需求消息
    pm_filter = MessageFilter(msg_types=[MessageType.REQUIREMENT])
    pm_sub = pool.subscribe("product_manager", pm_filter)
    
    # Architect订阅PRD消息
    arch_filter = MessageFilter(msg_types=[MessageType.PRD])
    arch_sub = pool.subscribe("architect", arch_filter)
    
    # Engineer订阅设计消息
    eng_filter = MessageFilter(msg_types=[MessageType.DESIGN])
    eng_sub = pool.subscribe("engineer", eng_filter)
    
    print(f"Subscribers: {list(pool.subscribers.keys())}\n")
    
    # 发布消息
    print("2. Publishing messages:")
    
    # 用户需求
    req_msg = Message(
        content="Create a todo app",
        msg_type=MessageType.REQUIREMENT,
        sender="user",
        receiver="product_manager"
    )
    pool.publish(req_msg)
    print(f"Published: {req_msg}")
    
    # PRD文档
    prd_msg = Message(
        content="Product Requirements Document",
        msg_type=MessageType.PRD,
        sender="product_manager",
        receiver="architect"
    )
    pool.publish(prd_msg)
    print(f"Published: {prd_msg}\n")
    
    # 检查订阅者消息
    print("3. Checking subscriber messages:")
    pm_messages = pool.get_subscriber_messages("product_manager")
    print(f"Product Manager received {len(pm_messages)} messages")
    
    arch_messages = pool.get_subscriber_messages("architect")
    print(f"Architect received {len(arch_messages)} messages\n")
    
    # 查询消息
    print("4. Querying messages:")
    all_messages = pool.get_messages()
    print(f"Total messages in pool: {len(all_messages)}")
    
    req_messages = pool.get_messages(msg_type=MessageType.REQUIREMENT)
    print(f"Requirement messages: {len(req_messages)}\n")
    
    # 统计信息
    print("5. Pool statistics:")
    print(json.dumps(pool.get_stats(), indent=2))
    
    print("\n=== Environment Module Test Completed ===")