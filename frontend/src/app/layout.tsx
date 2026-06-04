import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PalmLens",
  description: "基于手掌图像的非诊断型视觉特征分析网站"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

