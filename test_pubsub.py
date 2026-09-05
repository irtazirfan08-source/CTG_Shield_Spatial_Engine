import asyncio
from unittest.mock import AsyncMock, MagicMock
from pubsub import RedisBroadcastManager


async def run_test():
  manager = RedisBroadcastManager(redis_url="redis://fake-url")

  mock_redis = MagicMock()
  mock_pubsub = MagicMock()

  mock_redis.pubsub.return_value = mock_pubsub
  mock_pubsub.subscribe = AsyncMock()
  mock_redis.publish = AsyncMock()

  manager.redis = mock_redis
  manager.pubsub = mock_pubsub

  received_events = []

  def on_sos_alert(data):
    received_events.append(data)

  manager.register_handler(on_sos_alert)

  test_payload = {
      "incident_id": "INC-708",
      "lat": 22.3569,
      "lng": 91.7832,
      "severity": "CRITICAL",
  }

  await manager.publish_sos(test_payload)
  mock_redis.publish.assert_awaited_once()

  on_sos_alert(test_payload)

  assert len(received_events) == 1
  assert received_events[0]["severity"] == "CRITICAL"
  print("Redis Broadcast Manager unit test passed successfully.")


if __name__ == "__main__":
  asyncio.run(run_test())