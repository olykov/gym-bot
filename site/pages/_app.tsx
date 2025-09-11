import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { SessionProvider } from 'next-auth/react'
import { useEffect } from 'react'
import { initTelegramApp } from '../lib/telegram-mini-app'

export default function App({ 
  Component, 
  pageProps: { session, ...pageProps } 
}: AppProps) {
  
  // Initialize Telegram Web App when the app starts
  useEffect(() => {
    console.log('🚀 Initializing Telegram Web App...');
    initTelegramApp();
  }, []);

  return (
    <SessionProvider session={session}>
      <Component {...pageProps} />
    </SessionProvider>
  )
}
