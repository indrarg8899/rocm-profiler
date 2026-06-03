"""Alert engine for GPU metric thresholds."""

from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import time


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    name: str
    metric: str
    threshold: float
    operator: str  # "gt", "lt", "gte", "lte"
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: int = 60
    _last_fired: float = 0.0

    def check(self, value: float) -> bool:
        if time.time() - self._last_fired < self.cooldown_seconds:
            return False

        triggered = False
        if self.operator == "gt" and value > self.threshold:
            triggered = True
        elif self.operator == "lt" and value < self.threshold:
            triggered = True
        elif self.operator == "gte" and value >= self.threshold:
            triggered = True
        elif self.operator == "lte" and value <= self.threshold:
            triggered = True

        if triggered:
            self._last_fired = time.time()
        return triggered


@dataclass
class Alert:
    rule: AlertRule
    value: float
    gpu_id: int
    timestamp: float
    message: str = ""


class AlertEngine:
    """Monitor metrics and fire alerts on threshold violations."""

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self.max_alerts = 10000
        self.handlers: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self.handlers.append(handler)

    def evaluate(self, metrics: Dict) -> List[Alert]:
        """Evaluate all rules against current metrics."""
        fired = []
        gpu_id = metrics.get("gpu_id", 0)

        for rule in self.rules:
            value = metrics.get(rule.metric, 0)
            if value is None:
                continue

            if rule.check(value):
                alert = Alert(
                    rule=rule,
                    value=value,
                    gpu_id=gpu_id,
                    timestamp=time.time(),
                    message=f"GPU {gpu_id} {rule.name}: {rule.metric}={value} ({rule.operator} {rule.threshold})",
                )
                self.alerts.append(alert)
                fired.append(alert)

                for handler in self.handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        print(f"Alert handler error: {e}")

        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        return fired

    def get_recent_alerts(self, n: int = 10) -> List[Alert]:
        return self.alerts[-n:]


def setup_default_rules() -> List[AlertRule]:
    """Create sensible default alert rules."""
    return [
        AlertRule("High Temperature", "temperature_c", 85.0, "gt", AlertSeverity.WARNING),
        AlertRule("Critical Temperature", "temperature_c", 95.0, "gt", AlertSeverity.CRITICAL),
        AlertRule("High GPU Utilization", "utilization_gpu", 95.0, "gt", AlertSeverity.INFO),
        AlertRule("Memory Pressure", "memory_utilization", 90.0, "gt", AlertSeverity.WARNING),
        AlertRule("Critical Memory", "memory_utilization", 95.0, "gt", AlertSeverity.CRITICAL),
        AlertRule("High Power Draw", "power_utilization", 95.0, "gt", AlertSeverity.WARNING),
    ]
