"""
工作流编排模块

该模块实现了MetaGPT的工作流编排，基于LangGraph概念：
- WorkflowState: 工作流状态
- WorkflowOrchestrator: 工作流编排器
- 状态转换和Agent协调
- 可执行反馈循环

遵循Google Style Guide和PEP 8规范
"""

from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path

from messages import Message, MessageType, MessageBuilder
from memory import Memory
from environment import SharedMessagePool, MessageFilter
from agents import Agent, AgentFactory, AgentConfig
from config import Config
from logger import get_logger


logger = get_logger(__name__)


class WorkflowPhase(Enum):
    """工作流阶段枚举"""
    INIT = "init"
    REQUIREMENT = "requirement"
    PRD = "prd"
    DESIGN = "design"
    TASKS = "tasks"
    CODE = "code"
    TEST = "test"
    REVIEW = "review"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """
    工作流状态
    
    Attributes:
        phase: 当前阶段
        requirement: 用户需求
        prd: 产品需求文档
        design: 系统设计
        tasks: 任务列表
        code_files: 代码文件字典
        test_results: 测试结果
        review_results: 审查结果
        iteration: 当前迭代次数
        max_iterations: 最大迭代次数
        metadata: 元数据
    """
    phase: WorkflowPhase = WorkflowPhase.INIT
    requirement: str = ""
    prd: Optional[Message] = None
    design: Optional[Message] = None
    tasks: Optional[Message] = None
    code_files: Dict[str, str] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    review_results: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    max_iterations: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_complete(self) -> bool:
        """检查工作流是否完成"""
        return self.phase in [WorkflowPhase.COMPLETE, WorkflowPhase.FAILED]
    
    def should_retry(self) -> bool:
        """检查是否应该重试"""
        return self.iteration < self.max_iterations
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "phase": self.phase.value,
            "requirement": self.requirement,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "code_files_count": len(self.code_files),
            "metadata": self.metadata
        }


class WorkflowOrchestrator:
    """
    工作流编排器
    
    负责协调多个Agent按照SOP流程完成软件开发任务
    
    Attributes:
        config: 全局配置
        message_pool: 共享消息池
        agents: Agent字典
        state: 工作流状态
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化工作流编排器
        
        Args:
            config: 全局配置
        """
        self.config = config or Config()
        self.message_pool = SharedMessagePool()
        self.agents: Dict[str, Agent] = {}
        self.state = WorkflowState(
            max_iterations=self.config.workflow_config.max_iterations
        )
        
        # 初始化Agent
        self._init_agents()
        
        logger.info("WorkflowOrchestrator initialized")
    
    def _init_agents(self) -> None:
        """初始化所有Agent"""
        # 创建所有角色的Agent
        role_types = ["product_manager", "architect", "project_manager", "engineer", "qa_engineer"]
        
        for role_type in role_types:
            role_config = self.config.get_role_config(role_type)
            if role_config:
                # 为每个Agent创建独立的Memory
                memory = Memory()
                
                # 创建Agent
                agent = AgentFactory.create_from_role_config(
                    role_type,
                    role_config,
                    memory=memory,
                    message_pool=self.message_pool
                )
                
                if agent:
                    self.agents[role_type] = agent
                    
                    # 订阅消息池
                    self._subscribe_agent(agent, role_type)
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    def _subscribe_agent(self, agent: Agent, role_type: str) -> None:
        """
        为Agent订阅相应的消息类型
        
        Args:
            agent: Agent实例
            role_type: 角色类型
        """
        # 定义每个角色应该订阅的消息类型
        subscription_map = {
            "product_manager": [MessageType.REQUIREMENT],
            "architect": [MessageType.PRD],
            "project_manager": [MessageType.DESIGN],
            "engineer": [MessageType.TASKS, MessageType.FEEDBACK],
            "qa_engineer": [MessageType.CODE]
        }
        
        msg_types = subscription_map.get(role_type, [])
        if msg_types:
            message_filter = MessageFilter(msg_types=msg_types)
            agent.subscribe_to_pool(self.message_pool, message_filter)
    
    async def run(self, requirement: str, output_dir: Optional[Path] = None) -> WorkflowState:
        """
        运行完整的工作流
        
        Args:
            requirement: 用户需求
            output_dir: 输出目录
            
        Returns:
            最终的工作流状态
        """
        logger.info(f"Starting workflow for requirement: {requirement}")
        
        # 设置初始状态
        self.state.requirement = requirement
        self.state.phase = WorkflowPhase.REQUIREMENT
        
        if output_dir:
            self.state.metadata["output_dir"] = str(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 执行工作流各个阶段
            await self._phase_requirement()
            await self._phase_prd()
            await self._phase_design()
            await self._phase_tasks()
            await self._phase_code()
            
            if self.config.workflow_config.enable_testing:
                await self._phase_test()
            
            if self.config.workflow_config.enable_review:
                await self._phase_review()
            
            # 标记完成
            self.state.phase = WorkflowPhase.COMPLETE
            logger.info("Workflow completed successfully")
        
        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            self.state.phase = WorkflowPhase.FAILED
            self.state.metadata["error"] = str(e)
        
        finally:
            # 保存结果
            if output_dir:
                self._save_results(output_dir)
        
        return self.state
    
    async def _phase_requirement(self) -> None:
        """需求阶段：接收用户需求"""
        logger.info("Phase: Requirement")
        
        # 发布需求消息
        req_msg = MessageBuilder() \
            .with_type(MessageType.REQUIREMENT) \
            .with_content(self.state.requirement) \
            .with_sender("user") \
            .with_receiver("Alice") \
            .build() # Alice: Product Manager name
        
        self.message_pool.publish(req_msg)
        
        # 等待消息被处理
        await asyncio.sleep(0.5)
    
    async def _phase_prd(self) -> None:
        """PRD阶段：Product Manager生成PRD"""
        logger.info("Phase: PRD Generation")
        self.state.phase = WorkflowPhase.PRD
        
        # 运行Product Manager Agent
        pm_agent = self.agents.get("product_manager")
        if not pm_agent:
            raise RuntimeError("Product Manager agent not found")
        
        executed = await pm_agent.run_once()
        
        if not executed:
            raise RuntimeError("Failed to generate PRD")
        
        # 获取生成的PRD
        prd_messages = self.message_pool.get_messages(msg_type=MessageType.PRD, limit=1)
        if prd_messages:
            self.state.prd = prd_messages[0]
            logger.info("PRD generated successfully")
        else:
            raise RuntimeError("PRD not found in message pool")
        
        await asyncio.sleep(0.5)
    
    async def _phase_design(self) -> None:
        """设计阶段：Architect生成系统设计"""
        logger.info("Phase: System Design")
        self.state.phase = WorkflowPhase.DESIGN
        
        # 运行Architect Agent
        arch_agent = self.agents.get("architect")
        if not arch_agent:
            raise RuntimeError("Architect agent not found")
        
        executed = await arch_agent.run_once()
        
        if not executed:
            raise RuntimeError("Failed to generate system design")
        
        # 获取生成的设计
        design_messages = self.message_pool.get_messages(msg_type=MessageType.DESIGN, limit=1)
        if design_messages:
            self.state.design = design_messages[0]
            logger.info("System design generated successfully")
        else:
            raise RuntimeError("System design not found in message pool")
        
        await asyncio.sleep(0.5)
    
    async def _phase_tasks(self) -> None:
        """任务阶段：Project Manager生成任务列表"""
        logger.info("Phase: Task Breakdown")
        self.state.phase = WorkflowPhase.TASKS
        
        # 运行Project Manager Agent
        pm_agent = self.agents.get("project_manager")
        if not pm_agent:
            raise RuntimeError("Project Manager agent not found")
        
        executed = await pm_agent.run_once()
        
        if not executed:
            raise RuntimeError("Failed to generate task list")
        
        # 获取生成的任务列表
        task_messages = self.message_pool.get_messages(msg_type=MessageType.TASKS, limit=1)
        if task_messages:
            self.state.tasks = task_messages[0]
            logger.info("Task list generated successfully")
        else:
            raise RuntimeError("Task list not found in message pool")
        
        await asyncio.sleep(0.5)
    
    async def _phase_code(self) -> None:
        """代码阶段：Engineer生成代码"""
        logger.info("Phase: Code Implementation")
        self.state.phase = WorkflowPhase.CODE
        
        # 获取要实现的文件列表
        if not isinstance(self.state.tasks, Message):
            raise RuntimeError("Tasks not available")
        
        # 从tasks消息中提取文件列表
        # 这里简化处理，实际应该解析tasks内容
        file_list = ["main.py", "config.py", "utils.py"]  # 示例
        
        # 运行Engineer Agent实现每个文件
        engineer = self.agents.get("engineer")
        if not engineer:
            raise RuntimeError("Engineer agent not found")
        
        for filename in file_list:
            logger.info(f"Implementing {filename}")
            
            # 设置当前文件到工作上下文
            engineer.memory.set_context("current_file", filename)
            engineer.memory.set_context("implemented_files", list(self.state.code_files.keys()))
            
            # 执行代码生成
            executed = await engineer.run_once()
            
            if executed:
                # 获取生成的代码
                code_messages = self.message_pool.get_messages(msg_type=MessageType.CODE, limit=1)
                if code_messages:
                    code_msg = code_messages[-1]
                    self.state.code_files[filename] = code_msg.content
                    logger.info(f"Code for {filename} generated")
            
            # 可执行反馈循环
            if self.config.workflow_config.enable_feedback:
                await self._executable_feedback_loop(filename, engineer)
            
            await asyncio.sleep(0.3)
        
        logger.info(f"Code implementation completed: {len(self.state.code_files)} files")
    
    async def _executable_feedback_loop(self, filename: str, engineer: Agent) -> None:
        """
        可执行反馈循环
        
        Args:
            filename: 文件名
            engineer: Engineer agent
        """
        from tools import get_tool
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            code = self.state.code_files.get(filename, "")
            if not code:
                break
            
            # 尝试执行代码
            exec_tool = get_tool("code_execution")
            if not exec_tool:
                break
            
            result = await exec_tool.execute(code=code)
            
            if result.success:
                logger.info(f"Code execution successful for {filename}")
                break
            else:
                logger.warning(f"Code execution failed for {filename}, retry {retry_count + 1}/{max_retries}")
                
                # 发送反馈消息
                feedback_msg = MessageBuilder() \
                    .with_type(MessageType.FEEDBACK) \
                    .with_content(f"Execution failed: {result.error}") \
                    .with_sender("system") \
                    .with_receiver(engineer.config.name) \
                    .with_metadata({"filename": filename, "error": result.error}) \
                    .build()
                
                self.message_pool.publish(feedback_msg)
                
                # Engineer调试并修复
                engineer.memory.set_context("current_code", code)
                executed = await engineer.run_once()
                
                if executed:
                    # 更新修复后的代码
                    code_messages = self.message_pool.get_messages(msg_type=MessageType.CODE, limit=1)
                    if code_messages:
                        self.state.code_files[filename] = code_messages[-1].content
                
                retry_count += 1
                await asyncio.sleep(0.5)
    
    async def _phase_test(self) -> None:
        """测试阶段：QA Engineer编写测试"""
        logger.info("Phase: Testing")
        self.state.phase = WorkflowPhase.TEST
        
        qa_agent = self.agents.get("qa_engineer")
        if not qa_agent:
            logger.warning("QA Engineer agent not found, skipping tests")
            return
        
        # 为每个代码文件生成测试
        for filename in self.state.code_files.keys():
            logger.info(f"Writing tests for {filename}")
            
            executed = await qa_agent.run_once()
            
            if executed:
                test_messages = self.message_pool.get_messages(msg_type=MessageType.TEST, limit=1)
                if test_messages:
                    self.state.test_results[filename] = {
                        "test_code": test_messages[-1].content,
                        "status": "generated"
                    }
            
            await asyncio.sleep(0.3)
        
        logger.info(f"Tests generated for {len(self.state.test_results)} files")
    
    async def _phase_review(self) -> None:
        """审查阶段：QA Engineer审查代码"""
        logger.info("Phase: Code Review")
        self.state.phase = WorkflowPhase.REVIEW
        
        qa_agent = self.agents.get("qa_engineer")
        if not qa_agent:
            logger.warning("QA Engineer agent not found, skipping review")
            return
        
        # 审查每个代码文件
        for filename in self.state.code_files.keys():
            logger.info(f"Reviewing {filename}")
            
            executed = await qa_agent.run_once()
            
            if executed:
                review_messages = self.message_pool.get_messages(msg_type=MessageType.REVIEW, limit=1)
                if review_messages:
                    self.state.review_results[filename] = {
                        "review": review_messages[-1].content,
                        "passed": review_messages[-1].get_metadata("passed", True)
                    }
            
            await asyncio.sleep(0.3)
        
        logger.info(f"Code review completed for {len(self.state.review_results)} files")
    
    def _save_results(self, output_dir: Path) -> None:
        """
        保存工作流结果
        
        Args:
            output_dir: 输出目录
        """
        try:
            # 保存代码文件
            code_dir = output_dir / "code"
            code_dir.mkdir(exist_ok=True)
            
            for filename, content in self.state.code_files.items():
                file_path = code_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 保存PRD
            if self.state.prd:
                prd_path = output_dir / "PRD.md"
                with open(prd_path, 'w', encoding='utf-8') as f:
                    f.write(self.state.prd.content)
            
            # 保存系统设计
            if self.state.design:
                design_path = output_dir / "SystemDesign.md"
                with open(design_path, 'w', encoding='utf-8') as f:
                    f.write(self.state.design.content)
            
            # 保存任务列表
            if self.state.tasks:
                tasks_path = output_dir / "TaskList.md"
                with open(tasks_path, 'w', encoding='utf-8') as f:
                    f.write(self.state.tasks.content)
            
            # 保存工作流状态
            import json
            state_path = output_dir / "workflow_state.json"
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2)
            
            logger.info(f"Results saved to {output_dir}")
        
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取工作流状态
        
        Returns:
            状态字典
        """
        return {
            "phase": self.state.phase.value,
            "iteration": self.state.iteration,
            "agents": {name: agent.get_status() for name, agent in self.agents.items()},
            "message_pool_stats": self.message_pool.get_stats(),
            "state": self.state.to_dict()
        }
    
    def cleanup(self) -> None:
        """清理资源"""
        for agent in self.agents.values():
            agent.unsubscribe_from_pool()
        
        self.message_pool.clear()
        logger.info("Workflow resources cleaned up")


if __name__ == "__main__":
    # 测试工作流模块
    print("=== Testing Workflow Module ===\n")
    
    async def test_workflow():
        # 创建工作流编排器
        print("1. Creating WorkflowOrchestrator:")
        orchestrator = WorkflowOrchestrator()
        print(f"Initialized {len(orchestrator.agents)} agents\n")
        
        # 运行工作流
        print("2. Running workflow:")
        requirement = "Create a simple calculator application with basic operations"
        output_dir = Path("test_output")
        
        state = await orchestrator.run(requirement, output_dir)
        
        print(f"\n3. Workflow completed:")
        print(f"Phase: {state.phase.value}")
        print(f"Code files: {len(state.code_files)}")
        print(f"Test results: {len(state.test_results)}")
        print(f"Review results: {len(state.review_results)}")
        
        # 获取状态
        print("\n4. Workflow status:")
        status = orchestrator.get_status()
        print(f"Active agents: {len(status['agents'])}")
        print(f"Total messages: {status['message_pool_stats']['total_messages']}")
        
        # 清理
        orchestrator.cleanup()
        
        print("\n=== Workflow Module Test Completed ===")
    
    # 运行异步测试
    asyncio.run(test_workflow())