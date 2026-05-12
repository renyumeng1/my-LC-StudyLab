import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from openai import embeddings

from ..config import settings, get_logger
from .vector_stores import (
    create_vector_store,
    load_vector_store,
    save_vector_store,
    add_documents_to_vector_store,
    delete_vector_store,
    get_vector_store_stats,
)

logger = get_logger(__name__)


class IndexManager:
    
    
    def __init__(self,base_path:Optional[str]=None) -> None:
        self.base_path = Path(base_path or settings.vector_store_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 索引管理器初始化: {self.base_path}")
        
    
    def _get_index_path(self,name:str)->Path:
        
        return self.base_path / name
    
    def _get_metadata_path(self,name:str) -> Path:
        return self._get_index_path(name) / "metadata.json"
    
    
    def _save_metadata(
        self,
        name:str,
        metadata: dict[str, Any]
    )->None:
        metadata_path =self._get_metadata_path(name)
        
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_path,"w",encoding="utf-8") as f:
            json.dump(metadata,f,ensure_ascii=False,indent=2)
            
        logger.debug(f"💾 保存元数据: {metadata_path}")
        
    
    
    def _load_metadata(self,name:str) -> Optional[dict[str, Any]]:
        
        metadata_path = self._get_metadata_path(name)
        
        
        if not metadata_path.exists():
            return None
        
        
        try:
            with open(metadata_path,"r",encoding="utf-8") as f:
                metadata = json.load(f)
                logger.debug(f"📂 加载元数据: {metadata_path}")
            return metadata
        
        except Exception as e:
            logger.error(f"❌ 加载元数据失败: {e}")
            return None
        
        
    
    
    def create_index(
        self,
        name: str,
        documents: List[Document],
        embeddings: Embeddings,
        description: str = "",
        store_type: Optional[str] = None,
        overwrite: bool = False,
        **kwargs,
    ) -> VectorStore:
        """
        创建新索引
        
        Args:
            name: 索引名称
            documents: 文档列表
            embeddings: Embedding 模型
            description: 索引描述
            store_type: 向量库类型
            overwrite: 是否覆盖已存在的索引
            **kwargs: 其他参数
            
        Returns:
            创建的 VectorStore 实例
            
        Raises:
            ValueError: 如果索引已存在且 overwrite=False
            
        Example:
            >>> manager.create_index(
            ...     name="my_docs",
            ...     documents=chunks,
            ...     embeddings=embeddings,
            ...     description="我的文档集合"
            ... )
        """
        
        
        index_path = self._get_index_path(name)
        
        if index_path.exists() and not overwrite:
            raise ValueError(f"索引 '{name}' 已存在。设置 overwrite=True 以覆盖。")
        
        logger.info(f"🔨 创建索引: {name}")
        logger.info(f"   文档数量: {len(documents)}")
        logger.info(f"   描述: {description}")
        
        
        try:
            vector_store =create_vector_store(
                documents=documents,
                embeddings=embeddings,
                store_type=store_type,
                index_path=index_path,
                **kwargs
            )
            
            
            
            save_vector_store(vector_store,str(index_path),embeddings)
            
            # 保存元数据
            metadata = {
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "num_documents": len(documents),
                "store_type": store_type or settings.vector_store_type,
                "embedding_model": settings.embedding_model,
            }
            self._save_metadata(name, metadata)
            
            logger.info(f"✅ 索引创建成功: {name}")
            return vector_store
        
        except Exception as e:
            logger.error(f"❌ 创建索引失败: {e}")
            # 清理失败的索引
            if index_path.exists():
                delete_vector_store(str(index_path))
            raise
        
    
    
    def load_index(
        self,
        name:str,
        embeddings: Embeddings,
        **kwargs:Any,
    )->VectorStore:
        """
        加载索引
        
        Args:
            name: 索引名称
            embeddings: Embedding 模型
            **kwargs: 其他参数
            
        Returns:
            VectorStore 实例
            
        Raises:
            FileNotFoundError: 如果索引不存在
            
        Example:
            >>> vector_store = manager.load_index("my_docs", embeddings)
        """
        index_path = self._get_index_path(name)
        
        if not index_path.exists():
            raise FileNotFoundError(f"索引 '{name}' 不存在。")
        
        logger.info(f"📂 加载索引: {name}")

         
        
        try:
            metadata = self._load_metadata(name)
            
            if metadata:
                logger.info(f"   描述: {metadata.get('description','')}")
                logger.info(f"   文档数量: {metadata.get('num_documents', '未知')}")
                logger.info(f"   创建时间: {metadata.get('created_at', '未知')}")
                logger.info(f"   上次更新时间: {metadata.get('updated_at', '未知')}")
                
            vector_store = load_vector_store(
                load_path=str(index_path),
                embeddings=embeddings,
                **kwargs
            )
            
            logger.info(f"✅ 索引加载成功: {name}")
            return vector_store
        
        
        except Exception as e:
            logger.error(f"❌ 加载索引失败: {e}")
            raise
        
    
    
    def update_index(
        self,
        name:str,
        documents: list[Document],
        embeddings: Embeddings,
        **kwargs:Any,
    ) -> VectorStore:
        """
        更新索引（添加新文档）
        
        Args:
            name: 索引名称
            documents: 要添加的文档列表
            embeddings: Embedding 模型
            **kwargs: 其他参数
            
        Returns:
            更新后的 VectorStore 实例
            
        Example:
            >>> # 加载新文档
            >>> new_docs = load_document("new_doc.pdf")
            >>> chunks = split_documents(new_docs)
            >>> 
            >>> # 更新索引
            >>> manager.update_index("my_docs", chunks, embeddings)
        """
        
        logger.info(f"🔄 更新索引: {name}")
        logger.info(f"   新增文档: {len(documents)}")
        
        try:
            vector_store = self.load_index(name, embeddings,**kwargs)
            
            add_documents_to_vector_store(vector_store,documents)
            
            index_path = self._get_index_path(name)
            save_vector_store(vector_store,str(index_path),embeddings)
            
            
            metadata= self._load_metadata(name) or {}
            
            metadata["updated_at"] = datetime.now().isoformat()
            metadata["num_documents"] = metadata.get("num_documents",0) + len(documents)
            
            self._save_metadata(name,metadata)
            
            logger.info(f"✅ 索引更新成功: {name}")
            
            return vector_store
        
        except Exception as e:
            logger.error(f"❌ 更新索引失败: {e}")
            raise
        
        
    
    
    def delete_index(self, name: str) -> None:
        """
        删除索引
        
        Args:
            name: 索引名称
            
        Example:
            >>> manager.delete_index("old_index")
        """
        index_path = self._get_index_path(name)
        
        if not index_path.exists():
            logger.warning(f"索引不存在: {name}")
            return
        
        logger.info(f"🗑️  删除索引: {name}")
        
        try:
            delete_vector_store(str(index_path))
            logger.info(f"✅ 索引删除成功: {name}")
            
        except Exception as e:
            logger.error(f"❌ 删除索引失败: {e}")
            raise
    
    def list_indexes(self) -> List[Dict[str, Any]]:
        """
        列出所有索引
        
        Returns:
            索引信息列表
            
        Example:
            >>> indexes = manager.list_indexes()
            >>> for idx in indexes:
            ...     print(f"{idx['name']}: {idx['description']}")
        """
        logger.info("📋 列出所有索引")
        
        indexes = []
        
        # 遍历索引目录
        if not self.base_path.exists():
            return indexes
        
        for index_dir in self.base_path.iterdir():
            if not index_dir.is_dir():
                continue
            
            name = index_dir.name
            metadata = self._load_metadata(name)
            
            if metadata:
                indexes.append(metadata)
            else:
                # 如果没有元数据，创建基本信息
                indexes.append({
                    "name": name,
                    "description": "N/A",
                    "created_at": "N/A",
                    "updated_at": "N/A",
                    "num_documents": "N/A",
                })
        
        logger.info(f"   找到 {len(indexes)} 个索引")
        return indexes
    
    def get_index_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取索引详细信息
        
        Args:
            name: 索引名称
            
        Returns:
            索引信息字典，如果不存在返回 None
            
        Example:
            >>> info = manager.get_index_info("my_docs")
            >>> print(info)
        """
        index_path = self._get_index_path(name)
        
        if not index_path.exists():
            logger.warning(f"索引不存在: {name}")
            return None
        
        # 加载元数据
        metadata:Optional[dict[str,Any]] = self._load_metadata(name)
        
        if not metadata:
            metadata = {
                "name": name,
                "description": "N/A",
            }
        
        # 添加路径信息
        metadata["path"] = str(index_path)
        
        # 计算索引大小
        try:
            total_size = sum(
                f.stat().st_size
                for f in index_path.rglob("*")
                if f.is_file()
            )
            metadata["size_bytes"] = total_size
            metadata["size_mb"] = total_size / (1024 * 1024)
        except Exception as e:
            logger.warning(f"计算索引大小失败: {e}")
        
        return metadata
    
    def index_exists(self, name: str) -> bool:
        """
        检查索引是否存在
        
        Args:
            name: 索引名称
            
        Returns:
            是否存在
            
        Example:
            >>> if manager.index_exists("my_docs"):
            ...     print("索引存在")
        """
        return self._get_index_path(name).exists()
            
       
        