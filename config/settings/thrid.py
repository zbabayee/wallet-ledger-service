import os

CHANNEL_LAYERS = {
    "default": {
        "BACKEND":
        "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.getenv("REDIS_HOST"),
                    int(os.getenv("REDIS_PORT"))
                )
            ]

        }

    }

}