"""
Модуль интеграции с Azure для AI-ассистента Лиза.
"""

import logging
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from typing import Dict, Any, List, Optional


class AzureManager:
    """Менеджер для работы с Azure сервисами."""

    def __init__(self, subscription_id: str, tenant_id: str = None,
                 client_id: str = None, client_secret: str = None):
        self.logger = logging.getLogger(__name__)

        self.subscription_id = subscription_id
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

        # Клиенты Azure
        self.credential = None
        self.compute_client = None
        self.storage_client = None
        self.monitor_client = None

    def connect(self) -> bool:
        """Подключение к Azure сервисам."""
        try:
            # Создание credential
            if self.client_id and self.client_secret and self.tenant_id:
                from azure.identity import ClientSecretCredential
                self.credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                self.credential = DefaultAzureCredential()

            # Инициализация клиентов
            self.compute_client = ComputeManagementClient(
                self.credential, self.subscription_id
            )
            self.storage_client = StorageManagementClient(
                self.credential, self.subscription_id
            )
            self.monitor_client = MonitorManagementClient(
                self.credential, self.subscription_id
            )

            self.logger.info("Успешное подключение к Azure")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка подключения к Azure: {e}")
            return False

    def list_vms(self) -> List[Dict[str, Any]]:
        """Получение списка виртуальных машин."""
        if not self.compute_client:
            if not self.connect():
                return []

        try:
            vms = []
            for vm in self.compute_client.virtual_machines.list_all():
                vms.append({
                    'name': vm.name,
                    'location': vm.location,
                    'type': vm.hardware_profile.vm_size,
                    'os_type': vm.storage_profile.os_disk.os_type.value if vm.storage_profile.os_disk else 'Unknown',
                    'status': self._get_vm_status(vm.id)
                })

            return vms
        except Exception as e:
            self.logger.error(f"Ошибка получения списка VM: {e}")
            return []

    def _get_vm_status(self, vm_id: str) -> str:
        """Получение статуса виртуальной машины."""
        try:
            # Извлечение имени группы ресурсов и VM из ID
            parts = vm_id.split('/')
            resource_group = parts[parts.index('resourceGroups') + 1]
            vm_name = parts[parts.index('virtualMachines') + 1]

            # Получение статуса экземпляра
            instance_view = self.compute_client.virtual_machines.instance_view(
                resource_group, vm_name
            )

            for status in instance_view.statuses:
                if status.code.startswith('PowerState'):
                    return status.display_status

            return 'Unknown'
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса VM: {e}")
            return 'Error'

    def list_storage_accounts(self) -> List[Dict[str, Any]]:
        """Получение списка storage accounts."""
        if not self.storage_client:
            if not self.connect():
                return []

        try:
            accounts = []
            for account in self.storage_client.storage_accounts.list():
                accounts.append({
                    'name': account.name,
                    'location': account.location,
                    'type': account.sku.name,
                    'status': account.status_of_primary
                })

            return accounts
        except Exception as e:
            self.logger.error(f"Ошибка получения списка storage accounts: {e}")
            return []

    def get_metrics(self, resource_uri: str, metric_names: List[str],
                    time_range: str = "PT1H") -> Dict[str, List[float]]:
        """
        Получение метрик для ресурса.

        Args:
            resource_uri: URI ресурса
            metric_names: Список имен метрик
            time_range: Временной диапазон

        Returns:
            Словарь с метриками
        """
        if not self.monitor_client:
            if not self.connect():
                return {}

        try:
            metrics_data = {}

            for metric_name in metric_names:
                response = self.monitor_client.metrics.list(
                    resource_uri,
                    timespan=time_range,
                    interval="PT1M",
                    metricnames=metric_name,
                    aggregation="Average"
                )

                values = []
                for metric in response.value:
                    for timeseries in metric.timeseries:
                        for data in timeseries.data:
                            if data.average is not None:
                                values.append(data.average)

                metrics_data[metric_name] = values

            return metrics_data
        except Exception as e:
            self.logger.error(f"Ошибка получения метрик: {e}")
            return {}