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
    lastModified: new Date(),
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
  const categories: MetadataRoute.Sitemap = getAllCategories().map(
    (category) => ({
      url: `${baseUrl}/blog/category/${category.toLowerCase()}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.5,
    })
  );

  // Blog tags
  const tags: MetadataRoute.Sitemap = getAllTags().map((tag) => ({
    url: `${baseUrl}/blog/tag/${tag.toLowerCase()}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.4,
  }));

  return [...staticPages, ...docPages, ...blogPosts, ...categories, ...tags];
}
