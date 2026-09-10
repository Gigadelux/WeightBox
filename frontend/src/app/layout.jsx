import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Shell } from "@/components/shell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  icons: { icon: "/icon.svg", shortcut: "/icon.svg" },
  title: {
    default: "WeightBox — Your AI hardware workbench",
    template: "%s · WeightBox",
  },
  description:
    "Explore which AI models fit your GPU. Compare memory requirements, quantization, and hardware accessibility using the WeightBox research warehouse.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
