import asyncio
import json
from typing import Callable, Set
import redis.asyncio as aioredis


class RedisBroadcastManager:

  def __init__(self, redis_url: str = "redis://localhost:6379/0"):
    self.redis_url = redis_url
    self.redis = None
    self.pubsub = None
    self.listeners: Set[Callable[[dict], None]] = set()
    self._listener_task = None

  async def connect(self):
    self.redis = aioredis.from_url(
        self.redis_url, encoding="utf-8", decode_responses=True
    )
    self.pubsub = self.redis.pubsub()
    await self.pubsub.subscribe("sos_dispatch_channel")
    self._listener_task = asyncio.create_task(self._listen_loop())

  async def disconnect(self):
    if self._listener_task:
      self._listener_task.cancel()
    if self.pubsub:
      await self.pubsub.unsubscribe("sos_dispatch_channel")
      await self.pubsub.close()
    if self.redis:
      await self.redis.close()

  async def publish_sos(self, payload: dict):
    if self.redis:
      message = json.dumps(payload)
      await self.redis.publish("sos_dispatch_channel", message)

  def register_handler(self, handler: Callable[[dict], None]):
    self.listeners.add(handler)

  def unregister_handler(self, handler: Callable[[dict], None]):
    self.listeners.discard(handler)

  async def _listen_loop(self):
    try:
      async for message in self.pubsub.listen():
        if message and message.get("type") == "message":
          raw_data = message.get("data")
          if raw_data:
            data = json.loads(raw_data)
            for listener in list(self.listeners):
              if asyncio.iscoroutinefunction(listener):
                await listener(data)
              else:
                listener(data)
    except asyncio.CancelledError:
      pass