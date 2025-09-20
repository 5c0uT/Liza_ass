"""
Модуль интеграции с AWS для AI-ассистента Лиза.
"""
import datetime
import logging
import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError


class AWSManager:
    """Менеджер для работы с AWS сервисами."""

    def __init__(self, access_key: str, secret_key: str, region: str = "us-east-1"):
        self.logger = logging.getLogger(__name__)

        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

        # Клиенты AWS
        self.s3_client = None
        self.ec2_client = None
        self.lambda_client = None
        self.cloudwatch_client = None

    def connect(self) -> bool:
        """Подключение к AWS сервисам."""
        try:
            # Создание сессии
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )

            # Инициализация клиентов
            self.s3_client = session.client('s3')
            self.ec2_client = session.client('ec2')
            self.lambda_client = session.client('lambda')
            self.cloudwatch_client = session.client('cloudwatch')

            self.logger.info("Успешное подключение к AWS")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка подключения к AWS: {e}")
            return False

    def list_s3_buckets(self) -> List[str]:
        """Получение списка S3 buckets."""
        if not self.s3_client:
            if not self.connect():
                return []

        try:
            response = self.s3_client.list_buckets()
            return [bucket['Name'] for bucket in response['Buckets']]
        except ClientError as e:
            self.logger.error(f"Ошибка получения списка S3 buckets: {e}")
            return []

    def create_s3_bucket(self, bucket_name: str) -> bool:
        """Создание S3 bucket."""
        if not self.s3_client:
            if not self.connect():
                return False

        try:
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': self.region
                }
            )
            self.logger.info(f"S3 bucket создан: {bucket_name}")
            return True
        except ClientError as e:
            self.logger.error(f"Ошибка создания S3 bucket: {e}")
            return False

    def upload_to_s3(self, bucket_name: str, file_path: str,
                     object_name: str = None) -> bool:
        """
        Загрузка файла в S3 bucket.

        Args:
            bucket_name: Имя bucket
            file_path: Путь к файлу
            object_name: Имя объекта в S3 (опционально)

        Returns:
            True если файл загружен успешно
        """
        if not self.s3_client:
            if not self.connect():
                return False

        if object_name is None:
            object_name = file_path.split('/')[-1]

        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            self.logger.info(f"Файл загружен в S3: {bucket_name}/{object_name}")
            return True
        except ClientError as e:
            self.logger.error(f"Ошибка загрузки файла в S3: {e}")
            return False

    def list_ec2_instances(self) -> List[Dict[str, Any]]:
        """Получение списка EC2 инстансов."""
        if not self.ec2_client:
            if not self.connect():
                return []

        try:
            response = self.ec2_client.describe_instances()
            instances = []

            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'id': instance['InstanceId'],
                        'type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'launch_time': instance['LaunchTime'],
                        'public_ip': instance.get('PublicIpAddress', 'N/A'),
                        'private_ip': instance.get('PrivateIpAddress', 'N/A')
                    })

            return instances
        except ClientError as e:
            self.logger.error(f"Ошибка получения списка EC2 инстансов: {e}")
            return []

    def start_ec2_instance(self, instance_id: str) -> bool:
        """Запуск EC2 инстанса."""
        if not self.ec2_client:
            if not self.connect():
                return False

        try:
            self.ec2_client.start_instances(InstanceIds=[instance_id])
            self.logger.info(f"EC2 инстанс запущен: {instance_id}")
            return True
        except ClientError as e:
            self.logger.error(f"Ошибка запуска EC2 инстанса: {e}")
            return False

    def stop_ec2_instance(self, instance_id: str) -> bool:
        """Остановка EC2 инстанса."""
        if not self.ec2_client:
            if not self.connect():
                return False

        try:
            self.ec2_client.stop_instances(InstanceIds=[instance_id])
            self.logger.info(f"EC2 инстанс остановлен: {instance_id}")
            return True
        except ClientError as e:
            self.logger.error(f"Ошибка остановки EC2 инстанса: {e}")
            return False

    def get_cloudwatch_metrics(self, namespace: str, metric_name: str,
                               dimensions: List[Dict[str, str]],
                               period: int = 300, statistics: List[str] = None) -> List[Dict[str, Any]]:
        """
        Получение метрик из CloudWatch.

        Args:
            namespace: Пространство имен метрик
            metric_name: Имя метрики
            dimensions: Измерения метрики
            period: Период в секундах
            statistics: Статистики (Average, Sum, etc.)

        Returns:
            Список данных метрик
        """
        if not self.cloudwatch_client:
            if not self.connect():
                return []

        if statistics is None:
            statistics = ['Average']

        try:
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=datetime.utcnow() - datetime.timedelta(hours=1),
                EndTime=datetime.utcnow(),
                Period=period,
                Statistics=statistics
            )

            return response['Datapoints']
        except ClientError as e:
            self.logger.error(f"Ошибка получения метрик CloudWatch: {e}")
            return []