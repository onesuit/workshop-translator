# Workshop Translator 서브에이전트 모듈
# Agent as Tool 패턴으로 구현

from .analyzer import analyze_workshop
from .designer import generate_design
from .task_planner import generate_tasks
from .translator import translate_file, translate_files_parallel, check_background_tasks
from .reviewer import review_file, review_files_parallel, review_all_translations
from .validator import validate_structure

__all__ = [
    "analyze_workshop",
    "generate_design", 
    "generate_tasks",
    "translate_file",
    "translate_files_parallel",
    "check_background_tasks",
    "review_file",
    "review_files_parallel",
    "review_all_translations",
    "validate_structure",
]
