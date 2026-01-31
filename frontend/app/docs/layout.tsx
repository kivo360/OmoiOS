import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import Image from 'next/image';
import { source } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      nav={{
        title: (
          <div className="flex items-center gap-2">
            <Image
              src="/omoios-mark.svg"
              alt="OmoiOS"
              width={28}
              height={28}
              className="dark:invert-0"
            />
            <span className="font-semibold">OmoiOS Docs</span>
          </div>
        ),
        url: '/docs',
      }}
      sidebar={{
        defaultOpenLevel: 1,
        collapsible: true,
      }}
      links={[
        { text: 'App', url: '/', active: 'none' },
        { text: 'Blog', url: '/blog', active: 'none' },
      ]}
    >
      {children}
    </DocsLayout>
  );
}
