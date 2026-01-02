"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, Loader2, Building2 } from "lucide-react"
import { useCreateOrganization } from "@/hooks/useOrganizations"
import { createSubscriptionCheckout } from "@/lib/api/billing"

export default function NewOrganizationPage() {
  const router = useRouter()
  const createMutation = useCreateOrganization()
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    description: "",
  })

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
  }

  const handleNameChange = (name: string) => {
    setFormData({
      ...formData,
      name,
      slug: formData.slug || generateSlug(name),
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const result = await createMutation.mutateAsync({
        name: formData.name,
        slug: formData.slug,
        description: formData.description || undefined,
      })
      toast.success("Organization created successfully!")

      // Check for pending plan from pricing page signup flow
      const pendingPlan = localStorage.getItem("pending_plan")
      if (pendingPlan && (pendingPlan === "pro" || pendingPlan === "team")) {
        localStorage.removeItem("pending_plan")
        try {
          // Create checkout session and redirect to Stripe
          const checkout = await createSubscriptionCheckout(result.id, {
            tier: pendingPlan,
            success_url: `${window.location.origin}/organizations/${result.id}/billing?checkout=success`,
            cancel_url: `${window.location.origin}/organizations/${result.id}/billing?checkout=cancelled`,
          })
          window.location.href = checkout.checkout_url
          return
        } catch (checkoutError) {
          console.error("Failed to create checkout session:", checkoutError)
          toast.error("Failed to start checkout. You can upgrade from the billing page.")
        }
      }

      router.push(`/organizations/${result.id}`)
    } catch (error) {
      toast.error("Failed to create organization")
    }
  }

  return (
    <div className="container mx-auto max-w-2xl p-6 space-y-6">
      <Link
        href="/organizations"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Organizations
      </Link>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-6 w-6" />
            <div>
              <CardTitle>Create Organization</CardTitle>
              <CardDescription>
                Set up a new organization to collaborate with your team
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Organization Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Organization Name</Label>
              <Input
                id="name"
                placeholder="Acme Inc"
                value={formData.name}
                onChange={(e) => handleNameChange(e.target.value)}
                required
              />
            </div>

            {/* Slug */}
            <div className="space-y-2">
              <Label htmlFor="slug">URL Slug</Label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">omoios.dev/</span>
                <Input
                  id="slug"
                  placeholder="acme-inc"
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  required
                  pattern="[a-z0-9-]+"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Only lowercase letters, numbers, and hyphens
              </p>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Tell us about your organization..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/organizations">Cancel</Link>
              </Button>
              <Button type="submit" disabled={createMutation.isPending || !formData.name || !formData.slug}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Organization
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
