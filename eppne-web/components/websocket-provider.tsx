// components/web3/connect-wallet.tsx
"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import { motion } from "framer-motion";

export function ConnectWallet() {
  return (
    <div className="relative group">
      {/* 🟢 إضاءة نيون خلفية للزر */}
      <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-blue-600 rounded-full opacity-30 group-hover:opacity-75 blur transition duration-500" />
      
      <div className="relative bg-background/50 backdrop-blur-md rounded-full border border-white/10 shadow-inner">
        <ConnectButton 
          accountStatus={{
            smallScreen: 'avatar',
            largeScreen: 'full',
          }}
          chainStatus="icon"
          showBalance={false}
        />
      </div>
    </div>
  );
}