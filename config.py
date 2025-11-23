"""
配置管理模块

该模块负责管理整个MetaGPT框架的配置信息，包括：
- LLM API配置
- 日志配置
- 工作流配置
- 角色配置
- 工具配置

遵循Google Style Guide和PEP 8规范
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举类"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(Enum):
    """LLM提供商枚举类"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    LOCAL = "local"


@dataclass
class LLMConfig:
    """
    LLM配置类
    
    Attributes:
        provider: LLM提供商
        api_key: API密钥
        model_name: 模型名称
        temperature: 生成温度
        max_tokens: 最大token数
        timeout: 请求超时时间
        base_url: API基础URL（可选）
        organization: 组织ID（可选）
    """
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: str = ""
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    base_url: Optional[str] = None
    organization: Optional[str] = None
    
    def __post_init__(self):
        """初始化后验证配置"""
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        
        if not self.api_key and self.provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]:
            raise ValueError(f"API key is required for {self.provider.value}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "base_url": self.base_url,
            "organization": self.organization
        }


@dataclass
class LogConfig:
    """
    日志配置类
    
    Attributes:
        level: 日志级别
        log_dir: 日志目录
        log_file: 日志文件名
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        max_bytes: 单个日志文件最大字节数
        backup_count: 日志文件备份数量
        format_string: 日志格式字符串
    """
    level: LogLevel = LogLevel.INFO
    log_dir: Path = Path("logs")
    log_file: str = "metagpt.log"
    console_output: bool = True
    file_output: bool = True
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """确保日志目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def log_path(self) -> Path:
        """获取完整日志文件路径"""
        return self.log_dir / self.log_file


@dataclass
class WorkflowConfig:
    """
    工作流配置类
    
    Attributes:
        max_iterations: 最大迭代次数
        enable_feedback: 是否启用可执行反馈机制
        enable_review: 是否启用代码审查
        enable_testing: 是否启用测试
        output_dir: 输出目录
        workspace_dir: 工作空间目录
    """
    max_iterations: int = 3
    enable_feedback: bool = True
    enable_review: bool = True
    enable_testing: bool = True
    output_dir: Path = Path("output")
    workspace_dir: Path = Path("workspace")
    
    def __post_init__(self):
        """确保目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class RoleConfig:
    """
    角色配置类
    
    Attributes:
        name: 角色名称
        profile: 角色简介
        goal: 角色目标
        constraints: 角色约束
        tools: 可用工具列表
    """
    name: str
    profile: str
    goal: str
    constraints: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "profile": self.profile,
            "goal": self.goal,
            "constraints": self.constraints,
            "tools": self.tools
        }


@dataclass
class ToolConfig:
    """
    工具配置类
    
    Attributes:
        name: 工具名称
        enabled: 是否启用
        config: 工具特定配置
    """
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class Config:
    """
    全局配置管理类
    
    负责管理所有配置项，提供配置的加载、保存和访问功能。
    采用单例模式确保全局唯一配置实例。
    """
    
    _instance: Optional['Config'] = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置"""
        if self._initialized:
            return
        
        # 基础配置
        self.llm_config = LLMConfig()
        self.log_config = LogConfig()
        self.workflow_config = WorkflowConfig()
        
        # 角色配置
        self.roles: Dict[str, RoleConfig] = self._init_default_roles()
        
        # 工具配置
        self.tools: Dict[str, ToolConfig] = self._init_default_tools()
        
        # 其他配置
        self.project_name: str = "metagpt_project"
        self.project_root: Path = Path.cwd()
        
        self._initialized = True
    
    def _init_default_roles(self) -> Dict[str, RoleConfig]:
        """
        初始化默认角色配置
        
        Returns:
            角色配置字典
        """
        return {
            "product_manager": RoleConfig(
                name="Alice",
                profile="Product Manager",
                goal="Analyze user requirements and create comprehensive Product Requirements Documents (PRD)",
                constraints=[
                    "Must follow standardized PRD format",
                    "Must include user stories and competitive analysis",
                    "Must define clear requirements pool"
                ],
                tools=["web_search"]
            ),
            "architect": RoleConfig(
                name="Bob",
                profile="Architect",
                goal="Design system architecture and technical specifications",
                constraints=[
                    "Must follow software design principles",
                    "Must create clear interface definitions",
                    "Must generate sequence diagrams and class diagrams"
                ],
                tools=["diagram_tool"]
            ),
            "project_manager": RoleConfig(
                name="Charlie",
                profile="Project Manager",
                goal="Break down requirements into actionable tasks",
                constraints=[
                    "Must create clear task dependencies",
                    "Must assign tasks to appropriate roles",
                    "Must estimate task complexity"
                ],
                tools=["diagram_tool"]
            ),
            "engineer": RoleConfig(
                name="David",
                profile="Engineer",
                goal="Write elegant, readable, extensible, efficient code",
                constraints=[
                    "Code must conform to PEP 8 standards",
                    "Code must be modular and maintainable",
                    "Must include comprehensive docstrings",
                    "Must handle edge cases properly"
                ],
                tools=["debugging_tool", "code_execution"]
            ),
            "qa_engineer": RoleConfig(
                name="Eve",
                profile="QA Engineer",
                goal="Ensure code quality through comprehensive testing",
                constraints=[
                    "Must write comprehensive unit tests",
                    "Must verify code against requirements",
                    "Must check code quality and standards"
                ],
                tools=["web_search", "code_execution"]
            )
        }
    
    def _init_default_tools(self) -> Dict[str, ToolConfig]:
        """
        初始化默认工具配置
        
        Returns:
            工具配置字典
        """
        return {
            "web_search": ToolConfig(
                name="web_search",
                enabled=True,
                config={
                    "search_engine": "google",
                    "max_results": 10
                }
            ),
            "diagram_tool": ToolConfig(
                name="diagram_tool",
                enabled=True,
                config={
                    "formats": ["mermaid", "plantuml"],
                    "default_format": "mermaid"
                }
            ),
            "debugging_tool": ToolConfig(
                name="debugging_tool",
                enabled=True,
                config={
                    "breakpoint_enabled": True,
                    "trace_enabled": True
                }
            ),
            "code_execution": ToolConfig(
                name="code_execution",
                enabled=True,
                config={
                    "timeout": 30,
                    "sandbox_mode": True
                }
            )
        }
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Config':
        """
        从配置文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置实例
        """
        config = cls()
        path = Path(config_path)
        
        if not path.exists():
            print(f"Warning: Config file {config_path} not found, using default config")
            return config
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif path.suffix == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {path.suffix}")
            
            # 更新配置
            config._update_from_dict(data)
            print(f"Successfully loaded config from {config_path}")
            
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            print("Using default config instead")
        
        return config
    
    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        从字典更新配置
        
        Args:
            data: 配置数据字典
        """
        # 更新LLM配置
        if 'llm' in data:
            llm_data = data['llm']
            self.llm_config.provider = LLMProvider(llm_data.get('provider', 'openai'))
            self.llm_config.model_name = llm_data.get('model_name', 'gpt-4')
            self.llm_config.temperature = llm_data.get('temperature', 0.7)
            self.llm_config.max_tokens = llm_data.get('max_tokens', 4096)
        
        # 更新日志配置
        if 'logging' in data:
            log_data = data['logging']
            self.log_config.level = LogLevel(log_data.get('level', 'INFO'))
            self.log_config.console_output = log_data.get('console_output', True)
            self.log_config.file_output = log_data.get('file_output', True)
        
        # 更新工作流配置
        if 'workflow' in data:
            wf_data = data['workflow']
            self.workflow_config.max_iterations = wf_data.get('max_iterations', 3)
            self.workflow_config.enable_feedback = wf_data.get('enable_feedback', True)
        
        # 更新项目配置
        if 'project' in data:
            self.project_name = data['project'].get('name', 'metagpt_project')
    
    def save_to_file(self, config_path: str) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
        """
        path = Path(config_path)
        
        config_dict = {
            'llm': self.llm_config.to_dict(),
            'logging': {
                'level': self.log_config.level.value,
                'console_output': self.log_config.console_output,
                'file_output': self.log_config.file_output
            },
            'workflow': {
                'max_iterations': self.workflow_config.max_iterations,
                'enable_feedback': self.workflow_config.enable_feedback,
                'enable_review': self.workflow_config.enable_review,
                'enable_testing': self.workflow_config.enable_testing
            },
            'project': {
                'name': self.project_name
            },
            'roles': {k: v.to_dict() for k, v in self.roles.items()}
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    yaml.safe_dump(config_dict, f, default_flow_style=False)
                elif path.suffix == '.json':
                    json.dump(config_dict, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {path.suffix}")
            
            print(f"Successfully saved config to {config_path}")
            
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
    
    def get_role_config(self, role_type: str) -> Optional[RoleConfig]:
        """
        获取指定角色的配置
        
        Args:
            role_type: 角色类型
            
        Returns:
            角色配置，如果不存在返回None
        """
        return self.roles.get(role_type)
    
    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """
        获取指定工具的配置
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具配置，如果不存在返回None
        """
        return self.tools.get(tool_name)
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        检查工具是否启用
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具是否启用
        """
        tool_config = self.get_tool_config(tool_name)
        return tool_config.enabled if tool_config else False
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Config(\n"
            f"  project_name='{self.project_name}',\n"
            f"  llm_provider={self.llm_config.provider.value},\n"
            f"  llm_model={self.llm_config.model_name},\n"
            f"  log_level={self.log_config.level.value},\n"
            f"  max_iterations={self.workflow_config.max_iterations}\n"
            f")"
        )


# 全局配置实例
config = Config()


if __name__ == "__main__":
    # 测试配置模块
    print("=== Testing Config Module ===")
    
    # 创建配置实例
    cfg = Config()
    print(f"\n1. Default Config:\n{cfg}")
    
    # 测试角色配置
    pm_config = cfg.get_role_config("product_manager")
    print(f"\n2. Product Manager Config:\n{pm_config}")
    
    # 测试工具配置
    web_search_enabled = cfg.is_tool_enabled("web_search")
    print(f"\n3. Web Search Enabled: {web_search_enabled}")
    
    # 保存配置
    cfg.save_to_file("config_test.yaml")
    print("\n4. Config saved to config_test.yaml")
    
    # 加载配置
    cfg2 = Config.load_from_file("config_test.yaml")
    print(f"\n5. Loaded Config:\n{cfg2}")
    
    print("\n=== Config Module Test Completed ===")