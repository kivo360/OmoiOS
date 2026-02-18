"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ArrowLeft, Shield, Clock, Key, Info, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function SessionsPage() {
  const { logout, user } = useAuth();

  return (
    <div className="container mx-auto max-w-3xl p-6 space-y-6">
      <Link
        href="/settings"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Settings
      </Link>

      <div>
        <h1 className="text-2xl font-bold">Session Management</h1>
        <p className="text-muted-foreground">
          Understand how your login sessions work
        </p>
      </div>

      {/* Current Session Info */}
      <Card className="border-primary/50">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Current Session</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-muted p-4 space-y-3">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <p className="font-medium">JWT-Based Authentication</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Your session uses secure JSON Web Tokens (JWT). This provides
                  stateless authentication without tracking individual device
                  sessions.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-6 text-sm pl-8">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>Access Token: 15 min</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>Refresh Token: 7 days</span>
              </div>
            </div>
          </div>

          {user && (
            <div className="mt-4 p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Logged in as</p>
              <p className="font-medium">{user.email}</p>
              {user.full_name && (
                <p className="text-sm text-muted-foreground">
                  {user.full_name}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Manage your account security</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <Key className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">API Keys</p>
                <p className="text-sm text-muted-foreground">
                  Manage programmatic access keys
                </p>
              </div>
            </div>
            <Button variant="outline" asChild>
              <Link href="/settings/api-keys">Manage</Link>
            </Button>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">Security Settings</p>
                <p className="text-sm text-muted-foreground">
                  Change password and 2FA settings
                </p>
              </div>
            </div>
            <Button variant="outline" asChild>
              <Link href="/settings/security">View</Link>
            </Button>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-destructive/30 p-4">
            <div className="flex items-center gap-3">
              <LogOut className="h-5 w-5 text-destructive" />
              <div>
                <p className="font-medium">Sign Out</p>
                <p className="text-sm text-muted-foreground">
                  End your current session
                </p>
              </div>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">Sign Out</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Sign Out?</AlertDialogTitle>
                  <AlertDialogDescription>
                    You will be signed out and need to log in again to access
                    your account.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={logout}>
                    Sign Out
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </CardContent>
      </Card>

      {/* Security Tips */}
      <Card className="bg-muted/30">
        <CardHeader>
          <CardTitle className="text-base">Security Best Practices</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            • <strong>Sign out on shared devices.</strong> Always sign out when
            using public or shared computers.
          </p>
          <p>
            • <strong>Use strong passwords.</strong> Combine uppercase,
            lowercase, numbers, and symbols for better security.
          </p>
          <p>
            • <strong>Enable 2FA.</strong> Two-factor authentication adds an
            extra layer of security to your account.{" "}
            <Link
              href="/settings/security"
              className="text-primary hover:underline"
            >
              Enable in Security Settings →
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
