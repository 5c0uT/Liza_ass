"""
Пакет интеллектуальных модулей для AI-ассистента Лиза.
Содержит планирование, обучение и аналитику.
"""

from .planning.task_scheduler import TaskScheduler
from .planning.resource_allocator import ResourceAllocator
from .planning.priority_manager import PriorityManager

from .learning.user_profiler import UserProfiler
from .learning.pattern_detector import PatternDetector
from .learning.recommendation import RecommendationSystem

from .analytics.performance import PerformanceAnalyzer
from .analytics.productivity import ProductivityAnalyzer
from .analytics.anomaly_detection import AnomalyDetector

__all__ = [
    'TaskScheduler', 'ResourceAllocator', 'PriorityManager',
    'UserProfiler', 'PatternDetector', 'RecommendationSystem',
    'PerformanceAnalyzer', 'ProductivityAnalyzer', 'AnomalyDetector'
]