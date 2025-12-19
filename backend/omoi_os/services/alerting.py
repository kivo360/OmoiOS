"""Alerting service with rule evaluation and routing per REQ-ALERT-001."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from omoi_os.logging import get_logger
from omoi_os.models.monitor_anomaly import Alert
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


class AlertRule:
    """Alert rule definition from YAML."""
    
    def __init__(self, rule_id: str, config: Dict[str, Any]):
        self.rule_id = rule_id
        self.name = config.get("name", rule_id)
        self.metric_name = config.get("metric", "")
        self.condition = config.get("condition", "")
        self.severity = config.get("severity", "warning")
        self.routing = config.get("routing", [])
        self.deduplication_window = self._parse_duration(config.get("deduplication_window", "300s"))
        self.enabled = config.get("enabled", True)
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string like '300s' or '5m' to seconds."""
        match = re.match(r"(\d+)([smhd])", duration_str.lower())
        if not match:
            return 300  # Default 5 minutes
        
        value, unit = match.groups()
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return int(value) * multipliers.get(unit, 1)
    
    def evaluate(self, metric_name: str, value: float, labels: Dict[str, Any]) -> bool:
        """Evaluate rule condition against metric value."""
        if not self.enabled:
            return False
        
        if self.metric_name != metric_name:
            return False
        
        # Simple condition evaluation (supports: "value > 2", "value >= 0.8", "value < 10")
        # In production, use a proper expression evaluator like simpleeval
        try:
            # Replace 'value' with actual value in condition
            condition_expr = self.condition.replace("value", str(value))
            # Safe evaluation using operator module
            import operator
            ops = {
                ">": operator.gt,
                ">=": operator.ge,
                "<": operator.lt,
                "<=": operator.le,
                "==": operator.eq,
                "!=": operator.ne,
            }
            # Parse simple comparisons
            for op_str, op_func in ops.items():
                if op_str in condition_expr:
                    parts = condition_expr.split(op_str, 1)
                    if len(parts) == 2:
                        left = float(parts[0].strip())
                        right = float(parts[1].strip())
                        return op_func(left, right)
            # Fallback: try eval with restricted globals (not ideal but works for simple cases)
            result = eval(condition_expr, {"__builtins__": {}}, {})
            return bool(result)
        except Exception as e:
            logger.warning(f"Error evaluating condition '{self.condition}': {e}")
            return False


class AlertService:
    """Alerting service with rule evaluation and routing per REQ-ALERT-001."""
    
    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        rules_dir: Optional[Path] = None,
    ):
        self.db = db
        self.event_bus = event_bus
        self.rules_dir = rules_dir or Path("config/alert_rules")
        self.rules: Dict[str, AlertRule] = {}
        self.routers: Dict[str, Any] = {}
        
        # Load alert rules
        self._load_rules()
        
        # Initialize routing adapters
        self._init_routers()
        
        # Subscribe to monitoring events
        self._subscribe_to_events()
    
    def _load_rules(self) -> None:
        """Load alert rules from YAML files."""
        if not self.rules_dir.exists():
            logger.warning(f"Alert rules directory not found: {self.rules_dir}")
            return
        
        for yaml_file in self.rules_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                
                rules_config = data.get("rules", [])
                for rule_config in rules_config:
                    rule_id = rule_config.get("name", f"{yaml_file.stem}-{len(self.rules)}")
                    rule = AlertRule(rule_id, rule_config)
                    self.rules[rule_id] = rule
                    logger.info(f"Loaded alert rule: {rule_id}")
            except Exception as e:
                logger.error(f"Error loading alert rule from {yaml_file}: {e}")
    
    def _init_routers(self) -> None:
        """Initialize routing adapters."""
        # Email router (placeholder - would use smtplib or email service)
        self.routers["email"] = EmailRouter()
        
        # Slack router (placeholder - would use Slack webhook)
        self.routers["slack"] = SlackRouter()
        
        # Webhook router (placeholder - would use HTTP client)
        self.routers["webhook"] = WebhookRouter()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to monitoring events for alert evaluation."""
        # In production, this would use actual event bus subscription
        # For now, alerts are triggered via evaluate_rules() method
        logger.info("AlertService subscribed to monitoring events")
    
    def evaluate_rules(
        self, metric_name: str, value: float, labels: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Evaluate alert rules against metric values.
        
        Args:
            metric_name: Name of the metric
            value: Current metric value
            labels: Optional metric labels (agent_id, phase_id, etc.)
        
        Returns:
            List of triggered alerts
        """
        labels = labels or {}
        triggered_alerts = []
        
        for rule_id, rule in self.rules.items():
            if rule.evaluate(metric_name, value, labels):
                # Check for duplicate alerts (deduplication)
                if self._is_duplicate(rule_id, metric_name, labels):
                    continue
                
                # Create alert
                alert = self._create_alert(rule, metric_name, value, labels)
                triggered_alerts.append(alert)
                
                # Route alert
                self.route_alert(alert)
        
        return triggered_alerts
    
    def _is_duplicate(
        self, rule_id: str, metric_name: str, labels: Dict[str, Any]
    ) -> bool:
        """Check if similar alert was recently triggered (deduplication)."""
        with self.db.get_session() as session:
            from datetime import timedelta
            
            # Get deduplication window for this rule
            rule = self.rules.get(rule_id)
            if not rule:
                return False
            
            window_start = utc_now() - timedelta(seconds=rule.deduplication_window)
            
            # Check for similar alerts in the window
            existing = (
                session.query(Alert)
                .filter(
                    Alert.rule_id == rule_id,
                    Alert.metric_name == metric_name,
                    Alert.triggered_at >= window_start,
                    Alert.resolved_at.is_(None),  # Only active alerts
                )
                .first()
            )
            
            return existing is not None
    
    def _create_alert(
        self, rule: AlertRule, metric_name: str, value: float, labels: Dict[str, Any]
    ) -> Alert:
        """Create alert record in database."""
        with self.db.get_session() as session:
            alert = Alert(
                rule_id=rule.rule_id,
                metric_name=metric_name,
                severity=rule.severity,
                current_value=value,
                threshold=0.0,  # Would extract from condition
                message=f"{rule.name}: {metric_name} = {value} (condition: {rule.condition})",
                labels=labels,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            session.expunge(alert)
            
            # Publish alert event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="alert.triggered",
                        entity_type="alert",
                        entity_id=alert.id,
                        payload={
                            "rule_id": rule.rule_id,
                            "metric_name": metric_name,
                            "severity": rule.severity,
                            "value": value,
                            "labels": labels,
                        },
                    )
                )
            
            return alert
    
    def route_alert(self, alert: Alert) -> None:
        """Route alert to configured channels per REQ-ALERT-001."""
        rule = self.rules.get(alert.rule_id)
        if not rule:
            return
        
        for channel in rule.routing:
            router = self.routers.get(channel)
            if router:
                try:
                    router.send(alert, rule)
                except Exception as e:
                    logger.error(f"Error routing alert {alert.id} to {channel}: {e}")
            else:
                logger.warning(f"Unknown routing channel: {channel}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """Mark alert as acknowledged per REQ-ALERT-001."""
        with self.db.get_session() as session:
            alert = session.get(Alert, alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            alert.acknowledged_at = utc_now()
            alert.acknowledged_by = acknowledged_by
            session.commit()
            session.refresh(alert)
            session.expunge(alert)
            
            # Publish acknowledgment event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="alert.acknowledged",
                        entity_type="alert",
                        entity_id=alert_id,
                        payload={"acknowledged_by": acknowledged_by},
                    )
                )
            
            return alert
    
    def resolve_alert(
        self, alert_id: str, resolved_by: str, note: Optional[str] = None
    ) -> Alert:
        """Mark alert as resolved per REQ-ALERT-001."""
        with self.db.get_session() as session:
            alert = session.get(Alert, alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            alert.resolved_at = utc_now()
            alert.resolved_by = resolved_by
            alert.resolution_note = note
            session.commit()
            session.refresh(alert)
            session.expunge(alert)
            
            # Publish resolution event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="alert.resolved",
                        entity_type="alert",
                        entity_id=alert_id,
                        payload={"resolved_by": resolved_by, "note": note},
                    )
                )
            
            return alert
    
    def get_active_alerts(
        self, severity: Optional[str] = None, limit: int = 100
    ) -> List[Alert]:
        """Get active (unresolved) alerts."""
        with self.db.get_session() as session:
            query = session.query(Alert).filter(Alert.resolved_at.is_(None))
            
            if severity:
                query = query.filter(Alert.severity == severity)
            
            alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()
            
            # Expunge alerts so they can be used outside the session
            for alert in alerts:
                session.expunge(alert)
            
            return alerts


class EmailRouter:
    """Email routing adapter for alerts."""
    
    def send(self, alert: Alert, rule: AlertRule) -> None:
        """Send alert via email (placeholder implementation)."""
        logger.info(f"Email alert: {alert.message} (severity: {alert.severity})")
        # TODO: Implement actual email sending via SMTP or email service


class SlackRouter:
    """Slack webhook routing adapter for alerts."""
    
    def send(self, alert: Alert, rule: AlertRule) -> None:
        """Send alert via Slack webhook (placeholder implementation)."""
        logger.info(f"Slack alert: {alert.message} (severity: {alert.severity})")
        # TODO: Implement actual Slack webhook POST


class WebhookRouter:
    """Generic webhook routing adapter for alerts."""
    
    def send(self, alert: Alert, rule: AlertRule) -> None:
        """Send alert via webhook (placeholder implementation)."""
        logger.info(f"Webhook alert: {alert.message} (severity: {alert.severity})")
        # TODO: Implement actual HTTP webhook POST

