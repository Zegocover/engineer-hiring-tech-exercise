import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Crawler dashboard",
  description: "Start, follow and cancel site crawls run by the crawler API.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <header className="border-b border-zinc-200 dark:border-zinc-800">
          <nav className="mx-auto max-w-5xl px-4 py-3">
            <Link href="/" className="font-semibold">
              Crawler dashboard
            </Link>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
