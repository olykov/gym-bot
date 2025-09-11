import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Official Telegram WebApp Script - CRITICAL for Mini App functionality */}
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}
