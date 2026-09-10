"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Box, ArrowUpRight } from "lucide-react";
import { MotionProvider } from "./motion";
export function Shell({ children }) {
  const pathname = usePathname();
  return (
    <MotionProvider>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header bg-[var(--paper)] [border-bottom:1px_solid_var(--line)]">
        <div className="header-inner max-w-378 py-0 px-12 m-auto min-h-19.5 flex items-center gap-17.5 max-[1190px]:gap-10 max-[1190px]:px-7.5 max-[850px]:px-6 max-[850px]:gap-8.75 max-[620px]:min-h-26.25 max-[620px]:pt-4 max-[620px]:px-5 max-[620px]:pb-0 max-[620px]:flex-wrap max-[620px]:gap-2.5">
          <Link
            className="wordmark text-[25px] font-[650] tracking-[-1.3px] flex items-center max-[620px]:text-[23px]"
            href="/"
            aria-label="WeightBox home"
          >
            <span className="brand-icon grid place-items-center w-8.25 h-8.5 text-[var(--green)] mr-2.25">
              <Box size={23} strokeWidth={1.6} />
            </span>
            WeightBox<span className="brand-dot text-[var(--green)]">.</span>
          </Link>
          <nav aria-label="Main navigation">
            {[
              ["/", "Workbench"],
              ["/methodology", "Methodology"],
              ["/data", "The dataset"],
            ].map(([href, title]) => (
              <Link
                key={href}
                href={href}
                aria-current={pathname === href ? "page" : undefined}
              >
                {title}
              </Link>
            ))}
          </nav>
          <span className="header-caption ml-auto flex gap-2 items-center font-mono text-[10px] leading-[normal] text-[var(--muted)] max-[1190px]:hidden">
            <span className="tiny-square w-1.25 h-1.25 bg-[var(--green)] inline-block shrink-0" />{" "}
            A GPU × AI model explorer
          </span>
        </div>
      </header>
      {children}
      <footer className="site-footer max-w-354 w-[calc(100%_-_96px)] my-0 mx-auto pt-6.25 px-0 pb-7.5 [border-top:1px_solid_var(--line)] flex items-center gap-6.25 text-[var(--muted)] text-[10px] max-[1190px]:w-[calc(100%_-_60px)] max-[850px]:w-[calc(100%_-_48px)] max-[850px]:flex-wrap max-[850px]:gap-3 max-[620px]:w-[calc(100%_-_36px)] max-[620px]:py-5.5 max-[620px]:px-0 max-[620px]:grid max-[620px]:grid-cols-[1fr] max-[620px]:gap-2.5">
        <Link
          className="footer-brand text-[17px] font-[650] tracking-[-.7px] text-[var(--green)]"
          href="/"
        >
          WeightBox.
        </Link>
        <Link href="/methodology">
          Built on data, with context <ArrowUpRight size={14} />
        </Link>
      </footer>
    </MotionProvider>
  );
}
