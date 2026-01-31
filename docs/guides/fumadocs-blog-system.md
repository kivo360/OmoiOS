# Fumadocs Blog System Guide

**Version:** 1.0
**Last Updated:** January 30, 2026
**Applies To:** OmoiOS Frontend (`frontend/`)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Configuration](#configuration)
5. [Creating Blog Posts](#creating-blog-posts)
6. [Blog Index Page](#blog-index-page)
7. [Individual Post Page](#individual-post-page)
8. [Categories & Tags](#categories--tags)
9. [RSS Feed](#rss-feed)
10. [SEO for Blog Posts](#seo-for-blog-posts)
11. [Author Management](#author-management)
12. [Quick Reference](#quick-reference)

---

## Overview

The OmoiOS blog system uses **Fumadocs MDX** for content management, running alongside the documentation system within the same Next.js application. Blog posts are served at `/blog`.

### Key Features
- MDX content with full React component support
- Type-safe frontmatter validation with Zod
- Automatic Table of Contents generation
- Author attribution and date handling
- Category and tag support
- RSS feed generation
- Full SEO optimization with structured data

### Design Decisions
- **Separate collection** - Blog uses `defineCollections`, not `defineDocs`
- **Flat URL structure** - Posts at `/blog/[slug]` (no nested paths)
- **Shared components** - Same MDX components as documentation
- **Independent layout** - Blog has its own layout, separate from docs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js App Router                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    docs/     │  │    blog/     │  │   (app)/     │       │
│  │Documentation │  │    Blog      │  │  Main App    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                           │                                  │
│                           ▼                                  │
│                  ┌──────────────────┐                       │
│                  │  Blog Layout     │                       │
│                  │  (custom header) │                       │
│                  └──────────────────┘                       │
│                           │                                  │
├───────────────────────────┼─────────────────────────────────┤
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   content/blog/                      │    │
│  │                                                      │    │
│  │  ├── hello-world.mdx                                 │    │
│  │  ├── announcing-v2.mdx                               │    │
│  │  ├── agent-orchestration-deep-dive.mdx               │    │
│  │  └── ...                                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Required Files

```
frontend/
├── fumadocs.config.ts              # Add blog collection here
├── lib/
│   ├── source.ts                   # Docs source (existing)
│   └── blog.ts                     # Blog source (new)
├── app/
│   ├── blog/
│   │   ├── layout.tsx              # Blog layout
│   │   ├── page.tsx                # Blog index (list all posts)
│   │   └── [slug]/
│   │       └── page.tsx            # Individual post page
│   ├── feed.xml/
│   │   └── route.ts                # RSS feed
│   └── api/
│       └── search/
│           └── route.ts            # Update to include blog
└── content/
    ├── docs/                       # Existing docs
    └── blog/                       # Blog posts
        ├── hello-world.mdx
        ├── announcing-v2.mdx
        └── ...
```

---

## Configuration

### Step 1: Update Fumadocs Config

```typescript
// frontend/fumadocs.config.ts
import { defineDocs, defineCollections, defineConfig, frontmatterSchema } from 'fumadocs-mdx/config';
import { rehypeCode } from 'fumadocs-core/mdx-plugins';
import { z } from 'zod';

// Existing docs collection
export const docs = defineDocs({
  dir: 'content/docs',
});

// NEW: Blog posts collection
export const blogPosts = defineCollections({
  type: 'doc',
  dir: 'content/blog',
  schema: frontmatterSchema.extend({
    // Required fields
    author: z.string(),
    date: z.string().date().or(z.date()),

    // Optional fields
    category: z.string().optional(),
    tags: z.array(z.string()).optional().default([]),
    image: z.string().optional(),
    imageAlt: z.string().optional(),
    draft: z.boolean().optional().default(false),
    featured: z.boolean().optional().default(false),
  }),
});

export default defineConfig({
  mdxOptions: {
    rehypePlugins: [
      [rehypeCode, { themes: { light: 'github-light', dark: 'github-dark' } }],
    ],
    remarkPlugins: [],
  },
});
```

### Step 2: Create Blog Source Loader

```typescript
// frontend/lib/blog.ts
import { loader } from 'fumadocs-core/source';
import { toFumadocsSource } from 'fumadocs-mdx/runtime/server';
import { blogPosts } from 'fumadocs-mdx:collections/server';

export const blog = loader({
  baseUrl: '/blog',
  source: toFumadocsSource(blogPosts, []),
});

// Helper functions
export function getAllPosts() {
  return blog
    .getPages()
    .filter((post) => !post.data.draft)
    .sort((a, b) =>
      new Date(b.data.date).getTime() - new Date(a.data.date).getTime()
    );
}

export function getFeaturedPosts() {
  return getAllPosts().filter((post) => post.data.featured);
}

export function getPostsByCategory(category: string) {
  return getAllPosts().filter((post) => post.data.category === category);
}

export function getPostsByTag(tag: string) {
  return getAllPosts().filter((post) => post.data.tags?.includes(tag));
}

export function getAllCategories() {
  const categories = new Set<string>();
  getAllPosts().forEach((post) => {
    if (post.data.category) {
      categories.add(post.data.category);
    }
  });
  return Array.from(categories);
}

export function getAllTags() {
  const tags = new Set<string>();
  getAllPosts().forEach((post) => {
    post.data.tags?.forEach((tag) => tags.add(tag));
  });
  return Array.from(tags);
}
```

### Step 3: Create Blog Layout

```tsx
// frontend/app/blog/layout.tsx
import type { ReactNode } from 'react';
import Link from 'next/link';

export default function BlogLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      {/* Blog Header */}
      <header className="border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <nav className="flex items-center justify-between">
            <Link href="/blog" className="text-2xl font-bold">
              OmoiOS Blog
            </Link>
            <div className="flex gap-6">
              <Link
                href="/docs"
                className="text-muted-foreground hover:text-foreground"
              >
                Docs
              </Link>
              <Link
                href="/"
                className="text-muted-foreground hover:text-foreground"
              >
                App
              </Link>
            </div>
          </nav>
        </div>
      </header>

      {/* Blog Content */}
      <main>
        {children}
      </main>

      {/* Blog Footer */}
      <footer className="border-t mt-16">
        <div className="max-w-4xl mx-auto px-4 py-8 text-center text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} OmoiOS. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
```

---

## Creating Blog Posts

### Frontmatter Schema

Every blog post must include this frontmatter:

```yaml
---
title: Post Title (Required)
description: Brief summary for SEO and previews (Required)
author: Author Name (Required)
date: 2026-01-30 (Required, YYYY-MM-DD format)
category: Category Name (Optional)
tags: [tag1, tag2, tag3] (Optional)
image: /images/blog/post-image.jpg (Optional, for OG image)
imageAlt: Description of the image (Optional)
draft: false (Optional, hides from listing if true)
featured: false (Optional, shows in featured section)
---
```

### Example Blog Post

```mdx
---
title: Introducing OmoiOS v2.0
description: We're excited to announce OmoiOS v2.0 with intelligent agent orchestration, improved phase gates, and enhanced spec-driven development.
author: Kevin Hill
date: 2026-01-30
category: Announcements
tags: [release, agents, orchestration]
image: /images/blog/v2-announcement.jpg
imageAlt: OmoiOS v2.0 Dashboard Screenshot
featured: true
---

# Introducing OmoiOS v2.0

We're thrilled to announce the release of OmoiOS v2.0, our biggest update yet. This release focuses on three key areas: intelligent agent orchestration, improved phase gates, and enhanced spec-driven development.

## What's New

### Intelligent Agent Orchestration

OmoiOS v2.0 introduces a completely redesigned agent orchestration system. Agents now communicate through an event-driven architecture, enabling:

- **Parallel execution** - Multiple agents can work on independent tasks simultaneously
- **Smart dependency resolution** - The system automatically determines task order
- **Self-healing workflows** - Failed tasks are automatically retried with context

<Callout type="info">
  Learn more about agent orchestration in our [detailed guide](/docs/guides/agent-workflows).
</Callout>

### Improved Phase Gates

Phase gates now support conditional logic and automated quality checks:

```yaml
gates:
  - name: code-review
    conditions:
      - test-coverage >= 80%
      - no-critical-issues
    auto_approve: true
```

### Enhanced Spec-Driven Development

The spec workflow has been streamlined with new exploration and requirements phases...

## Migration Guide

Upgrading from v1.x? Check our [migration guide](/docs/guides/migration-v2) for step-by-step instructions.

## What's Next

We're already working on v2.1, which will include:

- Vector-based semantic search for documentation
- Public SDK for third-party integrations
- Enhanced monitoring dashboard

Stay tuned for more updates!

---

*Questions? Join our [Discord community](https://discord.gg/omoios) or reach out on [Twitter](https://twitter.com/omoios).*
```

---

## Blog Index Page

```tsx
// frontend/app/blog/page.tsx
import Link from 'next/link';
import Image from 'next/image';
import { getAllPosts, getFeaturedPosts, getAllCategories } from '@/lib/blog';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Blog | OmoiOS',
  description: 'Latest news, tutorials, and insights about OmoiOS and multi-agent orchestration.',
  openGraph: {
    title: 'OmoiOS Blog',
    description: 'Latest news, tutorials, and insights about OmoiOS and multi-agent orchestration.',
    type: 'website',
    url: 'https://omoios.dev/blog',
  },
  alternates: {
    canonical: 'https://omoios.dev/blog',
    types: {
      'application/rss+xml': 'https://omoios.dev/feed.xml',
    },
  },
};

export default function BlogIndex() {
  const posts = getAllPosts();
  const featuredPosts = getFeaturedPosts();
  const categories = getAllCategories();

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      {/* Featured Posts */}
      {featuredPosts.length > 0 && (
        <section className="mb-16">
          <h2 className="text-2xl font-bold mb-6">Featured</h2>
          <div className="grid gap-8 md:grid-cols-2">
            {featuredPosts.slice(0, 2).map((post) => (
              <Link
                key={post.url}
                href={post.url}
                className="group block rounded-lg border overflow-hidden hover:shadow-lg transition-shadow"
              >
                {post.data.image && (
                  <div className="aspect-video relative bg-muted">
                    <Image
                      src={post.data.image}
                      alt={post.data.imageAlt || post.data.title}
                      fill
                      className="object-cover"
                    />
                  </div>
                )}
                <div className="p-6">
                  {post.data.category && (
                    <span className="text-sm text-primary font-medium">
                      {post.data.category}
                    </span>
                  )}
                  <h3 className="text-xl font-semibold mt-2 group-hover:text-primary transition-colors">
                    {post.data.title}
                  </h3>
                  <p className="text-muted-foreground mt-2">
                    {post.data.description}
                  </p>
                  <div className="mt-4 text-sm text-muted-foreground">
                    {new Date(post.data.date).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Categories */}
      {categories.length > 0 && (
        <section className="mb-8">
          <div className="flex flex-wrap gap-2">
            <Link
              href="/blog"
              className="px-3 py-1 rounded-full bg-primary text-primary-foreground text-sm"
            >
              All
            </Link>
            {categories.map((category) => (
              <Link
                key={category}
                href={`/blog/category/${category.toLowerCase()}`}
                className="px-3 py-1 rounded-full bg-muted hover:bg-muted/80 text-sm"
              >
                {category}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* All Posts */}
      <section>
        <h2 className="text-2xl font-bold mb-6">All Posts</h2>
        <div className="space-y-8">
          {posts.map((post) => (
            <article
              key={post.url}
              className="border-b pb-8 last:border-0"
            >
              <Link href={post.url} className="group">
                <div className="flex gap-4">
                  <div className="flex-1">
                    {post.data.category && (
                      <span className="text-sm text-primary font-medium">
                        {post.data.category}
                      </span>
                    )}
                    <h3 className="text-xl font-semibold mt-1 group-hover:text-primary transition-colors">
                      {post.data.title}
                    </h3>
                    <p className="text-muted-foreground mt-2">
                      {post.data.description}
                    </p>
                    <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{post.data.author}</span>
                      <span>•</span>
                      <time dateTime={post.data.date}>
                        {new Date(post.data.date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </time>
                    </div>
                  </div>
                  {post.data.image && (
                    <div className="hidden sm:block w-32 h-24 relative rounded overflow-hidden">
                      <Image
                        src={post.data.image}
                        alt=""
                        fill
                        className="object-cover"
                      />
                    </div>
                  )}
                </div>
              </Link>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
```

---

## Individual Post Page

```tsx
// frontend/app/blog/[slug]/page.tsx
import { notFound } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { InlineTOC } from 'fumadocs-ui/components/inline-toc';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import { blog, getAllPosts } from '@/lib/blog';
import type { Metadata } from 'next';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function BlogPost({ params }: PageProps) {
  const { slug } = await params;
  const post = blog.getPage([slug]);

  if (!post || post.data.draft) notFound();

  const MDXContent = post.data.body;

  // Get related posts (same category, excluding current)
  const relatedPosts = getAllPosts()
    .filter((p) =>
      p.url !== post.url &&
      p.data.category === post.data.category
    )
    .slice(0, 3);

  return (
    <article className="max-w-3xl mx-auto px-4 py-12">
      {/* Post Header */}
      <header className="mb-8">
        {post.data.category && (
          <Link
            href={`/blog/category/${post.data.category.toLowerCase()}`}
            className="text-sm text-primary font-medium hover:underline"
          >
            {post.data.category}
          </Link>
        )}
        <h1 className="text-4xl font-bold mt-2 mb-4">
          {post.data.title}
        </h1>
        <p className="text-xl text-muted-foreground">
          {post.data.description}
        </p>
        <div className="mt-6 flex items-center gap-4">
          <div className="flex items-center gap-3">
            {/* Author avatar placeholder */}
            <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
              <span className="text-sm font-medium">
                {post.data.author.charAt(0)}
              </span>
            </div>
            <div>
              <div className="font-medium">{post.data.author}</div>
              <time
                dateTime={post.data.date}
                className="text-sm text-muted-foreground"
              >
                {new Date(post.data.date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </time>
            </div>
          </div>
        </div>
      </header>

      {/* Featured Image */}
      {post.data.image && (
        <div className="aspect-video relative rounded-lg overflow-hidden mb-8">
          <Image
            src={post.data.image}
            alt={post.data.imageAlt || post.data.title}
            fill
            className="object-cover"
            priority
          />
        </div>
      )}

      {/* Table of Contents */}
      {post.data.toc.length > 0 && (
        <div className="mb-8 p-4 rounded-lg bg-muted/50">
          <h2 className="text-sm font-semibold mb-2">On this page</h2>
          <InlineTOC items={post.data.toc} />
        </div>
      )}

      {/* Post Content */}
      <div className="prose prose-neutral dark:prose-invert max-w-none">
        <MDXContent components={defaultMdxComponents} />
      </div>

      {/* Tags */}
      {post.data.tags && post.data.tags.length > 0 && (
        <div className="mt-8 pt-8 border-t">
          <div className="flex flex-wrap gap-2">
            {post.data.tags.map((tag) => (
              <Link
                key={tag}
                href={`/blog/tag/${tag.toLowerCase()}`}
                className="px-3 py-1 rounded-full bg-muted hover:bg-muted/80 text-sm"
              >
                #{tag}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Related Posts */}
      {relatedPosts.length > 0 && (
        <section className="mt-16 pt-8 border-t">
          <h2 className="text-2xl font-bold mb-6">Related Posts</h2>
          <div className="grid gap-6 sm:grid-cols-3">
            {relatedPosts.map((related) => (
              <Link
                key={related.url}
                href={related.url}
                className="group"
              >
                <h3 className="font-medium group-hover:text-primary transition-colors">
                  {related.data.title}
                </h3>
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                  {related.data.description}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}
    </article>
  );
}

export function generateStaticParams() {
  return getAllPosts().map((post) => ({
    slug: post.slugs[0],
  }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = blog.getPage([slug]);

  if (!post) return {};

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';
  const postUrl = `${baseUrl}/blog/${slug}`;

  return {
    title: `${post.data.title} | OmoiOS Blog`,
    description: post.data.description,
    authors: [{ name: post.data.author }],
    openGraph: {
      title: post.data.title,
      description: post.data.description,
      type: 'article',
      url: postUrl,
      publishedTime: post.data.date,
      authors: [post.data.author],
      images: post.data.image ? [
        {
          url: `${baseUrl}${post.data.image}`,
          alt: post.data.imageAlt || post.data.title,
        },
      ] : [],
      tags: post.data.tags,
    },
    twitter: {
      card: 'summary_large_image',
      title: post.data.title,
      description: post.data.description,
      images: post.data.image ? [`${baseUrl}${post.data.image}`] : [],
    },
    alternates: {
      canonical: postUrl,
    },
  };
}
```

---

## Categories & Tags

### Category Page

```tsx
// frontend/app/blog/category/[category]/page.tsx
import { getAllPosts, getAllCategories } from '@/lib/blog';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';

interface PageProps {
  params: Promise<{ category: string }>;
}

export default async function CategoryPage({ params }: PageProps) {
  const { category } = await params;
  const decodedCategory = decodeURIComponent(category);

  const posts = getAllPosts().filter(
    (post) => post.data.category?.toLowerCase() === decodedCategory.toLowerCase()
  );

  if (posts.length === 0) notFound();

  const categoryName = posts[0].data.category;

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8">
        Category: {categoryName}
      </h1>
      <div className="space-y-8">
        {posts.map((post) => (
          <article key={post.url} className="border-b pb-8 last:border-0">
            <Link href={post.url} className="group">
              <h2 className="text-xl font-semibold group-hover:text-primary transition-colors">
                {post.data.title}
              </h2>
              <p className="text-muted-foreground mt-2">
                {post.data.description}
              </p>
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return getAllCategories().map((category) => ({
    category: category.toLowerCase(),
  }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { category } = await params;
  return {
    title: `${category} | OmoiOS Blog`,
    description: `All blog posts in the ${category} category`,
  };
}
```

### Tag Page (Similar Structure)

```tsx
// frontend/app/blog/tag/[tag]/page.tsx
// Similar to category page, but using getPostsByTag() and getAllTags()
```

---

## RSS Feed

```typescript
// frontend/app/feed.xml/route.ts
import { getAllPosts } from '@/lib/blog';

export async function GET() {
  const posts = getAllPosts();
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  const feed = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>OmoiOS Blog</title>
    <link>${baseUrl}/blog</link>
    <description>Latest news, tutorials, and insights about OmoiOS and multi-agent orchestration.</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${baseUrl}/feed.xml" rel="self" type="application/rss+xml"/>
    ${posts.map((post) => `
    <item>
      <title><![CDATA[${post.data.title}]]></title>
      <link>${baseUrl}${post.url}</link>
      <guid isPermaLink="true">${baseUrl}${post.url}</guid>
      <description><![CDATA[${post.data.description}]]></description>
      <pubDate>${new Date(post.data.date).toUTCString()}</pubDate>
      <author>${post.data.author}</author>
      ${post.data.category ? `<category>${post.data.category}</category>` : ''}
    </item>`).join('')}
  </channel>
</rss>`;

  return new Response(feed, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 's-maxage=3600, stale-while-revalidate',
    },
  });
}
```

---

## SEO for Blog Posts

See the [SEO Guide](./fumadocs-seo-guide.md) for comprehensive SEO implementation. Key points for blog:

### JSON-LD Structured Data

Add to individual post pages:

```tsx
// In frontend/app/blog/[slug]/page.tsx

// Add this component
function BlogPostJsonLd({ post, url }: { post: any; url: string }) {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.data.title,
    description: post.data.description,
    author: {
      '@type': 'Person',
      name: post.data.author,
    },
    datePublished: post.data.date,
    dateModified: post.data.date,
    url: url,
    image: post.data.image ? `${baseUrl}${post.data.image}` : undefined,
    publisher: {
      '@type': 'Organization',
      name: 'OmoiOS',
      logo: {
        '@type': 'ImageObject',
        url: `${baseUrl}/logo.png`,
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': url,
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}

// Add to the page component:
<>
  <BlogPostJsonLd post={post} url={postUrl} />
  <article>...</article>
</>
```

---

## Author Management

### Option 1: Simple (Author as String)

Current implementation uses author name as a string in frontmatter.

### Option 2: Author Collection (Future Enhancement)

For multiple authors with profiles:

```typescript
// frontend/fumadocs.config.ts
export const authors = defineCollections({
  type: 'meta',
  dir: 'content/authors',
  schema: z.object({
    name: z.string(),
    title: z.string().optional(),
    avatar: z.string().optional(),
    twitter: z.string().optional(),
    github: z.string().optional(),
    bio: z.string().optional(),
  }),
});
```

```yaml
# content/authors/kevin-hill.yaml
name: Kevin Hill
title: Founder & CEO
avatar: /images/authors/kevin.jpg
twitter: kevinhill
github: kevinhill
bio: Building the future of autonomous development.
```

---

## Quick Reference

| Task | Location |
|------|----------|
| Add new blog post | Create `content/blog/post-slug.mdx` |
| Set post as featured | Add `featured: true` to frontmatter |
| Hide draft post | Add `draft: true` to frontmatter |
| Add category | Add `category: Name` to frontmatter |
| Add tags | Add `tags: [tag1, tag2]` to frontmatter |
| Modify blog layout | `app/blog/layout.tsx` |
| Update RSS feed | `app/feed.xml/route.ts` |
| Run locally | `pnpm dev`, visit `/blog` |

### Frontmatter Template

```yaml
---
title:
description:
author:
date: 2026-01-30
category:
tags: []
image:
imageAlt:
draft: false
featured: false
---
```

### Category Suggestions

- `Announcements` - Product updates, releases
- `Tutorials` - Step-by-step guides
- `Engineering` - Technical deep-dives
- `Case Studies` - Customer success stories
- `Community` - Community highlights, events
