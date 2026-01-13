# 파일 처리 도구
import os
import glob
import re
import yaml
from pathlib import Path
from typing import Optional, Tuple

# 지원하는 언어 코드 목록 (파일명에 사용되는 2자리 코드)
SUPPORTED_LANG_CODES = [
    "en",  # English (en-US)
    "es",  # Español (es-US)
    "ja",  # 日本語 (ja-JP)
    "fr",  # Français (fr-FR)
    "ko",  # 한국어 (ko-KR)
    "pt",  # Português (pt-BR)
    "de",  # Deutsch (de-DE)
    "it",  # Italiano (it-IT)
    "zh",  # 中文 (zh-CN, zh-TW)
    "uk",  # українська (uk-UA)
    "pl",  # Polski (pl-PL)
    "id",  # Bahasa Indonesia (id-ID)
    "nl",  # Nederlands (nl-NL)
    "ar",  # العربية (ar-AE)
]

# 전체 locale 코드 매핑 (contentspec.yaml용)
LOCALE_CODE_MAP = {
    "en": "en-US",
    "es": "es-US",
    "ja": "ja-JP",
    "fr": "fr-FR",
    "ko": "ko-KR",
    "pt": "pt-BR",
    "de": "de-DE",
    "it": "it-IT",
    "zh": "zh-CN",  # 기본값, zh-TW도 가능
    "uk": "uk-UA",
    "pl": "pl-PL",
    "id": "id-ID",
    "nl": "nl-NL",
    "ar": "ar-AE",
}


def read_workshop_file(file_path: str) -> str:
    """
    Workshop 파일을 읽습니다.
    
    Args:
        file_path: 파일 경로
    
    Returns:
        str: 파일 내용
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_lang_from_filename(filename: str) -> Optional[str]:
    """
    파일명에서 언어 코드를 추출합니다.
    예: index.en.md → en, index.ko.md → ko
    
    Args:
        filename: 파일명
    
    Returns:
        str: 언어 코드 (없으면 None)
    """
    # .{lang}.md 패턴 매칭
    match = re.search(r'\.([a-z]{2})\.md$', filename)
    if match:
        lang = match.group(1)
        if lang in SUPPORTED_LANG_CODES:
            return lang
    return None


def write_translated_file(
    source_path: str, 
    content: str, 
    target_lang: str,
    source_lang: str = "en"
) -> str:
    """
    번역된 파일을 저장합니다.
    .{source_lang}.md → .{target_lang}.md 형식으로 저장
    
    Args:
        source_path: 원본 파일 경로
        content: 번역된 내용
        target_lang: 타겟 언어 코드 (ko, ja, zh 등)
        source_lang: 소스 언어 코드 (기본: en)
    
    Returns:
        str: 저장된 파일 경로
    """
    # .{source_lang}.md → .{target_lang}.md
    target_path = source_path.replace(f".{source_lang}.md", f".{target_lang}.md")
    
    # 디렉토리 생성 (필요시)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return target_path


def detect_source_language(workshop_path: str) -> Tuple[str, list[str]]:
    """
    Workshop에서 소스 언어를 자동 감지합니다.
    .en.md 우선, 없으면 다른 언어 파일 탐색
    
    Args:
        workshop_path: Workshop 루트 경로
    
    Returns:
        Tuple[str, list[str]]: (소스 언어 코드, 파일 목록)
    """
    content_path = os.path.join(workshop_path, "content")
    if os.path.exists(content_path):
        search_path = content_path
    else:
        search_path = workshop_path
    
    # 1. 먼저 .en.md 파일 탐색
    en_files = glob.glob(os.path.join(search_path, "**/*.en.md"), recursive=True)
    if en_files:
        return "en", sorted(en_files)
    
    # 2. .en.md가 없으면 다른 언어 파일 탐색
    for lang in SUPPORTED_LANG_CODES:
        if lang == "en":
            continue
        pattern = f"**/*.{lang}.md"
        files = glob.glob(os.path.join(search_path, pattern), recursive=True)
        if files:
            return lang, sorted(files)
    
    # 3. 언어 코드 없는 .md 파일도 확인 (기본 언어로 간주)
    md_files = glob.glob(os.path.join(search_path, "**/*.md"), recursive=True)
    # 언어 코드가 있는 파일 제외
    plain_md_files = [f for f in md_files if not extract_lang_from_filename(f)]
    if plain_md_files:
        return "unknown", sorted(plain_md_files)
    
    return "none", []


def list_workshop_files(
    workshop_path: str, 
    source_lang: str = None
) -> Tuple[str, list[str]]:
    """
    Workshop 디렉토리에서 번역 대상 파일 목록을 반환합니다.
    소스 언어를 자동 감지하거나 지정할 수 있습니다.
    
    Args:
        workshop_path: Workshop 루트 경로
        source_lang: 소스 언어 코드 (None이면 자동 감지)
    
    Returns:
        Tuple[str, list[str]]: (소스 언어 코드, 파일 경로 목록)
    """
    content_path = os.path.join(workshop_path, "content")
    if os.path.exists(content_path):
        search_path = content_path
    else:
        search_path = workshop_path
    
    # 소스 언어가 지정되지 않으면 자동 감지
    if source_lang is None:
        return detect_source_language(workshop_path)
    
    # 소스 언어가 지정된 경우 해당 패턴으로 탐색
    pattern = f"**/*.{source_lang}.md"
    files = glob.glob(os.path.join(search_path, pattern), recursive=True)
    return source_lang, sorted(files)


def read_contentspec(workshop_path: str) -> Optional[dict]:
    """
    contentspec.yaml 파일을 읽습니다.
    
    Args:
        workshop_path: Workshop 루트 경로
    
    Returns:
        dict: contentspec 내용 (없으면 None)
    """
    contentspec_path = os.path.join(workshop_path, "contentspec.yaml")
    if not os.path.exists(contentspec_path):
        return None
    
    with open(contentspec_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_supported_languages(workshop_path: str) -> list[str]:
    """
    Workshop에서 지원하는 언어 목록을 반환합니다.
    
    Args:
        workshop_path: Workshop 루트 경로
    
    Returns:
        list[str]: 언어 코드 목록
    """
    contentspec = read_contentspec(workshop_path)
    if contentspec and "locale_codes" in contentspec:
        return contentspec["locale_codes"]
    return ["en"]


def count_lines(file_path: str) -> int:
    """
    파일의 줄 수를 반환합니다.
    
    Args:
        file_path: 파일 경로
    
    Returns:
        int: 줄 수
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return len(f.readlines())


def compare_line_counts(source_path: str, target_path: str) -> dict:
    """
    원본과 번역본의 줄 수를 비교합니다.
    
    Args:
        source_path: 원본 파일 경로
        target_path: 번역 파일 경로
    
    Returns:
        dict: 비교 결과 (source_lines, target_lines, diff_percent)
    """
    source_lines = count_lines(source_path)
    target_lines = count_lines(target_path)
    
    if source_lines == 0:
        diff_percent = 0
    else:
        diff_percent = abs(target_lines - source_lines) / source_lines * 100
    
    return {
        "source_lines": source_lines,
        "target_lines": target_lines,
        "diff_percent": round(diff_percent, 2)
    }


def get_directory_structure(path: str, prefix: str = "", max_depth: int = 3) -> str:
    """
    디렉토리 구조를 트리 형식 문자열로 반환합니다.
    
    Args:
        path: 디렉토리 경로
        prefix: 출력 접두사
        max_depth: 최대 깊이
    
    Returns:
        str: 트리 형식 문자열
    """
    if max_depth == 0:
        return ""
    
    result = []
    items = sorted(os.listdir(path))
    
    # 숨김 파일 제외
    items = [i for i in items if not i.startswith(".")]
    
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = i == len(items) - 1
        
        # 현재 항목 출력
        connector = "└── " if is_last else "├── "
        result.append(f"{prefix}{connector}{item}")
        
        # 디렉토리면 재귀 호출
        if os.path.isdir(item_path):
            extension = "    " if is_last else "│   "
            sub_tree = get_directory_structure(
                item_path, 
                prefix + extension, 
                max_depth - 1
            )
            if sub_tree:
                result.append(sub_tree)
    
    return "\n".join(result)
