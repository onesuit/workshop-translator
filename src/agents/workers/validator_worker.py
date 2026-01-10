# Validator Worker - Stateless 구조 검증 워커
# 결과만 반환, tasks.md 직접 수정 안 함

import re
from strands import Agent
from strands_tools import file_read, file_write

from model.load import load_sonnet
from prompts.system_prompts import VALIDATOR_PROMPT
from task_manager.types import TaskResult
from tools.file_tools import read_workshop_file


def validate_single_file(
    source_path: str,
    target_path: str,
    target_lang: str,
    source_lang: str = "en"
) -> TaskResult:
    """
    단일 파일 구조 검증 (Stateless Worker)
    
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
        TaskResult: 검증 결과 (성공/실패, 오류 목록)
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
        
        # 기본 구조 검증 (Agent 호출 전 빠른 체크)
        errors = []
        warnings = []
        
        # 1. 헤더 구조 비교
        source_headers = re.findall(r'^(#{1,6})\s+', source_content, re.MULTILINE)
        target_headers = re.findall(r'^(#{1,6})\s+', target_content, re.MULTILINE)
        
        if len(source_headers) != len(target_headers):
            warnings.append(f"헤더 수 불일치: 원본 {len(source_headers)}개, 번역 {len(target_headers)}개")
        
        # 2. 코드 블록 수 비교
        source_code_blocks = len(re.findall(r'```', source_content))
        target_code_blocks = len(re.findall(r'```', target_content))
        
        if source_code_blocks != target_code_blocks:
            errors.append(f"코드 블록 수 불일치: 원본 {source_code_blocks//2}개, 번역 {target_code_blocks//2}개")
        
        # 3. Hugo shortcode 검증
        source_shortcodes = re.findall(r'\{\{[<%].*?[%>]\}\}', source_content)
        target_shortcodes = re.findall(r'\{\{[<%].*?[%>]\}\}', target_content)
        
        if len(source_shortcodes) != len(target_shortcodes):
            errors.append(f"Hugo shortcode 수 불일치: 원본 {len(source_shortcodes)}개, 번역 {len(target_shortcodes)}개")
        
        # 4. 링크 검증
        source_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', source_content)
        target_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', target_content)
        
        if len(source_links) != len(target_links):
            warnings.append(f"링크 수 불일치: 원본 {len(source_links)}개, 번역 {len(target_links)}개")
        
        # 5. 이미지 참조 검증
        source_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', source_content)
        target_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', target_content)
        
        # 이미지 경로가 동일한지 확인
        source_image_paths = set(img[1] for img in source_images)
        target_image_paths = set(img[1] for img in target_images)
        
        missing_images = source_image_paths - target_image_paths
        if missing_images:
            errors.append(f"누락된 이미지 참조: {', '.join(missing_images)}")
        
        # 6. Front matter 검증 (있는 경우)
        source_has_frontmatter = source_content.startswith('---')
        target_has_frontmatter = target_content.startswith('---')
        
        if source_has_frontmatter != target_has_frontmatter:
            errors.append("Front matter 불일치")
        
        # 심각한 오류가 없으면 성공
        is_valid = len(errors) == 0
        
        return TaskResult(
            task_id="",
            success=is_valid,
            output_path=target_path,
            error="; ".join(errors) if errors else None,
            metadata={
                "source_path": source_path,
                "target_path": target_path,
                "errors": errors,
                "warnings": warnings,
                "checks": {
                    "headers": len(source_headers) == len(target_headers),
                    "code_blocks": source_code_blocks == target_code_blocks,
                    "shortcodes": len(source_shortcodes) == len(target_shortcodes),
                    "links": len(source_links) == len(target_links),
                    "images": len(missing_images) == 0,
                    "frontmatter": source_has_frontmatter == target_has_frontmatter,
                },
                "stats": {
                    "source_headers": len(source_headers),
                    "target_headers": len(target_headers),
                    "source_code_blocks": source_code_blocks // 2,
                    "target_code_blocks": target_code_blocks // 2,
                    "source_links": len(source_links),
                    "target_links": len(target_links),
                    "source_images": len(source_images),
                    "target_images": len(target_images),
                }
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
