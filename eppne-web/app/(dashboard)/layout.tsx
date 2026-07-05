import type { Metadata, Viewport } from "next";
import { Inter, Cairo, Geist } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { cn } from "@/lib/utils";
import { WebSocketProvider } from "@/components/websocket-provider";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const cairo = Cairo({ subsets: ["arabic"], variable: "--font-cairo" });

export const metadata: Metadata = {
  title: "EPPNE - Sovereign Platform",
  description: "Military-grade Web2.5 ecosystem for sovereign entities",
  keywords: "blockchain, sovereign, web3, ai, marketplace",
  authors: [{ name: "EPPNE" }],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ar"
      dir="rtl"
      suppressHydrationWarning
      className={cn("font-sans", geist.variable)}
    >
      <body className={`${inter.variable} ${cairo.variable} font-sans`}>
        <Providers>
          <WebSocketProvider>{children}</WebSocketProvider>
        </Providers>
      </body>
    </html>
  );
}