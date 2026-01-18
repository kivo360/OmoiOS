"""
Taskiq-based task queue for background and scheduled tasks.

This module provides:
- Redis-backed task broker for distributed task execution
- Scheduled tasks for billing operations (dunning, invoice generation)
- Background task support for async operations
- Scaffolding tasks for spec-driven development workflows
"""

from omoi_os.tasks.broker import broker, scheduler
from omoi_os.tasks.billing_tasks import (
    process_failed_payments,
    generate_scheduled_invoices,
    send_payment_reminder,
)
from omoi_os.tasks.scaffolding import (
    trigger_scaffolding,
    trigger_scaffolding_for_ticket,
)

__all__ = [
    "broker",
    "scheduler",
    "process_failed_payments",
    "generate_scheduled_invoices",
    "send_payment_reminder",
    "trigger_scaffolding",
    "trigger_scaffolding_for_ticket",
]
