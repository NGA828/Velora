class ActionScopedThrottleMixin:
    """Select a DRF throttle scope from the current ViewSet action."""

    throttle_scope_by_action: dict[str, str] = {}

    def get_throttles(self):
        self.throttle_scope = self.throttle_scope_by_action.get(
            getattr(self, "action", ""),
            getattr(self, "throttle_scope", None),
        )
        return super().get_throttles()
