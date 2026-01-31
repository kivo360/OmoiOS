# Fumadocs Documentation System Guide

**Version:** 1.0
**Last Updated:** January 30, 2026
**Applies To:** OmoiOS Frontend (`frontend/`)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Configuration](#configuration)
5. [Creating Documentation Pages](#creating-documentation-pages)
6. [Navigation & Sidebar](#navigation--sidebar)
7. [Search Implementation](#search-implementation)
8. [MDX Components](#mdx-components)
9. [SEO Configuration](#seo-configuration)
10. [Deployment Considerations](#deployment-considerations)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The OmoiOS documentation system uses **Fumadocs** integrated within the existing Next.js 16 frontend application. Documentation is served at `/docs` and uses MDX for content authoring.

### Key Technologies
- **Fumadocs MDX** - Content processing and type-safe data transformation
- **Fumadocs Core** - Search, source adapters, and utilities
- **Fumadocs UI** - Pre-built documentation components and layouts
- **Orama** - Built-in full-text search (upgradeable to vector search)

### Design Decisions
- **Integrated approach** - Docs live within the main app, not a separate application
- **Route group isolation** - Docs use their own layout without affecting app routes
- **Shared authentication** - Same auth context as the main application
- **Reusable components** - ShadCN UI components work in MDX

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js App Router                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   (app)/     │  │   (auth)/    │  │    docs/     │       │
│  │  Main App    │  │    Auth      │  │Documentation │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                            │                 │
│                                            ▼                 │
│                                   ┌──────────────┐          │
│                                   │ Fumadocs UI  │          │
│                                   │   Layout     │          │
│                                   └──────────────┘          │
│                                            │                 │
├────────────────────────────────────────────┼────────────────┤
│                                            ▼                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   content/docs/                      │    │
│  │                                                      │    │
│  │  ├── index.mdx                                       │    │
│  │  ├── meta.json                                       │    │
│  │  ├── getting-started/                                │    │
│  │  │   ├── meta.json                                   │    │
│  │  │   ├── index.mdx                                   │    │
│  │  │   └── quick-start.mdx                             │    │
│  │  └── guides/                                         │    │
│  │      ├── meta.json                                   │    │
│  │      └── ...                                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Required Files

```
frontend/
├── fumadocs.config.ts              # Fumadocs configuration
├── lib/
│   └── source.ts                   # Source loader for docs
├── app/
│   ├── layout.tsx                  # Root layout (add RootProvider)
│   ├── api/
│   │   └── search/
│   │       └── route.ts            # Search API endpoint
│   └── docs/
│       ├── layout.tsx              # Docs-specific layout
│       └── [[...slug]]/
│           └── page.tsx            # Dynamic doc page renderer
└── content/
    └── docs/
        ├── index.mdx               # Docs landing page
        ├── meta.json               # Root navigation config
        ├── getting-started/
        │   ├── meta.json
        │   ├── index.mdx
        │   ├── installation.mdx
        │   └── quick-start.mdx
        ├── guides/
        │   ├── meta.json
        │   └── *.mdx
        ├── features/
        │   ├── meta.json
        │   └── *.mdx
        └── api-reference/
            ├── meta.json
            └── *.mdx
```

---

## Configuration

### Step 1: Install Dependencies

```bash
cd frontend
pnpm add fumadocs-mdx fumadocs-core fumadocs-ui @types/mdx
```

### Step 2: Create Fumadocs Configuration

```typescript
// frontend/fumadocs.config.ts
import { defineDocs, defineConfig } from 'fumadocs-mdx/config';
import { rehypeCode } from 'fumadocs-core/mdx-plugins';

// Define the docs collection
export const docs = defineDocs({
  dir: 'content/docs',
});

export default defineConfig({
  mdxOptions: {
    rehypePlugins: [
      [rehypeCode, { themes: { light: 'github-light', dark: 'github-dark' } }],
    ],
    // Add your existing remark plugins here if needed
    remarkPlugins: [],
  },
});
```

### Step 3: Update Next.js Configuration

```javascript
// frontend/next.config.js
import { withSentryConfig } from "@sentry/nextjs";
import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  productionBrowserSourceMaps: true,
};

const sentryWebpackPluginOptions = {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
  hideSourceMaps: true,
  deleteSourcemapsAfterUpload: true,
  dryRun: !process.env.SENTRY_AUTH_TOKEN,
  tunnelRoute: "/api/monitoring/sentry",
  automaticVercelMonitors: true,
  release: {
    create: true,
    finalize: true,
    name: process.env.SENTRY_RELEASE || process.env.VERCEL_GIT_COMMIT_SHA,
  },
  sourcemaps: {
    disable: false,
  },
};

// Apply MDX first, then Sentry
export default withSentryConfig(
  withMDX(nextConfig),
  sentryWebpackPluginOptions
);
```

### Step 4: Create Source Loader

```typescript
// frontend/lib/source.ts
import { loader } from 'fumadocs-core/source';
import { docs } from '../.source';

export const source = loader({
  source: docs.toFumadocsSource(),
  baseUrl: '/docs',
});
```

### Step 5: Update Root Layout

```tsx
// frontend/app/layout.tsx
import { RootProvider } from 'fumadocs-ui/provider';
import './globals.css';
// Import Fumadocs styles
import 'fumadocs-ui/style.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider>
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
```

### Step 6: Create Docs Layout

```tsx
// frontend/app/docs/layout.tsx
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { source } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      nav={{
        title: 'OmoiOS Documentation',
        url: '/docs',
      }}
      sidebar={{
        defaultOpenLevel: 1,
        collapsible: true,
      }}
      links={[
        { text: 'App', url: '/', active: 'none' },
        { text: 'Blog', url: '/blog', active: 'none' },
      ]}
    >
      {children}
    </DocsLayout>
  );
}
```

### Step 7: Create Dynamic Page

```tsx
// frontend/app/docs/[[...slug]]/page.tsx
import { source } from '@/lib/source';
import { notFound } from 'next/navigation';
import {
  DocsPage,
  DocsBody,
  DocsTitle,
  DocsDescription,
} from 'fumadocs-ui/page';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { Metadata } from 'next';

interface PageProps {
  params: Promise<{ slug?: string[] }>;
}

export default async function Page({ params }: PageProps) {
  const { slug } = await params;
  const page = source.getPage(slug);

  if (!page) notFound();

  const MDXContent = page.data.body;

  return (
    <DocsPage
      toc={page.data.toc}
      lastUpdate={page.data.lastModified}
      full={page.data.full}
    >
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDXContent components={defaultMdxComponents} />
      </DocsBody>
    </DocsPage>
  );
}

export function generateStaticParams() {
  return source.getPages().map((page) => ({
    slug: page.slugs,
  }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = source.getPage(slug);

  if (!page) return {};

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  return {
    title: page.data.title,
    description: page.data.description,
    openGraph: {
      title: page.data.title,
      description: page.data.description,
      type: 'article',
      url: `${baseUrl}/docs/${slug?.join('/') || ''}`,
      siteName: 'OmoiOS Documentation',
    },
    twitter: {
      card: 'summary_large_image',
      title: page.data.title,
      description: page.data.description,
    },
    alternates: {
      canonical: `${baseUrl}/docs/${slug?.join('/') || ''}`,
    },
  };
}
```

---

## Creating Documentation Pages

### Frontmatter Schema

Every documentation MDX file must include frontmatter:

```yaml
---
title: Page Title (Required)
description: Brief description for SEO and previews (Required)
icon: Lucide icon name (Optional)
full: true/false - Use full width layout (Optional, default: false)
---
```

### Example Documentation Page

```mdx
---
title: Getting Started with OmoiOS
description: Learn how to set up and configure OmoiOS for your development workflow
icon: Rocket
---

# Getting Started with OmoiOS

OmoiOS is a spec-driven, multi-agent orchestration system that scales development without scaling headcount.

## Prerequisites

Before you begin, ensure you have:

- Node.js 22 or higher
- Python 3.11 or higher
- Docker and Docker Compose
- A Supabase account

## Quick Installation

<Callout type="info">
  OmoiOS uses uv for Python package management and pnpm for JavaScript.
</Callout>

```bash
# Clone the repository
git clone https://github.com/your-org/omoios.git
cd omoios

# Install dependencies
just install

# Start development services
just dev-all
```

## Next Steps

<Cards>
  <Card title="Create Your First Project" href="/docs/guides/creating-projects" />
  <Card title="Understanding Specs" href="/docs/concepts/specs" />
  <Card title="Agent Workflows" href="/docs/guides/agent-workflows" />
</Cards>
```

---

## Navigation & Sidebar

### Meta.json Structure

Each folder can have a `meta.json` file to control navigation:

```json
{
  "title": "Getting Started",
  "description": "Learn the basics of OmoiOS",
  "icon": "BookOpen",
  "pages": [
    "index",
    "installation",
    "quick-start",
    "---Concepts---",
    "architecture",
    "terminology"
  ]
}
```

### Special Navigation Items

| Syntax | Description |
|--------|-------------|
| `"page-name"` | Link to page (without .mdx extension) |
| `"---Title---"` | Section separator with title |
| `"..."` | Include all remaining pages alphabetically |
| `"[Title](url)"` | External link |

### Root meta.json Example

```json
{
  "title": "Documentation",
  "pages": [
    "index",
    "---Getting Started---",
    "getting-started",
    "---Guides---",
    "guides",
    "---Features---",
    "features",
    "---Reference---",
    "api-reference"
  ]
}
```

---

## Search Implementation

### Step 1: Create Search API Route

```typescript
// frontend/app/api/search/route.ts
import { source } from '@/lib/source';
import { createSearchAPI } from 'fumadocs-core/search/server';

export const { GET } = createSearchAPI('advanced', {
  indexes: source.getPages().map((page) => ({
    title: page.data.title,
    description: page.data.description,
    url: page.url,
    structuredData: page.data.structuredData,
    id: page.url,
  })),
});
```

### Step 2: Search is Automatically Available

Fumadocs UI includes a search dialog by default. Press `Cmd/Ctrl + K` to open.

### Future: Vector Search with Orama Cloud

When you need semantic/vector search:

```typescript
// Future implementation with Orama Cloud
import { OramaClient } from '@oramacloud/client';

const client = new OramaClient({
  endpoint: process.env.ORAMA_ENDPOINT!,
  api_key: process.env.ORAMA_API_KEY!,
});

// Hybrid search (keyword + vector)
const results = await client.search({
  term: "how to create an agent",
  mode: "hybrid",
});
```

---

## MDX Components

### Built-in Components from Fumadocs UI

These components are available in all MDX files:

```mdx
{/* Callouts/Admonitions */}
<Callout type="info">Information message</Callout>
<Callout type="warn">Warning message</Callout>
<Callout type="error">Error message</Callout>

{/* Cards */}
<Cards>
  <Card title="Card Title" href="/docs/page" />
</Cards>

{/* Tabs */}
<Tabs items={["npm", "pnpm", "yarn"]}>
  <Tab value="npm">npm install package</Tab>
  <Tab value="pnpm">pnpm add package</Tab>
  <Tab value="yarn">yarn add package</Tab>
</Tabs>

{/* Steps */}
<Steps>
  <Step>First step content</Step>
  <Step>Second step content</Step>
</Steps>

{/* Files/Folder structure */}
<Files>
  <Folder name="src" defaultOpen>
    <File name="index.ts" />
    <Folder name="components">
      <File name="Button.tsx" />
    </Folder>
  </Folder>
</Files>

{/* TypeTable for API docs */}
<TypeTable
  type={{
    name: { type: 'string', description: 'The name' },
    count: { type: 'number', default: '0' },
  }}
/>
```

### Adding Custom Components

```tsx
// frontend/components/mdx/index.tsx
import defaultMdxComponents from 'fumadocs-ui/mdx';
import { CodeBlock } from './CodeBlock';
import { ApiEndpoint } from './ApiEndpoint';

export const mdxComponents = {
  ...defaultMdxComponents,
  CodeBlock,
  ApiEndpoint,
  // Add more custom components
};
```

Update the page to use custom components:

```tsx
// frontend/app/docs/[[...slug]]/page.tsx
import { mdxComponents } from '@/components/mdx';

// In the component:
<MDXContent components={mdxComponents} />
```

---

## SEO Configuration

See the separate [SEO Guide](./fumadocs-seo-guide.md) for comprehensive SEO implementation.

### Quick SEO Checklist for Docs

- [ ] Every page has `title` and `description` in frontmatter
- [ ] `generateMetadata` exports Open Graph and Twitter metadata
- [ ] Sitemap includes all doc pages
- [ ] Canonical URLs are set
- [ ] JSON-LD structured data for technical articles

---

## Deployment Considerations

### Docker Build

When using Docker with Fumadocs MDX:

```dockerfile
# Dockerfile
FROM node:22-alpine AS base

# ... other stages ...

FROM base AS builder
WORKDIR /app

# IMPORTANT: Copy fumadocs config and lockfile
COPY fumadocs.config.ts ./
COPY pnpm-lock.yaml ./
COPY package.json ./

RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build
```

### Vercel/Cloudflare

- Fumadocs works with Vercel out of the box
- **Note:** Fumadocs does NOT work on Cloudflare Edge Runtime with Next.js

### Environment Variables

```env
# Required for SEO
NEXT_PUBLIC_SITE_URL=https://omoios.dev

# Optional: Orama Cloud (future vector search)
ORAMA_ENDPOINT=
ORAMA_API_KEY=
```

---

## Troubleshooting

### Common Issues

#### "Cannot find module '.source'"

The `.source` folder is generated when running `next dev` or `next build`. Run:

```bash
pnpm dev
# or
npx fumadocs-mdx
```

#### Styles not loading

Ensure you've imported Fumadocs styles in your root layout:

```tsx
import 'fumadocs-ui/style.css';
```

#### Search not working

1. Verify the search API route exists at `app/api/search/route.ts`
2. Check that the route exports `GET`
3. Ensure pages are being indexed (check `source.getPages()`)

#### MDX components not rendering

Ensure you're passing components to the MDX content:

```tsx
<MDXContent components={defaultMdxComponents} />
```

### Getting Help

- [Fumadocs Documentation](https://fumadocs.dev/docs)
- [Fumadocs GitHub Discussions](https://github.com/fuma-nama/fumadocs/discussions)
- Internal: Check `#dev-frontend` Slack channel

---

## Quick Reference

| Task | Command/Location |
|------|------------------|
| Add new doc page | Create `content/docs/path/page.mdx` |
| Update navigation | Edit `meta.json` in folder |
| Add custom component | `components/mdx/index.tsx` |
| Modify search | `app/api/search/route.ts` |
| Change docs layout | `app/docs/layout.tsx` |
| Run docs locally | `pnpm dev`, visit `/docs` |
