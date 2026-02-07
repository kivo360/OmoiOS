"""
Billing scheduled tasks for dunning, invoice generation, and payment reminders.

These tasks run on a schedule via taskiq to handle:
- Retrying failed payments (dunning)
- Sending payment reminder emails
- Generating monthly invoices for usage

Usage:
    # Start the scheduler
    taskiq scheduler omoi_os.tasks.broker:scheduler

    # Start the worker to process tasks
    taskiq worker omoi_os.tasks.broker:broker
"""

import logging
from datetime import datetime, timedelta

from omoi_os.tasks.broker import broker

logger = logging.getLogger(__name__)


# =============================================================================
# Payment Retry / Dunning Tasks
# =============================================================================


@broker.task(
    schedule=[
        # Run every 6 hours to retry failed payments
        {"cron": "0 */6 * * *"}
    ]
)
async def process_failed_payments() -> dict:
    """
    Process failed payments for dunning.

    This task:
    1. Finds invoices that are past_due with failed payments
    2. Retries payment up to 3 times over 7 days
    3. Sends email notifications for each attempt
    4. Suspends accounts after final failure
    5. Cancels subscriptions after grace period

    Schedule: Every 6 hours
    """
    from sqlalchemy import select, and_
    from omoi_os.models.billing import (
        Invoice,
        InvoiceStatus,
        BillingAccount,
        BillingAccountStatus,
        Payment,
        PaymentStatus,
    )
    from omoi_os.models.organization import Organization
    from omoi_os.services.database import get_database_service
    from omoi_os.services.billing_service import BillingService
    from omoi_os.services.email_service import get_email_service
    from omoi_os.utils.datetime import utc_now

    logger.info("Starting failed payment processing (dunning)")

    db = get_database_service()
    billing = BillingService(db=db)
    email = get_email_service()

    processed = 0
    retried = 0
    emails_sent = 0
    suspended = 0
    errors = []

    try:
        with db.get_session() as session:
            # Find past_due invoices
            result = session.execute(
                select(Invoice)
                .where(
                    and_(
                        Invoice.status == InvoiceStatus.PAST_DUE.value,
                        Invoice.amount_due > 0,
                    )
                )
                .order_by(Invoice.due_date.asc())
            )
            past_due_invoices = result.scalars().all()

            logger.info(f"Found {len(past_due_invoices)} past-due invoices")

            for invoice in past_due_invoices:
                processed += 1

                try:
                    # Get billing account and organization
                    account_result = session.execute(
                        select(BillingAccount).where(
                            BillingAccount.id == invoice.billing_account_id
                        )
                    )
                    account = account_result.scalar_one_or_none()
                    if not account:
                        continue

                    org_result = session.execute(
                        select(Organization).where(
                            Organization.id == account.organization_id
                        )
                    )
                    org = org_result.scalar_one_or_none()
                    if not org:
                        continue

                    # Count failed payment attempts for this invoice
                    payment_result = session.execute(
                        select(Payment)
                        .where(
                            and_(
                                Payment.invoice_id == invoice.id,
                                Payment.status == PaymentStatus.FAILED.value,
                            )
                        )
                        .order_by(Payment.created_at.desc())
                    )
                    failed_payments = list(payment_result.scalars().all())
                    attempt_count = len(failed_payments)

                    # Determine action based on attempt count and time since last attempt
                    last_attempt = (
                        failed_payments[0].created_at
                        if failed_payments
                        else invoice.due_date
                    )
                    hours_since_last = (utc_now() - last_attempt).total_seconds() / 3600

                    # Retry schedule:
                    # - 1st retry: 24 hours after failure
                    # - 2nd retry: 72 hours after 1st retry
                    # - 3rd retry: 72 hours after 2nd retry
                    # - Suspend after 3rd failure
                    should_retry = False
                    next_retry_date = None

                    if attempt_count == 0:
                        # First failure - retry after 24 hours
                        should_retry = hours_since_last >= 24
                        next_retry_date = datetime.now() + timedelta(days=3)
                    elif attempt_count == 1 and hours_since_last >= 72:
                        # Second retry after 72 hours
                        should_retry = True
                        next_retry_date = datetime.now() + timedelta(days=3)
                    elif attempt_count == 2 and hours_since_last >= 72:
                        # Third and final retry
                        should_retry = True
                    elif attempt_count >= 3 and hours_since_last >= 24:
                        # After 3 failed attempts, suspend account
                        if account.status != BillingAccountStatus.SUSPENDED.value:
                            account.status = BillingAccountStatus.SUSPENDED.value
                            session.flush()
                            suspended += 1
                            logger.warning(
                                f"Suspended account {account.id} after {attempt_count} failed payment attempts"
                            )

                            # Send cancellation email
                            billing_email = account.billing_email or org.billing_email
                            if billing_email:
                                await email.send_subscription_canceled_email(
                                    to_email=billing_email,
                                    user_name=org.name,
                                    reason="payment_failed",
                                )
                                emails_sent += 1
                        continue

                    if should_retry:
                        # Attempt payment retry
                        try:
                            payment = billing.process_invoice_payment(
                                invoice_id=invoice.id,
                                session=session,
                            )
                            retried += 1

                            # Send appropriate email based on result
                            billing_email = account.billing_email or org.billing_email
                            if billing_email:
                                if payment.status == PaymentStatus.SUCCEEDED.value:
                                    await email.send_payment_success_email(
                                        to_email=billing_email,
                                        user_name=org.name,
                                        amount_cents=int(payment.amount * 100),
                                        currency=payment.currency,
                                    )
                                else:
                                    await email.send_payment_failed_email(
                                        to_email=billing_email,
                                        user_name=org.name,
                                        amount_cents=int(invoice.amount_due * 100),
                                        currency=invoice.currency,
                                        attempt_number=attempt_count + 1,
                                        next_retry_date=next_retry_date,
                                    )
                                emails_sent += 1

                        except Exception as e:
                            errors.append(f"Invoice {invoice.id}: {str(e)}")
                            logger.error(
                                f"Failed to retry payment for invoice {invoice.id}: {e}"
                            )

                except Exception as e:
                    errors.append(f"Invoice {invoice.id}: {str(e)}")
                    logger.error(f"Error processing invoice {invoice.id}: {e}")

            session.commit()

    except Exception as e:
        logger.error(f"Failed payment processing error: {e}")
        errors.append(str(e))

    result = {
        "processed": processed,
        "retried": retried,
        "emails_sent": emails_sent,
        "suspended": suspended,
        "errors": errors[:10],  # Limit error list
    }
    logger.info(f"Completed failed payment processing: {result}")
    return result


@broker.task(
    schedule=[
        # Run daily at 9 AM UTC to send payment reminders
        {"cron": "0 9 * * *"}
    ]
)
async def send_payment_reminder() -> dict:
    """
    Send payment reminder emails for upcoming due invoices.

    This task:
    1. Finds open invoices due within 3 days
    2. Sends reminder emails to billing contacts

    Schedule: Daily at 9 AM UTC
    """
    from sqlalchemy import select, and_
    from omoi_os.models.billing import Invoice, InvoiceStatus, BillingAccount
    from omoi_os.models.organization import Organization
    from omoi_os.services.database import get_database_service
    from omoi_os.services.email_service import get_email_service
    from omoi_os.utils.datetime import utc_now

    logger.info("Starting payment reminder task")

    db = get_database_service()
    email = get_email_service()

    reminders_sent = 0
    errors = []

    try:
        with db.get_session() as session:
            # Find open invoices due within 3 days
            now = utc_now()
            three_days_from_now = now + timedelta(days=3)

            result = session.execute(
                select(Invoice).where(
                    and_(
                        Invoice.status == InvoiceStatus.OPEN.value,
                        Invoice.due_date.isnot(None),
                        Invoice.due_date <= three_days_from_now,
                        Invoice.due_date >= now,
                    )
                )
            )
            upcoming_invoices = result.scalars().all()

            logger.info(f"Found {len(upcoming_invoices)} invoices due within 3 days")

            for invoice in upcoming_invoices:
                try:
                    # Get billing account and organization
                    account_result = session.execute(
                        select(BillingAccount).where(
                            BillingAccount.id == invoice.billing_account_id
                        )
                    )
                    account = account_result.scalar_one_or_none()
                    if not account:
                        continue

                    org_result = session.execute(
                        select(Organization).where(
                            Organization.id == account.organization_id
                        )
                    )
                    org = org_result.scalar_one_or_none()
                    if not org:
                        continue

                    billing_email = account.billing_email or org.billing_email
                    if billing_email:
                        await email.send_invoice_generated_email(
                            to_email=billing_email,
                            user_name=org.name,
                            amount_cents=int(invoice.amount_due * 100),
                            currency=invoice.currency,
                            due_date=invoice.due_date,
                            invoice_url=invoice.stripe_invoice_url,
                        )
                        reminders_sent += 1
                        logger.info(f"Sent payment reminder for invoice {invoice.id}")

                except Exception as e:
                    errors.append(f"Invoice {invoice.id}: {str(e)}")
                    logger.error(
                        f"Failed to send reminder for invoice {invoice.id}: {e}"
                    )

    except Exception as e:
        logger.error(f"Payment reminder task error: {e}")
        errors.append(str(e))

    result = {
        "reminders_sent": reminders_sent,
        "errors": errors[:10],
    }
    logger.info(f"Completed payment reminder task: {result}")
    return result


# =============================================================================
# Invoice Generation Tasks
# =============================================================================


@broker.task(
    schedule=[
        # Run on the 1st of each month at 1 AM UTC
        {"cron": "0 1 1 * *"}
    ]
)
async def generate_scheduled_invoices() -> dict:
    """
    Generate monthly invoices for unbilled usage.

    This task:
    1. Finds all billing accounts with unbilled usage
    2. Generates invoices for the previous month's usage
    3. Sends invoice emails

    Schedule: 1st of each month at 1 AM UTC
    """
    from sqlalchemy import select
    from omoi_os.models.billing import BillingAccount, BillingAccountStatus, UsageRecord
    from omoi_os.models.organization import Organization
    from omoi_os.services.database import get_database_service
    from omoi_os.services.billing_service import BillingService
    from omoi_os.services.email_service import get_email_service

    logger.info("Starting monthly invoice generation")

    db = get_database_service()
    billing = BillingService(db=db)
    email = get_email_service()

    invoices_generated = 0
    emails_sent = 0
    errors = []

    try:
        with db.get_session() as session:
            # Get all active billing accounts
            result = session.execute(
                select(BillingAccount).where(
                    BillingAccount.status == BillingAccountStatus.ACTIVE.value
                )
            )
            accounts = result.scalars().all()

            logger.info(f"Processing {len(accounts)} active billing accounts")

            for account in accounts:
                try:
                    # Check if account has unbilled usage
                    usage_result = session.execute(
                        select(UsageRecord).where(
                            UsageRecord.billing_account_id == account.id,
                            UsageRecord.billed is False,
                        )
                    )
                    unbilled_usage = list(usage_result.scalars().all())

                    if not unbilled_usage:
                        continue

                    # Generate invoice
                    invoice = billing.generate_invoice(
                        billing_account_id=account.id,
                        session=session,
                    )

                    if invoice:
                        invoices_generated += 1
                        logger.info(
                            f"Generated invoice {invoice.invoice_number} for account {account.id}"
                        )

                        # Get organization for email
                        org_result = session.execute(
                            select(Organization).where(
                                Organization.id == account.organization_id
                            )
                        )
                        org = org_result.scalar_one_or_none()

                        if org:
                            billing_email = account.billing_email or org.billing_email
                            if billing_email:
                                await email.send_invoice_generated_email(
                                    to_email=billing_email,
                                    user_name=org.name,
                                    amount_cents=int(invoice.amount_due * 100),
                                    currency=invoice.currency,
                                    due_date=invoice.due_date,
                                    invoice_url=invoice.stripe_invoice_url,
                                )
                                emails_sent += 1

                except Exception as e:
                    errors.append(f"Account {account.id}: {str(e)}")
                    logger.error(
                        f"Failed to generate invoice for account {account.id}: {e}"
                    )

            session.commit()

    except Exception as e:
        logger.error(f"Invoice generation task error: {e}")
        errors.append(str(e))

    result = {
        "invoices_generated": invoices_generated,
        "emails_sent": emails_sent,
        "errors": errors[:10],
    }
    logger.info(f"Completed monthly invoice generation: {result}")
    return result


# =============================================================================
# Low Credit Warning Tasks
# =============================================================================


@broker.task(
    schedule=[
        # Run daily at 10 AM UTC to check for low credits
        {"cron": "0 10 * * *"}
    ]
)
async def check_low_credit_balances() -> dict:
    """
    Check for accounts with low credit balances and send warnings.

    This task:
    1. Finds accounts on prepaid/credits with balance below threshold
    2. Sends low credit warning emails

    Schedule: Daily at 10 AM UTC
    """
    from decimal import Decimal
    from sqlalchemy import select, and_
    from omoi_os.models.billing import BillingAccount, BillingAccountStatus
    from omoi_os.models.organization import Organization
    from omoi_os.models.subscription import Subscription, SubscriptionStatus
    from omoi_os.services.database import get_database_service
    from omoi_os.services.email_service import get_email_service

    logger.info("Starting low credit balance check")

    db = get_database_service()
    email = get_email_service()

    warnings_sent = 0
    errors = []

    LOW_CREDIT_THRESHOLD = Decimal("5.00")  # Warn when credits drop below $5

    try:
        with db.get_session() as session:
            # Find accounts with low credits that don't have an active subscription
            result = session.execute(
                select(BillingAccount).where(
                    and_(
                        BillingAccount.status == BillingAccountStatus.ACTIVE.value,
                        BillingAccount.credit_balance < float(LOW_CREDIT_THRESHOLD),
                        BillingAccount.credit_balance > 0,
                    )
                )
            )
            low_credit_accounts = result.scalars().all()

            logger.info(f"Found {len(low_credit_accounts)} accounts with low credits")

            for account in low_credit_accounts:
                try:
                    # Check if account has an active subscription
                    sub_result = session.execute(
                        select(Subscription).where(
                            and_(
                                Subscription.organization_id == account.organization_id,
                                Subscription.status.in_(
                                    [
                                        SubscriptionStatus.ACTIVE.value,
                                        SubscriptionStatus.TRIALING.value,
                                    ]
                                ),
                            )
                        )
                    )
                    subscription = sub_result.scalar_one_or_none()

                    # Only warn accounts without active subscriptions (pay-as-you-go)
                    if subscription:
                        continue

                    # Get organization for email
                    org_result = session.execute(
                        select(Organization).where(
                            Organization.id == account.organization_id
                        )
                    )
                    org = org_result.scalar_one_or_none()
                    if not org:
                        continue

                    billing_email = account.billing_email or org.billing_email
                    if billing_email:
                        await email.send_credits_low_email(
                            to_email=billing_email,
                            user_name=org.name,
                            remaining_credits=Decimal(str(account.credit_balance)),
                            threshold=LOW_CREDIT_THRESHOLD,
                        )
                        warnings_sent += 1
                        logger.info(f"Sent low credit warning to account {account.id}")

                except Exception as e:
                    errors.append(f"Account {account.id}: {str(e)}")
                    logger.error(
                        f"Failed to send low credit warning for account {account.id}: {e}"
                    )

    except Exception as e:
        logger.error(f"Low credit check task error: {e}")
        errors.append(str(e))

    result = {
        "warnings_sent": warnings_sent,
        "errors": errors[:10],
    }
    logger.info(f"Completed low credit balance check: {result}")
    return result


# =============================================================================
# Manual Task Triggers (can be called directly)
# =============================================================================


@broker.task
async def retry_single_payment(invoice_id: str) -> dict:
    """
    Manually trigger a payment retry for a specific invoice.

    Args:
        invoice_id: UUID string of the invoice to retry

    Returns:
        Result dict with success status and details
    """
    from uuid import UUID as UUIDType
    from omoi_os.models.billing import PaymentStatus
    from omoi_os.services.database import get_database_service
    from omoi_os.services.billing_service import BillingService

    logger.info(f"Manual payment retry requested for invoice {invoice_id}")

    db = get_database_service()
    billing = BillingService(db=db)

    try:
        payment = billing.process_invoice_payment(
            invoice_id=UUIDType(invoice_id),
        )

        success = payment.status == PaymentStatus.SUCCEEDED.value
        return {
            "success": success,
            "payment_id": str(payment.id),
            "status": payment.status,
            "message": (
                "Payment processed successfully" if success else "Payment failed"
            ),
        }
    except Exception as e:
        logger.error(f"Manual payment retry failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@broker.task
async def send_test_billing_email(
    email_type: str,
    to_email: str,
    **kwargs,
) -> dict:
    """
    Send a test billing email for verification.

    Args:
        email_type: Type of email (payment_failed, payment_success, etc.)
        to_email: Email address to send to
        **kwargs: Additional parameters for the email

    Returns:
        Result dict with success status
    """
    from omoi_os.services.email_service import get_email_service

    email = get_email_service()

    email_methods = {
        "payment_failed": email.send_payment_failed_email,
        "payment_success": email.send_payment_success_email,
        "subscription_canceled": email.send_subscription_canceled_email,
        "invoice_generated": email.send_invoice_generated_email,
        "credits_low": email.send_credits_low_email,
    }

    if email_type not in email_methods:
        return {
            "success": False,
            "error": f"Unknown email type: {email_type}. Valid types: {list(email_methods.keys())}",
        }

    try:
        method = email_methods[email_type]
        success = await method(to_email=to_email, **kwargs)
        return {
            "success": success,
            "email_type": email_type,
            "to": to_email,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
