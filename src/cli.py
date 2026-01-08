#!/usr/bin/env python3
"""
Workshop Translator CLI
사용자가 명령줄에서 직접 실행할 수 있는 CLI 인터페이스 (로컬 모드)
"""

import sys
import argparse

# 로컬 실행용
from main import run_cli


def main():
    """CLI 메인 진입점"""
    parser = argparse.ArgumentParser(
        description="Workshop Translator - 워크샵 문서 번역 에이전트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 대화형 모드
  wstranslator
  
  # 단일 쿼리
  wstranslator "워크샵 분석"

참고:
  - Bedrock 모델 접근 권한이 필요합니다
  - AWS 자격 증명을 설정해주세요 (aws configure)
  - 원격 모드는 cli_remote_backup.py를 참고하세요
        """
    )
    
    parser.add_argument(
        'prompt',
        type=str,
        nargs='?',
        help='단일 쿼리 프롬프트 (없으면 대화형 모드)'
    )
    
    args = parser.parse_args()
    
    # 단일 쿼리가 제공된 경우
    if args.prompt:
        print(f"\n⚠️  단일 쿼리 모드는 아직 구현되지 않았습니다.")
        print(f"대화형 모드를 사용해주세요: wstranslator\n")
        sys.exit(1)
    
    # 대화형 모드 실행
    run_cli()


if __name__ == "__main__":
    main()
