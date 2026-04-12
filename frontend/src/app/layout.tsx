import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IASW — Intelligent Account Servicing Workflow",
  description: "AI-assisted banking account change request processing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <nav className="bg-blue-900 text-white px-6 py-3 flex items-center gap-6 shadow">
          <span className="font-bold text-lg tracking-tight">IASW</span>
          <a href="/" className="text-sm hover:text-blue-200 transition-colors">New Request</a>
          <a href="/checker" className="text-sm hover:text-blue-200 transition-colors">Checker Dashboard</a>
        </nav>
        <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
