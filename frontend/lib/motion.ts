/** Fade/slide variants without hiding content (safe when JS is slow or fails on mobile). */
export const fadeUpVariants = {
  hidden: { y: 16 },
  show: (i: number = 0) => ({
    y: 0,
    transition: { duration: 0.5, delay: i * 0.08, ease: "easeOut" },
  }),
};

/** Skip initial hidden state so SSR and no-JS users always see content. */
export const motionInitial = false as const;
