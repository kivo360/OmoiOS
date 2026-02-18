import { getAllPosts, getAllTags, getPostsByTag } from "@/lib/blog";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

interface PageProps {
  params: Promise<{ tag: string }>;
}

export default async function TagPage({ params }: PageProps) {
  const { tag } = await params;
  const decodedTag = decodeURIComponent(tag);

  const posts = getPostsByTag(decodedTag);

  if (posts.length === 0) notFound();

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8">Tag: #{decodedTag}</h1>
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
              <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
                <span>{post.data.author}</span>
                <span>•</span>
                <time dateTime={String(post.data.date)}>
                  {new Date(post.data.date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
              </div>
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return getAllTags().map((tag) => ({
    tag: tag.toLowerCase(),
  }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { tag } = await params;
  const decodedTag = decodeURIComponent(tag);

  return {
    title: `#${decodedTag} | OmoiOS Blog`,
    description: `All blog posts tagged with #${decodedTag}`,
  };
}
