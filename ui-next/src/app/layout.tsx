import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/nav";
import { Providers } from "./providers";
import { ErrorBoundary } from "@/components/error-boundary";

export const metadata: Metadata = {
  title: "ACORN Hub",
  description: "Adaptive Collaborative Orchestration and Reasoning Network",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">
        <Providers>
          <Sidebar />
          <main className="page-container">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
        </Providers>
      </body>
    </html>
  );
}
