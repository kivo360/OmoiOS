"""
Taskiq-based task queue for background and scheduled tasks.

This module provides:
- Redis-backed task broker for distributed task execution
- Scheduled tasks for billing operations (dunning, invoice generation)
- Background task support for async operations
"""

from omoi_os.tasks.broker import broker, scheduler
from omoi_os.tasks.billing_tasks import (
    process_failed_payments,
    generate_scheduled_invoices,
    send_payment_reminder,
)

__all__ = [
    "broker",
    "scheduler",
    "process_failed_payments",
    "generate_scheduled_invoices",
    "send_payment_reminder",
]
