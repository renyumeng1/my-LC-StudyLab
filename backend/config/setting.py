from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field
from typing import Optional
from ..schemas import OpenAIConfig 






class Settings(BaseSettings):
    """配置类，使用pydantic_settings进行管理
    """
    
    
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