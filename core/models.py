"""
Pydantic models for API request/response validation.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class ProcessRequest(BaseModel):
    """Request model for text processing."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to process")
    archetype: str = Field(..., min_length=1, max_length=100, description="Archetype to use")
    remember: bool = Field(default=True, description="Save to chat history")
    chat_id: Optional[str] = Field(default=None, max_length=255, description="Chat identifier")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="AI temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000, description="Max response tokens")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: Optional[int] = Field(default=None, ge=1, le=100, description="Top-k sampling")
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        """Validate text content."""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()
    
    @field_validator("archetype")
    @classmethod
    def validate_archetype(cls, v):
        """Validate archetype name."""
        if not v or not v.strip():
            raise ValueError("Archetype cannot be empty")
        # Only alphanumeric, underscore, hyphen
        if not all(c.isalnum() or c in ['_', '-'] for c in v):
            raise ValueError("Archetype contains invalid characters")
        return v.strip()
    
    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v):
        """Validate chat ID."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Only alphanumeric, underscore, hyphen
        if not all(c.isalnum() or c in ['_', '-'] for c in v):
            raise ValueError("Chat ID contains invalid characters")
        return v


class ProcessResponse(BaseModel):
    """Response model for text processing."""
    response: str
    archetype: str
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None


class RegisterRequest(BaseModel):
    """User registration request."""
    email: str = Field(..., min_length=5, max_length=255, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    username: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(..., min_length=8, max_length=100)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class Token(BaseModel):
    """JWT Token response model."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class UserInfo(BaseModel):
    """User information model."""
    id: int
    username: str
    email: str
    created_at: datetime
    archetypes_count: int = 0
    max_archetypes: int = 2


class ChatHistoryItem(BaseModel):
    """Chat history item model."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    archetype: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response model."""
    chat_id: str
    messages: List[ChatHistoryItem]
    total: int


class SearchRequest(BaseModel):
    """Search request model."""
    query: Optional[str] = Field(default=None, max_length=500)
    archetype: Optional[str] = Field(default=None, max_length=100)
    limit: int = Field(default=50, ge=1, le=1000)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class SearchResult(BaseModel):
    """Search result item."""
    chat_id: str
    preview: str
    archetype: Optional[str]
    created_at: datetime


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[SearchResult]
    total: int
    query: Optional[str]


class ArchetypeConfig(BaseModel):
    """Archetype configuration model."""
    name: str = Field(..., min_length=1, max_length=200)
    model_name: str = Field(..., min_length=1, max_length=100)
    prompt_file: Optional[str] = None
    prompt: Optional[str] = None
    additional_prompts: Optional[List[str]] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator("name", "model_name")
    @classmethod
    def validate_not_empty(cls, v):
        """Validate not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class ArchetypeResponse(BaseModel):
    """Archetype response model."""
    id: int
    name: str
    system_prompt: str
    model_name: str
    temperature: float
    max_tokens: int
    is_public: bool
    uses_count: int
    created_at: datetime
    is_owner: bool = True


class CreateArchetypeRequest(BaseModel):
    """Create archetype request."""
    name: str = Field(..., min_length=1, max_length=200)
    system_prompt: str = Field(..., min_length=10, max_length=10000)
    model_name: str = Field(default="gemini-1.5-flash", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class ShareArchetypeRequest(BaseModel):
    """Share archetype request."""
    archetype_id: int
    is_public: bool


class ArchetypesConfigRequest(BaseModel):
    """Request to save archetypes configuration."""
    archetypes: Dict[str, ArchetypeConfig]
    
    @field_validator("archetypes")
    @classmethod
    def validate_archetypes(cls, v):
        """Validate archetypes dict."""
        if not v:
            raise ValueError("Archetypes cannot be empty")
        if len(v) > 10:
            raise ValueError("Maximum 10 archetypes allowed")
        return v


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    version: str = "1.0.0"
    environment: str
    timestamp: datetime
    checks: Dict[str, bool] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    status_code: int
