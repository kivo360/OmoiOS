# Fumadocs SEO Implementation Guide

**Version:** 1.0
**Last Updated:** January 30, 2026
**Applies To:** OmoiOS Frontend (`frontend/`)

---

## Table of Contents

1. [Overview](#overview)
2. [Core SEO Strategy](#core-seo-strategy)
3. [Metadata Configuration](#metadata-configuration)
4. [Sitemap Generation](#sitemap-generation)
5. [Robots.txt](#robotstxt)
6. [Structured Data (JSON-LD)](#structured-data-json-ld)
7. [Open Graph & Social Cards](#open-graph--social-cards)
8. [Dynamic OG Images](#dynamic-og-images)
9. [Canonical URLs](#canonical-urls)
10. [Performance & Core Web Vitals](#performance--core-web-vitals)
11. [Internationalization (i18n)](#internationalization-i18n)
12. [SEO Checklist](#seo-checklist)
13. [Monitoring & Validation](#monitoring--validation)

---

## Overview

This guide covers comprehensive SEO implementation for the OmoiOS documentation and blog systems. All SEO is server-rendered for optimal search engine indexing.

### SEO Goals
- **Discoverability** - All docs and blog posts indexed by search engines
- **Rich Results** - Structured data for enhanced search listings
- **Social Sharing** - Optimized Open Graph and Twitter cards
- **Performance** - Core Web Vitals optimized for ranking signals
- **Crawlability** - Proper sitemap and robots.txt configuration

---

## Core SEO Strategy

### Server-Side Rendering Priority

Next.js App Router with React Server Components provides optimal SEO:

```
┌─────────────────────────────────────────┐
│         Search Engine Crawler           │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│    Next.js Server (Full HTML Response)  │
│                                         │
│  ├── <head>                             │
│  │   ├── <title>                        │
│  │   ├── <meta name="description">      │
│  │   ├── <meta property="og:*">         │
│  │   ├── <link rel="canonical">         │
│  │   └── <script type="application/ld+json">
│  │                                      │
│  └── <body>                             │
│      └── Full rendered content          │
└─────────────────────────────────────────┘
```

### URL Structure

```
https://omoios.dev/
├── /docs                    # Documentation root
│   ├── /docs/getting-started/installation
│   ├── /docs/guides/agent-workflows
│   └── /docs/api-reference/endpoints
├── /blog                    # Blog root
│   ├── /blog/announcing-v2
│   └── /blog/agent-deep-dive
├── /blog/category/[category]  # Category archives
├── /blog/tag/[tag]            # Tag archives
├── /sitemap.xml
├── /robots.txt
└── /feed.xml               # RSS feed
```

---

## Metadata Configuration

### Root Layout Metadata

```tsx
// frontend/app/layout.tsx
import type { Metadata, Viewport } from 'next';

const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: 'OmoiOS - Spec-Driven Multi-Agent Orchestration',
    template: '%s | OmoiOS',
  },
  description: 'Scale development without scaling headcount. OmoiOS combines autonomous agent execution with structured workflows for spec-driven development.',
  keywords: [
    'multi-agent orchestration',
    'autonomous development',
    'spec-driven development',
    'AI agents',
    'software development automation',
  ],
  authors: [{ name: 'OmoiOS Team' }],
  creator: 'OmoiOS',
  publisher: 'OmoiOS',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: baseUrl,
    siteName: 'OmoiOS',
    title: 'OmoiOS - Spec-Driven Multi-Agent Orchestration',
    description: 'Scale development without scaling headcount.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'OmoiOS Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@omoios',
    creator: '@omoios',
    title: 'OmoiOS - Spec-Driven Multi-Agent Orchestration',
    description: 'Scale development without scaling headcount.',
    images: ['/og-image.png'],
  },
  alternates: {
    canonical: baseUrl,
    types: {
      'application/rss+xml': '/feed.xml',
    },
  },
  verification: {
    google: process.env.GOOGLE_SITE_VERIFICATION,
    // yandex: '',
    // bing: '',
  },
  category: 'technology',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0a' },
  ],
};
```

### Documentation Page Metadata

```tsx
// frontend/app/docs/[[...slug]]/page.tsx
import type { Metadata } from 'next';
import { source } from '@/lib/source';

interface PageProps {
  params: Promise<{ slug?: string[] }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = source.getPage(slug);

  if (!page) return {};

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';
  const pageUrl = `${baseUrl}/docs/${slug?.join('/') || ''}`;

  return {
    title: page.data.title,
    description: page.data.description,
    openGraph: {
      title: page.data.title,
      description: page.data.description,
      type: 'article',
      url: pageUrl,
      siteName: 'OmoiOS Documentation',
      images: [
        {
          url: `/api/og/docs?title=${encodeURIComponent(page.data.title)}`,
          width: 1200,
          height: 630,
          alt: page.data.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: page.data.title,
      description: page.data.description,
      images: [`/api/og/docs?title=${encodeURIComponent(page.data.title)}`],
    },
    alternates: {
      canonical: pageUrl,
    },
  };
}
```

### Blog Post Metadata

```tsx
// frontend/app/blog/[slug]/page.tsx
import type { Metadata } from 'next';
import { blog } from '@/lib/blog';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = blog.getPage([slug]);

  if (!post) return {};

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';
  const postUrl = `${baseUrl}/blog/${slug}`;

  return {
    title: post.data.title,
    description: post.data.description,
    authors: [{ name: post.data.author }],
    openGraph: {
      title: post.data.title,
      description: post.data.description,
      type: 'article',
      url: postUrl,
      publishedTime: post.data.date,
      modifiedTime: post.data.date,
      authors: [post.data.author],
      section: post.data.category,
      tags: post.data.tags,
      images: post.data.image
        ? [
            {
              url: `${baseUrl}${post.data.image}`,
              width: 1200,
              height: 630,
              alt: post.data.imageAlt || post.data.title,
            },
          ]
        : [
            {
              url: `/api/og/blog?title=${encodeURIComponent(post.data.title)}&author=${encodeURIComponent(post.data.author)}`,
              width: 1200,
              height: 630,
              alt: post.data.title,
            },
          ],
    },
    twitter: {
      card: 'summary_large_image',
      title: post.data.title,
      description: post.data.description,
      images: post.data.image
        ? [`${baseUrl}${post.data.image}`]
        : [`/api/og/blog?title=${encodeURIComponent(post.data.title)}`],
    },
    alternates: {
      canonical: postUrl,
    },
  };
}
```

---

## Sitemap Generation

### Dynamic Sitemap

```typescript
// frontend/app/sitemap.ts
import type { MetadataRoute } from 'next';
import { source } from '@/lib/source';
import { getAllPosts, getAllCategories, getAllTags } from '@/lib/blog';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: `${baseUrl}/docs`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
  ];

  // Documentation pages
  const docPages: MetadataRoute.Sitemap = source.getPages().map((page) => ({
    url: `${baseUrl}${page.url}`,
    lastModified: page.data.lastModified || new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  // Blog posts
  const blogPosts: MetadataRoute.Sitemap = getAllPosts().map((post) => ({
    url: `${baseUrl}${post.url}`,
    lastModified: new Date(post.data.date),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }));

  // Blog categories
  const categories: MetadataRoute.Sitemap = getAllCategories().map((category) => ({
    url: `${baseUrl}/blog/category/${category.toLowerCase()}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.5,
  }));

  // Blog tags
  const tags: MetadataRoute.Sitemap = getAllTags().map((tag) => ({
    url: `${baseUrl}/blog/tag/${tag.toLowerCase()}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.4,
  }));

  return [
    ...staticPages,
    ...docPages,
    ...blogPosts,
    ...categories,
    ...tags,
  ];
}
```

### Large Sitemap Handling (50,000+ URLs)

For very large sites, split into multiple sitemaps:

```typescript
// frontend/app/sitemap/[id]/route.ts
import { source } from '@/lib/source';

const URLS_PER_SITEMAP = 50000;

export async function generateSitemaps() {
  const totalPages = source.getPages().length;
  const numSitemaps = Math.ceil(totalPages / URLS_PER_SITEMAP);

  return Array.from({ length: numSitemaps }, (_, i) => ({ id: i.toString() }));
}

export default function sitemap({ id }: { id: string }) {
  const start = parseInt(id) * URLS_PER_SITEMAP;
  const pages = source.getPages().slice(start, start + URLS_PER_SITEMAP);

  return pages.map((page) => ({
    url: `https://omoios.dev${page.url}`,
    lastModified: page.data.lastModified,
  }));
}
```

---

## Robots.txt

```typescript
// frontend/app/robots.ts
import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/_next/',
          '/private/',
          '*.json$',
        ],
      },
      {
        userAgent: 'GPTBot',
        allow: ['/docs/', '/blog/'],
        disallow: ['/api/', '/private/'],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
    host: baseUrl,
  };
}
```

---

## Structured Data (JSON-LD)

### Organization Schema (Root Layout)

```tsx
// frontend/app/layout.tsx
function OrganizationJsonLd() {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'OmoiOS',
    url: baseUrl,
    logo: `${baseUrl}/logo.png`,
    description: 'Spec-driven, multi-agent orchestration system that scales development without scaling headcount.',
    sameAs: [
      'https://twitter.com/omoios',
      'https://github.com/omoios',
      'https://linkedin.com/company/omoios',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      email: 'support@omoios.dev',
      contactType: 'customer service',
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}

// Add to layout:
<head>
  <OrganizationJsonLd />
</head>
```

### Documentation Article Schema

```tsx
// frontend/components/seo/DocArticleJsonLd.tsx
interface DocArticleJsonLdProps {
  title: string;
  description: string;
  url: string;
  lastModified?: Date;
  breadcrumbs: Array<{ name: string; url: string }>;
}

export function DocArticleJsonLd({
  title,
  description,
  url,
  lastModified,
  breadcrumbs,
}: DocArticleJsonLdProps) {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: title,
    description: description,
    url: url,
    dateModified: lastModified?.toISOString(),
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

  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs.map((crumb, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: crumb.name,
      item: `${baseUrl}${crumb.url}`,
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
      />
    </>
  );
}
```

### Blog Post Schema

```tsx
// frontend/components/seo/BlogPostJsonLd.tsx
interface BlogPostJsonLdProps {
  title: string;
  description: string;
  author: string;
  datePublished: string;
  dateModified?: string;
  url: string;
  image?: string;
  category?: string;
  tags?: string[];
}

export function BlogPostJsonLd({
  title,
  description,
  author,
  datePublished,
  dateModified,
  url,
  image,
  category,
  tags,
}: BlogPostJsonLdProps) {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: title,
    description: description,
    author: {
      '@type': 'Person',
      name: author,
    },
    datePublished: datePublished,
    dateModified: dateModified || datePublished,
    url: url,
    image: image ? `${baseUrl}${image}` : undefined,
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
    keywords: tags?.join(', '),
    articleSection: category,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

### FAQ Schema (for FAQ pages)

```tsx
// frontend/components/seo/FAQJsonLd.tsx
interface FAQItem {
  question: string;
  answer: string;
}

export function FAQJsonLd({ faqs }: { faqs: FAQItem[] }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

---

## Open Graph & Social Cards

### Default OG Image

Place a static fallback at `frontend/public/og-image.png` (1200x630px).

### Dynamic OG Images

```tsx
// frontend/app/api/og/docs/route.tsx
import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get('title') || 'OmoiOS Documentation';

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'flex-end',
          backgroundColor: '#0a0a0a',
          padding: '60px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <span
            style={{
              fontSize: '24px',
              color: '#888',
              textTransform: 'uppercase',
              letterSpacing: '2px',
            }}
          >
            OmoiOS Docs
          </span>
        </div>
        <div
          style={{
            fontSize: '64px',
            fontWeight: 'bold',
            color: '#fff',
            lineHeight: 1.2,
            maxWidth: '900px',
          }}
        >
          {title}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
```

```tsx
// frontend/app/api/og/blog/route.tsx
import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get('title') || 'OmoiOS Blog';
  const author = searchParams.get('author') || '';

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          backgroundColor: '#0a0a0a',
          padding: '60px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <span
            style={{
              fontSize: '24px',
              color: '#888',
              textTransform: 'uppercase',
              letterSpacing: '2px',
            }}
          >
            OmoiOS Blog
          </span>
        </div>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              fontSize: '56px',
              fontWeight: 'bold',
              color: '#fff',
              lineHeight: 1.2,
              maxWidth: '900px',
              marginBottom: '30px',
            }}
          >
            {title}
          </div>
          {author && (
            <div
              style={{
                fontSize: '28px',
                color: '#888',
              }}
            >
              By {author}
            </div>
          )}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
```

---

## Canonical URLs

### Setting Canonical URLs

Always set canonical URLs to prevent duplicate content issues:

```tsx
// In generateMetadata
return {
  alternates: {
    canonical: `${baseUrl}/docs/${slug?.join('/') || ''}`,
  },
};
```

### Handling Trailing Slashes

Ensure consistent URL format in `next.config.js`:

```javascript
const nextConfig = {
  trailingSlash: false, // or true - just be consistent
};
```

---

## Performance & Core Web Vitals

### Image Optimization

```tsx
import Image from 'next/image';

// Always use Next.js Image component
<Image
  src="/images/feature.jpg"
  alt="Feature description"
  width={800}
  height={400}
  priority // For above-the-fold images
  loading="lazy" // For below-the-fold images (default)
/>
```

### Font Optimization

```tsx
// frontend/app/layout.tsx
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap', // Prevents CLS
  variable: '--font-inter',
});

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
```

### Preloading Critical Resources

```tsx
// In metadata
export const metadata = {
  other: {
    'link': [
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      { rel: 'dns-prefetch', href: 'https://api.omoios.dev' },
    ],
  },
};
```

---

## Internationalization (i18n)

### Hreflang Tags (Future Enhancement)

```tsx
// When adding i18n support
export const metadata = {
  alternates: {
    canonical: 'https://omoios.dev/docs/getting-started',
    languages: {
      'en-US': 'https://omoios.dev/docs/getting-started',
      'es': 'https://omoios.dev/es/docs/getting-started',
      'ja': 'https://omoios.dev/ja/docs/getting-started',
    },
  },
};
```

---

## SEO Checklist

### Per-Page Requirements

- [ ] `title` - Unique, under 60 characters
- [ ] `description` - Unique, 150-160 characters
- [ ] `canonical` URL set
- [ ] Open Graph tags (`og:title`, `og:description`, `og:image`, `og:url`)
- [ ] Twitter Card tags (`twitter:card`, `twitter:title`, `twitter:description`)
- [ ] Structured data (JSON-LD) for rich results
- [ ] Heading hierarchy (single H1, logical H2-H6)
- [ ] Internal links to related content
- [ ] Alt text for all images

### Site-Wide Requirements

- [ ] `sitemap.xml` generated and submitted
- [ ] `robots.txt` properly configured
- [ ] RSS feed for blog
- [ ] Mobile-responsive design
- [ ] HTTPS enabled
- [ ] Fast load times (Core Web Vitals)
- [ ] 404 page with navigation

### Documentation-Specific

- [ ] Clear information architecture
- [ ] Breadcrumb navigation with schema
- [ ] Search functionality
- [ ] Last updated dates
- [ ] Version documentation (if applicable)

### Blog-Specific

- [ ] Author attribution
- [ ] Publication dates
- [ ] Category/tag organization
- [ ] Related posts links
- [ ] Social sharing buttons (optional)

---

## Monitoring & Validation

### Tools

| Tool | Purpose | URL |
|------|---------|-----|
| Google Search Console | Index status, search performance | https://search.google.com/search-console |
| Google Rich Results Test | Validate structured data | https://search.google.com/test/rich-results |
| Schema Markup Validator | Validate JSON-LD | https://validator.schema.org |
| PageSpeed Insights | Core Web Vitals | https://pagespeed.web.dev |
| Meta Tags Debugger | Preview social cards | https://metatags.io |
| Twitter Card Validator | Validate Twitter cards | https://cards-dev.twitter.com/validator |
| Facebook Sharing Debugger | Validate OG tags | https://developers.facebook.com/tools/debug |

### Environment Variables

```env
# Required
NEXT_PUBLIC_SITE_URL=https://omoios.dev

# Optional - Verification
GOOGLE_SITE_VERIFICATION=your-verification-code
```

### Testing Locally

```bash
# Build and run production server
pnpm build
pnpm start

# Check generated pages
curl -I http://localhost:3000/docs/getting-started
curl http://localhost:3000/sitemap.xml
curl http://localhost:3000/robots.txt
```

---

## Quick Reference

| SEO Element | Location |
|-------------|----------|
| Root metadata | `app/layout.tsx` |
| Page metadata | `generateMetadata()` in page |
| Sitemap | `app/sitemap.ts` |
| Robots.txt | `app/robots.ts` |
| RSS Feed | `app/feed.xml/route.ts` |
| OG Images | `app/api/og/*/route.tsx` |
| JSON-LD | `components/seo/*.tsx` |
