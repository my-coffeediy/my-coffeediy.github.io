import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "铲子的小蓝杯实验室｜瑞幸咖啡家庭复刻",
  description: "21 款瑞幸热门与当季咖啡的家庭复刻用量、步骤和制作提醒。",
  icons: {
    icon: `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/favicon.svg`,
    shortcut: `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/favicon.svg`,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
