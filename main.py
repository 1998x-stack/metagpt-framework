"""
MetaGPT 主入口模块

该模块提供MetaGPT框架的命令行接口和主要入口点：
- CLI命令行接口
- 配置加载
- 工作流执行
- 结果输出

遵循Google Style Guide和PEP 8规范
"""

import argparse
import sys
import asyncio
from pathlib import Path
from typing import Optional
import json

from config import Config
from logger import setup_logging_from_config, get_logger
from workflow import WorkflowOrchestrator, WorkflowPhase


# 初始化日志
logger = get_logger(__name__)


class MetaGPT:
    """
    MetaGPT主类
    
    提供高层API for框架使用
    
    Attributes:
        config: 全局配置
        orchestrator: 工作流编排器
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化MetaGPT
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        if config_path:
            self.config = Config.load_from_file(config_path)
        else:
            self.config = Config()
        
        # 设置日志
        setup_logging_from_config(self.config)
        
        # 创建工作流编排器
        self.orchestrator = WorkflowOrchestrator(self.config)
        
        logger.info("MetaGPT initialized")
    
    async def run(
        self,
        requirement: str,
        output_dir: Optional[Path] = None
    ) -> dict:
        """
        运行MetaGPT工作流
        
        Args:
            requirement: 用户需求描述
            output_dir: 输出目录
            
        Returns:
            执行结果字典
        """
        logger.info(f"Starting MetaGPT with requirement: {requirement}")
        
        # 设置输出目录
        if output_dir is None:
            output_dir = self.config.workflow_config.output_dir / self.config.project_name
        
        output_dir = Path(output_dir)
        
        try:
            # 运行工作流
            state = await self.orchestrator.run(requirement, output_dir)
            
            # 构建结果
            result = {
                "success": state.phase == WorkflowPhase.COMPLETE,
                "phase": state.phase.value,
                "output_dir": str(output_dir),
                "code_files": list(state.code_files.keys()),
                "test_results": len(state.test_results),
                "review_results": len(state.review_results),
                "metadata": state.metadata
            }
            
            if state.phase == WorkflowPhase.COMPLETE:
                logger.info("MetaGPT completed successfully")
            else:
                logger.error(f"MetaGPT failed at phase: {state.phase.value}")
            
            return result
        
        except Exception as e:
            logger.error(f"MetaGPT execution error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "output_dir": str(output_dir)
            }
        
        finally:
            # 清理资源
            self.orchestrator.cleanup()
    
    def get_status(self) -> dict:
        """
        获取当前状态
        
        Returns:
            状态字典
        """
        return self.orchestrator.get_status()


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        ArgumentParser实例
    """
    parser = argparse.ArgumentParser(
        prog="metagpt",
        description="MetaGPT - A Multi-Agent Framework for Software Development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 使用默认配置运行
  python main.py "Create a todo list app"
  
  # 指定配置文件
  python main.py "Create a calculator" --config config.yaml
  
  # 指定输出目录
  python main.py "Create a game" --output ./my_project
  
  # 设置项目名称
  python main.py "Create a website" --project-name my_website
  
  # 显示详细日志
  python main.py "Create an API" --verbose

For more information, visit: https://github.com/geekan/MetaGPT
        """
    )
    
    # 必需参数
    parser.add_argument(
        "requirement",
        type=str,
        help="User requirement description (e.g., 'Create a todo list application')"
    )
    
    # 可选参数
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file (YAML or JSON)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory for generated code and documents"
    )
    
    parser.add_argument(
        "-p", "--project-name",
        type=str,
        default=None,
        help="Project name (used for output directory if --output not specified)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of iterations for code generation feedback loop"
    )
    
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Disable executable feedback mechanism"
    )
    
    parser.add_argument(
        "--no-testing",
        action="store_true",
        help="Disable test generation"
    )
    
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="Disable code review"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="MetaGPT v1.0.0"
    )
    
    return parser


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ███╗   ███╗███████╗████████╗ █████╗  ██████╗ ██████╗ ████████╗   ║
║   ████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔════╝ ██╔══██╗╚══██╔══╝   ║
║   ██╔████╔██║█████╗     ██║   ███████║██║  ███╗██████╔╝   ██║      ║
║   ██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██║   ██║██╔═══╝    ██║      ║
║   ██║ ╚═╝ ██║███████╗   ██║   ██║  ██║╚██████╔╝██║        ██║      ║
║   ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝        ╚═╝      ║
║                                                                ║
║         Multi-Agent Framework for Software Development        ║
║                        Version 1.0.0                          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_result_summary(result: dict):
    """
    打印执行结果摘要
    
    Args:
        result: 执行结果字典
    """
    print("\n" + "="*70)
    print("EXECUTION SUMMARY".center(70))
    print("="*70 + "\n")
    
    if result["success"]:
        print("✅ Status: SUCCESS")
        print(f"📁 Output Directory: {result['output_dir']}")
        print(f"📝 Generated Files: {len(result['code_files'])}")
        
        if result['code_files']:
            print("\nGenerated Code Files:")
            for filename in result['code_files']:
                print(f"  • {filename}")
        
        if result.get('test_results', 0) > 0:
            print(f"\n🧪 Test Files: {result['test_results']}")
        
        if result.get('review_results', 0) > 0:
            print(f"✔️  Code Reviews: {result['review_results']}")
    else:
        print("❌ Status: FAILED")
        if 'phase' in result:
            print(f"⚠️  Failed at phase: {result['phase']}")
        if 'error' in result:
            print(f"🔴 Error: {result['error']}")
    
    print("\n" + "="*70 + "\n")


async def main_async(args: argparse.Namespace) -> int:
    """
    异步主函数
    
    Args:
        args: 命令行参数
        
    Returns:
        退出码（0表示成功，1表示失败）
    """
    try:
        # 打印横幅
        print_banner()
        
        # 创建MetaGPT实例
        print("🚀 Initializing MetaGPT...")
        metagpt = MetaGPT(config_path=args.config)
        
        # 应用命令行参数
        if args.project_name:
            metagpt.config.project_name = args.project_name
        
        if args.verbose:
            metagpt.config.log_config.level = "DEBUG"
            setup_logging_from_config(metagpt.config)
        
        if args.max_iterations:
            metagpt.config.workflow_config.max_iterations = args.max_iterations
        
        if args.no_feedback:
            metagpt.config.workflow_config.enable_feedback = False
        
        if args.no_testing:
            metagpt.config.workflow_config.enable_testing = False
        
        if args.no_review:
            metagpt.config.workflow_config.enable_review = False
        
        # 设置输出目录
        output_dir = Path(args.output) if args.output else None
        
        # 显示配置信息
        print(f"\n📋 Configuration:")
        print(f"  • Project Name: {metagpt.config.project_name}")
        print(f"  • Max Iterations: {metagpt.config.workflow_config.max_iterations}")
        print(f"  • Feedback: {'Enabled' if metagpt.config.workflow_config.enable_feedback else 'Disabled'}")
        print(f"  • Testing: {'Enabled' if metagpt.config.workflow_config.enable_testing else 'Disabled'}")
        print(f"  • Review: {'Enabled' if metagpt.config.workflow_config.enable_review else 'Disabled'}")
        
        # 显示需求
        print(f"\n💡 Requirement:")
        print(f"  {args.requirement}")
        print()
        
        # 运行MetaGPT
        print("⚙️  Starting workflow...\n")
        result = await metagpt.run(args.requirement, output_dir)
        
        # 打印结果摘要
        print_result_summary(result)
        
        # 保存结果到JSON
        if output_dir:
            result_file = Path(result['output_dir']) / "result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"📄 Full result saved to: {result_file}\n")
        
        return 0 if result["success"] else 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        return 1


def main() -> int:
    """
    主函数
    
    Returns:
        退出码
    """
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 运行异步主函数
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())