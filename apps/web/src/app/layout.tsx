import type { Metadata } from "next";
import { Footer, Header } from "@/components/Chrome";
import { Preloader } from "@/components/Preloader";
import { SmoothScroll } from "@/components/SmoothScroll";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Uniloop · Pass it on",
  description: "Buy and sell used textbooks, calculators, lab gear and more with students on your campus.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Preloader />
        <SmoothScroll>
          <Header />
          <main>{children}</main>
          <Footer />
        </SmoothScroll>
      </body>
    </html>
  );
}
