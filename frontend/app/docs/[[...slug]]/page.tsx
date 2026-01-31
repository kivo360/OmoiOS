import { source } from '@/lib/source';
import { notFound } from 'next/navigation';
import {
  DocsPage,
  DocsBody,
  DocsTitle,
  DocsDescription,
} from 'fumadocs-ui/page';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import { Mermaid } from '@/components/docs/mermaid';
import type { Metadata } from 'next';

// Extend default MDX components with Mermaid support
// The remarkMdxMermaid plugin converts ```mermaid blocks to <Mermaid chart="..." />
const mdxComponents = {
  ...defaultMdxComponents,
  Mermaid,
};

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
      full={page.data.full}
    >
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDXContent components={mdxComponents} />
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
    },
    twitter: {
      card: 'summary_large_image',
      title: page.data.title,
      description: page.data.description,
    },
    alternates: {
      canonical: pageUrl,
    },
  };
}
