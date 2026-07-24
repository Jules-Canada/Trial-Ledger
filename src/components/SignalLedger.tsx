import { scaleTime } from "d3-scale";
import { timeFormat } from "d3-time-format";
import type {
  Drug,
  EfficacyRecord,
  TimelineEvent,
  TimelineEventType,
  Trial,
} from "../types";
import { hasPrimaryEvidence } from "../types";
import { theme } from "../theme";

// ---- editorial narrative (per-drug copy; authoring lives here for now — see
// docs/design/single-drug-view.md "open design questions") --------------------
const NARRATIVE: Record<
  string,
  {
    headline: string;
    standfirst: string[];
    annotations: Record<string, string[]>;
    approvalCallout: string;
  }
> = {
  sotorasib: {
    headline: "Cracking the “undruggable” — then watching the signal narrow",
    standfirst: [
      "Sotorasib was the first medicine to hit KRAS G12C, and it won fast-track U.S. approval on single-arm data.",
      "When the randomized trial finally arrived, the benefit held — but narrowed, and overall survival never delivered.",
    ],
    annotations: {
      "codebreak-100": [
        "Striking response rate — but single-arm,",
        "with no comparator to beat.",
      ],
      "codebreak-200": [
        "Against real chemotherapy the edge held on",
        "PFS and response — yet survival showed none.",
      ],
    },
    approvalCallout: "Approved before the confirmatory Phase 3 even reported.",
  },
};

const EVENT_LABEL: Partial<Record<TimelineEventType, string>> = {
  first_in_human: "First-in-human",
  filing: "FDA filing (NDA)",
  accelerated_approval: "Accelerated approval",
  data_readout: "Phase 3 readout",
  regulatory_event: "Post-approval review",
};

// ---- geometry ---------------------------------------------------------------
const W = 1200;
const H = 706;
const SPINE_Y = 246;
const X0 = 90;
const X1 = 1110;

const fmtNode = timeFormat("%b %Y");

function parseDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

function formatValue(e: EfficacyRecord): string {
  if (e.value === null) return "—";
  if (e.unit === "%") return `${e.value}%`;
  if (e.unit === "months") return `${e.value} mo`;
  return `${e.value} ${e.unit}`;
}

function shortComparator(c?: string | null): string | null {
  if (!c) return null;
  const head = c.split("(")[0].trim().replace(/,+$/, "");
  return `vs ${head}`;
}

// ---- endpoint marker: ● met · ✕ missed · ◌ no formal bar --------------------
function Marker({
  cx,
  cy,
  met,
  primary,
}: {
  cx: number;
  cy: number;
  met: boolean | null;
  primary: boolean;
}) {
  const r = primary ? 8 : 6;
  if (met === true) return <circle cx={cx} cy={cy} r={r} fill={theme.met} />;
  if (met === false) {
    const sw = primary ? 3 : 2.4;
    return (
      <g stroke={theme.missed} strokeWidth={sw} strokeLinecap="round">
        <line x1={cx - r} y1={cy - r} x2={cx + r} y2={cy + r} />
        <line x1={cx - r} y1={cy + r} x2={cx + r} y2={cy - r} />
      </g>
    );
  }
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill="none"
      stroke={theme.noBar}
      strokeWidth={primary ? 2.4 : 2}
    />
  );
}

// ---- one trial's signal column ---------------------------------------------
function SignalGroup({
  trial,
  records,
  annotation,
  gx,
  gw,
}: {
  trial: Trial;
  records: EfficacyRecord[];
  annotation: string[];
  gx: number;
  gw: number;
}) {
  const markerX = gx + 18;
  const labelX = gx + 40;
  const valueX = gx + gw - 8;
  const rowY0 = 452;
  const step = 40;
  const randomized = records.some((r) => r.comparator);
  const subtitle = `PHASE ${trial.phases.join("/")} · ${
    randomized ? "RANDOMIZED, VS DOCETAXEL" : "SINGLE-ARM"
  }`;

  return (
    <g>
      <text
        x={gx + 4}
        y={396}
        fontFamily={theme.serif}
        fontSize={20}
        fontWeight={600}
        fill={theme.ink}
      >
        {trial.name}
      </text>
      <text
        x={gx + 4}
        y={416}
        fontFamily={theme.sans}
        fontSize={11}
        letterSpacing={0.8}
        fill={theme.muted}
      >
        {subtitle}
      </text>

      {records.map((e, i) => {
        const y = rowY0 + i * step;
        const primary = e.role === "primary";
        const comp = shortComparator(e.comparator);
        const valColor =
          e.met === false
            ? theme.missed
            : e.met === true
            ? theme.ink
            : theme.muted;
        return (
          <g key={e.endpoint}>
            <Marker cx={markerX} cy={y - 5} met={e.met} primary={primary} />
            <text
              x={labelX}
              y={y}
              fontFamily={theme.sans}
              fontSize={14}
              fontWeight={primary ? 600 : 400}
              fill={theme.ink}
            >
              {e.endpoint}
              {e.role === "exploratory" && (
                <tspan fill={theme.faint} fontSize={11}>
                  {"  exploratory"}
                </tspan>
              )}
            </text>
            <text
              x={valueX}
              y={y}
              textAnchor="end"
              fontFamily={theme.serif}
              fontSize={17}
              fontWeight={600}
              fill={valColor}
            >
              {formatValue(e)}
            </text>
            {/* source_type provenance: solid = primary evidence, dashed = topline */}
            <line
              x1={valueX - 26}
              y1={y + 5}
              x2={valueX}
              y2={y + 5}
              stroke={theme.faint}
              strokeWidth={1.5}
              strokeDasharray={hasPrimaryEvidence(e.sources) ? undefined : "3 2"}
            />
            {comp && (
              <text
                x={valueX}
                y={y + 17}
                textAnchor="end"
                fontFamily={theme.sans}
                fontSize={11}
                fill={theme.muted}
              >
                {comp}
              </text>
            )}
          </g>
        );
      })}

      {annotation.map((line, i) => (
        <text
          key={i}
          x={gx + 4}
          y={624 + i * 17}
          fontFamily={theme.serif}
          fontSize={13.5}
          fontStyle="italic"
          fill={theme.accent}
        >
          {line}
        </text>
      ))}
    </g>
  );
}

// ---- journey timeline -------------------------------------------------------
function JourneyTrack({ events }: { events: TimelineEvent[] }) {
  const dated = events.filter((e) => e.date) as (TimelineEvent & {
    date: string;
  })[];
  const x = scaleTime()
    .domain([new Date(2018, 4, 1), new Date(2024, 1, 1)])
    .range([X0, X1]);

  return (
    <g>
      <text
        x={56}
        y={190}
        fontFamily={theme.sans}
        fontSize={12}
        fontWeight={700}
        letterSpacing={1.5}
        fill={theme.ink}
      >
        THE JOURNEY
      </text>
      <line
        x1={X0}
        y1={SPINE_Y}
        x2={X1}
        y2={SPINE_Y}
        stroke={theme.rule}
        strokeWidth={2}
      />

      {dated.map((e) => {
        const px = x(parseDate(e.date));
        const isApproval = e.type === "accelerated_approval";
        const faint = e.type === "regulatory_event";
        const label = EVENT_LABEL[e.type] ?? e.type.replace(/_/g, " ");
        const dateStr = fmtNode(parseDate(e.date));
        const anchor = px > 1040 ? "end" : px < 130 ? "start" : "middle";

        if (isApproval) {
          return (
            <g key={e.type}>
              <text
                x={px}
                y={228}
                textAnchor="middle"
                fontFamily={theme.sans}
                fontSize={11}
                fill={theme.muted}
              >
                {dateStr}
              </text>
              <text
                x={px}
                y={SPINE_Y + 6}
                textAnchor="middle"
                fontFamily={theme.serif}
                fontSize={22}
                fill={theme.accent}
              >
                ★
              </text>
              <text
                x={px}
                y={SPINE_Y + 30}
                textAnchor="middle"
                fontFamily={theme.sans}
                fontSize={12.5}
                fontWeight={700}
                fill={theme.accent}
              >
                {label}
              </text>
              <text
                x={px}
                y={SPINE_Y + 45}
                textAnchor="middle"
                fontFamily={theme.serif}
                fontSize={12}
                fontStyle="italic"
                fill={theme.accent}
              >
                Approved before the confirmatory Phase 3 even reported.
              </text>
            </g>
          );
        }

        return (
          <g key={e.type} opacity={faint ? 0.45 : 1}>
            <circle
              cx={px}
              cy={SPINE_Y}
              r={4.5}
              fill={theme.ink}
              stroke={theme.ground}
              strokeWidth={2}
            />
            <text
              x={px}
              y={SPINE_Y - 16}
              textAnchor={anchor}
              fontFamily={theme.sans}
              fontSize={12.5}
              fontWeight={600}
              fill={theme.ink}
            >
              {label}
            </text>
            <text
              x={px}
              y={SPINE_Y + 20}
              textAnchor={anchor}
              fontFamily={theme.sans}
              fontSize={11}
              fill={theme.muted}
            >
              {dateStr}
            </text>
          </g>
        );
      })}
    </g>
  );
}

// ---- footer: legend + sources ----------------------------------------------
function Footer() {
  const y = 656;
  return (
    <g fontFamily={theme.sans} fontSize={11.5} fill={theme.muted}>
      <circle cx={60} cy={y - 4} r={5} fill={theme.met} />
      <text x={72} y={y}>
        met
      </text>
      <g stroke={theme.missed} strokeWidth={2.4} strokeLinecap="round">
        <line x1={118} y1={y - 9} x2={128} y2={y + 1} />
        <line x1={118} y1={y + 1} x2={128} y2={y - 9} />
      </g>
      <text x={136} y={y}>
        missed
      </text>
      <circle cx={205} cy={y - 4} r={5} fill="none" stroke={theme.noBar} strokeWidth={2} />
      <text x={217} y={y}>
        no formal bar
      </text>

      <line x1={305} y1={y - 4} x2={331} y2={y - 4} stroke={theme.faint} strokeWidth={1.5} />
      <text x={339} y={y}>
        peer-reviewed / registry
      </text>
      <line
        x1={488}
        y1={y - 4}
        x2={514}
        y2={y - 4}
        stroke={theme.faint}
        strokeWidth={1.5}
        strokeDasharray="3 2"
      />
      <text x={522} y={y}>
        press release
      </text>

      <text x={56} y={686} fontSize={11} fill={theme.faint}>
        Sources: CodeBreaK 100 — JCO 2022 (NCT03600883) · CodeBreaK 200 — Lancet
        2023 (NCT04303780) · Drugs@FDA. Efficacy figures human-verified, Jul 2026.
      </text>
    </g>
  );
}

// ---- top-level view ---------------------------------------------------------
export function SignalLedger({ drug }: { drug: Drug }) {
  const narrative = NARRATIVE[drug.id];
  const kicker = `${drug.identity.target} · NSCLC · ${drug.identity.sponsors
    .join(", ")
    .toUpperCase()}`;

  // signal groups in trial order (single-arm → randomized = evidence rigor)
  const groups = drug.trials.map((t) => ({
    trial: t,
    records: drug.efficacy.filter((e) => e.trial === t.id),
  }));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={narrative.headline}>
      <rect x={0} y={0} width={W} height={H} fill={theme.ground} />

      {/* header */}
      <text
        x={56}
        y={48}
        fontFamily={theme.sans}
        fontSize={12.5}
        fontWeight={700}
        letterSpacing={2}
        fill={theme.accent}
      >
        {kicker}
      </text>
      <text
        x={56}
        y={92}
        fontFamily={theme.serif}
        fontSize={33}
        fontWeight={600}
        fill={theme.ink}
      >
        {narrative.headline}
      </text>
      {narrative.standfirst.map((line, i) => (
        <text
          key={i}
          x={56}
          y={121 + i * 21}
          fontFamily={theme.sans}
          fontSize={14.5}
          fill={theme.muted}
        >
          {line}
        </text>
      ))}

      <JourneyTrack events={drug.timeline} />

      {/* signal section */}
      <line x1={56} y1={318} x2={W - 56} y2={318} stroke={theme.rule} strokeWidth={1} />
      <text
        x={56}
        y={352}
        fontFamily={theme.sans}
        fontSize={12}
        fontWeight={700}
        letterSpacing={1.5}
        fill={theme.ink}
      >
        THE SIGNAL
      </text>
      <text
        x={W - 56}
        y={352}
        textAnchor="end"
        fontFamily={theme.sans}
        fontSize={11.5}
        letterSpacing={1}
        fill={theme.muted}
      >
        EVIDENCE RIGOR →
      </text>
      <line x1={610} y1={384} x2={610} y2={592} stroke={theme.rule} strokeWidth={1} />

      <SignalGroup
        trial={groups[0].trial}
        records={groups[0].records}
        annotation={narrative.annotations[groups[0].trial.id] ?? []}
        gx={64}
        gw={520}
      />
      <SignalGroup
        trial={groups[1].trial}
        records={groups[1].records}
        annotation={narrative.annotations[groups[1].trial.id] ?? []}
        gx={636}
        gw={500}
      />

      <Footer />
    </svg>
  );
}
