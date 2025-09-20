"""
Модуль интеграции с Google Cloud Platform для AI-ассистента Лиза.
"""

import logging
from google.cloud import compute_v1, storage, monitoring_v3
from google.oauth2 import service_account
from typing import Dict, Any, List, Optional


class GCPManager:
    """Менеджер для работы с GCP сервисами."""

    def __init__(self, project_id: str, credentials_path: str = None):
        self.logger = logging.getLogger(__name__)

        self.project_id = project_id
        self.credentials_path = credentials_path

        # Клиенты GCP
        self.compute_client = None
        self.storage_client = None
        self.monitoring_client = None

    def connect(self) -> bool:
        """Подключение к GCP сервисам."""
        try:
            # Настройка credentials
            if self.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
            else:
                # Использование Application Default Credentials
                credentials = None

            # Инициализация клиентов
            self.compute_client = compute_v1.InstancesClient(credentials=credentials)
            self.storage_client = storage.Client(
                project=self.project_id, credentials=credentials
            )
            self.monitoring_client = monitoring_v3.MetricServiceClient(credentials=credentials)

            self.logger.info("Успешное подключение к GCP")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка подключения к GCP: {e}")
            return False

    def list_instances(self, zone: str = "us-central1-a") -> List[Dict[str, Any]]:
        """Получение списка VM instances."""
        if not self.compute_client:
            if not self.connect():
                return []

        try:
            instances = []
            request = compute_v1.ListInstancesRequest(
                project=self.project_id,
                zone=zone
            )

            for instance in self.compute_client.list(request=request):
                instances.append({
                    'name': instance.name,
                    'zone': zone,
                    'type': instance.machine_type.split('/')[-1],
                    'status': instance.status,
                    'ip': instance.network_interfaces[0].access_configs[
                        0].nat_ip if instance.network_interfaces else 'N/A'
                })

            return instances
        except Exception as e:
            self.logger.error(f"Ошибка получения списка instances: {e}")
            return []

    def list_buckets(self) -> List[Dict[str, Any]]:
        """Получение списка Cloud Storage buckets."""
        if not self.storage_client:
            if not self.connect():
                return []

        try:
            buckets = []
            for bucket in self.storage_client.list_buckets():
                buckets.append({
                    'name': bucket.name,
                    'location': bucket.location,
                    'created': bucket.time_created,
                    'storage_class': bucket.storage_class
                })

            return buckets
        except Exception as e:
            self.logger.error(f"Ошибка получения списка buckets: {e}")
            return []

    def get_monitoring_data(self, metric_type: str, resource_type: str = "gce_instance",
                            minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Получение данных мониторинга из Cloud Monitoring.

        Args:
            metric_type: Тип метрики
            resource_type: Тип ресурса
            minutes: Количество минут для данных

        Returns:
            Список данных мониторинга
        """
        if not self.monitoring_client:
            if not self.connect():
                return []

        try:
            project_name = f"projects/{self.project_id}"

            # Подготовка запроса
            interval = monitoring_v3.TimeInterval()
            now = datetime.now()
            interval.end_time = now
            interval.start_time = now - timedelta(minutes=minutes)

            request = monitoring_v3.ListTimeSeriesRequest(
                name=project_name,
                filter=f'resource.type="{resource_type}" AND metric.type="{metric_type}"',
                interval=interval,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            )

            # Получение данных
            results = []
            for time_series in self.monitoring_client.list_time_series(request=request):
                for point in time_series.points:
                    results.append({
                        'metric': time_series.metric.type,
                        'value': point.value.double_value or point.value.int64_value,
                        'timestamp': point.interval.end_time,
                        'resource': time_series.resource.labels.get('instance_id', 'unknown')
                    })

            return results
        except Exception as e:
            self.logger.error(f"Ошибка получения данных мониторинга: {e}")
            return []