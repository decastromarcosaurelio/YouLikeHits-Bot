import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YouLikeHits Autobot | Free Social Media Growth",
  description:
    "Automate website views, YouTube views, SoundCloud plays and the daily bonus on YouLikeHits. Open-source Python bot with GUI and CLI. Works on XFCE, KDE Plasma, and any Linux desktop.",
  keywords: [
    "youlikehits",
    "bot",
    "automation",
    "youtube views",
    "soundcloud plays",
    "social media",
    "free",
    "open source",
  ],
  openGraph: {
    title: "YouLikeHits Autobot",
    description:
      "Automate social media exchange tasks on YouLikeHits. Free, open-source Python bot with GUI.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 antialiased">{children}</body>
    </html>
  );
}
