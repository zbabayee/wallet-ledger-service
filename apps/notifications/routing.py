from django.urls import path

from apps.notifications.consumer import NotificationConsumer

websocket_urlpatterns = [
    path(
        "ws/notifications/",
        NotificationConsumer.as_asgi(),
    ),
]