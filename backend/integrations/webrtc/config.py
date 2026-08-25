"""Configurable WebRTC ICE servers.

In-app voice calls use a browser peer connection. STUN alone lets the browser
discover public addresses but cannot relay media through symmetric NAT or
restricted corporate networks. For calls between browsers on different
networks, a TURN server is required. This settings object lets a deployment
supply one or more TURN servers through environment variables without changing
code and exposes them to the frontend through ``GET /api/v1/calls/ice/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class WebRTCSettings:
    ice_servers: list[dict]

    @property
    def available(self) -> bool:
        return bool(self.ice_servers)


def get_webrtc_settings() -> WebRTCSettings:
    stun_urls = _csv(
        "WEBRTC_STUN_URLS",
        "stun:stun.l.google.com:19302",
    )
    turn_urls = _csv("WEBRTC_TURN_URLS")
    turn_username = os.getenv("WEBRTC_TURN_USERNAME", "")
    turn_credential = os.getenv("WEBRTC_TURN_CREDENTIAL", "")

    ice_servers: list[dict] = []
    if stun_urls:
        ice_servers.append({"urls": stun_urls})
    if turn_urls and turn_username and turn_credential:
        ice_servers.append(
            {
                "urls": turn_urls,
                "username": turn_username,
                "credential": turn_credential,
            }
        )
    return WebRTCSettings(ice_servers=ice_servers)
