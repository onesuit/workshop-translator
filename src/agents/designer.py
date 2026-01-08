# Designer 에이전트 - Design 문서 생성
# Oracle 패턴 참고: 단일 명확한 접근 방식, 노력 추정

import os
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import DESIGNER_PROMPT


# Design 문서 템플릿
DESIGN_TEMPLATE = """# Design Document

## Overview

{target_lang} 언어로 AWS Workshop 콘텐츠를 번역합니다.

**Workshop 경로**: {workshop_path}
**번역 대상 파일 수**: {file_count}개
**타겟 언어**: {target_lang}

## Architecture

```mermaid
flowchart TD
    A[원본 .en.md 파일] --> B[Analyzer]
    B --> C[번역 대상 파일 목록]
    C --> D[Translator]
    D --> E[.{target_lang}.md 파일]
    E --> F[Reviewer]
    F --> G[품질 검토 결과]
    G --> H[Validator]
    H --> I[최종 검증]
```

## File Structure Design

원본 파일 구조를 유지하며, 파일명만 변경합니다:
- `index.en.md` → `index.{target_lang}.md`
- `1-introduction/index.en.md` → `1-introduction/index.{target_lang}.md`

## Technical Term Glossary

| 영어 | {target_lang_name} | 비고 |
|------|---------------------|------|
| Amazon SES | Amazon SES | 서비스명 유지 |
| AWS Lambda | AWS Lambda | 서비스명 유지 |
| Amazon S3 | Amazon S3 | 서비스명 유지 |
| IAM | IAM | 약어 유지 |
| API | API | 기술 용어 유지 |
| SDK | SDK | 기술 용어 유지 |

## Translation Rules

1. **AWS 서비스명**: 영어 유지 (Amazon SES, AWS Lambda 등)
2. **기술 용어**: 공식 AWS 문서 참조
3. **코드 블록**: 내용 유지, 주석만 번역
4. **Frontmatter**: title만 번역, 나머지 유지
5. **링크**: URL 유지, 텍스트만 번역
6. **이미지 alt 텍스트**: 번역

## Testing Strategy

1. **구조 검증**: Frontmatter 필수 필드 확인
2. **줄 수 비교**: 원본 대비 10% 이내 차이
3. **품질 검토**: 80점 이상 PASS

## Effort Estimate

- 환경 설정: Quick (<1h)
- 번역 실행: {effort_estimate}
- 검증: Short (1-4h)
"""


@tool
def generate_design(
    workshop_path: str,
    target_lang: str,
    file_count: int,
    output_path: str = None
) -> dict:
    """
    Design 문서를 생성합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        file_count: 번역 대상 파일 수
        output_path: 출력 파일 경로 (선택)
    
    Returns:
        dict: 생성 결과
            - content: Design 문서 내용
            - output_path: 저장된 파일 경로
    """
    # 언어 이름 매핑
    lang_names = {
        "ko": "한국어",
        "ja": "日本語",
        "zh": "中文",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "pt": "Português",
    }
    target_lang_name = lang_names.get(target_lang, target_lang)
    
    # 노력 추정
    if file_count <= 10:
        effort_estimate = "Short (1-4h)"
    elif file_count <= 30:
        effort_estimate = "Medium (1-2d)"
    else:
        effort_estimate = "Large (3d+)"
    
    # Design 문서 생성
    content = DESIGN_TEMPLATE.format(
        workshop_path=workshop_path,
        file_count=file_count,
        target_lang=target_lang,
        target_lang_name=target_lang_name,
        effort_estimate=effort_estimate,
    )
    
    # 파일 저장
    if output_path is None:
        output_path = os.path.join(workshop_path, ".kiro", "specs", "translation", "design.md")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {
        "content": content,
        "output_path": output_path,
        "target_lang": target_lang,
        "file_count": file_count,
    }


def run_designer_agent(
    workshop_path: str,
    target_lang: str,
    file_count: int,
    files: list[str],
    requirements_path: str = None
) -> dict:
    """
    Designer 에이전트를 실행하여 더 상세한 Design 문서를 생성합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드
        file_count: 번역 대상 파일 수
        files: 파일 목록
        requirements_path: requirements.md 경로 (선택)
    
    Returns:
        dict: 생성 결과
    """
    # 기본 템플릿으로 생성
    result = generate_design(workshop_path, target_lang, file_count)
    
    # requirements.md가 있으면 에이전트로 보강
    if requirements_path and os.path.exists(requirements_path):
        agent = Agent(
            model=load_sonnet(),
            system_prompt=DESIGNER_PROMPT,
            tools=[file_read, file_write],
        )
        
        prompt = f"""
        requirements.md를 참고하여 Design 문서를 보강해주세요.
        
        Requirements 경로: {requirements_path}
        Workshop 경로: {workshop_path}
        타겟 언어: {target_lang}
        파일 수: {file_count}
        
        기존 Design 문서:
        {result['content']}
        """
        
        response = agent(prompt)
        result["agent_response"] = str(response)
    
    return result
