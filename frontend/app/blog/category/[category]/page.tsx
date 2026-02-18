import { getAllPosts, getAllCategories } from "@/lib/blog";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

interface PageProps {
  params: Promise<{ category: string }>;
}

export default async function CategoryPage({ params }: PageProps) {
  const { category } = await params;
  const decodedCategory = decodeURIComponent(category);

  const posts = getAllPosts().filter(
    (post) =>
      post.data.category?.toLowerCase() === decodedCategory.toLowerCase(),
  );

  if (posts.length === 0) notFound();

  const categoryName = posts[0].data.category;

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8">Category: {categoryName}</h1>
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
  return getAllCategories().map((category) => ({
    category: category.toLowerCase(),
  }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { category } = await params;
  const decodedCategory = decodeURIComponent(category);
  const formattedCategory =
    decodedCategory.charAt(0).toUpperCase() + decodedCategory.slice(1);

  return {
    title: `${formattedCategory} | OmoiOS Blog`,
    description: `All blog posts in the ${formattedCategory} category`,
  };
}
