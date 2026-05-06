import os
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from langchain.tools import tool

from config import settings,get_logger


logger = get_logger(__name__)




class ResearchFileSystem:
    
    
    
    def __init__(self,thread_id:str,base_path:Optional[str] = None) -> None:
        """
        初始化研究文件系统
        
        Args:
            thread_id: 研究任务的唯一标识符
            base_path: 文件系统根目录，默认使用配置中的路径
        """
        
        if base_path is None:
            base_path = os.path.join(settings.DATA_DIR,"research")
            
        self.base_path = Path(base_path)
        
        self.workspace_path = self.base_path / thread_id
        
        self._init_workspace()
        
        logger.info(f"📁 初始化研究文件系统: {self.workspace_path}")
        
        
    
    def _init_workspace(self) -> None:
        """
        初始化工作空间目录结构
        
        创建以下目录：
        - plans/: 存储研究计划
        - notes/: 存储研究笔记
        - reports/: 存储最终报告
        - temp/: 存储临时文件
        """
        
        directories = [
            self.workspace_path / "plans",
            self.workspace_path / "notes",
            self.workspace_path / "reports",
            self.workspace_path / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.debug(f"   工作空间目录已创建: {self.workspace_path}")
        
    def write_file(
        self,
        filename:str,
        content: str,
        subdirectory: Optional[str] = None,
        metadata:Optional[dict[str,Any]] = None
    ):
        """
        写入文件（同步操作，确保写入完成）
        
        Args:
            filename: 文件名
            content: 文件内容
            subdirectory: 子目录（plans/notes/reports/temp）
            metadata: 文件元数据（可选）
            
        Returns:
            文件的完整路径
            
        Example:
            >>> fs.write_file("plan.md", "# 研究计划", subdirectory="plans")
            '/path/to/research/thread_123/plans/plan.md'
        """  
        
        # 确定文件路径
        if subdirectory:
            file_path = self.workspace_path / subdirectory / filename
        else:
            file_path = self.workspace_path / filename
            
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path,'w',encoding='utf-8') as f:
                f.write(content)
                
                f.flush()
                import os
                os.fsync(f.fileno())
                
            if metadata:
                metadata_path = file_path.with_suffix(file_path.suffix + ".meta.json")
                metadata['created_at'] = datetime.now().isoformat()
                metadata['filename'] = filename
                
                with open(metadata_path,'w',encoding='utf-8') as f:
                    json.dump(metadata,f,ensure_ascii=False,indent=2)
                    
                    f.flush()
                    
                    os.fsync(f.fileno())
            
            logger.info(f"✅ 文件已写入: {file_path.relative_to(self.base_path)}")
            return str(file_path)   
        
        
        except Exception as e:
            logger.error(f"❌ 写入文件失败: {e}")
            raise
        
        
    def read_file(self,filename:str,subdirectory: Optional[str] = None) -> str:
        """
        读取文件内容
        
        Args:
            filename: 文件名
            subdirectory: 子目录
            
        Returns:
            文件内容
            
        Raises:
            FileNotFoundError: 如果文件不存在
            
        Example:
            >>> content = fs.read_file("plan.md", subdirectory="plans")
        """
        
        if subdirectory:
            filepath = self.workspace_path / subdirectory / filename
        else:
            filepath = self.workspace_path / filename
            
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: { filename}")
        
        try:
            with open(filepath,'r',encoding='utf-8') as f:
                content = f.read()
                
            logger.debug(f"📖 文件已读取: {filepath.relative_to(self.base_path)}")
            return content
        
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {e}")
            raise
        
    
    
    def list_files(self,subdirectory: Optional[str] = None,pattern:str = "*") -> list[str]:
        """
        列出文件
        
        Args:
            subdirectory: 子目录，None 表示列出所有文件
            pattern: 文件名模式（支持通配符）
            
        Returns:
            文件名列表
            
        Example:
            >>> files = fs.list_files(subdirectory="notes")
            >>> md_files = fs.list_files(pattern="*.md")
        """
        
        if subdirectory:
            search_path = self.workspace_path / subdirectory
        else:
            search_path = self.workspace_path
            
        files = []
        
        for file_path in search_path.glob(pattern):
            if file_path.is_file() and not file_path.name.endswith('.meta.json'):
                relative_path = file_path.relative_to(self.workspace_path)
                
                files.append(str(relative_path))
        logger.debug(f"📋 列出文件: {len(files)} 个文件")
        
        return files
    
    
    def delete_file(self,filename:str,subdirectory: Optional[str] = None) -> bool:
        """
        删除文件
        
        Args:
            filename: 文件名
            subdirectory: 子目录
            
        Returns:
            是否成功删除
            
        Example:
            >>> success = fs.delete_file("old_plan.md", subdirectory="plans")
        """
        
        if subdirectory:
            file_path = self.workspace_path / subdirectory / filename
        else:
            file_path = self.workspace_path / filename
            
        if not file_path.exists():
            logger.warning(f"⚠️ 文件不存在，无法删除: {file_path.relative_to(self.base_path)}")
            return False
        
        try:
            file_path.unlink()
            
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta.json")
            if metadata_path.exists():
                metadata_path.unlink()
                
            logger.info(f"🗑️ 文件已删除: {file_path.relative_to(self.base_path)}")
            return True
        
        except Exception as e:
            logger.error(f"❌ 删除文件失败: {e}")
            return False
        
    
    
    def file_exists(
        self,
        filename: str,
        subdirectory: Optional[str] = None,
    ) -> bool:
        """
        检查文件是否存在
        
        Args:
            filename: 文件名
            subdirectory: 子目录
            
        Returns:
            文件是否存在
        """
        if subdirectory:
            file_path = self.workspace_path / subdirectory / filename
        else:
            file_path = self.workspace_path / filename
        
        return file_path.exists()
    
    def get_file_info(
        self,
        filename: str,
        subdirectory: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        获取文件信息
        
        Args:
            filename: 文件名
            subdirectory: 子目录
            
        Returns:
            文件信息字典
            
        Example:
            >>> info = fs.get_file_info("plan.md", subdirectory="plans")
            >>> print(info['size'], info['modified_at'])
        """
        if subdirectory:
            file_path = self.workspace_path / subdirectory / filename
        else:
            file_path = self.workspace_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {filename}")
        
        stat = file_path.stat()
        
        info = {
            "filename": filename,
            "path": str(file_path),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
        
        # 读取元数据（如果存在）
        metadata_path = file_path.with_suffix(file_path.suffix + '.meta.json')
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    info['metadata'] = metadata
            except Exception as e:
                logger.warning(f"⚠️ 读取元数据失败: {e}")
        
        return info
    
    
    
    def search_files(
        self,
        keyword: str,
        subdirectory: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        搜索包含关键词的文件
        
        Args:
            keyword: 搜索关键词
            subdirectory: 子目录
            
        Returns:
            匹配的文件列表，每个元素包含文件名和匹配的行
            
        Example:
            >>> results = fs.search_files("机器学习")
            >>> for result in results:
            ...     print(result['filename'], result['matches'])
        """
        if subdirectory:
            search_path = self.workspace_path / subdirectory
        else:
            search_path = self.workspace_path
        
        if not search_path.exists():
            return []
        
        results = []
        
        # 递归搜索所有文本文件
        for file_path in search_path.rglob("*"):
            if not file_path.is_file() or file_path.name.endswith('.meta.json'):
                continue
            
            # 只搜索文本文件
            if file_path.suffix not in ['.md', '.txt', '.json', '.py', '.yaml', '.yml']:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找匹配的行
                matches = []
                for i, line in enumerate(content.split('\n'), 1):
                    if keyword.lower() in line.lower():
                        matches.append({
                            "line_number": i,
                            "line": line.strip()
                        })
                
                if matches:
                    relative_path = file_path.relative_to(self.workspace_path)
                    results.append({
                        "filename": str(relative_path),
                        "matches": matches,
                        "match_count": len(matches)
                    })
                    
            except Exception as e:
                logger.warning(f"⚠️ 搜索文件失败 {file_path}: {e}")
                continue
        
        logger.debug(f"🔍 搜索完成: 找到 {len(results)} 个匹配文件")
        return results
    
    
    def cleanup(self) -> None:
        
        
        temp_path = self.workspace_path / "temp"
        if temp_path.exists():
            for file_path in temp_path.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
                    
        logger.info(f"🧹 工作空间已清理: {self.workspace_path}")
        
        


_filesystem_cache:dict[str,ResearchFileSystem] = {}


def get_filesystem(thread_id:str) -> ResearchFileSystem:
    """创建或获取文件系统示例

    Args:
        thread_id (str): 线程 id

    Returns:
        ResearchFileSystem: 文件系统示例
    """
    
    
    if thread_id not in _filesystem_cache:
        _filesystem_cache[thread_id] = ResearchFileSystem(thread_id)
        
    return _filesystem_cache[thread_id]


@tool
def write_research_file(
    filename: str,
    content: str,
    thread_id: str,
    subdirectory: str = "notes",
) -> str:
    """
    写入研究文件
    
    将研究过程中的内容保存到文件系统。
    适用于保存研究计划、笔记、中间结果等。
    
    Args:
        filename: 文件名（包含扩展名，如 "plan.md"）
        content: 文件内容
        thread_id: 研究任务 ID
        subdirectory: 子目录，可选值：plans, notes, reports, temp
        
    Returns:
        成功消息和文件路径
        
    Example:
        >>> write_research_file(
        ...     filename="research_plan.md",
        ...     content="# 研究计划\\n\\n1. 搜索相关资料\\n2. 分析数据",
        ...     thread_id="research_123",
        ...     subdirectory="plans"
        ... )
        '文件已保存: research_plan.md'
    """
    try:
        fs = get_filesystem(thread_id)
        file_path = fs.write_file(filename, content, subdirectory)
        return f"文件已保存: {filename} (路径: {file_path})"
    except Exception as e:
        return f"保存文件失败: {str(e)}"


@tool
def read_research_file(
    filename: str,
    thread_id: str,
    subdirectory: str = "notes",
) -> str:
    """
    读取研究文件
    
    从文件系统读取之前保存的文件内容。
    
    Args:
        filename: 文件名
        thread_id: 研究任务 ID
        subdirectory: 子目录
        
    Returns:
        文件内容
        
    Example:
        >>> read_research_file(
        ...     filename="research_plan.md",
        ...     thread_id="research_123",
        ...     subdirectory="plans"
        ... )
        '# 研究计划\\n\\n1. 搜索相关资料\\n2. 分析数据'
    """
    try:
        fs = get_filesystem(thread_id)
        content = fs.read_file(filename, subdirectory)
        return content
    except FileNotFoundError:
        return f"文件不存在: {filename}"
    except Exception as e:
        return f"读取文件失败: {str(e)}"


@tool
def list_research_files(
    thread_id: str,
    subdirectory: Optional[str] = None,
) -> str:
    """
    列出研究文件
    
    列出工作空间中的所有文件。
    
    Args:
        thread_id: 研究任务 ID
        subdirectory: 子目录（可选），不指定则列出所有文件
        
    Returns:
        文件列表（格式化的字符串）
        
    Example:
        >>> list_research_files(thread_id="research_123", subdirectory="notes")
        '找到 3 个文件:\\n- notes/note1.md\\n- notes/note2.md\\n- notes/summary.md'
    """
    try:
        fs = get_filesystem(thread_id)
        files = fs.list_files(subdirectory)
        
        if not files:
            return f"没有找到文件（目录: {subdirectory or '全部'}）"
        
        file_list = "\n".join([f"- {f}" for f in files])
        return f"找到 {len(files)} 个文件:\n{file_list}"
        
    except Exception as e:
        return f"列出文件失败: {str(e)}"


@tool
def search_research_files(
    keyword: str,
    thread_id: str,
    subdirectory: Optional[str] = None,
) -> str:
    """
    搜索研究文件
    
    在文件内容中搜索关键词。
    
    Args:
        keyword: 搜索关键词
        thread_id: 研究任务 ID
        subdirectory: 子目录（可选）
        
    Returns:
        搜索结果（格式化的字符串）
        
    Example:
        >>> search_research_files(
        ...     keyword="机器学习",
        ...     thread_id="research_123"
        ... )
        '找到 2 个匹配文件:\\n\\n文件: notes/ml_basics.md\\n- 第 5 行: 机器学习是...'
    """
    try:
        fs = get_filesystem(thread_id)
        results = fs.search_files(keyword, subdirectory)
        
        if not results:
            return f"没有找到包含 '{keyword}' 的文件"
        
        # 格式化结果
        output = [f"找到 {len(results)} 个匹配文件:\n"]
        
        for result in results:
            output.append(f"\n文件: {result['filename']}")
            output.append(f"匹配次数: {result['match_count']}")
            
            # 显示前 3 个匹配
            for match in result['matches'][:3]:
                output.append(f"- 第 {match['line_number']} 行: {match['line']}")
            
            if result['match_count'] > 3:
                output.append(f"  ... 还有 {result['match_count'] - 3} 个匹配")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"搜索失败: {str(e)}"
    
        
FILE_SYSTEM_TOOLS = [
    write_research_file,
    read_research_file,
    list_research_files,
    search_research_files
]   


FILESYSTEM_TOOL_NAMES = [tool.name for tool in FILE_SYSTEM_TOOLS]   

logger.info(f"✅ 文件系统工具已加载: {', '.join(FILESYSTEM_TOOL_NAMES)}")
        