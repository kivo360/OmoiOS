"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Mail, CheckCircle, Loader2, ArrowLeft } from "lucide-react";
import {
  verifyEmail as apiVerifyEmail,
  resendVerification,
} from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email");
  const token = searchParams.get("token");

  const [isVerifying, setIsVerifying] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState("");

  // If token is present, verify automatically
  useEffect(() => {
    if (token) {
      handleVerifyEmail(token);
    }
  }, [token]);

  const handleVerifyEmail = async (verifyToken: string) => {
    setIsVerifying(true);
    setError("");

    try {
      await apiVerifyEmail(verifyToken);
      setIsVerified(true);
      setTimeout(() => {
        router.push("/onboarding");
      }, 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Verification failed. Please try again.");
      }
    } finally {
      setIsVerifying(false);
    }
  };

  const resendEmail = async () => {
    if (!email) return;
    setIsResending(true);
    setError("");

    try {
      await resendVerification(email);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        const message =
          err instanceof Error ? err.message : "Failed to resend email";
        setError(message);
      }
    } finally {
      setIsResending(false);
    }
  };

  if (isVerifying) {
    return (
      <div className="space-y-6 text-center">
        <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary" />
        <div>
          <CardTitle className="text-2xl">Verifying your email...</CardTitle>
          <CardDescription className="mt-2">
            Please wait while we verify your email address.
          </CardDescription>
        </div>
      </div>
    );
  }

  if (isVerified) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
          <CheckCircle className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <CardTitle className="text-2xl">Email verified!</CardTitle>
          <CardDescription className="mt-2">
            Your email has been verified. Redirecting to onboarding...
          </CardDescription>
        </div>
        <Button asChild className="w-full">
          <Link href="/onboarding">Continue to onboarding</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
        <Mail className="h-6 w-6 text-primary" />
      </div>
      <div>
        <CardTitle className="text-2xl">Verify your email</CardTitle>
        <CardDescription className="mt-2">
          {email ? (
            <>
              We&apos;ve sent a verification link to{" "}
              <span className="font-medium text-foreground">{email}</span>
            </>
          ) : (
            "Check your email for the verification link"
          )}
        </CardDescription>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="space-y-2 text-sm text-muted-foreground">
        <p>Click the link in the email to verify your account.</p>
        <p>
          Didn&apos;t receive the email? Check your spam folder or{" "}
          <button
            onClick={resendEmail}
            disabled={isResending || !email}
            className="text-primary hover:underline disabled:opacity-50"
          >
            {isResending ? "Sending..." : "resend it"}
          </button>
        </p>
      </div>

      <div className="pt-4">
        <Link
          href="/login"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to login
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
