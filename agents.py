"""
Agent模块

该模块定义了MetaGPT框架中的Agent基类和工厂，包括：
- Agent: Agent基类
- AgentFactory: Agent工厂（工厂模式）
- Agent生命周期管理
- LLM集成

遵循Google Style Guide和PEP 8规范
"""

from typing import Dict, Any, Optional, List, Type, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import asyncio

from messages import Message, MessageType
from memory import Memory
from actions import Action, ActionContext, get_action
from environment import SharedMessagePool, MessageFilter
from config import RoleConfig
from logger import get_logger


logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """
    Agent配置类
    
    Attributes:
        name: Agent名称
        role: 角色类型
        profile: 角色简介
        goal: 角色目标
        constraints: 约束条件列表
        actions: 可用动作列表
        tools: 可用工具列表
        llm_config: LLM配置
    """
    name: str
    role: str
    profile: str
    goal: str
    constraints: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_role_config(cls, role_config: RoleConfig) -> 'AgentConfig':
        """
        从RoleConfig创建AgentConfig
        
        Args:
            role_config: 角色配置对象
            
        Returns:
            AgentConfig实例
        """
        return cls(
            name=role_config.name,
            role=role_config.profile,
            profile=role_config.profile,
            goal=role_config.goal,
            constraints=role_config.constraints,
            tools=role_config.tools
        )


class Agent(ABC):
    """
    Agent基类
    
    定义了Agent的基本结构和行为，所有具体Agent都继承自此类
    
    Attributes:
        config: Agent配置
        memory: 记忆系统
        actions: 动作字典
        message_pool: 共享消息池
        is_active: 是否处于活动状态
    """
    
    def __init__(
        self,
        config: AgentConfig,
        memory: Optional[Memory] = None,
        message_pool: Optional[SharedMessagePool] = None
    ):
        """
        初始化Agent
        
        Args:
            config: Agent配置
            memory: 记忆系统（可选）
            message_pool: 共享消息池（可选）
        """
        self.config = config
        self.memory = memory or Memory()
        self.message_pool = message_pool
        self.actions: Dict[str, Action] = {}
        self.is_active = False
        self._subscriber = None
        
        # 初始化动作
        self._init_actions()
        
        logger.info(f"Agent '{config.name}' ({config.role}) initialized")
    
    def _init_actions(self) -> None:
        """初始化Agent的动作（子类可重写）"""
        # 子类应该重写此方法来添加特定的动作
        pass
    
    def add_action(self, action: Action) -> None:
        """
        添加动作到Agent
        
        Args:
            action: 动作对象
        """
        self.actions[action.name] = action
        logger.debug(f"Action '{action.name}' added to agent '{self.config.name}'")
    
    def get_action(self, action_name: str) -> Optional[Action]:
        """
        获取动作
        
        Args:
            action_name: 动作名称
            
        Returns:
            动作对象，如果不存在返回None
        """
        return self.actions.get(action_name)
    
    def can_handle_message(self, message: Message) -> bool:
        """
        检查是否可以处理给定消息
        
        Args:
            message: 消息对象
            
        Returns:
            是否可以处理
        """
        # 检查是否有可以处理该消息类型的动作
        for action in self.actions.values():
            if action.can_handle(message):
                return True
        return False
    
    async def observe(self) -> List[Message]:
        """
        观察环境，获取新消息
        
        Returns:
            新消息列表
        """
        if not self.message_pool or not self._subscriber:
            return []
        
        # 从订阅者获取未读消息
        messages = self.message_pool.get_subscriber_messages(
            self.config.name,
            clear=True
        )
        
        # 将消息添加到记忆
        for msg in messages:
            self.memory.add_message(msg)
        
        logger.debug(f"Agent '{self.config.name}' observed {len(messages)} messages")
        return messages
    
    async def think(self, messages: List[Message]) -> Optional[Action]:
        """
        思考阶段：根据消息选择要执行的动作
        
        Args:
            messages: 消息列表
            
        Returns:
            要执行的动作，如果没有合适的动作返回None
        """
        if not messages:
            return None
        
        # 获取最新的可处理消息
        for message in reversed(messages):
            for action in self.actions.values():
                if action.can_handle(message):
                    logger.info(
                        f"Agent '{self.config.name}' selected action '{action.name}' "
                        f"for message type {message.msg_type.value}"
                    )
                    return action
        
        return None
    
    async def act(self, action: Action, trigger_message: Message) -> Optional[Message]:
        """
        行动阶段：执行选定的动作
        
        Args:
            action: 要执行的动作
            trigger_message: 触发动作的消息
            
        Returns:
            动作执行结果消息
        """
        try:
            # 创建动作上下文
            context = ActionContext(
                agent_name=self.config.name,
                current_message=trigger_message,
                history_messages=self.memory.get_recent_messages(20),
                working_context=self.memory.get_all_context(),
                config=self.config.llm_config
            )
            
            # 执行动作
            logger.info(f"Agent '{self.config.name}' executing action '{action.name}'")
            result_message = await action.execute(context)
            
            # 更新记忆
            self.memory.add_message(result_message)
            
            # 发布结果到消息池
            if self.message_pool:
                self.message_pool.publish(result_message)
            
            logger.info(f"Agent '{self.config.name}' completed action '{action.name}'")
            return result_message
        
        except Exception as e:
            logger.error(f"Error executing action '{action.name}': {e}", exc_info=True)
            return None
    
    async def run_once(self) -> bool:
        """
        运行一次完整的Agent循环：observe -> think -> act
        
        Returns:
            是否执行了动作
        """
        # 观察环境
        messages = await self.observe()
        
        if not messages:
            return False
        
        # 思考选择动作
        action = await self.think(messages)
        
        if not action:
            return False
        
        # 执行动作
        result = await self.act(action, messages[-1])
        
        return result is not None
    
    async def run(self, max_iterations: Optional[int] = None) -> None:
        """
        持续运行Agent
        
        Args:
            max_iterations: 最大迭代次数（None表示无限循环）
        """
        self.is_active = True
        iteration = 0
        
        logger.info(f"Agent '{self.config.name}' started running")
        
        try:
            while self.is_active:
                if max_iterations and iteration >= max_iterations:
                    break
                
                executed = await self.run_once()
                
                if not executed:
                    # 没有新消息或动作，等待一段时间
                    await asyncio.sleep(0.5)
                
                iteration += 1
        
        finally:
            self.is_active = False
            logger.info(f"Agent '{self.config.name}' stopped after {iteration} iterations")
    
    def stop(self) -> None:
        """停止Agent运行"""
        self.is_active = False
        logger.info(f"Agent '{self.config.name}' stop requested")
    
    def subscribe_to_pool(
        self,
        message_pool: SharedMessagePool,
        message_filter: Optional[MessageFilter] = None
    ) -> None:
        """
        订阅消息池
        
        Args:
            message_pool: 共享消息池
            message_filter: 消息过滤器
        """
        self.message_pool = message_pool
        
        if message_filter is None:
            # 默认订阅所有发送给自己的消息
            message_filter = MessageFilter(receivers=[self.config.name])
        
        self._subscriber = message_pool.subscribe(
            self.config.name,
            message_filter
        )
        
        logger.info(f"Agent '{self.config.name}' subscribed to message pool")
    
    def unsubscribe_from_pool(self) -> None:
        """取消订阅消息池"""
        if self.message_pool:
            self.message_pool.unsubscribe(self.config.name)
            self._subscriber = None
            logger.info(f"Agent '{self.config.name}' unsubscribed from message pool")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态
        
        Returns:
            状态字典
        """
        return {
            "name": self.config.name,
            "role": self.config.role,
            "is_active": self.is_active,
            "actions": list(self.actions.keys()),
            "memory_summary": self.memory.get_summary()
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"Agent(name='{self.config.name}', role='{self.config.role}')"


class ProductManagerAgent(Agent):
    """
    Product Manager Agent
    
    负责分析需求并生成PRD
    """
    
    def _init_actions(self) -> None:
        """初始化Product Manager的动作"""
        write_prd = get_action("write_prd")
        if write_prd:
            self.add_action(write_prd)


class ArchitectAgent(Agent):
    """
    Architect Agent
    
    负责系统设计
    """
    
    def _init_actions(self) -> None:
        """初始化Architect的动作"""
        write_design = get_action("write_design")
        if write_design:
            self.add_action(write_design)


class ProjectManagerAgent(Agent):
    """
    Project Manager Agent
    
    负责任务分解
    """
    
    def _init_actions(self) -> None:
        """初始化Project Manager的动作"""
        write_tasks = get_action("write_tasks")
        if write_tasks:
            self.add_action(write_tasks)


class EngineerAgent(Agent):
    """
    Engineer Agent
    
    负责代码实现和调试
    """
    
    def _init_actions(self) -> None:
        """初始化Engineer的动作"""
        write_code = get_action("write_code")
        debug_code = get_action("debug_code")
        
        if write_code:
            self.add_action(write_code)
        if debug_code:
            self.add_action(debug_code)


class QAEngineerAgent(Agent):
    """
    QA Engineer Agent
    
    负责测试和代码审查
    """
    
    def _init_actions(self) -> None:
        """初始化QA Engineer的动作"""
        write_test = get_action("write_test")
        review_code = get_action("review_code")
        
        if write_test:
            self.add_action(write_test)
        if review_code:
            self.add_action(review_code)


class AgentFactory:
    """
    Agent工厂
    
    使用工厂模式创建不同类型的Agent
    """
    
    # Agent类型映射
    AGENT_TYPES: Dict[str, Type[Agent]] = {
        "product_manager": ProductManagerAgent,
        "architect": ArchitectAgent,
        "project_manager": ProjectManagerAgent,
        "engineer": EngineerAgent,
        "qa_engineer": QAEngineerAgent
    }
    
    @classmethod
    def create_agent(
        cls,
        role_type: str,
        config: AgentConfig,
        memory: Optional[Memory] = None,
        message_pool: Optional[SharedMessagePool] = None
    ) -> Optional[Agent]:
        """
        创建指定类型的Agent
        
        Args:
            role_type: 角色类型
            config: Agent配置
            memory: 记忆系统
            message_pool: 共享消息池
            
        Returns:
            Agent实例，如果类型不存在返回None
        """
        agent_class = cls.AGENT_TYPES.get(role_type)
        
        if not agent_class:
            logger.error(f"Unknown agent type: {role_type}")
            return None
        
        agent = agent_class(config, memory, message_pool)
        
        logger.info(f"Created {role_type} agent: {agent.config.name}")
        return agent
    
    @classmethod
    def create_from_role_config(
        cls,
        role_type: str,
        role_config: RoleConfig,
        memory: Optional[Memory] = None,
        message_pool: Optional[SharedMessagePool] = None
    ) -> Optional[Agent]:
        """
        从RoleConfig创建Agent
        
        Args:
            role_type: 角色类型
            role_config: 角色配置
            memory: 记忆系统
            message_pool: 共享消息池
            
        Returns:
            Agent实例
        """
        agent_config = AgentConfig.from_role_config(role_config)
        return cls.create_agent(role_type, agent_config, memory, message_pool)
    
    @classmethod
    def register_agent_type(cls, role_type: str, agent_class: Type[Agent]) -> None:
        """
        注册新的Agent类型
        
        Args:
            role_type: 角色类型
            agent_class: Agent类
        """
        cls.AGENT_TYPES[role_type] = agent_class
        logger.info(f"Registered new agent type: {role_type}")
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        获取所有可用的Agent类型
        
        Returns:
            Agent类型列表
        """
        return list(cls.AGENT_TYPES.keys())


if __name__ == "__main__":
    # 测试Agent模块
    print("=== Testing Agents Module ===\n")
    
    async def test_agents():
        # 创建消息池
        pool = SharedMessagePool()
        
        # 创建Product Manager配置
        pm_config = AgentConfig(
            name="Alice",
            role="product_manager",
            profile="Product Manager",
            goal="Analyze requirements and create PRD",
            constraints=["Must follow PRD format"]
        )
        
        # 创建Product Manager Agent
        print("1. Creating Product Manager Agent:")
        pm_agent = AgentFactory.create_agent(
            "product_manager",
            pm_config,
            message_pool=pool
        )
        print(f"Created: {pm_agent}")
        print(f"Actions: {list(pm_agent.actions.keys())}\n")
        
        # 订阅消息池
        pm_agent.subscribe_to_pool(
            pool,
            MessageFilter(msg_types=[MessageType.REQUIREMENT])
        )
        
        # 发送需求消息
        print("2. Publishing requirement message:")
        req_msg = Message(
            content="Create a todo list application",
            msg_type=MessageType.REQUIREMENT,
            sender="user",
            receiver="Alice"
        )
        pool.publish(req_msg)
        
        # 运行Agent一次
        print("\n3. Running agent once:")
        executed = await pm_agent.run_once()
        print(f"Action executed: {executed}")
        
        # 检查生成的消息
        print("\n4. Checking generated messages:")
        prd_messages = pool.get_messages(msg_type=MessageType.PRD)
        print(f"PRD messages count: {len(prd_messages)}")
        
        # 获取Agent状态
        print("\n5. Agent status:")
        print(pm_agent.get_status())
        
        # 清理
        pm_agent.unsubscribe_from_pool()
        
        print("\n=== Agents Module Test Completed ===")
    
    # 运行异步测试
    asyncio.run(test_agents())