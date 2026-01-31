import { defineDocs, defineCollections, defineConfig, frontmatterSchema } from 'fumadocs-mdx/config';
import { remarkMdxMermaid } from 'fumadocs-core/mdx-plugins';
import { z } from 'zod';

// Define the docs collection
export const docs = defineDocs({
  dir: 'content/docs',
});

// Define the blog posts collection
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
    remarkPlugins: [remarkMdxMermaid],
    rehypePlugins: [],
  },
});
