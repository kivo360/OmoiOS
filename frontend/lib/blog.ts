import { loader } from "fumadocs-core/source";
import { toFumadocsSource } from "fumadocs-mdx/runtime/server";
import { blogPosts } from "@/.source/server";

export const blog = loader({
  baseUrl: "/blog",
  source: toFumadocsSource(blogPosts, []),
});

// Helper functions
export function getAllPosts() {
  return blog
    .getPages()
    .filter((post) => !post.data.draft)
    .sort(
      (a, b) =>
        new Date(b.data.date).getTime() - new Date(a.data.date).getTime(),
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
