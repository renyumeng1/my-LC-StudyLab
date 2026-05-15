from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import ClassVar, Optional
from ..schemas import OpenAIConfig 






class Settings(BaseSettings):
    """配置类，使用pydantic_settings进行管理
    """
    PROJECT_ROOT: ClassVar[Path] = Path(__file__).resolve().parents[2]
    
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    
    def validate_required_keys(self) -> None:
        """验证必要的配置
        
        Raises:
            ValueError: 如果缺少必要的配置项，则抛出异常
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI_API_KEY未设置！请在环境变量或.env文件中设置。")
        
        
        
    def resolve_path(self, path: str | Path) -> Path:
        """将项目内相对路径解析到仓库根目录，避免受启动目录影响。"""
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return self.PROJECT_ROOT / resolved
        
        
    def get_openai_config(self) -> OpenAIConfig:
        """获取OpenAI相关的配置项
        
        Returns:
            dict: 包含OpenAI相关配置的字典
        """
        config:OpenAIConfig = OpenAIConfig(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
            model=self.model_name,
            temperature=self.openai_temperature
            )
        
        if self.open_ai_max_tokens is not None:
            config["max_tokens"] = self.open_ai_max_tokens
            
        return config
        
        
        
    
    # ================= 模型配置 =================
    openai_api_key:str = Field(
        default="",
        description="OpenAI API Key必须设置"
    )
    
    openai_base_url:str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API Base URL，默认为https://api.openai.com/v1"
    )
    
    model_name:str = Field(
        default="gpt-5.4",
        description="模型名称，默认为gpt-5.4"
    )
    
    openai_model:str = Field(
        default="gpt-5.4",
        description="模型名称，默认为gpt-5.4"
    )
    
    
    openai_temperature:float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="OpenAI模型的温度参数，默认为0.7，范围为0.0-2.0"
    )
    
    open_ai_max_tokens:Optional[int] = Field(
        default=None,
        description="OpenAI模型的最大token数，默认为None，表示使用模型默认值"
    )
    
    openai_stream: bool = Field(
        default=True,
        description="是否使用OpenAI的流式输出，默认为True"
    )
    
     # ================= 日志配置 =================
     
    log_level:str = Field(
         default="INFO",
         description="日志级别，默认为INFO，可选值为DEBUG、INFO、WARNING"
     )
    
    
    log_file :str = Field(
        default="logs/app.log",
        description="日志文件路径，默认为logs/app.log"
    )
    
    log_rotation: str = Field(
        default="100 MB",
        description="日志文件轮转大小，默认为100 MB"
    )
    
    log_retention: str = Field(
        default="30 days",
        description="日志文件保留时间，默认为30 days"
    )
    
    # ==================== 应用配置 ====================
    app_name: str = Field(
        default="LC-StudyLab",
        description="应用名称"
    )
    
    app_version: str = Field(
        default="0.1.0",
        description="应用版本"
    )
    
    debug: bool = Field(
        default=False,
        description="是否启用调试模式"
    )
    
    # ==================== 高德地图配置 ====================
    amap_key: str = Field(
        default="",
        description="高德地图 API 密钥（可选，用于天气查询等服务）"
    )
    
    # ==================== Tavily 搜索配置 ====================
    tavily_api_key: str = Field(
        default="",
        description="Tavily API Key（可选，用于Web搜索工具）"
    )
    
    tavily_max_results:int = Field(
        default=5,
        ge=1,
        le=20,
        description="Tavily搜索结果的最大数量，默认为5，范围为1-20"
    )
    
    
    # ==================== 数据目录配置 ====================
    DATA_DIR: str = Field(
        default="data",
        description="数据存储根目录"
    )
    
    
    # ================= Agent配置 =================
    
    agent_max_iterations:int = Field(
        default=15,
        ge=1,
        le=100,
        description="Agent的最大迭代次数，默认为15，范围为1-100"
    )
    
    agent_max_execution_time: Optional[float] = Field(
        default=None,
        description="Agent 最大执行时间（秒），None 表示无限制"
    )
    
    # ==================== rag配置 ====================
    embedding_model:str = Field(
        default="BAAI/bge-large-zh-v1.5",
        description="用于生成嵌入的模型名称，默认为BAAI/bge-large-zh-v1.5"
    )
    
    embedding_batch_size:int = Field(
        default=50,
        ge=1,
        le=1000,
        description="嵌入批处理大小，默认为50，范围为1-1000"
    )
    
    
    chunk_size:int =Field(
        default=1000,
        ge=100,
        le=10000,
        description="文本块大小，默认为1000，范围为100-10000"
    )
    
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="文本分块重叠大小（字符数）"
    )
    
    # 向量库配置
    vector_store_type: str = Field(
        default="faiss",
        description="向量库类型：faiss, inmemory, chroma"
    )
    
    vector_store_path: str = Field(
        default="data/indexes",
        description="向量库存储路径"
    )
    
    # 检索配置
    retriever_search_type: str = Field(
        default="similarity",
        description="检索类型：similarity, mmr, similarity_score_threshold"
    )
    
    retriever_k: int = Field(
        default=4,
        ge=1,
        le=20,
        description="检索返回的文档数量"
    )
    
    retriever_score_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="相似度阈值（仅用于 similarity_score_threshold 模式）"
    )
    
    retriever_fetch_k: int = Field(
        default=20,
        ge=1,
        le=100,
        description="MMR 检索的候选文档数量"
    )
    
    
settings: Settings = Settings()



def validate_settings() -> None:
    """验证配置项的有效性
    """
    try:
        settings.validate_required_keys()
    except ValueError as e:
        if settings.debug:
            print(f"配置警告：{e}")
        else:
            raise
        
# 如果不是在测试环境，则验证配置
import sys
if "pytest" not in sys.modules:
    validate_settings()
    pass
