# Fumadocs Implementation Report for OmoiOS

**Date:** January 30, 2026
**Prepared for:** OmoiOS Documentation Strategy

---

## Executive Summary

Fumadocs is a modern, flexible documentation framework built for Next.js that would integrate well with your existing OmoiOS frontend. Based on research, I recommend **integrating Fumadocs within your existing application** rather than creating a separate docs application—at least initially.

---

## 1. Architecture Decision: Integrated vs Separate Application

### Recommendation: **Integrated (within existing app)**

| Factor | Integrated | Separate App |
|--------|------------|--------------|
| **Shared auth/context** | ✅ Easy - same auth system | ⚠️ Requires SSO setup |
| **Deployment complexity** | ✅ Single deployment | ⚠️ Two deployments to manage |
| **Shared components** | ✅ Reuse ShadCN UI directly | ⚠️ Duplicate or publish shared lib |
| **Build time** | ⚠️ Longer builds as docs grow | ✅ Independent build times |
| **Route conflicts** | ⚠️ Must namespace carefully | ✅ Completely isolated |
| **Team separation** | ⚠️ Same repo | ✅ Separate ownership possible |

### Why Integrated Works for OmoiOS

1. **Your app already uses Next.js 16 App Router** - Fumadocs is designed for this exact architecture
2. **ShadCN UI compatibility** - Fumadocs UI is built on Radix primitives (same as your current stack)
3. **Same Tailwind setup** - No CSS configuration conflicts
4. **Future SDK docs** - When you build your developer SDK, having docs in the same app makes API reference generation easier
5. **Gradual migration** - Start with `/docs` route, expand later if needed

### File Structure Recommendation

```
frontend/
├── app/
│   ├── (app)/                    # Your existing app routes
│   ├── (auth)/                   # Your existing auth routes
│   ├── (dashboard)/              # Your existing dashboard
│   └── docs/                     # NEW: Fumadocs routes
│       ├── [[...slug]]/
│       │   └── page.tsx          # Dynamic doc pages
│       └── layout.tsx            # Docs layout with sidebar
├── content/
│   └── docs/                     # MDX documentation files
│       ├── index.mdx
│       ├── getting-started/
│       │   ├── meta.json
│       │   ├── installation.mdx
│       │   └── quick-start.mdx
│       ├── guides/
│       ├── api-reference/        # Future: OpenAPI generated
│       └── sdk/                  # Future: SDK documentation
├── lib/
│   └── source.ts                 # Fumadocs source configuration
└── fumadocs.config.ts            # Fumadocs configuration
```

---

## 2. Implementation Steps

### Phase 1: Basic Setup (Day 1)

#### Step 1: Install Dependencies

```bash
cd frontend
pnpm add fumadocs-mdx fumadocs-core fumadocs-ui @types/mdx
```

#### Step 2: Create Configuration File

```typescript
// frontend/fumadocs.config.ts
import { defineDocs, defineConfig } from 'fumadocs-mdx/config';

export const docs = defineDocs({
  dir: 'content/docs',
});

export default defineConfig({
  mdxOptions: {
    // Your existing remark/rehype plugins can go here
    remarkPlugins: [],
    rehypePlugins: [],
  },
});
```

#### Step 3: Update Next.js Config

```javascript
// frontend/next.config.js
import { withSentryConfig } from "@sentry/nextjs"
import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  productionBrowserSourceMaps: true,
}

// Wrap with MDX first, then Sentry
export default withSentryConfig(
  withMDX(nextConfig),
  sentryWebpackPluginOptions
)
```

#### Step 4: Create Source Loader

```typescript
// frontend/lib/source.ts
import { loader } from 'fumadocs-core/source';
import { docs } from '../.source';

export const source = loader({
  source: docs.toFumadocsSource(),
  baseUrl: '/docs',
});
```

#### Step 5: Create Docs Layout

```tsx
// frontend/app/docs/layout.tsx
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { source } from '@/lib/source';
import type { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      nav={{
        title: 'OmoiOS Docs',
      }}
    >
      {children}
    </DocsLayout>
  );
}
```

#### Step 6: Create Dynamic Page

```tsx
// frontend/app/docs/[[...slug]]/page.tsx
import { source } from '@/lib/source';
import { notFound } from 'next/navigation';
import { DocsPage, DocsBody } from 'fumadocs-ui/page';

export default async function Page({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  const page = source.getPage(slug);

  if (!page) notFound();

  const MDX = page.data.body;

  return (
    <DocsPage toc={page.data.toc}>
      <DocsBody>
        <h1>{page.data.title}</h1>
        <MDX />
      </DocsBody>
    </DocsPage>
  );
}

export function generateStaticParams() {
  return source.getPages().map((page) => ({
    slug: page.slugs,
  }));
}
```

#### Step 7: Add Root Provider

```tsx
// Update frontend/app/layout.tsx
import { RootProvider } from 'fumadocs-ui/provider';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <RootProvider>
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
```

---

## 3. Search Implementation Strategy

### Now: Built-in Orama Search (Free, Self-Hosted)

Fumadocs includes Orama as the default search engine—it's free, self-hosted, and works out of the box.

```tsx
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

### Later: Vector Search with Orama Cloud

When you need dev-focused vector search:

```typescript
// Future: Orama Cloud with vector embeddings
import { OramaClient } from '@oramacloud/client';

const client = new OramaClient({
  endpoint: process.env.ORAMA_ENDPOINT,
  api_key: process.env.ORAMA_API_KEY,
});

// Vector search automatically converts queries to embeddings
const results = await client.search({
  term: "how to spawn an agent",
  mode: "vector", // Uses embeddings for semantic search
});
```

**Why Orama Cloud for later:**
- Native vector search support
- OpenAI embedding integration
- Hybrid search (keyword + vector)
- No need for separate vector DB infrastructure

### Alternative: Algolia (if needed)

If you need more advanced features sooner, Algolia is also supported:

```typescript
// Algolia integration (optional)
import { createSearchAPI } from 'fumadocs-core/search/algolia';
```

---

## 4. Future SDK Documentation

### OpenAPI Integration (for your future API SDK)

Fumadocs has excellent OpenAPI support for auto-generating API reference docs:

```typescript
// When you're ready for SDK docs
import { createOpenAPI, createAPIPage } from 'fumadocs-openapi';

const openapi = createOpenAPI({
  // Your backend OpenAPI spec
  document: './openapi.yaml',
});

// Auto-generates MDX files from OpenAPI spec
await openapi.generateFiles({
  per: 'operation', // One page per endpoint
  groupBy: 'tag',   // Group by API tags
});
```

**Features included:**
- Interactive API playground
- Code samples in multiple languages
- TypeScript type definitions
- Request/response examples

---

## 5. MDX Content Organization

### Recommended Structure

```
content/docs/
├── index.mdx                     # Docs landing page
├── meta.json                     # Sidebar order & titles
│
├── getting-started/
│   ├── meta.json
│   ├── index.mdx                 # Overview
│   ├── installation.mdx
│   ├── quick-start.mdx
│   └── concepts.mdx
│
├── guides/
│   ├── meta.json
│   ├── creating-projects.mdx
│   ├── managing-specs.mdx
│   ├── agent-workflows.mdx
│   └── phase-gates.mdx
│
├── features/
│   ├── meta.json
│   ├── kanban-board.mdx
│   ├── dependency-graph.mdx
│   ├── agent-health.mdx
│   └── command-center.mdx
│
├── api-reference/                # Future: auto-generated
│   ├── meta.json
│   └── ... (generated from OpenAPI)
│
└── sdk/                          # Future: SDK docs
    ├── meta.json
    ├── installation.mdx
    ├── authentication.mdx
    └── examples/
```

### Meta.json Example

```json
{
  "title": "Getting Started",
  "pages": [
    "index",
    "installation",
    "quick-start",
    "concepts"
  ]
}
```

### MDX Frontmatter

```mdx
---
title: Creating Your First Project
description: Learn how to create and configure projects in OmoiOS
icon: Folder
---

# Creating Your First Project

OmoiOS projects are the foundation of your development workflow...
```

---

## 6. Comparison: Fumadocs vs Alternatives

| Feature | Fumadocs | Docusaurus | Nextra |
|---------|----------|------------|--------|
| **Next.js App Router** | ✅ Native | ❌ React only | ✅ Native |
| **RSC Support** | ✅ Full | ❌ No | ✅ Full |
| **OpenAPI Integration** | ✅ Built-in | ⚠️ Plugin | ❌ No |
| **TypeScript Docs** | ✅ Built-in | ⚠️ Plugin | ❌ No |
| **Search (Free)** | ✅ Orama | ⚠️ Algolia (paid tier) | ✅ Pagefind |
| **Tailwind CSS** | ✅ Native | ⚠️ Manual | ✅ Native |
| **Bundle Size** | Small | Large | Small |
| **Customization** | High | High | Medium |
| **Learning Curve** | Low | Medium | Low |

**Verdict:** Fumadocs is the best choice for your Next.js 16 App Router setup.

---

## 7. Monorepo Considerations

Since you're already in a monorepo structure, Fumadocs works well:

```
senior_sandbox/
├── backend/                      # Python backend
├── frontend/                     # Next.js with Fumadocs
│   ├── app/docs/                 # Docs routes
│   └── content/docs/             # MDX files
└── docs/                         # Your existing docs (can migrate)
```

**Note:** Fumadocs officially supports monorepo setups. If you encounter CSS issues, ensure Tailwind's content paths include the fumadocs-ui package.

---

## 8. Migration Path

### Phase 1: Initial Setup (Now)
- Install Fumadocs
- Create basic `/docs` route
- Add 5-10 initial MDX pages
- Use built-in Orama search

### Phase 2: Content Migration (Week 2-3)
- Migrate relevant docs from `docs/` directory
- Add guides for main features
- Set up proper navigation structure

### Phase 3: API Reference (When SDK Ready)
- Generate OpenAPI spec from FastAPI backend
- Use `fumadocs-openapi` for auto-generation
- Add interactive API playground

### Phase 4: Vector Search (When Scale Requires)
- Migrate to Orama Cloud
- Enable vector embeddings
- Implement semantic search for developer queries

---

## 9. Quick Start Commands

```bash
# 1. Install dependencies
cd frontend
pnpm add fumadocs-mdx fumadocs-core fumadocs-ui @types/mdx

# 2. Create initial structure
mkdir -p content/docs/getting-started
mkdir -p app/docs/[[...slug]]

# 3. Create first doc
cat > content/docs/index.mdx << 'EOF'
---
title: Welcome to OmoiOS
description: Spec-driven, multi-agent orchestration system
---

# Welcome to OmoiOS Documentation

Get started with OmoiOS, the platform that scales development without scaling headcount.
EOF

# 4. Run dev server
pnpm dev
```

---

## 10. Key Takeaways

1. **Integrate, don't separate** - Same app, `/docs` route
2. **Start with Orama** - Free search, upgrade to vectors later
3. **MDX is your friend** - Already using react-markdown, MDX is similar
4. **OpenAPI for SDK** - Future-proof for when you build the public SDK
5. **Same tech stack** - Tailwind, Radix, React 19—all compatible

---

---

## 11. Related Documentation

For detailed implementation instructions, refer to these guides:

| Guide | Description |
|-------|-------------|
| [Documentation System Guide](../guides/fumadocs-documentation-system.md) | Complete setup for `/docs` routes, MDX configuration, search, and components |
| [Blog System Guide](../guides/fumadocs-blog-system.md) | Blog setup at `/blog`, categories, tags, RSS feed, and author management |
| [SEO Guide](../guides/fumadocs-seo-guide.md) | Comprehensive SEO: metadata, sitemap, structured data, OG images, Core Web Vitals |

---

## Resources

- [Fumadocs Official Docs](https://fumadocs.dev/docs)
- [Fumadocs GitHub](https://github.com/fuma-nama/fumadocs)
- [Fumadocs Blog Guide](https://fumadocs.dev/blog/make-a-blog)
- [OpenAPI Integration](https://fumadocs.dev/docs/integrations/openapi)
- [Orama Search](https://fumadocs.dev/docs/headless/search/orama)
- [Monorepo FAQ](https://github.com/fuma-nama/fumadocs/discussions/868)
