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