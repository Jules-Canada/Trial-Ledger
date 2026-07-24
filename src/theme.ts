// Editorial palette — FT / Our World in Data register. Restrained: two data
// colors + ink. See docs/design/single-drug-view.md.
export const theme = {
  ground: "#FCFBF7",
  ink: "#1A1A1A",
  muted: "#6B6B6B",
  faint: "#B7B4AC",
  rule: "#E4E0D6",
  met: "#1A8F5A", // endpoint met
  missed: "#D1495B", // endpoint missed
  noBar: "#9A9A9A", // single-arm / no formal bar
  accent: "#C25A2B", // editorial highlight (the "before P3" kink)
  serif: "'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif",
  sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
} as const;
