"use client";
import { mainnet, polygon, bsc } from 'wagmi/chains';
import { RainbowKitProvider, getDefaultConfig } from "@rainbow-me/rainbowkit";
import { WagmiProvider } from "wagmi";
// إعداد Wagmi + RainbowKit
const config = getDefaultConfig({
  appName: "EPPNE Sovereign Platform",
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID || "YOUR_PROJECT_ID", // سجل مجاناً من WalletConnect
  chains: [mainnet, polygon, bsc],
  ssr: true,
});

export function Web3Provider({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <RainbowKitProvider locale="ar">{children}</RainbowKitProvider>
    </WagmiProvider>
  );
}