# Designer 에이전트 - Design 문서 생성
# Oracle 패턴 참고: 단일 명확한 접근 방식, 노력 추정

import os
from strands import Agent, tool
from strands_tools import file_read, file_write
from model.load import load_sonnet
from prompts.system_prompts import DESIGNER_PROMPT


def create_designer_agent() -> Agent:
    """
    Designer 에이전트 인스턴스를 생성합니다.
    
    Agent는 Design 문서 생성만 수행하며, 파일 읽기/쓰기는 generate_design 함수에서 처리합니다.
    
    Returns:
        Agent: Designer 에이전트 인스턴스
    """
    return Agent(
        model=load_sonnet(),
        system_prompt=DESIGNER_PROMPT,
        tools=[],  # 도구 없음 - Design 문서 내용만 반환
    )


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
    output_path: str = None,
    requirements_content: str = None
) -> dict:
    """
    Design 문서를 생성합니다.
    
    이 도구는 Orchestrator가 호출하며, 내부에서 Designer Agent를 실행합니다.
    Agent는 LLM을 사용하여 번역 프로젝트의 설계 문서를 생성합니다.
    
    Args:
        workshop_path: Workshop 디렉토리 경로
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        file_count: 번역 대상 파일 수
        output_path: 출력 파일 경로 (선택)
        requirements_content: requirements.md 파일 내용 (선택, Orchestrator가 읽어서 전달)
    
    Returns:
        dict: 생성 결과
            - content: Design 문서 내용
            - output_path: 저장된 파일 경로
            - target_lang: 타겟 언어
            - file_count: 파일 수
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
    target_lang_name = lang_names.get(target_lang, target_lang.upper())
    
    # 노력 추정 계산
    if file_count <= 5:
        effort_estimate = "Quick (<1h)"
    elif file_count <= 20:
        effort_estimate = "Short (1-4h)"
    elif file_count <= 50:
        effort_estimate = "Medium (1-2d)"
    else:
        effort_estimate = "Long (>2d)"
    
    # Agent 생성
    agent = create_designer_agent()
    
    # 출력 경로 설정
    if output_path is None:
        output_path = os.path.join(workshop_path, "translation", "design.md")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Requirements 정보 포함
    requirements_section = ""
    if requirements_content:
        requirements_section = f"""

## 사용자 요구사항

다음은 사용자가 제공한 번역 요구사항입니다. Design 문서에 이 내용을 반영하세요:

<requirements>
{requirements_content}
</requirements>
"""
    
    # Agent에게 Design 문서 생성 요청
    prompt = f"""
Design 문서를 생성해주세요.

**Workshop 경로**: {workshop_path}
**타겟 언어**: {target_lang} ({target_lang_name})
**번역 대상 파일 수**: {file_count}개
**노력 추정**: {effort_estimate}
{requirements_section}

DESIGNER_PROMPT에 명시된 형식으로 Design 문서를 작성해주세요.

반드시 다음 섹션을 포함하세요:
1. Overview
2. Architecture (Mermaid 다이어그램)
3. File Structure Design
4. Technical Term Glossary
5. Translation Rules
6. Testing Strategy

**중요**: Design 문서 내용만 반환해주세요. 설명이나 추가 텍스트 없이 Markdown 문서만 출력하세요.
"""
    
    try:
        response = agent(prompt)
        content = str(response).strip()
        
        # 빈 응답 체크
        if not content or len(content) < 100:
            raise ValueError(f"Design 문서가 비어있거나 너무 짧습니다 (길이: {len(content)})")
        
        # 파일 저장
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "content": content,
            "output_path": output_path,
            "target_lang": target_lang,
            "file_count": file_count,
            "success": True,
        }
        
    except Exception as e:
        # 에러 발생 시 템플릿 사용
        print(f"[WARNING] Design 생성 실패, 템플릿 사용: {e}")
        content = DESIGN_TEMPLATE.format(
            workshop_path=workshop_path,
            file_count=file_count,
            target_lang=target_lang,
            target_lang_name=target_lang_name,
            effort_estimate=effort_estimate,
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "content": content,
            "output_path": output_path,
            "target_lang": target_lang,
            "file_count": file_count,
            "success": False,
            "error": str(e),
        }
