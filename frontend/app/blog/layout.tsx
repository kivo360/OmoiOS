'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useTheme } from 'next-themes';
import { useState, useEffect } from 'react';
import { Moon, Sun, Rss } from 'lucide-react';

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="w-9 h-9" />;
  }

  return (
    <button
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg hover:bg-muted transition-colors"
      aria-label="Toggle theme"
    >
      {resolvedTheme === 'dark' ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </button>
  );
}

export default function BlogLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      {/* Blog Header */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <nav className="flex items-center justify-between">
            <Link href="/blog" className="flex items-center gap-3 group">
              <Image
                src="/omoios-mark.svg"
                alt="OmoiOS"
                width={32}
                height={32}
                className="transition-transform group-hover:scale-110"
              />
              <span className="text-xl font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
                OmoiOS Blog
              </span>
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/docs"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Docs
              </Link>
              <Link
                href="/"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                App
              </Link>
              <Link
                href="/feed.xml"
                className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                aria-label="RSS Feed"
              >
                <Rss className="h-5 w-5" />
              </Link>
              <ThemeToggle />
            </div>
          </nav>
        </div>
      </header>

      {/* Blog Content */}
      <main>{children}</main>

      {/* Blog Footer */}
      <footer className="border-t mt-16 bg-muted/30">
        <div className="max-w-5xl mx-auto px-4 py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <Image
                src="/omoios-mark.svg"
                alt="OmoiOS"
                width={24}
                height={24}
              />
              <span className="text-sm text-muted-foreground">
                &copy; {new Date().getFullYear()} OmoiOS. All rights reserved.
              </span>
            </div>
            <div className="flex items-center gap-6 text-sm">
              <Link
                href="/docs"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Documentation
              </Link>
              <Link
                href="/feed.xml"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                RSS Feed
              </Link>
              <Link
                href="/"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Launch App
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
