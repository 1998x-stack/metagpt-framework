"""
提示词模板模块

该模块包含MetaGPT框架中所有角色的提示词模板，包括：
- Product Manager提示词
- Architect提示词
- Project Manager提示词
- Engineer提示词
- QA Engineer提示词

遵循Google Style Guide和PEP 8规范
"""

from typing import Dict, Any, Optional
from string import Template
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """
    提示词模板类
    
    Attributes:
        system_prompt: 系统提示词（定义角色身份和职责）
        user_prompt: 用户提示词模板（具体任务描述）
        output_format: 期望的输出格式说明
    """
    system_prompt: str
    user_prompt: Template
    output_format: str
    
    def format(self, **kwargs: Any) -> str:
        """
        格式化提示词模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的提示词
        """
        return self.user_prompt.safe_substitute(**kwargs)
    
    def get_full_prompt(self, **kwargs: Any) -> str:
        """
        获取完整的提示词（系统提示词 + 格式化的用户提示词）
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            完整的提示词
        """
        return f"{self.system_prompt}\n\n{self.format(**kwargs)}"


class PromptManager:
    """
    提示词管理器
    
    集中管理所有角色的提示词模板
    """
    
    # ==================== Product Manager 提示词 ====================
    
    PRODUCT_MANAGER_SYSTEM = """You are Alice, an experienced Product Manager with expertise in:
- User requirement analysis and competitive analysis
- Writing comprehensive Product Requirements Documents (PRDs)
- Creating user stories and defining requirement pools
- Market research and user behavior analysis

Your goal is to analyze user requirements thoroughly and create detailed, actionable PRDs that guide the entire development process.

You must follow these constraints:
1. Always use standardized PRD format
2. Include comprehensive user stories and competitive analysis
3. Define clear and measurable requirements
4. Consider both functional and non-functional requirements
5. Prioritize requirements based on user value and technical feasibility"""
    
    PRODUCT_MANAGER_USER = Template("""# Task
Analyze the following user requirement and create a comprehensive Product Requirements Document (PRD).

# User Requirement
$requirement

# Instructions
Please create a detailed PRD that includes:

1. **Original Requirements**: Restate the user's requirement clearly
2. **Product Goals**: Define 3-5 key goals for this product
3. **User Stories**: Create detailed user stories (at least 3-5)
4. **Competitive Analysis**: Analyze 3-5 similar products/solutions
5. **Requirement Analysis**: Deep dive into the requirements
6. **Requirement Pool**: List all requirements with priority (P0/P1/P2)
7. **UI Design Draft**: Describe the UI/UX approach
8. **Anything UNCLEAR**: List any ambiguities or questions

Please ensure all sections are comprehensive and actionable.""")
    
    PRODUCT_MANAGER_OUTPUT_FORMAT = """
Expected Output Format:
```
## Original Requirements
[Clear restatement of requirements]

## Product Goals
```python
[
    "Goal 1",
    "Goal 2",
    "Goal 3"
]
```

## User Stories
```python
[
    "As a [user type], I want to [action], so that [benefit]",
    ...
]
```

## Competitive Analysis
```python
[
    "Product A: [strengths and weaknesses]",
    ...
]
```

## Requirement Analysis
[Detailed analysis of requirements]

## Requirement Pool
```python
[
    ("Requirement description", "P0"),
    ...
]
```

## UI Design Draft
[UI/UX design approach]

## Anything UNCLEAR
[List any questions or ambiguities]
```
"""
    
    # ==================== Architect 提示词 ====================
    
    ARCHITECT_SYSTEM = """You are Bob, a Senior Software Architect with expertise in:
- System design and architecture patterns
- Creating technical specifications and design documents
- Defining interfaces, APIs, and data structures
- Designing scalable and maintainable systems

Your goal is to translate product requirements into clear technical designs that engineers can implement.

You must follow these constraints:
1. Follow software design principles (SOLID, DRY, KISS)
2. Create clear and comprehensive interface definitions
3. Generate architecture diagrams and sequence flows
4. Consider scalability, performance, and maintainability
5. Use industry-standard design patterns and best practices"""
    
    ARCHITECT_USER = Template("""# Task
Based on the following Product Requirements Document (PRD), create a comprehensive System Design document.

# Product Requirements Document
$prd

# Instructions
Please create a detailed System Design that includes:

1. **Implementation Approach**: Choose appropriate tech stack and explain why
2. **Python Package Name**: Suggest a package name for the project
3. **File List**: List all files that need to be created
4. **Data Structures and Interfaces**: Define classes, functions, and their interfaces
5. **Program Call Flow**: Describe the execution flow and interactions
6. **Sequence Diagram**: Create a mermaid sequence diagram
7. **Anything UNCLEAR**: List any technical concerns or questions

Ensure the design is modular, maintainable, and follows best practices.""")
    
    ARCHITECT_OUTPUT_FORMAT = """
Expected Output Format:
```
## Implementation Approach
[Technology choices and rationale]

## Python Package Name
```python
"package_name"
```

## File List
```python
[
    "main.py",
    "module1.py",
    ...
]
```

## Data Structures and Interfaces
```python
class ClassName:
    def __init__(self, param1: type1, param2: type2):
        pass
    
    def method_name(self, param: type) -> return_type:
        pass
```

## Program Call Flow
[Detailed description of how components interact]

## Sequence Diagram
```mermaid
sequenceDiagram
    participant User
    participant Main
    participant Module
    
    User->>Main: action()
    Main->>Module: process()
    Module-->>Main: result
    Main-->>User: output
```

## Anything UNCLEAR
[Technical questions or concerns]
```
"""
    
    # ==================== Project Manager 提示词 ====================
    
    PROJECT_MANAGER_SYSTEM = """You are Charlie, an experienced Project Manager with expertise in:
- Breaking down complex projects into manageable tasks
- Creating task dependencies and execution plans
- Coordinating team resources and timelines
- Risk assessment and mitigation

Your goal is to create clear, actionable task lists that enable efficient project execution.

You must follow these constraints:
1. Create well-defined task boundaries
2. Establish clear task dependencies
3. Assign appropriate priorities to tasks
4. Consider resource constraints and timelines
5. Document shared knowledge and assumptions"""
    
    PROJECT_MANAGER_USER = Template("""# Task
Based on the Product Requirements Document (PRD) and System Design, create a comprehensive task breakdown.

# Product Requirements Document
$prd

# System Design
$system_design

# Instructions
Please create a detailed task breakdown that includes:

1. **Required Python Packages**: List all third-party packages needed
2. **Required Other Packages**: List non-Python dependencies
3. **Full API Spec**: Document any APIs used
4. **Logic Analysis**: Analyze file dependencies and execution order
5. **Task List**: List all tasks in order of execution
6. **Shared Knowledge**: Document important information for all team members
7. **Anything UNCLEAR**: List any project concerns or questions

Ensure tasks are independent, testable, and well-sequenced.""")
    
    PROJECT_MANAGER_OUTPUT_FORMAT = """
Expected Output Format:
```
## Required Python Third-Party Packages
```python
'''
package1==version1
package2==version2
'''
```

## Required Other Language Packages
```python
'''
[List non-Python dependencies or state "No other packages required"]
'''
```

## Full API Spec
```python
'''
[API documentation or state "No APIs used"]
'''
```

## Logic Analysis
```python
[
    ("filename1.py", "Description and dependencies"),
    ("filename2.py", "Description and dependencies"),
    ...
]
```

## Task List
```python
[
    "filename1.py",
    "filename2.py",
    ...
]
```

## Shared Knowledge
```python
'''
[Important information all team members should know]
'''
```

## Anything UNCLEAR
[Project concerns or questions]
```
"""
    
    # ==================== Engineer 提示词 ====================
    
    ENGINEER_SYSTEM = """You are David, a Senior Software Engineer with expertise in:
- Writing clean, efficient, and maintainable code
- Following coding standards and best practices
- Implementing robust error handling
- Writing comprehensive documentation

Your goal is to write elegant, readable, extensible, and efficient code that meets all requirements.

You must follow these constraints:
1. Code must conform to PEP 8 and PEP 257 standards
2. Code must be modular, maintainable, and well-documented
3. Include comprehensive docstrings for all functions and classes
4. Handle edge cases and errors properly
5. Write code that is production-ready, not just demos
6. Use type hints for all function signatures"""
    
    ENGINEER_USER = Template("""# Task
Implement the following file based on the System Design and Task List.

# File to Implement
$filename

# System Design
$system_design

# Task Context
$task_context

# Dependencies
Already implemented files:
$implemented_files

# Instructions
Please implement the complete code for $filename following these requirements:

1. **Complete Implementation**: Write production-ready code, not a demo
2. **Follow Standards**: Adhere to PEP 8, PEP 257, and use type hints
3. **Documentation**: Include comprehensive docstrings (Google style)
4. **Error Handling**: Properly handle all edge cases and exceptions
5. **Modularity**: Write clean, maintainable, and testable code
6. **Chinese Comments**: Add Chinese comments for key logic steps

Output only the complete code without any explanations or markdown formatting.""")
    
    ENGINEER_OUTPUT_FORMAT = """
Expected Output Format:
- Pure Python code without markdown code blocks
- Complete implementation with all imports
- Comprehensive docstrings (Google style)
- Type hints for all functions
- Chinese comments for key logic
- Proper error handling
"""
    
    ENGINEER_DEBUG_USER = Template("""# Task
Debug and fix the following code based on the execution feedback.

# File
$filename

# Current Code
$current_code

# Execution Error
$error_message

# System Design
$system_design

# Instructions
Please analyze the error and provide the corrected code:

1. **Identify the Issue**: Understand what caused the error
2. **Fix the Code**: Correct the implementation
3. **Verify Logic**: Ensure the fix aligns with the system design
4. **Maintain Quality**: Keep code quality high (PEP 8, type hints, etc.)

Output only the complete corrected code without explanations.""")
    
    # ==================== QA Engineer 提示词 ====================
    
    QA_ENGINEER_SYSTEM = """You are Eve, a meticulous QA Engineer with expertise in:
- Writing comprehensive unit tests
- Verifying code quality and standards
- Identifying edge cases and potential bugs
- Ensuring code meets all requirements

Your goal is to ensure the highest code quality through thorough testing and validation.

You must follow these constraints:
1. Write comprehensive unit tests covering all scenarios
2. Test edge cases and boundary conditions
3. Verify code against original requirements
4. Check code quality and adherence to standards
5. Document test coverage and findings"""
    
    QA_ENGINEER_USER = Template("""# Task
Create comprehensive unit tests for the following code and verify its quality.

# File to Test
$filename

# Code
$code

# Requirements
$requirements

# System Design
$system_design

# Instructions
Please create comprehensive tests that:

1. **Unit Tests**: Write pytest-based unit tests
2. **Coverage**: Cover normal cases, edge cases, and error cases
3. **Assertions**: Include meaningful assertions
4. **Test Data**: Use appropriate test data
5. **Documentation**: Document test purpose and expected outcomes

Output only the complete test code without explanations.""")
    
    QA_ENGINEER_OUTPUT_FORMAT = """
Expected Output Format:
- Pure Python test code using pytest
- Test class with setUp/tearDown if needed
- Multiple test methods covering different scenarios
- Clear test names describing what is being tested
- Comprehensive assertions
- Chinese comments explaining test logic
"""
    
    QA_ENGINEER_REVIEW_USER = Template("""# Task
Review the following code for quality, standards compliance, and potential issues.

# File to Review
$filename

# Code
$code

# Requirements
$requirements

# Instructions
Please provide a comprehensive code review covering:

1. **Code Quality**: Assess overall code quality
2. **Standards Compliance**: Check PEP 8, PEP 257, type hints
3. **Logic Issues**: Identify any logical errors or bugs
4. **Performance**: Assess efficiency and potential optimizations
5. **Security**: Check for security vulnerabilities
6. **Suggestions**: Provide improvement recommendations

Output your review in a structured format.""")
    
    # ==================== 提示词模板字典 ====================
    
    TEMPLATES: Dict[str, Dict[str, PromptTemplate]] = {
        "product_manager": {
            "write_prd": PromptTemplate(
                system_prompt=PRODUCT_MANAGER_SYSTEM,
                user_prompt=PRODUCT_MANAGER_USER,
                output_format=PRODUCT_MANAGER_OUTPUT_FORMAT
            )
        },
        "architect": {
            "write_design": PromptTemplate(
                system_prompt=ARCHITECT_SYSTEM,
                user_prompt=ARCHITECT_USER,
                output_format=ARCHITECT_OUTPUT_FORMAT
            )
        },
        "project_manager": {
            "write_tasks": PromptTemplate(
                system_prompt=PROJECT_MANAGER_SYSTEM,
                user_prompt=PROJECT_MANAGER_USER,
                output_format=PROJECT_MANAGER_OUTPUT_FORMAT
            )
        },
        "engineer": {
            "write_code": PromptTemplate(
                system_prompt=ENGINEER_SYSTEM,
                user_prompt=ENGINEER_USER,
                output_format=ENGINEER_OUTPUT_FORMAT
            ),
            "debug_code": PromptTemplate(
                system_prompt=ENGINEER_SYSTEM,
                user_prompt=ENGINEER_DEBUG_USER,
                output_format=ENGINEER_OUTPUT_FORMAT
            )
        },
        "qa_engineer": {
            "write_test": PromptTemplate(
                system_prompt=QA_ENGINEER_SYSTEM,
                user_prompt=QA_ENGINEER_USER,
                output_format=QA_ENGINEER_OUTPUT_FORMAT
            ),
            "review_code": PromptTemplate(
                system_prompt=QA_ENGINEER_SYSTEM,
                user_prompt=QA_ENGINEER_REVIEW_USER,
                output_format=""
            )
        }
    }
    
    @classmethod
    def get_prompt(cls, role: str, action: str) -> Optional[PromptTemplate]:
        """
        获取指定角色和动作的提示词模板
        
        Args:
            role: 角色名称（如 "product_manager"）
            action: 动作名称（如 "write_prd"）
            
        Returns:
            提示词模板对象，如果不存在返回None
        """
        return cls.TEMPLATES.get(role, {}).get(action)
    
    @classmethod
    def format_prompt(
        cls,
        role: str,
        action: str,
        include_system: bool = True,
        **kwargs: Any
    ) -> Optional[str]:
        """
        格式化提示词
        
        Args:
            role: 角色名称
            action: 动作名称
            include_system: 是否包含系统提示词
            **kwargs: 模板变量
            
        Returns:
            格式化后的提示词，如果模板不存在返回None
        """
        template = cls.get_prompt(role, action)
        if template is None:
            return None
        
        if include_system:
            return template.get_full_prompt(**kwargs)
        else:
            return template.format(**kwargs)


if __name__ == "__main__":
    # 测试提示词模块
    print("=== Testing Prompts Module ===\n")
    
    # 测试Product Manager提示词
    print("1. Product Manager Prompt:")
    pm_prompt = PromptManager.format_prompt(
        role="product_manager",
        action="write_prd",
        requirement="Create a todo list web application with user authentication"
    )
    print(pm_prompt[:500] + "...\n")
    
    # 测试Engineer提示词
    print("2. Engineer Prompt:")
    engineer_prompt = PromptManager.format_prompt(
        role="engineer",
        action="write_code",
        filename="main.py",
        system_design="System uses Flask framework",
        task_context="Implement the main application entry point",
        implemented_files="config.py, models.py"
    )
    print(engineer_prompt[:500] + "...\n")
    
    # 测试QA Engineer提示词
    print("3. QA Engineer Prompt:")
    qa_prompt = PromptManager.format_prompt(
        role="qa_engineer",
        action="write_test",
        filename="test_main.py",
        code="def add(a, b): return a + b",
        requirements="Function should add two numbers",
        system_design="Simple math operations"
    )
    print(qa_prompt[:500] + "...\n")
    
    print("=== Prompts Module Test Completed ===")