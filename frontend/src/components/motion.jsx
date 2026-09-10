"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, LazyMotion, MotionConfig, domAnimation } from "framer-motion";
import { animate } from "framer-motion/dom/mini";
import * as m from "framer-motion/m";

const settle = [0.22, 1, 0.36, 1];
const reducedMotionQuery = "(prefers-reduced-motion: reduce)";

function subscribeToMotionPreference(onChange) {
  const preference = window.matchMedia(reducedMotionQuery);
  preference.addEventListener("change", onChange);
  return () => preference.removeEventListener("change", onChange);
}

function getMotionPreference() {
  return window.matchMedia(reducedMotionQuery).matches;
}

function getServerMotionPreference() {
  return true;
}

function usePrefersReducedMotion() {
  // React to preference changes even while the user stays on the same page.
  return useSyncExternalStore(
    subscribeToMotionPreference,
    getMotionPreference,
    getServerMotionPreference,
  );
}

export function MotionProvider({ children }) {
  return <MotionConfig reducedMotion="user" transition={{ duration: 0.28, ease: settle }}>
    <LazyMotion features={domAnimation} strict>{children}</LazyMotion>
  </MotionConfig>;
}

export function useMotionTiming(duration = 0.28) {
  const reduced = usePrefersReducedMotion();
  // Stay still until the browser preference is known, including during hydration.
  return { duration: reduced === false ? duration : 0, ease: settle };
}

export function useEntrance(identity, { distance = 12, stagger = false, inView = false } = {}) {
  const scope = useRef(null);
  const reduced = usePrefersReducedMotion();
  useEffect(() => {
    const element = scope.current;
    if (reduced !== false || !element) return;
    const elements = stagger ? Array.from(element.children) : [element];
    const originals = elements.map((target) => ({
      opacity: target.style.opacity,
      transform: target.style.transform,
    }));
    let animations = [];
    function reveal() {
      animations = elements.map((target, index) => animate(target, {
        opacity: [0.35, 1],
        transform: [`translateY(${distance}px)`, "translateY(0px)"],
      }, { duration: 0.42, delay: Math.min(index, 3) * 0.045, ease: settle }));
    }
    // Observe only the few annotated landmarks; disconnect after their first entrance.
    const observer = inView ? new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        reveal();
        observer.disconnect();
      }
    }, { threshold: 0.15 }) : null;
    if (observer) observer.observe(element);
    else reveal();
    return () => {
      observer?.disconnect();
      animations.forEach((animation) => animation.cancel());
      elements.forEach((target, index) => {
        target.style.opacity = originals[index].opacity;
        target.style.transform = originals[index].transform;
      });
    };
  }, [identity, reduced, distance, stagger, inView]);
  return scope;
}

export function Reveal({ children, className, stagger = false, inView = false }) {
  const pathname = usePathname();
  const scope = useEntrance(pathname, { stagger, inView });
  // Visible in server HTML; motion enhances content after hydration, never gates it.
  return <div ref={scope} className={className}>{children}</div>;
}

export function Expandable({ open, children }) {
  return <AnimatePresence initial={false}>
    {open && <ExpandableContent key="content">{children}</ExpandableContent>}
  </AnimatePresence>;
}

function ExpandableContent({ children }) {
  // Keep the preference subscription alive during AnimatePresence's exit.
  const transition = useMotionTiming();
  return <m.div className="overflow-hidden" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={transition}>
    {children}
  </m.div>;
}
