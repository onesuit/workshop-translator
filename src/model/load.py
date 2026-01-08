# 다중 모델 로드 모듈
from strands.models import BedrockModel

# 모델 ID 정의 (Global Inference Profile 사용)
# https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
MODELS = {
    # Opus 4.5 - Orchestrator용 (extended thinking 지원)
    "opus": "global.anthropic.claude-opus-4-5-20251101-v1:0",
    # Sonnet 4.5 - Designer, TaskPlanner, Translator, Reviewer용
    "sonnet": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    # Haiku 4.5 - Analyzer, Validator용 (빠른 처리)
    "haiku": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
}

# 기본 모델 (Sonnet)
DEFAULT_MODEL = "sonnet"


def load_model(model_id: str = None) -> BedrockModel:
    """
    Bedrock 모델 클라이언트를 반환합니다.
    IAM 인증은 실행 역할을 통해 자동으로 처리됩니다.
    
    Args:
        model_id: 모델 ID (None이면 기본 Sonnet 사용)
    
    Returns:
        BedrockModel: Bedrock 모델 클라이언트
    """
    if model_id is None:
        model_id = MODELS[DEFAULT_MODEL]
    return BedrockModel(model_id=model_id)


def load_model_by_type(model_type: str) -> BedrockModel:
    """
    모델 타입으로 Bedrock 모델 클라이언트를 반환합니다.
    
    Args:
        model_type: 모델 타입 ("opus", "sonnet", "haiku")
    
    Returns:
        BedrockModel: Bedrock 모델 클라이언트
    
    Raises:
        ValueError: 지원하지 않는 모델 타입
    """
    if model_type not in MODELS:
        raise ValueError(f"지원하지 않는 모델 타입: {model_type}. 사용 가능: {list(MODELS.keys())}")
    return BedrockModel(model_id=MODELS[model_type])


def load_opus() -> BedrockModel:
    """Opus 4.5 모델을 반환합니다. (Orchestrator용)"""
    return load_model_by_type("opus")


def load_sonnet() -> BedrockModel:
    """Sonnet 4.5 모델을 반환합니다. (Designer, Translator 등)"""
    return load_model_by_type("sonnet")


def load_haiku() -> BedrockModel:
    """Haiku 4.5 모델을 반환합니다. (Analyzer, Validator용)"""
    return load_model_by_type("haiku")
