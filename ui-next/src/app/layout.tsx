import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/nav";
import { Providers } from "./providers";

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
          <main className="page-container">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
