# Figma Make Prompt 2: Authentication Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. The foundation and design system components from Prompt 1 are already built. Now build the Authentication Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use Shadcn UI components (Button, Input, Card, etc.) with the custom warm theme from the foundation.

**SHADCN COMPONENTS TO USE:**
- Card (CardHeader, CardContent, CardFooter) for auth forms
- Input for email/password fields
- Button (variant="default" for primary, variant="outline" for secondary)
- Checkbox for "remember me" / terms
- Label for form labels
- Separator for dividers
- Alert for error messages
- Skeleton for loading states

**DESIGN NOTES:**
- Use warm cream background bg-background for full-page layouts
- Centered Card layouts with border-border, no heavy shadows
- Primary Button uses dark accent (--primary), not blue
- Text hierarchy: text-foreground, text-muted-foreground, placeholder:text-muted-foreground
- Minimal shadows, generous whitespace, low contrast aesthetic

**AUTHENTICATION PAGES TO BUILD:**

**1. Landing Page (`/`)**
- Layout: Full-width hero section, centered content, navigation bar at top, footer at bottom
- Components: Top nav bar (Logo, "Login", "Sign Up" buttons), Hero section (headline, value proposition, CTA buttons), Feature highlights (3-4 cards), Footer
- Content:
  - Headline: "Scale Development Without Scaling Headcount"
  - Subheadline: "Autonomous engineering platform that orchestrates AI agents through adaptive workflows"
  - Primary CTA: "Get Started Free"
  - Secondary CTA: "Login with GitHub"
  - Feature cards: "Spec-Driven Workflows", "Multi-Agent Coordination", "Real-Time Visibility", "Adaptive Discovery"
- States: Default, Loading (spinner on CTA), Error (OAuth failure message)
- Navigation: Click "Login" → `/login`, Click "Sign Up" → `/register`, Click "Login with GitHub" → OAuth flow

**2. Register (`/register`)**
- Layout: Centered card layout on full-width background, minimal navigation
- Components: Registration form (email, password, confirm password, terms checkbox), Form validation messages, "Already have an account? Login" link, "Sign up with GitHub" button, Password strength indicator
- Content:
  - Page title: "Create Your Account"
  - Form fields: Email, Password, Confirm Password
  - Terms checkbox: "I agree to terms and conditions"
  - Submit button: "Create Account"
  - Footer link: "Already have an account? Login"
- States: Empty, Validating (real-time feedback), Loading (spinner, form disabled), Success (redirect to `/verify-email`), Error (display above form)
- Navigation: Submit → `/verify-email`, "Login" link → `/login`, "Sign up with GitHub" → OAuth

**3. Login (`/login`)**
- Layout: Centered card layout on full-width background, minimal navigation
- Components: Login form (email, password, remember me checkbox), "Forgot password?" link, "Login with GitHub" button, "Don't have an account? Register" link, Form validation messages
- Content:
  - Page title: "Welcome Back"
  - Form fields: Email, Password
  - Remember me checkbox: "Keep me signed in"
  - Submit button: "Login"
  - Footer links: "Forgot password?", "Don't have an account? Register"
- States: Empty, Loading (spinner, form disabled), Success (redirect to `/dashboard`), Error (display above form)
- Navigation: Submit → `/dashboard`, "Forgot password?" → `/forgot-password`, "Register" link → `/register`, "Login with GitHub" → OAuth

**4. Login OAuth (`/login/oauth`)**
- Layout: Full-page loading state, minimal UI
- Components: Loading spinner, Status message, "Cancel" button (optional)
- Content: Loading message: "Redirecting to GitHub...", Status updates: "Authorizing...", "Completing login..."
- States: Loading, Success (redirect to callback then dashboard), Error (error message with "Try Again"), Cancelled (redirect to `/login`)
- Navigation: Auto-redirect to OAuth provider → Callback → `/dashboard`

**5. Verify Email (`/verify-email`)**
- Layout: Centered card layout with icon and message
- Components: Email icon/illustration, Verification message, "Resend email" button, "Change email" link
- Content:
  - Icon: Email/envelope illustration
  - Title: "Verify Your Email"
  - Message: "We've sent a verification link to [email]. Click the link in the email to activate your account."
  - Resend button: "Resend Verification Email"
  - Change email link: "Wrong email address?"
- States: Pending, Resending (button spinner), Resent (success message), Verified (auto-redirect to dashboard)
- Navigation: Resend → show success, Change email → `/register`, Email link click → auto-redirect

**6. Forgot Password (`/forgot-password`)**
- Layout: Centered card layout, minimal navigation
- Components: Email input form, Submit button, "Back to login" link, Success message area
- Content:
  - Title: "Reset Your Password"
  - Message: "Enter your email address and we'll send you a link to reset your password."
  - Email input field
  - Submit button: "Send Reset Link"
  - Footer link: "Back to login"
- States: Empty, Loading (spinner), Success ("Check your email for reset instructions"), Error (email not found, etc.)
- Navigation: Submit → show success, "Back to login" → `/login`, Email link → `/reset-password`

**7. Reset Password (`/reset-password`)**
- Layout: Centered card layout with form
- Components: Password input fields (new password, confirm), Password strength indicator, Submit button, Token validation (hidden)
- Content:
  - Title: "Set New Password"
  - Form fields: New Password, Confirm Password
  - Password strength indicator
  - Submit button: "Reset Password"
- States: Invalid Token (error message), Loading (spinner), Success (success message, redirect to login), Error (validation errors)
- Navigation: Submit → `/login` (after success)

**Requirements:**
- Use foundation components (Button, Input, Card, etc.)
- Implement form validation with real-time feedback
- Add loading states with spinners
- Handle error states with clear messages
- Implement proper navigation between pages
- Make all pages responsive (mobile, tablet, desktop)
- Include proper form accessibility (labels, error announcements, keyboard navigation)
- Use React Router or similar for navigation structure
- Password strength indicator should show visual feedback (weak/medium/strong)

Generate all 7 authentication pages as separate React components with full functionality.

