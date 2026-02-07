"""Email service using Resend."""

import resend
from pydantic_settings import BaseSettings
from typing import Optional
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailSettings(BaseSettings):
    """Email configuration."""

    resend_api_key: Optional[str] = None
    email_from: str = "OmoiOS <noreply@updates.omoios.dev>"
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_prefix": "", "extra": "ignore"}


class EmailService:
    """Service for sending transactional emails via Resend."""

    def __init__(self, settings: Optional[EmailSettings] = None):
        self.settings = settings or EmailSettings()
        if self.settings.resend_api_key:
            resend.api_key = self.settings.resend_api_key
        self._enabled = bool(self.settings.resend_api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send_verification_email(
        self, to_email: str, token: str, user_name: Optional[str] = None
    ) -> bool:
        """Send email verification link."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send verification to {to_email}"
            )
            return False

        verify_url = f"{self.settings.frontend_url}/verify-email?token={token}"
        name = user_name or "there"

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": "Verify your OmoiOS account",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Welcome to OmoiOS!</h2>
                    <p>Hi {name},</p>
                    <p>Thanks for signing up. Please verify your email address by clicking the button below:</p>
                    <p style="margin: 30px 0;">
                        <a href="{verify_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Verify Email
                        </a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="color: #666; word-break: break-all;">{verify_url}</p>
                    <p>This link expires in 24 hours.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you didn't create an account with OmoiOS, you can safely ignore this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Verification email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False

    async def send_password_reset_email(
        self, to_email: str, token: str, user_name: Optional[str] = None
    ) -> bool:
        """Send password reset link."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send password reset to {to_email}"
            )
            return False

        reset_url = f"{self.settings.frontend_url}/reset-password?token={token}"
        name = user_name or "there"

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": "Reset your OmoiOS password",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Password Reset Request</h2>
                    <p>Hi {name},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="margin: 30px 0;">
                        <a href="{reset_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Reset Password
                        </a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="color: #666; word-break: break-all;">{reset_url}</p>
                    <p>This link expires in 1 hour.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you didn't request a password reset, you can safely ignore this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Password reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False

    async def send_welcome_email(
        self, to_email: str, user_name: Optional[str] = None
    ) -> bool:
        """Send welcome email after verification."""
        if not self._enabled:
            logger.warning(f"Email not configured - would send welcome to {to_email}")
            return False

        name = user_name or "there"
        dashboard_url = f"{self.settings.frontend_url}/dashboard"

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": "Welcome to OmoiOS!",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>You're all set!</h2>
                    <p>Hi {name},</p>
                    <p>Your email has been verified and your OmoiOS account is ready to go.</p>
                    <p style="margin: 30px 0;">
                        <a href="{dashboard_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Go to Dashboard
                        </a>
                    </p>
                    <p>Here's what you can do next:</p>
                    <ul>
                        <li>Create your first organization</li>
                        <li>Set up your AI agents</li>
                        <li>Start automating your workflows</li>
                    </ul>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        Questions? Reply to this email and we'll help you out.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Welcome email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False

    # =========================================================================
    # Billing Emails
    # =========================================================================

    async def send_payment_failed_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        amount_cents: int = 0,
        currency: str = "usd",
        attempt_number: int = 1,
        next_retry_date: Optional[datetime] = None,
    ) -> bool:
        """Send payment failure notification."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send payment failed to {to_email}"
            )
            return False

        name = user_name or "there"
        amount = (
            f"${amount_cents / 100:.2f}"
            if currency == "usd"
            else f"{amount_cents / 100:.2f} {currency.upper()}"
        )
        billing_url = f"{self.settings.frontend_url}/settings/billing"

        # Adjust messaging based on attempt number
        if attempt_number == 1:
            subject = "Payment failed - Action required"
            urgency_message = "We'll automatically retry your payment in a few days."
        elif attempt_number == 2:
            subject = "Second payment attempt failed"
            urgency_message = (
                "Please update your payment method to avoid service interruption."
            )
        else:
            subject = "Final payment notice - Action required"
            urgency_message = "<strong>Your subscription may be canceled if payment is not received soon.</strong>"

        retry_info = ""
        if next_retry_date:
            retry_info = (
                f"<p>Next automatic retry: {next_retry_date.strftime('%B %d, %Y')}</p>"
            )

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": subject,
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Payment Failed</h2>
                    <p>Hi {name},</p>
                    <p>We weren't able to process your payment of {amount}.</p>
                    <p>{urgency_message}</p>
                    {retry_info}
                    <p style="margin: 30px 0;">
                        <a href="{billing_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Update Payment Method
                        </a>
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you have questions about this charge, please reply to this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(
                f"Payment failed email sent to {to_email} (attempt {attempt_number})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send payment failed email: {e}")
            return False

    async def send_payment_success_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        amount_cents: int = 0,
        currency: str = "usd",
        invoice_url: Optional[str] = None,
    ) -> bool:
        """Send payment success confirmation."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send payment success to {to_email}"
            )
            return False

        name = user_name or "there"
        amount = (
            f"${amount_cents / 100:.2f}"
            if currency == "usd"
            else f"{amount_cents / 100:.2f} {currency.upper()}"
        )

        invoice_link = ""
        if invoice_url:
            invoice_link = f"""
            <p style="margin: 30px 0;">
                <a href="{invoice_url}"
                   style="background-color: #7c3aed; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Invoice
                </a>
            </p>
            """

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": f"Payment received - {amount}",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Payment Successful</h2>
                    <p>Hi {name},</p>
                    <p>We've received your payment of {amount}. Thank you!</p>
                    {invoice_link}
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you have questions about this payment, please reply to this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Payment success email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send payment success email: {e}")
            return False

    async def send_subscription_canceled_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        end_date: Optional[datetime] = None,
        reason: str = "canceled",
    ) -> bool:
        """Send subscription cancellation notification."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send subscription canceled to {to_email}"
            )
            return False

        name = user_name or "there"
        billing_url = f"{self.settings.frontend_url}/settings/billing"

        end_info = ""
        if end_date:
            end_info = f"<p>Your access will continue until {end_date.strftime('%B %d, %Y')}.</p>"

        # Different messaging based on reason
        if reason == "payment_failed":
            subject = "Your subscription has been canceled due to payment issues"
            message = "We were unable to process your payment after multiple attempts, so your subscription has been canceled."
        else:
            subject = "Your subscription has been canceled"
            message = "Your subscription to OmoiOS has been canceled."

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": subject,
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Subscription Canceled</h2>
                    <p>Hi {name},</p>
                    <p>{message}</p>
                    {end_info}
                    <p>We'd love to have you back. You can resubscribe anytime from your billing page:</p>
                    <p style="margin: 30px 0;">
                        <a href="{billing_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Resubscribe
                        </a>
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you canceled by mistake or have feedback, please reply to this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Subscription canceled email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send subscription canceled email: {e}")
            return False

    async def send_invoice_generated_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        amount_cents: int = 0,
        currency: str = "usd",
        due_date: Optional[datetime] = None,
        invoice_url: Optional[str] = None,
    ) -> bool:
        """Send invoice notification."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send invoice generated to {to_email}"
            )
            return False

        name = user_name or "there"
        amount = (
            f"${amount_cents / 100:.2f}"
            if currency == "usd"
            else f"{amount_cents / 100:.2f} {currency.upper()}"
        )
        billing_url = f"{self.settings.frontend_url}/settings/billing"

        due_info = ""
        if due_date:
            due_info = (
                f"<p><strong>Due date:</strong> {due_date.strftime('%B %d, %Y')}</p>"
            )

        invoice_button = ""
        if invoice_url:
            invoice_button = f"""
            <p style="margin: 30px 0;">
                <a href="{invoice_url}"
                   style="background-color: #7c3aed; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Invoice
                </a>
            </p>
            """
        else:
            invoice_button = f"""
            <p style="margin: 30px 0;">
                <a href="{billing_url}"
                   style="background-color: #7c3aed; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    View Billing
                </a>
            </p>
            """

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": f"New invoice for {amount}",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Invoice Ready</h2>
                    <p>Hi {name},</p>
                    <p>A new invoice has been generated for your account.</p>
                    <p><strong>Amount:</strong> {amount}</p>
                    {due_info}
                    {invoice_button}
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you have questions about this invoice, please reply to this email.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Invoice generated email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send invoice generated email: {e}")
            return False

    async def send_credits_low_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        remaining_credits: Decimal = Decimal("0"),
        threshold: Decimal = Decimal("5"),
    ) -> bool:
        """Send low credits warning."""
        if not self._enabled:
            logger.warning(
                f"Email not configured - would send credits low to {to_email}"
            )
            return False

        name = user_name or "there"
        billing_url = f"{self.settings.frontend_url}/settings/billing"

        try:
            resend.Emails.send(
                {
                    "from": self.settings.email_from,
                    "to": [to_email],
                    "subject": "Your OmoiOS credits are running low",
                    "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Low Credits Warning</h2>
                    <p>Hi {name},</p>
                    <p>Your OmoiOS account has <strong>${remaining_credits:.2f}</strong> in credits remaining.</p>
                    <p>To ensure uninterrupted service, please add more credits to your account.</p>
                    <p style="margin: 30px 0;">
                        <a href="{billing_url}"
                           style="background-color: #7c3aed; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Add Credits
                        </a>
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px;">
                        Consider upgrading to a subscription plan for better value and automatic renewals.
                    </p>
                </div>
                """,
                }
            )
            logger.info(f"Credits low email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send credits low email: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
