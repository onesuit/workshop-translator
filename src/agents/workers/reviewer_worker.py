# Reviewer Worker - Stateless 품질 검토 워커
# 결과만 반환, tasks.md 직접 수정 안 함

import re
from strands import Agent
from strands_tools import file_read, file_write

from model.load import load_sonnet
from prompts.system_prompts import REVIEWER_PROMPT
from task_manager.types import TaskResult
from tools.file_tools import read_workshop_file


def review_single_file(
    source_path: str,
    target_path: str,
    target_lang: str,
    source_lang: str = "en"
) -> TaskResult:
    """
    단일 파일 품질 검토 (Stateless Worker)
    
    Stateless 원칙:
    - tasks.md 직접 수정 안 함
    - 결과만 TaskResult로 반환
    - Orchestrator가 결과를 받아 상태 업데이트
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
        target_lang: 타겟 언어 코드
        source_lang: 소스 언어 코드
    
    Returns:
        TaskResult: 검토 결과 (성공/실패, 점수, 피드백)
    """
    try:
        # 파일 읽기
        source_content = read_workshop_file(source_path)
        target_content = read_workshop_file(target_path)
        
        if not source_content:
            return TaskResult(
                task_id="",
                success=False,
                error=f"원본 파일을 읽을 수 없습니다: {source_path}"
            )
        
        if not target_content:
            return TaskResult(
                task_id="",
                success=False,
                error=f"번역 파일을 읽을 수 없습니다: {target_path}"
            )
        
        # 언어 이름 매핑
        lang_names = {
            "ko": "한국어",
            "ja": "일본어",
            "zh": "중국어 간체",
            "es": "스페인어",
            "pt": "포르투갈어",
            "fr": "프랑스어",
            "de": "독일어",
            "en": "영어",
        }
        target_lang_name = lang_names.get(target_lang, target_lang)
        
        # Reviewer Agent 생성 (Stateless)
        agent = Agent(
            model=load_sonnet(),
            system_prompt=REVIEWER_PROMPT,
            tools=[file_read, file_write],
        )
        
        # 검토 프롬프트
        prompt = f"""다음 AWS Workshop 번역의 품질을 검토해주세요.

## 파일 정보
- 원본: {source_path}
- 번역: {target_path}
- 타겟 언어: {target_lang_name}

## 원본 내용
```markdown
{source_content[:3000]}
```
{f"... (총 {len(source_content)} 문자)" if len(source_content) > 3000 else ""}

## 번역 내용
```markdown
{target_content[:3000]}
```
{f"... (총 {len(target_content)} 문자)" if len(target_content) > 3000 else ""}

## 검토 기준
1. 번역 정확성 (30점): 원문 의미 정확히 전달
2. 자연스러움 (25점): {target_lang_name} 표현의 자연스러움
3. 기술 용어 (20점): AWS 용어 일관성
4. 구조 보존 (15점): Markdown 구조 유지
5. 완전성 (10점): 누락 없이 전체 번역

## 출력 형식
다음 XML 형식으로 결과를 반환해주세요:

<review>
<score>총점 (0-100)</score>
<accuracy>정확성 점수</accuracy>
<naturalness>자연스러움 점수</naturalness>
<terminology>기술 용어 점수</terminology>
<structure>구조 보존 점수</structure>
<completeness>완전성 점수</completeness>
<issues>발견된 문제점 (있으면)</issues>
<suggestions>개선 제안 (있으면)</suggestions>
<verdict>PASS 또는 FAIL (80점 이상이면 PASS)</verdict>
</review>"""

        # Agent 실행
        response = agent(prompt)
        response_text = str(response)
        
        # XML 파싱
        def extract_xml(text: str, tag: str) -> str:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, text, re.DOTALL)
            return match.group(1).strip() if match else ""
        
        score = int(extract_xml(response_text, "score") or "0")
        verdict = extract_xml(response_text, "verdict") or "FAIL"
        issues = extract_xml(response_text, "issues")
        suggestions = extract_xml(response_text, "suggestions")
        
        # 80점 이상이면 PASS
        is_pass = score >= 80 or verdict.upper() == "PASS"
        
        return TaskResult(
            task_id="",
            success=is_pass,
            output_path=target_path,
            error=issues if not is_pass else None,
            metadata={
                "source_path": source_path,
                "target_path": target_path,
                "score": score,
                "verdict": "PASS" if is_pass else "FAIL",
                "accuracy": extract_xml(response_text, "accuracy"),
                "naturalness": extract_xml(response_text, "naturalness"),
                "terminology": extract_xml(response_text, "terminology"),
                "structure": extract_xml(response_text, "structure"),
                "completeness": extract_xml(response_text, "completeness"),
                "issues": issues,
                "suggestions": suggestions,
            }
        )
        
    except Exception as e:
        return TaskResult(
            task_id="",
            success=False,
            error=str(e),
            metadata={
                "source_path": source_path,
                "target_path": target_path,
            }
        )
