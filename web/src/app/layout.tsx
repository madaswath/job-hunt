import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { inter, instrumentSerif, instrumentSerifItalic } from "@/lib/fonts";
import { AppShell } from "@/components/app-shell";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job-hunt — Your AI Job Search Command Center",
  description:
    "Job-hunt — Local-first AI Job Search Command Center powered by Vishwakarma, Narada, Ganesha, Arjuna, Brihaspati, Saraswati, Dharma, Hanuman, Krishna, Skanda, Lakshmi.",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "Job-hunt" },
};

export const viewport: Viewport = {
  viewportFit: "cover",
  themeColor: "#0a0a0a",
};

const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('career-ops:theme');var s=t==='light'||t==='dark'?t:null;var d=s==='dark'||(!s&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');var m=document.querySelector('meta[name="theme-color"]');if(!m){m=document.createElement('meta');m.setAttribute('name','theme-color');document.head.appendChild(m);}m.setAttribute('content',d?'#0a0a0a':'#f7f6f3');}catch(e){document.documentElement.classList.add('dark');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${instrumentSerif.variable} ${instrumentSerifItalic.variable}`}
    >
      <body className="font-sans antialiased">
        <ClerkProvider>
          <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
          <ThemeProvider>
            <AppShell>{children}</AppShell>
          </ThemeProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
