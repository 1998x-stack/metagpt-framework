"""
动作模块

该模块定义了MetaGPT框架中所有角色的动作基类和具体实现，包括：
- Action: 动作基类
- 角色特定动作：WritePRD, WriteDesign, WriteTasks, WriteCode, WriteTest等

遵循Google Style Guide和PEP 8规范
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
import asyncio

from messages import Message, MessageType, StructuredMessage, MessageBuilder
from prompts import PromptManager
from logger import get_logger


logger = get_logger(__name__)


@dataclass
class ActionContext:
    """
    动作执行上下文
    
    Attributes:
        agent_name: 执行动作的Agent名称
        current_message: 当前触发动作的消息
        history_messages: 历史消息列表
        working_context: 工作上下文字典
        config: 配置信息
    """
    agent_name: str
    current_message: Optional[Message] = None
    history_messages: List[Message] = None
    working_context: Dict[str, Any] = None
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化默认值"""
        if self.history_messages is None:
            self.history_messages = []
        if self.working_context is None:
            self.working_context = {}
        if self.config is None:
            self.config = {}


class Action(ABC):
    """
    动作基类
    
    所有具体动作都继承自此基类，定义了动作的基本接口和通用行为
    
    Attributes:
        name: 动作名称
        description: 动作描述
        input_types: 输入消息类型列表
        output_type: 输出消息类型
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        input_types: List[MessageType],
        output_type: MessageType
    ):
        """
        初始化动作
        
        Args:
            name: 动作名称
            description: 动作描述
            input_types: 输入消息类型列表
            output_type: 输出消息类型
        """
        self.name = name
        self.description = description
        self.input_types = input_types
        self.output_type = output_type
        
        logger.debug(f"Action '{name}' initialized")
    
    @abstractmethod
    async def execute(self, context: ActionContext) -> Message:
        """
        执行动作（抽象方法，子类必须实现）
        
        Args:
            context: 动作执行上下文
            
        Returns:
            执行结果消息
        """
        pass
    
    def can_handle(self, message: Message) -> bool:
        """
        检查是否可以处理给定的消息
        
        Args:
            message: 待检查的消息
            
        Returns:
            是否可以处理
        """
        return message.msg_type in self.input_types
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        调用LLM生成响应（模拟实现，实际需要集成LLM API）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大token数
            
        Returns:
            LLM生成的响应
        """
        # TODO: 实际实现需要调用OpenAI/Anthropic等API
        # 这里返回模拟响应
        logger.info(f"Calling LLM for action '{self.name}'")
        
        # 模拟异步调用
        await asyncio.sleep(0.1)
        
        # 实际实现示例：
        # from openai import AsyncOpenAI
        # client = AsyncOpenAI()
        # response = await client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": prompt}
        #     ],
        #     temperature=temperature,
        #     max_tokens=max_tokens
        # )
        # return response.choices[0].message.content
        
        return f"[Simulated LLM Response for {self.name}]"
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"Action(name='{self.name}', output_type={self.output_type.value})"


class WritePRD(Action):
    """
    编写PRD动作（Product Manager）
    
    根据用户需求生成产品需求文档
    """
    
    def __init__(self):
        super().__init__(
            name="WritePRD",
            description="Analyze requirements and write Product Requirements Document",
            input_types=[MessageType.REQUIREMENT],
            output_type=MessageType.PRD
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行PRD编写
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含PRD的结构化消息
        """
        logger.info(f"Executing WritePRD action by {context.agent_name}")
        
        # 获取需求内容
        requirement = context.current_message.content if context.current_message else ""
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="product_manager",
            action="write_prd",
            requirement=requirement
        )
        
        # 调用LLM生成PRD
        prd_content = await self._call_llm(prompt)
        
        # 解析PRD内容并创建结构化消息
        # TODO: 实际实现需要解析LLM返回的markdown格式
        prd_message = (MessageBuilder()
                       .as_structured("Product Requirements Document")
                       .with_type(MessageType.PRD)
                       .with_sender(context.agent_name)
                       .with_receiver("architect")
                       .with_content(prd_content)
                       .with_section("Original Requirements", requirement)
                       .with_section("Product Goals", ["Goal 1", "Goal 2", "Goal 3"])
                       .with_section("User Stories", ["Story 1", "Story 2"])
                       .with_section("Competitive Analysis", ["Competitor 1", "Competitor 2"])
                       .with_section("Requirement Analysis", "Detailed analysis...")
                       .with_section("Requirement Pool", [("Req 1", "P0"), ("Req 2", "P1")])
                       .with_metadata({"action": self.name})
                       .build())
        
        logger.info(f"PRD generated by {context.agent_name}")
        return prd_message


class WriteDesign(Action):
    """
    编写系统设计动作（Architect）
    
    基于PRD生成系统设计文档
    """
    
    def __init__(self):
        super().__init__(
            name="WriteDesign",
            description="Create system design based on PRD",
            input_types=[MessageType.PRD],
            output_type=MessageType.DESIGN
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行系统设计
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含系统设计的结构化消息
        """
        logger.info(f"Executing WriteDesign action by {context.agent_name}")
        
        # 获取PRD内容
        prd_content = context.current_message.content if context.current_message else ""
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="architect",
            action="write_design",
            prd=prd_content
        )
        
        # 调用LLM生成系统设计
        design_content = await self._call_llm(prompt)
        
        # 创建结构化设计消息
        design_message = (MessageBuilder()
                          .as_structured("System Design Document")
                          .with_type(MessageType.DESIGN)
                          .with_sender(context.agent_name)
                          .with_receiver("project_manager")
                          .with_content(design_content)
                          .with_section("Implementation Approach", "Tech stack and rationale...")
                          .with_section("Python Package Name", "project_name")
                          .with_section("File List", ["main.py", "module1.py", "module2.py"])
                          .with_section("Data Structures", {"Class1": "description", "Class2": "description"})
                          .with_section("Program Call Flow", "Detailed flow description...")
                          .with_section("Sequence Diagram", "```mermaid\nsequenceDiagram\n...```")
                          .with_metadata({"action": self.name})
                          .build())
        
        logger.info(f"System design generated by {context.agent_name}")
        return design_message


class WriteTasks(Action):
    """
    编写任务列表动作（Project Manager）
    
    基于PRD和系统设计生成任务列表
    """
    
    def __init__(self):
        super().__init__(
            name="WriteTasks",
            description="Break down project into tasks",
            input_types=[MessageType.DESIGN],
            output_type=MessageType.TASKS
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行任务分解
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含任务列表的结构化消息
        """
        logger.info(f"Executing WriteTasks action by {context.agent_name}")
        
        # 获取PRD和设计内容
        design_content = context.current_message.content if context.current_message else ""
        
        # 从历史消息中获取PRD
        prd_content = ""
        for msg in context.history_messages:
            if msg.msg_type == MessageType.PRD:
                prd_content = msg.content
                break
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="project_manager",
            action="write_tasks",
            prd=prd_content,
            system_design=design_content
        )
        
        # 调用LLM生成任务列表
        tasks_content = await self._call_llm(prompt)
        
        # 创建结构化任务消息
        tasks_message = (MessageBuilder()
                         .as_structured("Task List")
                         .with_type(MessageType.TASKS)
                         .with_sender(context.agent_name)
                         .with_receiver("engineer")
                         .with_content(tasks_content)
                         .with_section("Required Python Packages", ["package1==1.0.0", "package2==2.0.0"])
                         .with_section("Required Other Packages", [])
                         .with_section("Full API Spec", "No APIs used")
                         .with_section("Logic Analysis", [
                             ("main.py", "Entry point, initializes app"),
                             ("module1.py", "Core logic implementation"),
                             ("module2.py", "Helper functions")
                         ])
                         .with_section("Task List", ["main.py", "module1.py", "module2.py"])
                         .with_section("Shared Knowledge", "Important information for all team members...")
                         .with_metadata({"action": self.name})
                         .build())
        
        logger.info(f"Task list generated by {context.agent_name}")
        return tasks_message


class WriteCode(Action):
    """
    编写代码动作（Engineer）
    
    基于系统设计和任务列表实现代码
    """
    
    def __init__(self):
        super().__init__(
            name="WriteCode",
            description="Implement code based on design and tasks",
            input_types=[MessageType.TASKS],
            output_type=MessageType.CODE
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行代码编写
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含代码的消息
        """
        logger.info(f"Executing WriteCode action by {context.agent_name}")
        
        # 获取任务信息
        tasks_content = context.current_message.content if context.current_message else ""
        
        # 获取当前要实现的文件名
        current_file = context.working_context.get("current_file", "main.py")
        
        # 从历史消息中获取系统设计
        design_content = ""
        for msg in context.history_messages:
            if msg.msg_type == MessageType.DESIGN:
                design_content = msg.content
                break
        
        # 获取已实现的文件列表
        implemented_files = context.working_context.get("implemented_files", [])
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="engineer",
            action="write_code",
            filename=current_file,
            system_design=design_content,
            task_context=tasks_content,
            implemented_files=", ".join(implemented_files)
        )
        
        # 调用LLM生成代码
        code_content = await self._call_llm(prompt, max_tokens=8192)
        
        # 创建代码消息
        code_message = (MessageBuilder()
                        .with_type(MessageType.CODE)
                        .with_sender(context.agent_name)
                        .with_receiver("qa_engineer")
                        .with_content(code_content)
                        .with_metadata({
                            "action": self.name,
                            "filename": current_file,
                            "language": "python"
                        })
                        .build())
        
        logger.info(f"Code for {current_file} generated by {context.agent_name}")
        return code_message


class DebugCode(Action):
    """
    调试代码动作（Engineer）
    
    基于执行反馈修复代码错误
    """
    
    def __init__(self):
        super().__init__(
            name="DebugCode",
            description="Debug and fix code based on execution feedback",
            input_types=[MessageType.FEEDBACK],
            output_type=MessageType.CODE
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行代码调试
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含修复后代码的消息
        """
        logger.info(f"Executing DebugCode action by {context.agent_name}")
        
        # 获取错误反馈
        feedback = context.current_message.content if context.current_message else ""
        error_message = context.current_message.get_metadata("error", "")
        
        # 获取当前代码
        current_file = context.working_context.get("current_file", "")
        current_code = context.working_context.get("current_code", "")
        
        # 获取系统设计
        design_content = ""
        for msg in context.history_messages:
            if msg.msg_type == MessageType.DESIGN:
                design_content = msg.content
                break
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="engineer",
            action="debug_code",
            filename=current_file,
            current_code=current_code,
            error_message=error_message,
            system_design=design_content
        )
        
        # 调用LLM生成修复后的代码
        fixed_code = await self._call_llm(prompt, max_tokens=8192)
        
        # 创建修复后的代码消息
        code_message = (MessageBuilder()
                        .with_type(MessageType.CODE)
                        .with_sender(context.agent_name)
                        .with_receiver("qa_engineer")
                        .with_content(fixed_code)
                        .with_metadata({
                            "action": self.name,
                            "filename": current_file,
                            "language": "python",
                            "is_fix": True
                        })
                        .build())
        
        logger.info(f"Code debugged for {current_file} by {context.agent_name}")
        return code_message


class WriteTest(Action):
    """
    编写测试动作（QA Engineer）
    
    为代码编写单元测试
    """
    
    def __init__(self):
        super().__init__(
            name="WriteTest",
            description="Write unit tests for code",
            input_types=[MessageType.CODE],
            output_type=MessageType.TEST
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行测试编写
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含测试代码的消息
        """
        logger.info(f"Executing WriteTest action by {context.agent_name}")
        
        # 获取代码内容
        code = context.current_message.content if context.current_message else ""
        filename = context.current_message.get_metadata("filename", "")
        
        # 获取需求和设计
        requirements = ""
        design = ""
        for msg in context.history_messages:
            if msg.msg_type == MessageType.PRD:
                requirements = msg.content
            elif msg.msg_type == MessageType.DESIGN:
                design = msg.content
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="qa_engineer",
            action="write_test",
            filename=f"test_{filename}",
            code=code,
            requirements=requirements,
            system_design=design
        )
        
        # 调用LLM生成测试代码
        test_code = await self._call_llm(prompt, max_tokens=4096)
        
        # 创建测试消息
        test_message = (MessageBuilder()
                        .with_type(MessageType.TEST)
                        .with_sender(context.agent_name)
                        .with_content(test_code)
                        .with_metadata({
                            "action": self.name,
                            "filename": f"test_{filename}",
                            "test_framework": "pytest"
                        })
                        .build())
        
        logger.info(f"Test for {filename} generated by {context.agent_name}")
        return test_message


class ReviewCode(Action):
    """
    代码审查动作（QA Engineer）
    
    审查代码质量和规范
    """
    
    def __init__(self):
        super().__init__(
            name="ReviewCode",
            description="Review code quality and standards compliance",
            input_types=[MessageType.CODE],
            output_type=MessageType.REVIEW
        )
    
    async def execute(self, context: ActionContext) -> Message:
        """
        执行代码审查
        
        Args:
            context: 动作执行上下文
            
        Returns:
            包含审查结果的消息
        """
        logger.info(f"Executing ReviewCode action by {context.agent_name}")
        
        # 获取代码内容
        code = context.current_message.content if context.current_message else ""
        filename = context.current_message.get_metadata("filename", "")
        
        # 获取需求
        requirements = ""
        for msg in context.history_messages:
            if msg.msg_type == MessageType.PRD:
                requirements = msg.content
                break
        
        # 构建提示词
        prompt = PromptManager.format_prompt(
            role="qa_engineer",
            action="review_code",
            filename=filename,
            code=code,
            requirements=requirements
        )
        
        # 调用LLM进行审查
        review_content = await self._call_llm(prompt)
        
        # 创建审查消息
        review_message = (MessageBuilder()
                          .with_type(MessageType.REVIEW)
                          .with_sender(context.agent_name)
                          .with_content(review_content)
                          .with_metadata({
                              "action": self.name,
                              "filename": filename,
                              "passed": True  # 实际需要解析审查结果
                          })
                          .build())
        
        logger.info(f"Code review completed for {filename} by {context.agent_name}")
        return review_message


# 动作注册表
ACTION_REGISTRY: Dict[str, Action] = {
    "write_prd": WritePRD(),
    "write_design": WriteDesign(),
    "write_tasks": WriteTasks(),
    "write_code": WriteCode(),
    "debug_code": DebugCode(),
    "write_test": WriteTest(),
    "review_code": ReviewCode()
}


def get_action(action_name: str) -> Optional[Action]:
    """
    从注册表获取动作实例
    
    Args:
        action_name: 动作名称
        
    Returns:
        动作实例，如果不存在返回None
    """
    return ACTION_REGISTRY.get(action_name)


if __name__ == "__main__":
    # 测试动作模块
    print("=== Testing Actions Module ===\n")
    
    async def test_actions():
        # 创建测试上下文
        context = ActionContext(
            agent_name="test_agent",
            current_message=Message(
                content="Create a todo app",
                msg_type=MessageType.REQUIREMENT,
                sender="user"
            )
        )
        
        # 测试WritePRD动作
        print("1. Testing WritePRD action:")
        write_prd = get_action("write_prd")
        prd_msg = await write_prd.execute(context)
        print(f"Action: {write_prd}")
        print(f"Output type: {prd_msg.msg_type.value}")
        print(f"Output sender: {prd_msg.sender}\n")
        
        # 测试WriteDesign动作
        print("2. Testing WriteDesign action:")
        write_design = get_action("write_design")
        context.current_message = prd_msg
        context.history_messages = [prd_msg]
        design_msg = await write_design.execute(context)
        print(f"Action: {write_design}")
        print(f"Output type: {design_msg.msg_type.value}\n")
        
        # 测试WriteCode动作
        print("3. Testing WriteCode action:")
        write_code = get_action("write_code")
        context.working_context = {"current_file": "main.py", "implemented_files": []}
        code_msg = await write_code.execute(context)
        print(f"Action: {write_code}")
        print(f"Output metadata: {code_msg.metadata}\n")
        
        print("=== Actions Module Test Completed ===")
    
    # 运行异步测试
    asyncio.run(test_actions())