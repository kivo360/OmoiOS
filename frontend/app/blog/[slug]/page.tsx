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

function BlogPostJsonLd({
  post,
  url,
}: {
  post: ReturnType<typeof blog.getPage>;
  url: string;
}) {
  if (!post) return null;

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

export default async function BlogPost({ params }: PageProps) {
  const { slug } = await params;
  const post = blog.getPage([slug]);

  if (!post || post.data.draft) notFound();

  const MDXContent = post.data.body;
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://omoios.dev';
  const postUrl = `${baseUrl}/blog/${slug}`;

  // Get related posts (same category, excluding current)
  const relatedPosts = getAllPosts()
    .filter((p) => p.url !== post.url && p.data.category === post.data.category)
    .slice(0, 3);

  return (
    <>
      <BlogPostJsonLd post={post} url={postUrl} />
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
          <h1 className="text-4xl font-bold mt-2 mb-4">{post.data.title}</h1>
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
                  dateTime={String(post.data.date)}
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
        {post.data.toc && post.data.toc.length > 0 && (
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
                  className="px-3 py-1 rounded-full bg-muted hover:bg-muted/80 text-sm transition-colors"
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
                <Link key={related.url} href={related.url} className="group">
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
    </>
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
      publishedTime: String(post.data.date),
      authors: [post.data.author],
      images: post.data.image
        ? [
            {
              url: `${baseUrl}${post.data.image}`,
              alt: post.data.imageAlt || post.data.title,
            },
          ]
        : [],
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
