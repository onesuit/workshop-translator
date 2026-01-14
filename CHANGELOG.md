# Changelog

All notable changes to WsTranslator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.37] - 2026-01-14

### Fixed
- README 한국어 링크 경로 수정

## [0.1.36] - 2026-01-14

### Changed
- README 다국어 지원 (영문 메인, 한국어 별도 파일)
- PyPI 페이지에서 영문 README 표시

## [0.1.35] - 2026-01-14

### Changed
- preview_build 다운로드 URL 수정 (Linux ARM 추가, macOS Intel 제거)
- OS별 프리뷰 서버 실행/종료 로직 개선 (Windows, macOS, Linux 지원)
- README.md 전면 업데이트 (프로젝트 구조, 모델 구성, 의존성 정보 추가)

### Fixed
- Windows에서 프리뷰 서버 실행 시 `CREATE_NEW_PROCESS_GROUP` 플래그 사용
- Windows에서 `chmod` 호출 스킵

## [0.1.33] - 2026-01-13

### Added
- 언어 확장자 없는 `.md` 파일 자동 감지 및 파일명 정규화 기능
- 15개 언어 지원 확장 (en, es, ja, fr, ko, pt, de, it, zh, uk, pl, id, nl, ar)
- Phase 1에서 파일 내용 분석 후 언어 자동 감지

### Changed
- Analyzer 프롬프트에 파일명 정규화 로직 추가
- `file_tools.py`에 전체 locale 코드 매핑 추가

## [0.1.32] - 2026-01-12

### Fixed
- CLI 엔트리 포인트를 위한 `py-modules` 설정 추가

## [0.1.31] - 2026-01-12

### Fixed
- CLI 엔트리 포인트를 `main:run_cli`로 수정

## [0.1.30] - 2026-01-11

### Added
- `preview_build` 파일이 없을 경우 AWS에서 자동 다운로드 기능

## [0.1.29] - 2026-01-11

### Added
- `run_preview_phase`에 `tasks_path` 파라미터 추가
- 워크플로우 초기화 시 `.gitignore`에 `translation/` 자동 추가

## [0.1.28] - 2026-01-10

### Added
- Phase 7: 로컬 프리뷰 지원 (`run_preview_phase`, `stop_preview`)
- 프롬프트 업데이트

## [0.1.26] - 2026-01-09

### Added
- 로컬 프리뷰 단계 추가

## [0.1.25] - 2026-01-09

### Added
- 단계별 리포트 자동 생성 기능 (`review_report.md`, `validate_report.md`)

## [0.1.24] - 2026-01-08

### Fixed
- `callback_handler` 타입 체크 추가

## [0.1.23] - 2026-01-08

### Fixed
- `callback_handler`를 함수 기반으로 수정

## [0.1.22] - 2026-01-07

### Added
- AWS Documentation MCP 연동
- 도구 호출 시 색상 표시 기능

## [0.1.20] - 2026-01-06

### Changed
- Designer agent가 requirements를 프롬프트로 받도록 리팩토링

## [0.1.19] - 2026-01-05

### Added
- Translator agent 상세 디버그 로깅

## [0.1.18] - 2026-01-05

### Fixed
- Translator agent 빈 응답 이슈 수정

## [0.1.10] - 2026-01-04

### Fixed
- `tasks.md` 동시 편집 방지를 위한 Lock 추가

## [0.1.9] - 2026-01-03

### Added
- `tasks.md` 자동 업데이트 기능

## [0.1.8] - 2026-01-02

### Fixed
- 번역 Agent 응답 처리 개선

## [0.1.5] - 2026-01-01

### Fixed
- PyPI uvx 에러 수정
- 도구 동의 절차 우회 설정 추가

## [0.1.2] - 2025-12-30

### Changed
- README 개선

## [0.1.1] - 2025-12-29

### Added
- AWS 자격 증명 안내 추가

## [0.1.0] - 2025-12-28

### Added
- Workshop Translator Agent 초기 구현
- Orchestrator 중심 아키텍처
- 병렬 번역/검토/검증 워크플로우
- `tasks.md` 기반 상태 관리
- PyPI 배포 지원
