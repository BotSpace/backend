import redis

from config.env import env

url = env.str("REDIS_URL")
if not isinstance(url, str):
    raise Exception("Invalid REDIS_URL")
client = redis.StrictRedis.from_url(url)


def subscribe(channel):
    sub = client.pubsub()
    sub.subscribe(channel)
    return sub.listen()


def publish(channel, message):
    return client.publish(channel, message)
