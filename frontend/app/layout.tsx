import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Atoms Demo",
  description: "智能体驱动生成应用",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="border-b bg-white">
          <div className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-6">
            <Link href="/" className="font-bold text-blue-600">
              ⚡ Atoms Demo
            </Link>
            <Link
              href="/projects"
              className="text-sm text-gray-600 hover:text-blue-600"
            >
              作品库
            </Link>
            <span className="ml-auto text-xs text-gray-400">
              7 智能体 · 3 模式 · 附件 · 连接器
            </span>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
