"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { Toaster } from "sonner";
import { Web3Provider } from "@/app/web3-provider";
import { AuthProvider } from "@/providers/AuthProvider";
import { getWebSocketService } from "@/services/websocket.service";
import "@rainbow-me/rainbowkit/styles.css";
import { useState, useEffect } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  // تفعيل WebSocket عند تحميل التطبيق
  useEffect(() => {
    const ws = getWebSocketService();
    ws.connect();

    // إغلاق الاتصال عند مغادرة الصفحة
    return () => {
      ws.disconnect();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <Web3Provider>
        <NextThemesProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            {children}
            <Toaster position="top-center" richColors closeButton />
          </AuthProvider>
        </NextThemesProvider>
      </Web3Provider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}