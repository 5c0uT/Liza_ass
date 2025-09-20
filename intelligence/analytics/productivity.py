"""
Анализ продуктивности для AI-ассистента Лиза.
"""

import logging
import json
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


class ProductivityAnalyzer:
    """Анализатор продуктивности пользователя."""

    def __init__(self, data_dir: str = "data/productivity"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Данные продуктивности
        self.productivity_data = {
            'daily_stats': {},
            'weekly_stats': {},
            'monthly_stats': {}
        }

        # Цели продуктивности
        self.productivity_goals = {}

        # Блокировка для потокобезопасности
        self.lock = threading.RLock()

        # Загрузка данных при инициализации
        self.load_data()

    def load_data(self):
        """Загрузка данных продуктивности из файлов."""
        data_file = self.data_dir / "productivity_data.json"
        goals_file = self.data_dir / "productivity_goals.json"

        try:
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.productivity_data = json.load(f)
                self.logger.info(f"Загружены данные продуктивности")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных продуктивности: {e}")

        try:
            if goals_file.exists():
                with open(goals_file, 'r', encoding='utf-8') as f:
                    self.productivity_goals = json.load(f)
                self.logger.info(f"Загружены цели продуктивности")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки целей продуктивности: {e}")

    def save_data(self):
        """Сохранение данных продуктивности в файлы."""
        data_file = self.data_dir / "productivity_data.json"
        goals_file = self.data_dir / "productivity_goals.json"

        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self.productivity_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных продуктивности: {e}")

        try:
            with open(goals_file, 'w', encoding='utf-8') as f:
                json.dump(self.productivity_goals, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения целей продуктивности: {e}")

    def track_activity(self, user_id: str, activity_type: str,
                       duration: float, metadata: Dict[str, Any] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None):
        """
        Отслеживание активности пользователя.

        Args:
            user_id: ID пользователя
            activity_type: Тип активности
            duration: Продолжительность в секундах
            metadata: Дополнительные метаданные
            start_time: Время начала активности
            end_time: Время окончания активности
        """
        if metadata is None:
            metadata = {}

        if start_time is None:
            start_time = datetime.now()
        if end_time is None:
            end_time = start_time + timedelta(seconds=duration)

        current_date = start_time.date()
        date_str = current_date.isoformat()
        hour = start_time.hour

        with self.lock:
            # Инициализация daily stats
            if date_str not in self.productivity_data['daily_stats']:
                self.productivity_data['daily_stats'][date_str] = {
                    'total_activities': 0,
                    'total_duration': 0.0,
                    'focused_time': 0.0,
                    'distracted_time': 0.0,
                    'by_type': {},
                    'by_hour': {str(h): 0 for h in range(24)},
                    'user_activities': {}
                }

            daily_stats = self.productivity_data['daily_stats'][date_str]

            # Обновление статистик
            daily_stats['total_activities'] += 1
            daily_stats['total_duration'] += duration

            # Классификация времени (фокусированное/отвлеченное)
            if activity_type in ['coding', 'research', 'writing', 'learning']:
                daily_stats['focused_time'] += duration
            elif activity_type in ['social_media', 'entertainment', 'browsing']:
                daily_stats['distracted_time'] += duration

            # Статистика по часам
            daily_stats['by_hour'][str(hour)] += duration

            # Статистика по типам активности
            if activity_type not in daily_stats['by_type']:
                daily_stats['by_type'][activity_type] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'avg_duration': 0.0,
                    'last_used': start_time.isoformat()
                }

            type_stats = daily_stats['by_type'][activity_type]
            type_stats['count'] += 1
            type_stats['total_duration'] += duration
            type_stats['avg_duration'] = type_stats['total_duration'] / type_stats['count']
            type_stats['last_used'] = start_time.isoformat()

            # Статистика по пользователям
            if user_id not in daily_stats['user_activities']:
                daily_stats['user_activities'][user_id] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'focused_time': 0.0,
                    'distracted_time': 0.0,
                    'by_type': {}
                }

            user_stats = daily_stats['user_activities'][user_id]
            user_stats['count'] += 1
            user_stats['total_duration'] += duration

            if activity_type in ['coding', 'research', 'writing', 'learning']:
                user_stats['focused_time'] += duration
            elif activity_type in ['social_media', 'entertainment', 'browsing']:
                user_stats['distracted_time'] += duration

            if activity_type not in user_stats['by_type']:
                user_stats['by_type'][activity_type] = {
                    'count': 0,
                    'total_duration': 0.0
                }

            user_type_stats = user_stats['by_type'][activity_type]
            user_type_stats['count'] += 1
            user_type_stats['total_duration'] += duration

            # Агрегация weekly и monthly stats
            self._aggregate_stats(current_date)

            # Сохранение данных
            self.save_data()

    def _aggregate_stats(self, current_date: datetime):
        """Агрегация статистик за неделю и месяц."""
        date_str = current_date.isoformat()
        week_start = current_date - timedelta(days=current_date.weekday())
        week_str = week_start.date().isoformat()
        month_start = current_date.replace(day=1)
        month_str = month_start.date().isoformat()

        # Инициализация weekly stats
        if week_str not in self.productivity_data['weekly_stats']:
            self.productivity_data['weekly_stats'][week_str] = {
                'total_activities': 0,
                'total_duration': 0.0,
                'focused_time': 0.0,
                'distracted_time': 0.0,
                'by_type': {},
                'by_day': {},
                'user_activities': {}
            }

        # Инициализация monthly stats
        if month_str not in self.productivity_data['monthly_stats']:
            self.productivity_data['monthly_stats'][month_str] = {
                'total_activities': 0,
                'total_duration': 0.0,
                'focused_time': 0.0,
                'distracted_time': 0.0,
                'by_type': {},
                'by_week': {},
                'user_activities': {}
            }

        # Получаем daily stats для текущей даты
        daily_stats = self.productivity_data['daily_stats'].get(date_str, {})
        if not daily_stats:
            return

        weekly_stats = self.productivity_data['weekly_stats'][week_str]
        monthly_stats = self.productivity_data['monthly_stats'][month_str]

        # Агрегация для weekly stats
        weekly_stats['total_activities'] += daily_stats.get('total_activities', 0)
        weekly_stats['total_duration'] += daily_stats.get('total_duration', 0.0)
        weekly_stats['focused_time'] += daily_stats.get('focused_time', 0.0)
        weekly_stats['distracted_time'] += daily_stats.get('distracted_time', 0.0)

        # Агрегация по дням недели
        day_name = current_date.strftime('%A')
        if day_name not in weekly_stats['by_day']:
            weekly_stats['by_day'][day_name] = {
                'activities': 0,
                'duration': 0.0
            }
        weekly_stats['by_day'][day_name]['activities'] += daily_stats.get('total_activities', 0)
        weekly_stats['by_day'][day_name]['duration'] += daily_stats.get('total_duration', 0.0)

        # Агрегация для monthly stats
        monthly_stats['total_activities'] += daily_stats.get('total_activities', 0)
        monthly_stats['total_duration'] += daily_stats.get('total_duration', 0.0)
        monthly_stats['focused_time'] += daily_stats.get('focused_time', 0.0)
        monthly_stats['distracted_time'] += daily_stats.get('distracted_time', 0.0)

        # Агрегация по неделям
        if week_str not in monthly_stats['by_week']:
            monthly_stats['by_week'][week_str] = {
                'activities': 0,
                'duration': 0.0
            }
        monthly_stats['by_week'][week_str]['activities'] += daily_stats.get('total_activities', 0)
        monthly_stats['by_week'][week_str]['duration'] += daily_stats.get('total_duration', 0.0)

        # Агрегация по типам активности
        for activity_type, stats in daily_stats.get('by_type', {}).items():
            # Weekly aggregation by type
            if activity_type not in weekly_stats['by_type']:
                weekly_stats['by_type'][activity_type] = {
                    'count': 0,
                    'total_duration': 0.0
                }
            weekly_stats['by_type'][activity_type]['count'] += stats.get('count', 0)
            weekly_stats['by_type'][activity_type]['total_duration'] += stats.get('total_duration', 0.0)

            # Monthly aggregation by type
            if activity_type not in monthly_stats['by_type']:
                monthly_stats['by_type'][activity_type] = {
                    'count': 0,
                    'total_duration': 0.0
                }
            monthly_stats['by_type'][activity_type]['count'] += stats.get('count', 0)
            monthly_stats['by_type'][activity_type]['total_duration'] += stats.get('total_duration', 0.0)

        # Агрегация по пользователям
        for user_id, user_data in daily_stats.get('user_activities', {}).items():
            # Weekly user aggregation
            if user_id not in weekly_stats['user_activities']:
                weekly_stats['user_activities'][user_id] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'focused_time': 0.0,
                    'distracted_time': 0.0
                }
            weekly_stats['user_activities'][user_id]['count'] += user_data.get('count', 0)
            weekly_stats['user_activities'][user_id]['total_duration'] += user_data.get('total_duration', 0.0)
            weekly_stats['user_activities'][user_id]['focused_time'] += user_data.get('focused_time', 0.0)
            weekly_stats['user_activities'][user_id]['distracted_time'] += user_data.get('distracted_time', 0.0)

            # Monthly user aggregation
            if user_id not in monthly_stats['user_activities']:
                monthly_stats['user_activities'][user_id] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'focused_time': 0.0,
                    'distracted_time': 0.0
                }
            monthly_stats['user_activities'][user_id]['count'] += user_data.get('count', 0)
            monthly_stats['user_activities'][user_id]['total_duration'] += user_data.get('total_duration', 0.0)
            monthly_stats['user_activities'][user_id]['focused_time'] += user_data.get('focused_time', 0.0)
            monthly_stats['user_activities'][user_id]['distracted_time'] += user_data.get('distracted_time', 0.0)

    def get_productivity_report(self, period: str = "daily",
                                user_id: Optional[str] = None,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Получение отчета о продуктивности.

        Args:
            period: Период (daily, weekly, monthly)
            user_id: ID пользователя (опционально)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации

        Returns:
            Отчет о продуктивности
        """
        if period not in ['daily', 'weekly', 'monthly']:
            return {}

        stats_key = f'{period}_stats'
        if stats_key not in self.productivity_data:
            return {}

        stats = self.productivity_data[stats_key]

        # Фильтрация по дате, если указана
        if start_date or end_date:
            filtered_stats = {}
            for date_str, date_data in stats.items():
                date_obj = datetime.fromisoformat(date_str).date()
                if start_date and date_obj < start_date.date():
                    continue
                if end_date and date_obj > end_date.date():
                    continue
                filtered_stats[date_str] = date_data
            stats = filtered_stats

        if user_id:
            # Фильтрация по пользователю
            user_stats = {}
            for date_str, date_data in stats.items():
                if user_id in date_data.get('user_activities', {}):
                    user_stats[date_str] = date_data['user_activities'][user_id]
            return user_stats
        else:
            return stats

    def calculate_productivity_score(self, user_id: str,
                                     period: str = "daily",
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> float:
        """
        Вычисление score продуктивности.

        Args:
            user_id: ID пользователя
            period: Период
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации

        Returns:
            Score продуктивности (0-100)
        """
        report = self.get_productivity_report(period, user_id, start_date, end_date)

        if not report:
            return 0.0

        # Сбор статистик
        total_activities = 0
        total_duration = 0.0
        focused_time = 0.0
        distracted_time = 0.0

        for date_data in report.values():
            total_activities += date_data.get('count', 0)
            total_duration += date_data.get('total_duration', 0.0)
            focused_time += date_data.get('focused_time', 0.0)
            distracted_time += date_data.get('distracted_time', 0.0)

        # Расчет эффективности (отношение фокусированного времени к общему)
        efficiency = 0.0
        if total_duration > 0:
            efficiency = focused_time / total_duration

        # Нормализация score
        activity_score = min(total_activities / 50.0, 1.0)  # Макс 50 активностей = 1.0
        duration_score = min(total_duration / (8 * 3600), 1.0)  # 8 часов = 1.0
        efficiency_score = efficiency  # 0-1

        # Общий score (взвешенное среднее)
        productivity_score = (
            activity_score * 0.3 +
            duration_score * 0.3 +
            efficiency_score * 0.4
        ) * 100

        return round(productivity_score, 2)

    def set_productivity_goal(self, user_id: str, goal_type: str, target_value: float,
                              period: str = "daily", description: str = ""):
        """
        Установка цели продуктивности.

        Args:
            user_id: ID пользователя
            goal_type: Тип цели (activities, duration, focused_time, score)
            target_value: Целевое значение
            period: Период цели (daily, weekly, monthly)
            description: Описание цели
        """
        goal_id = f"{user_id}_{goal_type}_{period}_{datetime.now().timestamp()}"

        goal = {
            'id': goal_id,
            'user_id': user_id,
            'type': goal_type,
            'target_value': target_value,
            'period': period,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'progress': 0.0,
            'achieved': False
        }

        with self.lock:
            if user_id not in self.productivity_goals:
                self.productivity_goals[user_id] = []
            self.productivity_goals[user_id].append(goal)

            # Сохранение данных
            self.save_data()

    def check_goals_progress(self, user_id: str):
        """
        Проверка прогресса по целям продуктивности.

        Args:
            user_id: ID пользователя
        """
        if user_id not in self.productivity_goals:
            return

        with self.lock:
            for goal in self.productivity_goals[user_id]:
                if goal['achieved']:
                    continue

                # Получаем текущее значение для типа цели
                current_value = 0.0
                if goal['type'] == 'activities':
                    report = self.get_productivity_report(goal['period'], user_id)
                    for date_data in report.values():
                        current_value += date_data.get('count', 0)
                elif goal['type'] == 'duration':
                    report = self.get_productivity_report(goal['period'], user_id)
                    for date_data in report.values():
                        current_value += date_data.get('total_duration', 0.0)
                elif goal['type'] == 'focused_time':
                    report = self.get_productivity_report(goal['period'], user_id)
                    for date_data in report.values():
                        current_value += date_data.get('focused_time', 0.0)
                elif goal['type'] == 'score':
                    current_value = self.calculate_productivity_score(user_id, goal['period'])

                # Обновляем прогресс
                goal['progress'] = min(current_value / goal['target_value'], 1.0)
                goal['achieved'] = current_value >= goal['target_value']

            # Сохранение данных
            self.save_data()

    def get_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получение целей продуктивности пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список целей
        """
        self.check_goals_progress(user_id)
        return self.productivity_goals.get(user_id, [])

    def identify_productivity_patterns(self, user_id: str,
                                       days_back: int = 30) -> Dict[str, Any]:
        """
        Идентификация паттернов продуктивности.

        Args:
            user_id: ID пользователя
            days_back: Количество дней для анализа

        Returns:
            Паттерны продуктивности
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        daily_report = self.get_productivity_report('daily', user_id, start_date, end_date)

        patterns = {
            'most_productive_days': [],
            'most_common_activities': [],
            'optimal_working_hours': [],
            'productivity_trend': [],
            'efficiency_metrics': {}
        }

        if not daily_report:
            return patterns

        # Анализ по дням недели
        day_stats = {}
        for date_str, data in daily_report.items():
            date = datetime.fromisoformat(date_str)
            day_name = date.strftime('%A')

            if day_name not in day_stats:
                day_stats[day_name] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'focused_time': 0.0,
                    'efficiency': 0.0
                }

            day_stats[day_name]['count'] += data.get('count', 0)
            day_stats[day_name]['total_duration'] += data.get('total_duration', 0.0)
            day_stats[day_name]['focused_time'] += data.get('focused_time', 0.0)

            # Расчет эффективности для дня
            if data.get('total_duration', 0) > 0:
                efficiency = data.get('focused_time', 0) / data.get('total_duration', 1)
                day_stats[day_name]['efficiency'] += efficiency

        # Нормализация эффективности
        for day in day_stats:
            if day_stats[day]['count'] > 0:
                day_stats[day]['efficiency'] /= day_stats[day]['count']

        # Самые продуктивные дни
        if day_stats:
            sorted_days = sorted(day_stats.items(),
                                 key=lambda x: x[1]['focused_time'],
                                 reverse=True)
            patterns['most_productive_days'] = [
                {
                    'day': day,
                    'focused_time': stats['focused_time'],
                    'efficiency': stats['efficiency']
                }
                for day, stats in sorted_days
            ]

        # Самые частые активности
        activity_stats = {}
        for date_str, data in daily_report.items():
            for activity_type, stats in data.get('by_type', {}).items():
                if activity_type not in activity_stats:
                    activity_stats[activity_type] = {
                        'count': 0,
                        'total_duration': 0.0
                    }

                activity_stats[activity_type]['count'] += stats.get('count', 0)
                activity_stats[activity_type]['total_duration'] += stats.get('total_duration', 0.0)

        if activity_stats:
            sorted_activities = sorted(activity_stats.items(),
                                       key=lambda x: x[1]['count'],
                                       reverse=True)
            patterns['most_common_activities'] = [
                {'activity': activity, 'count': stats['count'], 'duration': stats['total_duration']}
                for activity, stats in sorted_activities[:5]
            ]

        # Оптимальные рабочие часы
        hour_stats = {h: 0 for h in range(24)}
        for date_str, data in daily_report.items():
            for hour_str, duration in data.get('by_hour', {}).items():
                hour = int(hour_str)
                hour_stats[hour] += duration

        if hour_stats:
            # Находим часы с максимальной продуктивностью
            max_hours = sorted(hour_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns['optimal_working_hours'] = [
                {'hour': hour, 'productivity': duration}
                for hour, duration in max_hours
            ]

        # Тренд продуктивности
        productivity_trend = []
        for i in range(days_back):
            date = start_date + timedelta(days=i)
            date_str = date.date().isoformat()

            if date_str in daily_report:
                data = daily_report[date_str]
                score = self.calculate_productivity_score(user_id, 'daily', date, date)
                productivity_trend.append({
                    'date': date_str,
                    'score': score,
                    'activities': data.get('count', 0),
                    'duration': data.get('total_duration', 0.0)
                })
            else:
                productivity_trend.append({
                    'date': date_str,
                    'score': 0,
                    'activities': 0,
                    'duration': 0.0
                })

        patterns['productivity_trend'] = productivity_trend

        # Метрики эффективности
        total_duration = sum([data.get('total_duration', 0) for data in daily_report.values()])
        total_focused = sum([data.get('focused_time', 0) for data in daily_report.values()])

        patterns['efficiency_metrics'] = {
            'total_duration': total_duration,
            'total_focused_time': total_focused,
            'efficiency_ratio': total_focused / total_duration if total_duration > 0 else 0,
            'avg_daily_activities': statistics.mean([data.get('count', 0) for data in daily_report.values()]),
            'avg_daily_duration': statistics.mean([data.get('total_duration', 0) for data in daily_report.values()])
        }

        return patterns

    def generate_productivity_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Генерация инсайтов о продуктивности.

        Args:
            user_id: ID пользователя

        Returns:
            Список инсайтов
        """
        insights = []

        # Score продуктивности
        weekly_score = self.calculate_productivity_score(user_id, 'weekly')
        monthly_score = self.calculate_productivity_score(user_id, 'monthly')

        if weekly_score < 30:
            insights.append({
                'type': 'low_productivity',
                'message': 'Низкая продуктивность на прошлой неделе',
                'suggestion': 'Попробуйте планировать задачи заранее и минимизировать отвлечения',
                'priority': 'high',
                'metric': 'weekly_score',
                'value': weekly_score
            })
        elif weekly_score > 80:
            insights.append({
                'type': 'high_productivity',
                'message': 'Отличная продуктивность на прошлой неделе!',
                'suggestion': 'Продолжайте в том же духе и делитесь своими методами',
                'priority': 'low',
                'metric': 'weekly_score',
                'value': weekly_score
            })

        # Анализ паттернов
        patterns = self.identify_productivity_patterns(user_id, 14)  # Анализ за 2 недели

        if patterns['most_productive_days']:
            best_day = patterns['most_productive_days'][0]
            insights.append({
                'type': 'productive_day',
                'message': f'Самый продуктивный день: {best_day["day"]}',
                'suggestion': 'Запланируйте важные задачи на этот день',
                'priority': 'medium',
                'metric': 'daily_focused_time',
                'value': best_day['focused_time']
            })

        # Анализ эффективности
        efficiency = patterns['efficiency_metrics']['efficiency_ratio']
        if efficiency < 0.5:
            insights.append({
                'type': 'low_efficiency',
                'message': 'Низкая эффективность работы',
                'suggestion': 'Уделите больше времени фокусированной работе, уменьшите отвлечения',
                'priority': 'high',
                'metric': 'efficiency_ratio',
                'value': efficiency
            })

        # Анализ оптимальных часов
        if patterns['optimal_working_hours']:
            best_hour = patterns['optimal_working_hours'][0]
            insights.append({
                'type': 'productive_hour',
                'message': f'Самый продуктивный час: {best_hour["hour"]}:00',
                'suggestion': 'Запланируйте сложные задачи на это время',
                'priority': 'medium',
                'metric': 'hourly_productivity',
                'value': best_hour['productivity']
            })

        # Проверка целей
        goals = self.get_goals(user_id)
        for goal in goals:
            if not goal['achieved'] and goal['progress'] > 0.7:
                insights.append({
                    'type': 'goal_progress',
                    'message': f'Цель "{goal["description"]}" близка к достижению',
                    'suggestion': 'Продолжайте в том же темпе для достижения цели',
                    'priority': 'medium',
                    'metric': goal['type'],
                    'value': goal['progress'] * 100
                })

        return insights

    def get_visualization_data(self, user_id: str, period: str = "weekly") -> Dict[str, Any]:
        """
        Подготовка данных для визуализации.

        Args:
            user_id: ID пользователя
            period: Период для визуализации

        Returns:
            Данные для визуализации
        """
        report = self.get_productivity_report(period, user_id)
        patterns = self.identify_productivity_patterns(user_id)

        visualization_data = {
            'summary': {
                'total_activities': sum([d.get('count', 0) for d in report.values()]),
                'total_duration': sum([d.get('total_duration', 0) for d in report.values()]),
                'focused_time': sum([d.get('focused_time', 0) for d in report.values()]),
                'distracted_time': sum([d.get('distracted_time', 0) for d in report.values()]),
                'productivity_score': self.calculate_productivity_score(user_id, period)
            },
            'by_day': patterns['most_productive_days'],
            'by_activity': patterns['most_common_activities'],
            'by_hour': patterns['optimal_working_hours'],
            'trend': patterns['productivity_trend'],
            'efficiency': patterns['efficiency_metrics']
        }

        return visualization_data

    def cleanup_old_data(self, max_age_days: int = 365):
        """
        Очистка устаревших данных.

        Args:
            max_age_days: Максимальный возраст данных в днях
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff_date.date().isoformat()

        with self.lock:
            # Очистка daily stats
            self.productivity_data['daily_stats'] = {
                k: v for k, v in self.productivity_data['daily_stats'].items()
                if k >= cutoff_str
            }

            # Пересчет weekly и monthly stats
            self.productivity_data['weekly_stats'] = {}
            self.productivity_data['monthly_stats'] = {}

            for date_str, daily_data in self.productivity_data['daily_stats'].items():
                date_obj = datetime.fromisoformat(date_str)
                self._aggregate_stats(date_obj)

            # Сохранение данных
            self.save_data()

    def shutdown(self):
        """Корректное завершение работы анализатора."""
        self.save_data()
        self.logger.info("Анализатор продуктивности завершил работу")