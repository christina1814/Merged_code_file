"""
Kafka connector for Sensei 2.0 (Apache Kafka on AKS).

Uses aiokafka for:
- Async producer with trace_id headers.
- Async consumer with handler callback.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from common.sensei_common.logging.logger import get_logger


class KafkaClient:
    """
    Async Kafka client for producing and consuming messages.

    This client is designed for Apache Kafka running on AKS.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        component: str = "common",
    ) -> None:
        """
        Initialize the Kafka client.

        Parameters
        ----------
        bootstrap_servers : str
            Comma-separated list of Kafka brokers.
        component : str
            Component label.
        """
        self._bootstrap_servers = bootstrap_servers
        self._component = component
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """
        Start the Kafka producer.
        """
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self) -> None:
        """
        Stop the Kafka producer.
        """
        if self._producer is not None:
            await self._producer.stop()

    async def publish(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Publish a JSON message to Kafka.

        Parameters
        ----------
        topic : str
            Topic name.
        value : Dict[str, Any]
            JSON-serializable payload.
        key : Optional[str]
            Message key.
        headers : Optional[Dict[str, str]]
            Additional headers.
        trace_id : Optional[str]
            Correlation ID.
        """
        if self._producer is None:
            raise RuntimeError("KafkaClient.start() must be called before publish()")

        logger = get_logger(self._component, "bus", "KafkaClient.publish", trace_id)
        hdrs = headers or {}
        if trace_id:
            hdrs.setdefault("trace_id", trace_id)

        kafka_headers = [(k, v.encode("utf-8")) for k, v in hdrs.items()]

        try:
            await self._producer.send_and_wait(
                topic=topic,
                key=None if key is None else key.encode("utf-8"),
                value=value,
                headers=kafka_headers,
            )
            logger.info("Published message to topic=%s", topic)
        except Exception as exc:  # noqa: BLE001
            logger.error("Kafka publish failed: %s", exc, ka_code="KA-BUS-0010")
            raise

    async def consume(
        self,
        topic: str,
        group_id: str,
        handler: Callable[[Dict[str, Any], Dict[str, str]], Awaitable[None]],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Consume messages from a topic and process them with handler.

        Parameters
        ----------
        topic : str
            Topic name.
        group_id : str
            Consumer group id.
        handler : Callable
            Async callback: handler(payload_dict, headers_dict).
        """
        logger = get_logger(self._component, "bus", "KafkaClient.consume", trace_id)
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )

        await consumer.start()
        try:
            async for msg in consumer:
                headers = {
                    k: v.decode("utf-8") for (k, v) in (msg.headers or [])
                }
                payload = msg.value
                try:
                    await handler(payload, headers)
                    await consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Kafka handler error for topic=%s: %s",
                        topic,
                        exc,
                        ka_code="KA-BUS-0011",
                    )
                    # Decide DLQ behavior here (e.g., publish to <topic>.dlq)
        finally:
            await consumer.stop()
