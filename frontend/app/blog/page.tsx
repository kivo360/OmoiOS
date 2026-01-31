import Link from 'next/link';
import Image from 'next/image';
import { getAllPosts, getFeaturedPosts, getAllCategories } from '@/lib/blog';
import { Sparkles, BookOpen, Megaphone, Lightbulb, ArrowRight } from 'lucide-react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Blog | OmoiOS',
  description:
    'Ship more without hiring more. Ideas on breaking the cycle of endless backlogs, burned-out engineers, and features that never ship.',
  openGraph: {
    title: 'OmoiOS Blog',
    description:
      'Ship more without hiring more. Ideas on breaking the cycle of endless backlogs, burned-out engineers, and features that never ship.',
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

// Category icon and color mapping
const categoryStyles: Record<string, { icon: typeof Sparkles; color: string; bg: string }> = {
  Announcements: {
    icon: Megaphone,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 hover:bg-amber-500/20',
  },
  Tutorials: {
    icon: BookOpen,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10 hover:bg-blue-500/20',
  },
  Updates: {
    icon: Sparkles,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10 hover:bg-purple-500/20',
  },
  Tips: {
    icon: Lightbulb,
    color: 'text-green-500',
    bg: 'bg-green-500/10 hover:bg-green-500/20',
  },
};

function getCategoryStyle(category: string) {
  return categoryStyles[category] || {
    icon: Sparkles,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 hover:bg-amber-500/20',
  };
}

export default function BlogIndex() {
  const posts = getAllPosts();
  const featuredPosts = getFeaturedPosts();
  const categories = getAllCategories();

  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 via-background to-orange-500/5" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-amber-500/20 via-transparent to-transparent" />

        {/* Grid Pattern Overlay */}
        <div
          className="absolute inset-0 opacity-[0.02] dark:opacity-[0.05]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23f59e0b' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        <div className="relative max-w-5xl mx-auto px-4 py-16 md:py-24">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-sm font-medium mb-6">
              <Sparkles className="h-4 w-4" />
              Ship More, Hire Less
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
              Your Backlog Shouldn&apos;t{' '}
              <span className="bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
                Outpace Your Team
              </span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Ideas on breaking the cycle of endless hiring, burned-out engineers,
              and features that never ship.
            </p>
          </div>
        </div>
      </section>

      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Featured Posts */}
        {featuredPosts.length > 0 && (
          <section className="mb-16">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <Sparkles className="h-5 w-5 text-amber-500" />
              </div>
              <h2 className="text-2xl font-bold">Featured</h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {featuredPosts.slice(0, 2).map((post, index) => {
                const style = getCategoryStyle(post.data.category || '');
                const Icon = style.icon;
                return (
                  <Link
                    key={post.url}
                    href={post.url}
                    className={`group relative block rounded-2xl border overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-amber-500/10 hover:-translate-y-1 ${
                      index === 0 ? 'md:col-span-2' : ''
                    }`}
                  >
                    {/* Gradient Border Effect */}
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-amber-500/50 via-transparent to-orange-500/50 opacity-0 group-hover:opacity-100 transition-opacity -z-10 blur-xl" />

                    <div className={`flex flex-col ${index === 0 ? 'md:flex-row' : ''}`}>
                      {/* Image Section */}
                      {post.data.image ? (
                        <div className={`relative bg-muted ${
                          index === 0 ? 'aspect-video md:aspect-auto md:w-1/2' : 'aspect-video'
                        }`}>
                          <Image
                            src={post.data.image}
                            alt={post.data.imageAlt || post.data.title}
                            fill
                            className="object-cover"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                        </div>
                      ) : (
                        <div className={`relative bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-500/20 dark:to-orange-500/20 flex items-center justify-center ${
                          index === 0 ? 'aspect-video md:aspect-auto md:w-1/2 md:min-h-[280px]' : 'aspect-video'
                        }`}>
                          <Image
                            src="/omoios-mark.svg"
                            alt="OmoiOS"
                            width={index === 0 ? 80 : 60}
                            height={index === 0 ? 80 : 60}
                            className="opacity-40 dark:opacity-30"
                          />
                        </div>
                      )}

                      {/* Content Section */}
                      <div className={`p-6 ${index === 0 ? 'md:w-1/2 md:p-8 md:flex md:flex-col md:justify-center' : ''}`}>
                        {post.data.category && (
                          <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${style.color}`}>
                            <Icon className="h-3.5 w-3.5" />
                            {post.data.category}
                          </span>
                        )}
                        <h3 className={`font-bold mt-2 text-foreground group-hover:text-amber-500 transition-colors ${
                          index === 0 ? 'text-2xl md:text-3xl' : 'text-xl'
                        }`}>
                          {post.data.title}
                        </h3>
                        <p className="text-muted-foreground mt-3 line-clamp-2">
                          {post.data.description}
                        </p>
                        <div className="mt-4 flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">
                            {new Date(post.data.date).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                            })}
                          </span>
                          <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-500 group-hover:gap-2 transition-all">
                            Read more
                            <ArrowRight className="h-4 w-4" />
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Categories */}
        {categories.length > 0 && (
          <section className="mb-12">
            <div className="flex flex-wrap gap-3">
              <Link
                href="/blog"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500 text-white text-sm font-medium shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 transition-shadow"
              >
                <Sparkles className="h-4 w-4" />
                All Posts
              </Link>
              {categories.map((category) => {
                const style = getCategoryStyle(category);
                const Icon = style.icon;
                return (
                  <Link
                    key={category}
                    href={`/blog/category/${category.toLowerCase()}`}
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${style.bg} ${style.color}`}
                  >
                    <Icon className="h-4 w-4" />
                    {category}
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* All Posts */}
        <section>
          <h2 className="text-2xl font-bold mb-8">All Posts</h2>
          {posts.length === 0 ? (
            <div className="text-center py-16 rounded-2xl border border-dashed">
              <p className="text-muted-foreground">No posts yet. Check back soon!</p>
            </div>
          ) : (
            <div className="space-y-6">
              {posts.map((post) => {
                const style = getCategoryStyle(post.data.category || '');
                const Icon = style.icon;
                return (
                  <article
                    key={post.url}
                    className="group relative rounded-xl border p-6 hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-500/5 transition-all duration-300"
                  >
                    <Link href={post.url} className="flex gap-6">
                      <div className="flex-1 min-w-0">
                        {post.data.category && (
                          <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${style.color}`}>
                            <Icon className="h-3.5 w-3.5" />
                            {post.data.category}
                          </span>
                        )}
                        <h3 className="text-xl font-semibold mt-1 group-hover:text-amber-500 transition-colors">
                          {post.data.title}
                        </h3>
                        <p className="text-muted-foreground mt-2 line-clamp-2">
                          {post.data.description}
                        </p>
                        <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground/80">{post.data.author}</span>
                          <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                          <time dateTime={String(post.data.date)}>
                            {new Date(post.data.date).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                            })}
                          </time>
                        </div>
                      </div>
                      {post.data.image ? (
                        <div className="hidden sm:block w-40 h-28 relative rounded-lg overflow-hidden flex-shrink-0">
                          <Image
                            src={post.data.image}
                            alt=""
                            fill
                            className="object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                        </div>
                      ) : (
                        <div className="hidden sm:flex w-40 h-28 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-500/10 dark:to-orange-500/10 items-center justify-center flex-shrink-0 border border-amber-200/50 dark:border-amber-500/20">
                          <Image
                            src="/omoios-mark.svg"
                            alt=""
                            width={40}
                            height={40}
                            className="opacity-40 dark:opacity-30"
                          />
                        </div>
                      )}
                    </Link>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Newsletter CTA */}
        <section className="mt-16 relative overflow-hidden rounded-2xl border bg-gradient-to-br from-amber-500/10 via-background to-orange-500/5 p-8 md:p-12">
          <div className="absolute top-0 right-0 -translate-y-1/4 translate-x-1/4 w-64 h-64 rounded-full bg-amber-500/20 blur-3xl" />
          <div className="relative text-center">
            <h3 className="text-2xl font-bold mb-3">Stop Playing Catch-Up</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Get insights on shipping faster without burning out your team. No spam, just signal.
            </p>
            <Link
              href="/feed.xml"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-amber-500 text-white font-medium shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 hover:bg-amber-600 transition-all"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19 7.38 20 6.18 20C5 20 4 19 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z" />
              </svg>
              Subscribe via RSS
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
