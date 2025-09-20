"""
Детекция аномалий для AI-ассистента Лиза.
"""

import logging
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque, defaultdict
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope


class AnomalyDetector:
    """Детектор аномалий в данных и поведении системы."""

    def __init__(self, data_dir: str = "data/anomalies", sensitivity: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.sensitivity = max(0.1, min(2.0, sensitivity))  # 0.1 - 2.0, где 1.0 = нормальная чувствительность

        # Исторические данные для detection
        self.historical_data = {}

        # Статистики для различных метрик
        self.metric_stats = {}

        # Журнал обнаруженных аномалий
        self.anomaly_log = deque(maxlen=1000)

        # Модели машинного обучения для обнаружения аномалий
        self.models = {
            'isolation_forest': IsolationForest(contamination=0.1 * sensitivity),
            'dbscan': DBSCAN(eps=0.5 * sensitivity, min_samples=10),
            'lof': LocalOutlierFactor(n_neighbors=20, contamination=0.1 * sensitivity),
            'elliptic_envelope': EllipticEnvelope(contamination=0.1 * sensitivity)
        }

        # Система правил для обнаружения аномалий
        self.rules = self._initialize_rules()

        # Загрузка данных при инициализации
        self.load_data()

    def _initialize_rules(self) -> List[Dict[str, Any]]:
        """Инициализация системы правил для обнаружения аномалий."""
        return [
            {
                'name': 'sudden_spike',
                'description': 'Внезапный скачок значения метрики',
                'condition': lambda data, new_value: self._check_sudden_spike(data, new_value),
                'severity': 'high'
            },
            {
                'name': 'prolonged_high_value',
                'description': 'Продолжительное высокое значение метрики',
                'condition': lambda data, new_value: self._check_prolonged_high_value(data, new_value),
                'severity': 'medium'
            },
            {
                'name': 'zero_value',
                'description': 'Нулевое значение для ненулевой метрики',
                'condition': lambda data, new_value: self._check_zero_value(data, new_value),
                'severity': 'medium'
            },
            {
                'name': 'repeated_anomalies',
                'description': 'Повторяющиеся аномалии в короткий период',
                'condition': lambda data, new_value: self._check_repeated_anomalies(data['metric']),
                'severity': 'critical'
            }
        ]

    def load_data(self):
        """Загрузка исторических данных и статистик из файлов."""
        data_file = self.data_dir / "historical_data.json"
        stats_file = self.data_dir / "metric_stats.json"
        log_file = self.data_dir / "anomaly_log.json"

        try:
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Преобразование строк обратно в datetime
                    for metric, points in loaded_data.items():
                        self.historical_data[metric] = [
                            {'timestamp': datetime.fromisoformat(point['timestamp']), 'value': point['value']}
                            for point in points
                        ]
                self.logger.info(f"Загружены исторические данные для {len(self.historical_data)} метрик")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки исторических данных: {e}")

        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    # Преобразование строк обратно в datetime
                    for metric, stats in loaded_stats.items():
                        if 'last_trained' in stats:
                            stats['last_trained'] = datetime.fromisoformat(stats['last_trained'])
                        self.metric_stats[metric] = stats
                self.logger.info(f"Загружены статистики для {len(self.metric_stats)} метрик")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки статистик метрик: {e}")

        try:
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    loaded_log = json.load(f)
                    # Преобразование строк обратно в datetime
                    for anomaly in loaded_log:
                        anomaly['timestamp'] = datetime.fromisoformat(anomaly['timestamp'])
                        if 'detected_at' in anomaly:
                            anomaly['detected_at'] = datetime.fromisoformat(anomaly['detected_at'])
                    self.anomaly_log = deque(loaded_log, maxlen=1000)
                self.logger.info(f"Загружено {len(self.anomaly_log)} записей в журнале аномалий")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки журнала аномалий: {e}")

    def save_data(self):
        """Сохранение исторических данных, статистик и журнала аномалий."""
        data_file = self.data_dir / "historical_data.json"
        stats_file = self.data_dir / "metric_stats.json"
        log_file = self.data_dir / "anomaly_log.json"

        try:
            # Преобразование datetime в строки для сериализации
            serializable_data = {}
            for metric, points in self.historical_data.items():
                serializable_data[metric] = [
                    {'timestamp': point['timestamp'].isoformat(), 'value': point['value']}
                    for point in points
                ]

            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения исторических данных: {e}")

        try:
            # Преобразование datetime в строки для сериализации
            serializable_stats = {}
            for metric, stats in self.metric_stats.items():
                serializable_stats[metric] = stats.copy()
                if 'last_trained' in serializable_stats[metric]:
                    serializable_stats[metric]['last_trained'] = serializable_stats[metric]['last_trained'].isoformat()

            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения статистик метрик: {e}")

        try:
            # Преобразование datetime в строки для сериализации
            serializable_log = []
            for anomaly in self.anomaly_log:
                anomaly_copy = anomaly.copy()
                anomaly_copy['timestamp'] = anomaly_copy['timestamp'].isoformat()
                if 'detected_at' in anomaly_copy:
                    anomaly_copy['detected_at'] = anomaly_copy['detected_at'].isoformat()
                serializable_log.append(anomaly_copy)

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения журнала аномалий: {e}")

    def add_metric_data(self, metric_name: str, value: float, timestamp: datetime = None):
        """
        Добавление данных метрики для анализа.

        Args:
            metric_name: Имя метрики
            value: Значение метрики
            timestamp: Временная метка (опционально)
        """
        if timestamp is None:
            timestamp = datetime.now()

        if metric_name not in self.historical_data:
            self.historical_data[metric_name] = []

        self.historical_data[metric_name].append({
            'timestamp': timestamp,
            'value': value
        })

        # Поддержание размера исторических данных
        if len(self.historical_data[metric_name]) > 1000:
            self.historical_data[metric_name] = self.historical_data[metric_name][-1000:]

        # Сохранение данных
        self.save_data()

    def detect_anomalies(self, metric_name: str, new_value: float,
                         timestamp: datetime = None, use_ml: bool = True) -> List[Dict[str, Any]]:
        """
        Обнаружение аномалий в метрике с использованием multiple methods.

        Args:
            metric_name: Имя метрики
            new_value: Новое значение
            timestamp: Временная метка (опционально)
            use_ml: Использовать методы машинного обучения

        Returns:
            Список обнаруженных аномалий
        """
        if timestamp is None:
            timestamp = datetime.now()

        anomalies = []

        # Проверка с помощью статистических методов
        statistical_anomaly = self._detect_statistical_anomaly(metric_name, new_value, timestamp)
        if statistical_anomaly:
            anomalies.append(statistical_anomaly)

        # Проверка с помощью сезонного анализа
        seasonal_anomaly = self._detect_seasonal_anomaly(metric_name, new_value, timestamp)
        if seasonal_anomaly:
            anomalies.append(seasonal_anomaly)

        # Проверка с помощью методов машинного обучения
        if use_ml and metric_name in self.historical_data and len(self.historical_data[metric_name]) >= 50:
            ml_anomalies = self._detect_ml_anomalies(metric_name, new_value, timestamp)
            anomalies.extend(ml_anomalies)

        # Проверка с помощью системы правил
        rule_anomalies = self._check_rules(metric_name, new_value, timestamp)
        anomalies.extend(rule_anomalies)

        # Добавление нормального значения в historical data
        self.add_metric_data(metric_name, new_value, timestamp)

        # Логирование обнаруженных аномалий
        for anomaly in anomalies:
            self._log_anomaly(anomaly)

        return anomalies

    def _detect_statistical_anomaly(self, metric_name: str, new_value: float,
                                    timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Обнаружение аномалий с помощью статистических методов."""
        if metric_name not in self.historical_data or len(self.historical_data[metric_name]) < 10:
            return None

        historical_values = [point['value'] for point in self.historical_data[metric_name]]

        # Вычисление статистик
        mean = np.mean(historical_values)
        std = np.std(historical_values)

        if std == 0:
            return None

        # Z-score нового значения
        z_score = abs((new_value - mean) / std)

        # Порог аномалии на основе sensitivity
        threshold = 3.0 / self.sensitivity

        if z_score > threshold:
            return {
                'metric': metric_name,
                'value': new_value,
                'timestamp': timestamp,
                'z_score': z_score,
                'mean': mean,
                'std': std,
                'threshold': threshold,
                'severity': self._calculate_severity(z_score, threshold),
                'method': 'statistical'
            }

        return None

    def _detect_seasonal_anomaly(self, metric_name: str, new_value: float,
                                 timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Обнаружение сезонных аномалий с учетом временных patterns."""
        if metric_name not in self.historical_data or len(self.historical_data[metric_name]) < 100:
            return None

        # Группировка данных по времени суток
        hourly_data = {}
        for point in self.historical_data[metric_name]:
            hour = point['timestamp'].hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(point['value'])

        # Получение relevant hour
        current_hour = timestamp.hour
        if current_hour not in hourly_data:
            return None

        # Статистики для текущего часа
        hour_values = hourly_data[current_hour]
        hour_mean = np.mean(hour_values)
        hour_std = np.std(hour_values)

        if hour_std == 0:
            return None

        # Z-score относительно hourly patterns
        z_score = abs((new_value - hour_mean) / hour_std)
        threshold = 2.5 / self.sensitivity

        if z_score > threshold:
            return {
                'metric': metric_name,
                'value': new_value,
                'timestamp': timestamp,
                'z_score': z_score,
                'hourly_mean': hour_mean,
                'hourly_std': hour_std,
                'threshold': threshold,
                'severity': self._calculate_severity(z_score, threshold),
                'method': 'seasonal'
            }

        return None

    def _detect_ml_anomalies(self, metric_name: str, new_value: float,
                             timestamp: datetime) -> List[Dict[str, Any]]:
        """Обнаружение аномалий с помощью методов машинного обучения."""
        anomalies = []

        # Подготовка данных
        values = np.array([point['value'] for point in self.historical_data[metric_name]]).reshape(-1, 1)
        new_value_arr = np.array([[new_value]])

        # StandardScaler для нормализации данных
        scaler = StandardScaler()
        values_scaled = scaler.fit_transform(values)
        new_value_scaled = scaler.transform(new_value_arr)

        # Isolation Forest
        try:
            self.models['isolation_forest'].fit(values_scaled)
            prediction = self.models['isolation_forest'].predict(new_value_scaled)
            if prediction[0] == -1:  # -1 означает аномалию
                anomalies.append({
                    'metric': metric_name,
                    'value': new_value,
                    'timestamp': timestamp,
                    'method': 'isolation_forest',
                    'severity': 'medium'
                })
        except Exception as e:
            self.logger.error(f"Ошибка Isolation Forest: {e}")

        # Local Outlier Factor
        try:
            prediction = self.models['lof'].fit_predict(np.vstack([values_scaled, new_value_scaled]))
            if prediction[-1] == -1:  # -1 означает аномалию
                anomalies.append({
                    'metric': metric_name,
                    'value': new_value,
                    'timestamp': timestamp,
                    'method': 'lof',
                    'severity': 'medium'
                })
        except Exception as e:
            self.logger.error(f"Ошибка LOF: {e}")

        # Elliptic Envelope
        try:
            self.models['elliptic_envelope'].fit(values_scaled)
            prediction = self.models['elliptic_envelope'].predict(new_value_scaled)
            if prediction[0] == -1:  # -1 означает аномалию
                anomalies.append({
                    'metric': metric_name,
                    'value': new_value,
                    'timestamp': timestamp,
                    'method': 'elliptic_envelope',
                    'severity': 'medium'
                })
        except Exception as e:
            self.logger.error(f"Ошибка Elliptic Envelope: {e}")

        return anomalies

    def _check_rules(self, metric_name: str, new_value: float,
                     timestamp: datetime) -> List[Dict[str, Any]]:
        """Проверка аномалий с помощью системы правил."""
        anomalies = []

        # Получаем исторические данные для метрики
        metric_data = {
            'values': [point['value'] for point in self.historical_data.get(metric_name, [])],
            'timestamps': [point['timestamp'] for point in self.historical_data.get(metric_name, [])],
            'metric': metric_name
        }

        # Применяем все правила
        for rule in self.rules:
            try:
                if rule['condition'](metric_data, new_value):
                    anomalies.append({
                        'metric': metric_name,
                        'value': new_value,
                        'timestamp': timestamp,
                        'method': f'rule_{rule["name"]}',
                        'severity': rule['severity'],
                        'rule_description': rule['description']
                    })
            except Exception as e:
                self.logger.error(f"Ошибка применения правила {rule['name']}: {e}")

        return anomalies

    def _check_sudden_spike(self, data: Dict[str, Any], new_value: float) -> bool:
        """Проверка внезапного скачка значения метрики."""
        if not data['values']:
            return False

        # Берем последние 10 значений
        recent_values = data['values'][-10:] if len(data['values']) >= 10 else data['values']
        avg_recent = np.mean(recent_values)
        std_recent = np.std(recent_values) if len(recent_values) > 1 else 0

        if std_recent == 0:
            return False

        # Проверяем, превышает ли новое значение среднее более чем на 3 стандартных отклонения
        return abs(new_value - avg_recent) > 3 * std_recent

    def _check_prolonged_high_value(self, data: Dict[str, Any], new_value: float) -> bool:
        """Проверка продолжительного высокого значения метрики."""
        if not data['values']:
            return False

        # Вычисляем историческое среднее и стандартное отклонение
        historical_mean = np.mean(data['values'])
        historical_std = np.std(data['values'])

        if historical_std == 0:
            return False

        # Проверяем, является ли новое значение аномально высоким
        is_high = new_value > historical_mean + 2 * historical_std

        if not is_high:
            return False

        # Проверяем, были ли предыдущие значения также высокими
        recent_values = data['values'][-5:] if len(data['values']) >= 5 else data['values']
        high_count = sum(1 for v in recent_values if v > historical_mean + historical_std)

        # Если 4 из последних 5 значений были высокими
        return high_count >= 4

    def _check_zero_value(self, data: Dict[str, Any], new_value: float) -> bool:
        """Проверка нулевого значения для ненулевой метрики."""
        if new_value != 0:
            return False

        # Проверяем, является ли нулевое значение аномалией
        # (если метрика обычно не равна нулю)
        zero_count = sum(1 for v in data['values'] if v == 0)
        total_count = len(data['values'])

        if total_count == 0:
            return False

        # Если менее 5% исторических значений равны нулю
        return zero_count / total_count < 0.05

    def _check_repeated_anomalies(self, metric_name: str) -> bool:
        """Проверка повторяющихся аномалий в короткий период."""
        # Получаем последние аномалии для этой метрики
        recent_anomalies = [
            anomaly for anomaly in self.anomaly_log
            if anomaly['metric'] == metric_name and
            (datetime.now() - anomaly['detected_at']).total_seconds() < 3600  # За последний час
        ]

        # Если было 3 или более аномалий за последний час
        return len(recent_anomalies) >= 3

    def _calculate_severity(self, z_score: float, threshold: float) -> str:
        """Вычисление severity аномалии."""
        ratio = z_score / threshold

        if ratio > 2.0:
            return 'critical'
        elif ratio > 1.5:
            return 'high'
        elif ratio > 1.2:
            return 'medium'
        else:
            return 'low'

    def _log_anomaly(self, anomaly: Dict[str, Any]):
        """Логирование обнаруженной аномалии."""
        anomaly_with_timestamp = anomaly.copy()
        anomaly_with_timestamp['detected_at'] = datetime.now()
        self.anomaly_log.append(anomaly_with_timestamp)

        # Сохранение данных
        self.save_data()

    def train_baseline(self, metric_name: str, training_period: timedelta = timedelta(days=7)):
        """
        Обучение baseline модели для метрики.

        Args:
            metric_name: Имя метрики
            training_period: Период обучения
        """
        if metric_name not in self.historical_data:
            return

        cutoff_time = datetime.now() - training_period
        training_data = [
            point for point in self.historical_data[metric_name]
            if point['timestamp'] >= cutoff_time
        ]

        if not training_data:
            return

        values = [point['value'] for point in training_data]

        # Сохранение статистик
        self.metric_stats[metric_name] = {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'count': len(values),
            'last_trained': datetime.now()
        }

        self.logger.info(f"Baseline обучен для метрики {metric_name}")

        # Сохранение данных
        self.save_data()

    def multivariate_anomaly_detection(self, metrics: Dict[str, float],
                                      timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        Многомерное обнаружение аномалий.

        Args:
            metrics: Словарь метрик и их значений
            timestamp: Временная метка (опционально)

        Returns:
            Список обнаруженных аномалий
        """
        if timestamp is None:
            timestamp = datetime.now()

        anomalies = []

        # Проверяем, есть ли достаточные исторические данные для всех метрик
        valid_metrics = {}
        for metric_name, value in metrics.items():
            if metric_name in self.historical_data and len(self.historical_data[metric_name]) >= 20:
                valid_metrics[metric_name] = value

        if len(valid_metrics) < 2:
            return anomalies  # Недостаточно данных для многомерного анализа

        # Подготавливаем матрицу признаков
        feature_matrix = []
        for metric_name in valid_metrics.keys():
            # Берем последние 20 значений для каждой метрики
            recent_values = [point['value'] for point in self.historical_data[metric_name][-20:]]
            feature_matrix.append(recent_values)

        # Транспонируем матрицу (строки = временные точки, столбцы = метрики)
        feature_matrix = np.array(feature_matrix).T

        # Добавляем новое наблюдение
        new_observation = np.array(list(valid_metrics.values())).reshape(1, -1)

        # Применяем StandardScaler
        scaler = StandardScaler()
        feature_matrix_scaled = scaler.fit_transform(feature_matrix)
        new_observation_scaled = scaler.transform(new_observation)

        # Используем Isolation Forest для многомерного обнаружения аномалий
        try:
            iso_forest = IsolationForest(contamination=0.1 * self.sensitivity)
            iso_forest.fit(feature_matrix_scaled)
            prediction = iso_forest.predict(new_observation_scaled)

            if prediction[0] == -1:  # Аномалия
                # Вычисляем score аномалии
                scores = iso_forest.decision_function(new_observation_scaled)

                anomalies.append({
                    'type': 'multivariate',
                    'metrics': valid_metrics,
                    'timestamp': timestamp,
                    'method': 'isolation_forest',
                    'score': scores[0],
                    'severity': 'high' if scores[0] < -0.5 else 'medium'
                })
        except Exception as e:
            self.logger.error(f"Ошибка многомерного обнаружения аномалий: {e}")

        # Логирование обнаруженных аномалий
        for anomaly in anomalies:
            self._log_anomaly(anomaly)

        return anomalies

    def generate_anomaly_report(self, time_window: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Генерация отчета об аномалиях.

        Args:
            time_window: Временное окно

        Returns:
            Отчет об аномалиях
        """
        cutoff_time = datetime.now() - time_window
        recent_anomalies = [
            anomaly for anomaly in self.anomaly_log
            if anomaly['detected_at'] >= cutoff_time
        ]

        report = {
            'total_anomalies': len(recent_anomalies),
            'time_window': {
                'start': cutoff_time.isoformat(),
                'end': datetime.now().isoformat()
            },
            'by_severity': defaultdict(int),
            'by_metric': defaultdict(int),
            'by_method': defaultdict(int),
            'timeline': []
        }

        # Анализ аномалий
        for anomaly in recent_anomalies:
            report['by_severity'][anomaly.get('severity', 'unknown')] += 1

            if 'metric' in anomaly:
                report['by_metric'][anomaly['metric']] += 1
            elif 'metrics' in anomaly:
                for metric in anomaly['metrics']:
                    report['by_metric'][metric] += 1

            report['by_method'][anomaly.get('method', 'unknown')] += 1

            # Добавляем в timeline
            timeline_entry = {
                'timestamp': anomaly['detected_at'].isoformat(),
                'severity': anomaly.get('severity', 'unknown'),
                'method': anomaly.get('method', 'unknown')
            }

            if 'metric' in anomaly:
                timeline_entry['metric'] = anomaly['metric']
                timeline_entry['value'] = anomaly.get('value', 'unknown')
            elif 'metrics' in anomaly:
                timeline_entry['type'] = 'multivariate'
                timeline_entry['metrics'] = list(anomaly['metrics'].keys())

            report['timeline'].append(timeline_entry)

        # Сортируем timeline по времени
        report['timeline'].sort(key=lambda x: x['timestamp'])

        # Преобразуем defaultdict в обычные dict для сериализации
        report['by_severity'] = dict(report['by_severity'])
        report['by_metric'] = dict(report['by_metric'])
        report['by_method'] = dict(report['by_method'])

        return report

    def evaluate_detector_performance(self, metric_name: str,
                                     known_anomalies: List[Tuple[datetime, float]]) -> Dict[str, float]:
        """
        Оценка производительности детектора для конкретной метрики.

        Args:
            metric_name: Имя метрики
            known_anomalies: Список известных аномалий (временная метка, значение)

        Returns:
            Метрики производительности (precision, recall, f1)
        """
        if metric_name not in self.historical_data:
            return {'precision': 0, 'recall': 0, 'f1': 0}

        # Получаем все аномалии, обнаруженные для этой метрики
        detected_anomalies = [
            anomaly for anomaly in self.anomaly_log
            if anomaly.get('metric') == metric_name
        ]

        # Сопоставляем обнаруженные аномалии с известными
        true_positives = 0
        false_positives = 0
        false_negatives = 0

        # Для каждой известной аномалии проверяем, была ли она обнаружена
        for known_ts, known_value in known_anomalies:
            detected = False
            for detected_anomaly in detected_anomalies:
                # Проверяем временную близость (в пределах 5 минут)
                time_diff = abs((detected_anomaly['timestamp'] - known_ts).total_seconds())
                if time_diff < 300:  # 5 минут
                    detected = True
                    break

            if detected:
                true_positives += 1
            else:
                false_negatives += 1

        # Ложные срабатывания - обнаруженные аномалии, которых нет в известных
        for detected_anomaly in detected_anomalies:
            found = False
            for known_ts, known_value in known_anomalies:
                time_diff = abs((detected_anomaly['timestamp'] - known_ts).total_seconds())
                if time_diff < 300:  # 5 минут
                    found = True
                    break

            if not found:
                false_positives += 1

        # Вычисляем метрики
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            'precision': round(precision, 3),
            'recall': round(recall, 3),
            'f1': round(f1, 3),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives
        }

    def set_sensitivity(self, sensitivity: float):
        """
        Установка чувствительности детектора.

        Args:
            sensitivity: Уровень чувствительности (0.1 - 2.0)
        """
        self.sensitivity = max(0.1, min(2.0, sensitivity))

        # Обновляем параметры моделей машинного обучения
        self.models['isolation_forest'] = IsolationForest(contamination=0.1 * self.sensitivity)
        self.models['dbscan'] = DBSCAN(eps=0.5 * self.sensitivity, min_samples=10)
        self.models['lof'] = LocalOutlierFactor(n_neighbors=20, contamination=0.1 * self.sensitivity)
        self.models['elliptic_envelope'] = EllipticEnvelope(contamination=0.1 * self.sensitivity)

        self.logger.info(f"Установлена чувствительность: {self.sensitivity}")

    def add_custom_rule(self, name: str, description: str, condition: callable, severity: str = 'medium'):
        """
        Добавление пользовательского правила для обнаружения аномалий.

        Args:
            name: Имя правила
            description: Описание правила
            condition: Функция-условие (принимает data и new_value, возвращает bool)
            severity: Уровень серьезности (low, medium, high, critical)
        """
        self.rules.append({
            'name': name,
            'description': description,
            'condition': condition,
            'severity': severity
        })

        self.logger.info(f"Добавлено пользовательское правило: {name}")

    def cleanup_old_data(self, max_age_days: int = 365):
        """
        Очистка устаревших данных.

        Args:
            max_age_days: Максимальный возраст данных в днях
        """
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        # Очистка исторических данных
        for metric_name in list(self.historical_data.keys()):
            self.historical_data[metric_name] = [
                point for point in self.historical_data[metric_name]
                if point['timestamp'] >= cutoff_time
            ]

            # Если после очистки данных не осталось, удаляем метрику
            if not self.historical_data[metric_name]:
                del self.historical_data[metric_name]
                if metric_name in self.metric_stats:
                    del self.metric_stats[metric_name]

        # Очистка журнала аномалий
        self.anomaly_log = deque([
            anomaly for anomaly in self.anomaly_log
            if anomaly['detected_at'] >= cutoff_time
        ], maxlen=1000)

        # Сохранение данных
        self.save_data()

        self.logger.info(f"Очищены данные старше {max_age_days} дней")

    def shutdown(self):
        """Корректное завершение работы детектора аномалий."""
        self.save_data()
        self.logger.info("Детектор аномалий завершил работу")