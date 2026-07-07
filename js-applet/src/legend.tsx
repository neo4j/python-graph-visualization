import { useState } from "react";

// Mirrors the Legend/LegendSection/LegendEntry pydantic models in
// python-wrapper/src/neo4j_viz/options.py. Field names match the wire format verbatim, and a
// section is a discriminated union on `colorSpace` (discrete color boxes vs. a continuous gradient).
export type LegendEntry = { label: string; color: string };

export type DiscreteLegendSection = {
  title?: string;
  colorSpace: "discrete";
  entries?: LegendEntry[];
};

export type ContinuousLegendSection = {
  title?: string;
  colorSpace: "continuous";
  gradient?: string[];
  minValue?: string;
  maxValue?: string;
};

export type LegendSection = DiscreteLegendSection | ContinuousLegendSection;

export type LegendData = {
  nodes?: LegendSection | null;
  relationships?: LegendSection | null;
  visible?: boolean;
};

// Needle design tokens (set by the surrounding NeedleThemeProvider) so the legend tracks the
// light/dark theme and matches the other overlays. These are guaranteed to be defined wherever
// the widget renders — the whole NDL-based UI depends on them — so no fallbacks are needed.
const TOKENS = {
  background: "var(--theme-color-neutral-bg-default)",
  border: "var(--theme-color-neutral-border-weak)",
  text: "var(--theme-color-neutral-text-default)",
  mutedText: "var(--theme-color-neutral-text-weak)",
  shadow: "var(--theme-shadow-overlay)",
};

function hasContent(section?: LegendSection | null): section is LegendSection {
  if (!section) return false;
  if (section.colorSpace === "continuous") {
    return (section.gradient?.length ?? 0) > 0;
  }
  return (section.entries?.length ?? 0) > 0;
}

/** Whether the legend would render anything (used to decide whether to open the side panel). */
export function hasLegendContent(legend: LegendData): boolean {
  if (legend.visible === false) return false;
  return hasContent(legend.nodes) || hasContent(legend.relationships);
}

function GradientBar({ section }: { section: ContinuousLegendSection }) {
  const stops = section.gradient ?? [];
  return (
    <div>
      <div
        className="nvl-legend-gradient"
        style={{
          height: "12px",
          width: "100%",
          borderRadius: "3px",
          background: `linear-gradient(to right, ${stops.join(", ")})`,
        }}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "11px",
          color: TOKENS.mutedText,
          marginTop: "2px",
        }}
      >
        <span>{section.minValue ?? ""}</span>
        <span>{section.maxValue ?? ""}</span>
      </div>
    </div>
  );
}

function Section({
  heading,
  section,
}: {
  heading: string;
  section: LegendSection;
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{ marginTop: "6px" }}>
      <button
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "6px",
          width: "100%",
          padding: 0,
          background: "transparent",
          border: "none",
          color: TOKENS.mutedText,
          font: "inherit",
          fontSize: "11px",
          letterSpacing: "0.04em",
          marginBottom: "4px",
          cursor: "pointer",
        }}
      >
        <span>
          {/* Always show whether this section is for nodes or relationships; the field/property
              it was colored by is shown as a secondary qualifier. */}
          <span style={{ fontWeight: 700, textTransform: "uppercase" }}>{heading}</span>
          {section.title ? (
            <>
              <span aria-hidden> · </span>
              <span>{section.title}</span>
            </>
          ) : null}
        </span>
        <span aria-hidden>{collapsed ? "▸" : "▾"}</span>
      </button>
      {!collapsed &&
        (section.colorSpace === "continuous" ? (
          <GradientBar section={section} />
        ) : (
          (section.entries ?? []).map((entry, index) => (
            <div
              key={`${entry.label}-${index}`}
              className="nvl-legend-row"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "1px 0",
              }}
            >
              <span
                className="nvl-legend-color-box"
                style={{
                  display: "inline-block",
                  width: "12px",
                  height: "12px",
                  borderRadius: "3px",
                  flex: "0 0 auto",
                  backgroundColor: entry.color,
                  border: `1px solid ${TOKENS.border}`,
                }}
              />
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {entry.label}
              </span>
            </div>
          ))
        ))}
    </div>
  );
}

export function Legend({ legend }: { legend: LegendData }) {
  const [collapsed, setCollapsed] = useState(false);

  const sections: Array<[string, LegendSection]> = [];
  if (hasContent(legend.nodes)) sections.push(["Nodes", legend.nodes]);
  if (hasContent(legend.relationships))
    sections.push(["Relationships", legend.relationships]);

  if (legend.visible === false || sections.length === 0) {
    return null;
  }

  return (
    // A floating overlay in the graph's bottom-left corner, toggled by its own island button.
    <div
      className="nvl-legend"
      style={{
        position: "absolute",
        bottom: "12px",
        left: "12px",
        zIndex: 10,
        maxHeight: "calc(100% - 24px)",
        maxWidth: "240px",
        overflowY: "auto",
        padding: "8px 10px",
        borderRadius: "6px",
        border: `1px solid ${TOKENS.border}`,
        background: TOKENS.background,
        color: TOKENS.text,
        fontSize: "12px",
        lineHeight: 1.4,
        boxShadow: TOKENS.shadow,
      }}
    >
      <button
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          padding: 0,
          background: "transparent",
          border: "none",
          color: "inherit",
          font: "inherit",
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        <span>Legend</span>
        <span aria-hidden style={{ color: TOKENS.mutedText }}>
          {collapsed ? "▸" : "▾"}
        </span>
      </button>
      {!collapsed &&
        sections.map(([heading, section]) => (
          <Section key={heading} heading={heading} section={section} />
        ))}
    </div>
  );
}
