from django.urls import path

from apps.messaging.consumers import UserEventsConsumer

websocket_urlpatterns = [
    path("ws/events/", UserEventsConsumer.as_asgi()),
]
