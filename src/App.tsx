import { useState, useRef, useCallback, useEffect } from "react";


// ─── API + normalized data ────────────────────────────────────────────────────

const API_BASE_URL = "https://oil-trace.onrender.com";

interface Vessel {
  id: string;
  name: string;
  mmsi: string;
  score: number;
  spatial: number;
  temporal: number;
  trajectory: number;
  behaviour: number;
  type: string;
  flag: string;
}

interface SpillData {
  spillId: string;
  confidence: number | null;
  area: string;
  centroid: string;
  detectedAt: string;
}

interface TimelineEvent {
  id: string;
  time: string;
  label: string;
  kind: "detection" | "historical" | "predicted" | "ais";
}

interface EvidenceData {
  vessel: Vessel;
  evidence: Array<{ label: string; value: string }>;
}

interface DetectionData {
  spill: SpillData;
  vessels: Vessel[];
  evidenceByVessel: Record<string, EvidenceData>;
  timeline: TimelineEvent[];
  raw: unknown;
}

type UploadState = "idle" | "dragging" | "loading" | "done" | "error-fail" | "error-no-spill";

const EMPTY_SPILL: SpillData = {
  spillId: "",
  confidence: null,
  area: "—",
  centroid: "—",
  detectedAt: "—",
};

const toRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};

const firstDefined = (...values: unknown[]) =>
  values.find(value => value !== undefined && value !== null && value !== "");

const asString = (value: unknown, fallback = "—") => {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return fallback;
};

const asNumber = (value: unknown, fallback = 0) => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const n = Number.parseFloat(value.replace("%", "").trim());
    if (Number.isFinite(n)) return n;
  }
  return fallback;
};

const asPercent = (value: unknown) => {
  const n = asNumber(value, 0);
  return n > 0 && n <= 1 ? n * 100 : n;
};

const formatValue = (value: unknown, suffix = "") => {
  if (value === undefined || value === null || value === "") return "—";
  return `${asString(value)}${suffix}`;
};

const pickNested = (root: unknown, keys: string[]) => {
  let current: unknown = root;
  for (const key of keys) {
    const obj = toRecord(current);
    current = firstDefined(obj[key], obj[key.toLowerCase()], obj[key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())]);
    if (current === undefined) return undefined;
  }
  return current;
};

const arrayFrom = (value: unknown): unknown[] => {
  if (Array.isArray(value)) return value;
  const obj = toRecord(value);
  const candidate = firstDefined(obj.items, obj.data, obj.results, obj.vessels, obj.suspect_vessels, obj.suspectVessels, obj.evidence);
  return Array.isArray(candidate) ? candidate : [];
};

const extractVesselArray = (root: unknown): unknown[] => {
  const obj = toRecord(root);
  const candidates = [
    obj.vessels,
    obj.suspect_vessels,
    obj.suspectVessels,
    pickNested(root, ["data", "vessels"]),
    pickNested(root, ["data", "suspect_vessels"]),
    pickNested(root, ["data", "suspectVessels"]),
    pickNested(root, ["spill", "vessels"]),
    pickNested(root, ["spill", "suspect_vessels"]),
    pickNested(root, ["spill", "suspectVessels"]),
  ];
  for (const candidate of candidates) {
    const list = arrayFrom(candidate);
    if (list.length) return list;
  }
  return [];
};

const normalizeVessel = (raw: unknown, index: number): Vessel => {
  const v = toRecord(raw);
  const score = asPercent(firstDefined(
    v.score, v.attribution_score, v.attributionScore, v.final_score, v.finalScore,
    v.confidence, v.attribution_confidence
  ));

  const component = (keys: string[]) => asPercent(firstDefined(...keys.map(k => v[k])));
  return {
    id: asString(firstDefined(v.id, v.vessel_id, v.vesselId, v.mmsi, `vessel-${index + 1}`)),
    name: asString(firstDefined(v.name, v.vessel_name, v.vesselName, v.ship_name, v.shipName), `Vessel ${index + 1}`),
    mmsi: asString(firstDefined(v.mmsi, v.MMSI, v.mmsi_number, v.mmsiNumber), "—"),
    score,
    spatial: component(["spatial", "spatial_score", "spatialScore", "spatial_proximity", "spatialProximity"]),
    temporal: component(["temporal", "temporal_score", "temporalScore", "temporal_correlation", "temporalCorrelation"]),
    trajectory: component(["trajectory", "trajectory_score", "trajectoryScore", "trajectory_match", "trajectoryMatch"]),
    behaviour: component(["behaviour", "behavior", "behaviour_score", "behavior_score", "behaviourScore", "behaviorScore"]),
    type: asString(firstDefined(v.type, v.vessel_type, v.vesselType, v.ship_type, v.shipType), "Unknown"),
    flag: asString(firstDefined(v.flag, v.flag_code, v.flagCode, v.country), "—"),
  };
};

const normalizeSpill = (root: unknown, spillId = ""): SpillData => {
  const obj = toRecord(root);
  const detections = Array.isArray(obj.detections) ? obj.detections : [];
  const firstDetection = detections.length > 0 ? detections[0] : undefined;
  const spill = toRecord(firstDefined(
    obj.spill,
    obj.spill_details,
    obj.spillDetails,
    obj.detection,
    firstDetection,
    obj.data,
    root,
  ));
  const confidence = firstDefined(
    spill.confidence, spill.confidence_score, spill.confidenceScore,
    spill.detection_confidence, spill.detectionConfidence, obj.confidence
  );
  const area = firstDefined(
    spill.area, spill.area_km2, spill.areaKm2, spill.spill_area, spill.spillArea,
    spill.area_sq_km, spill.areaSqKm
  );
  const centroid = firstDefined(
    spill.centroid, spill.centroid_coordinates, spill.centroidCoordinates,
    spill.location, spill.coordinates
  );
  const lat = firstDefined(spill.latitude, spill.lat, spill.centroid_latitude, spill.centroidLatitude);
  const lon = firstDefined(spill.longitude, spill.lon, spill.centroid_longitude, spill.centroidLongitude);
  const centroidValue = centroid ?? (lat !== undefined && lon !== undefined ? `${asString(lat)}°, ${asString(lon)}°` : undefined);

  return {
    spillId: asString(firstDefined(
      obj.spill_id,
      obj.spillId,
      spill.spill_id,
      spill.spillId,
      spill.spill_code,
      spill.spillCode,
      spill.id,
      spillId,
    ), spillId),
    confidence: confidence === undefined ? null : asPercent(confidence),
    area: formatValue(area, typeof area === "number" ? " km²" : ""),
    centroid: typeof centroidValue === "object" && centroidValue !== null
      ? (() => {
          const c = toRecord(centroidValue);
          return `${asString(firstDefined(c.lat, c.latitude))}, ${asString(firstDefined(c.lon, c.lng, c.longitude))}`;
        })()
      : asString(centroidValue),
    detectedAt: asString(firstDefined(
      spill.detected_at, spill.detectedAt, spill.detection_time, spill.detectionTime,
      spill.timestamp, obj.detected_at, obj.detectedAt, obj.timestamp
    )),
  };
};

const normalizeTimeline = (root: unknown, spill: SpillData): TimelineEvent[] => {
  const obj = toRecord(root);
  const raw = firstDefined(obj.timeline, obj.events, obj.history, pickNested(root, ["data", "timeline"]));
  const list = arrayFrom(raw);
  const normalized = list.map((item, index) => {
    const e = toRecord(item);
    const kindRaw = asString(firstDefined(e.kind, e.type, e.event_type, e.eventType), "detection").toLowerCase();
    const kind: TimelineEvent["kind"] =
      kindRaw.includes("pred") ? "predicted" :
      kindRaw.includes("hist") ? "historical" :
      kindRaw.includes("ais") ? "ais" : "detection";
    return {
      id: asString(firstDefined(e.id, `event-${index + 1}`)),
      time: asString(firstDefined(e.time, e.timestamp, e.datetime, e.date)),
      label: asString(firstDefined(e.label, e.name, e.description, e.event)),
      kind,
    };
  }).filter(e => e.time !== "—" || e.label !== "—");

  if (normalized.length) return normalized;
  return spill.detectedAt !== "—"
    ? [{ id: "detection", time: spill.detectedAt, label: "Sentinel-1 detection", kind: "detection" }]
    : [];
};

const normalizeDetection = (root: unknown, spillId = ""): DetectionData => {
  const spill = normalizeSpill(root, spillId);
  const vessels = extractVesselArray(root).map(normalizeVessel);
  const evidenceByVessel: Record<string, EvidenceData> = {};
  const obj = toRecord(root);
  const evidenceList = arrayFrom(firstDefined(
    obj.attribution, obj.attribution_evidence, obj.attributionEvidence, obj.evidence,
    pickNested(root, ["data", "attribution"]), pickNested(root, ["data", "evidence"])
  ));

  evidenceList.forEach((item, index) => {
    const e = toRecord(item);
    const vessel = normalizeVessel(firstDefined(e.vessel, e), index);
    evidenceByVessel[vessel.id] = {
      vessel,
      evidence: [
        ["spatial", "Spatial proximity"],
        ["temporal", "Temporal correlation"],
        ["trajectory", "Trajectory match"],
        ["behaviour", "Behaviour"],
      ].map(([key, label]) => ({
        label,
        value: formatValue(firstDefined(e[key], e[`${key}_score`], e[`${key}Score`], e[key === "behaviour" ? "behavior" : key]))
      })),
    };
  });

  return {
    spill,
    vessels,
    evidenceByVessel,
    timeline: normalizeTimeline(root, spill),
    raw: root,
  };
};

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

async function getJson(path: string): Promise<unknown | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    return await readJson(response);
  } catch {
    return null;
  }
}

async function enrichDetection(data: DetectionData): Promise<DetectionData> {
  if (!data.spill.spillId) return data;

  const needsVessels = data.vessels.length === 0;
  const needsMoreSpill = data.spill.area === "—" && data.spill.centroid === "—" && data.spill.detectedAt === "—";
  if (!needsVessels && !needsMoreSpill) return data;

  // The detection response may already contain all panels. If it only returns a spill_id,
  // try the most common REST resource shapes without making the UI dependent on one exact schema.
  const candidates = [
    `/api/spills/${encodeURIComponent(data.spill.spillId)}`,
    `/api/spills/${encodeURIComponent(data.spill.spillId)}/details`,
  ];

  for (const path of candidates) {
    const extra = await getJson(path);
    if (!extra) continue;
    const merged = normalizeDetection({ ...toRecord(data.raw), ...toRecord(extra), spill: firstDefined(toRecord(extra).spill, toRecord(data.raw).spill) }, data.spill.spillId);
    if (merged.vessels.length || merged.spill.area !== "—" || merged.spill.centroid !== "—" || merged.spill.detectedAt !== "—") {
      return {
        ...data,
        spill: merged.spill,
        vessels: merged.vessels.length ? merged.vessels : data.vessels,
        evidenceByVessel: Object.keys(merged.evidenceByVessel).length ? merged.evidenceByVessel : data.evidenceByVessel,
        timeline: merged.timeline.length ? merged.timeline : data.timeline,
      };
    }
  }

  return data;
}

// ─── SVG map geometry ─────────────────────────────────────────────────────────

const SPILL_POLYGON  = "M400,210 L430,198 L458,205 L472,225 L465,248 L440,260 L415,255 L398,238 Z";
const HIST_DRIFT     = "M435,228 L480,242 L525,258 L570,278 L610,295";
const PRED_DRIFT     = "M610,295 L648,312 L685,330 L715,352 L738,375";
const SELECTED_TRAJ  = "M390,170 L410,185 L428,200 L435,228";
const AIS_POS = [
  { x: 390, y: 170, id: 1 },
  { x: 520, y: 145, id: 2 },
  { x: 610, y: 210, id: 3 },
  { x: 340, y: 290, id: 4 },
];

// ─── Micro-components ─────────────────────────────────────────────────────────

const mono: React.CSSProperties = { fontFamily: "'JetBrains Mono', monospace" };
const sans: React.CSSProperties = { fontFamily: "'IBM Plex Sans', system-ui, sans-serif" };

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ ...mono, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase" as const, color: "var(--color-text-dim)", paddingBottom: 7, borderBottom: "1px solid var(--color-border-subtle)", marginBottom: 10 }}>
      {children}
    </div>
  );
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: ok ? "var(--color-green)" : "var(--color-red)", display: "inline-block", boxShadow: ok ? "0 0 5px #22c55e88" : "0 0 5px #ef444488" }} />
      <span style={{ ...mono, fontSize: 10, color: "var(--color-text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.07em" }}>{label}</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? "#ef4444" : value >= 60 ? "#f59e0b" : "#3a5a70";
  return (
    <div style={{ display: "flex", flexDirection: "column" as const, gap: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ ...mono, fontSize: 10, color: "var(--color-text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" as const }}>{label}</span>
        <span style={{ ...mono, fontSize: 11, color, fontWeight: 600 }}>{value}</span>
      </div>
      <div style={{ height: 3, background: "var(--color-border)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${value}%`, background: color, borderRadius: 2, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────

function UploadZone({ state, progress, onFile, onStateChange, errorMessage }: {
  state: UploadState;
  progress: number;
  onFile: (f: File) => void;
  onStateChange: (s: UploadState) => void;
  errorMessage?: string;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const open = () => fileRef.current?.click();
    window.addEventListener("oiltrace:open-upload", open);
    return () => window.removeEventListener("oiltrace:open-upload", open);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    onStateChange("idle");
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }, [onFile, onStateChange]);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); onStateChange("dragging"); };
  const handleDragLeave = () => onStateChange("idle");

  // ── Error banner
  if (state === "error-fail" || state === "error-no-spill") {
    const msg = state === "error-fail" ? (errorMessage || "Upload failed — check the API response and retry.") : "No spill detected in this image.";
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.4)",
          borderRadius: 4, padding: "9px 12px",
        }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0 }}>
            <path d="M7 1L13 12H1L7 1Z" stroke="#ef4444" strokeWidth="1.2" fill="rgba(239,68,68,0.15)" />
            <line x1="7" y1="5.5" x2="7" y2="8.5" stroke="#ef4444" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="7" cy="10.2" r="0.7" fill="#ef4444" />
          </svg>
          <span style={{ ...mono, fontSize: 10, color: "#ef4444", flex: 1 }}>{msg}</span>
          <button
            onClick={() => onStateChange("idle")}
            style={{ ...mono, fontSize: 9, color: "rgba(239,68,68,0.6)", background: "none", border: "none", cursor: "pointer", padding: "0 2px", letterSpacing: "0.06em" }}
          >
            ✕
          </button>
        </div>
        <button
          onClick={() => fileRef.current?.click()}
          style={{ ...mono, marginTop: 6, width: "100%", fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "var(--color-text-muted)", border: "1px solid var(--color-border)", background: "transparent", padding: "6px", borderRadius: 3, cursor: "pointer" }}
        >
          Try again
        </button>
        <input ref={fileRef} type="file" accept=".tif,.tiff,image/jpeg,image/png,.jpg,.jpeg,.png" style={{ display: "none" }} onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
      </div>
    );
  }

  // ── Loading state
  if (state === "loading") {
    return (
      <div style={{ marginBottom: 12, border: "1px solid var(--color-border)", borderRadius: 4, padding: "12px 14px", background: "rgba(0,212,255,0.03)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ ...mono, fontSize: 10, color: "var(--color-text-muted)", letterSpacing: "0.08em", textTransform: "uppercase" as const }}>Processing SAR image…</span>
          <span style={{ ...mono, fontSize: 10, color: "var(--color-cyan)" }}>{progress}%</span>
        </div>
        <div style={{ height: 3, background: "var(--color-border)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 2,
            width: `${progress}%`,
            background: "linear-gradient(90deg, #005577, #00d4ff)",
            transition: "width 0.3s ease",
          }} />
        </div>
        <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", marginTop: 6 }}>Running spill detection model · ETA ~12s</div>
      </div>
    );
  }

  // ── Idle / dragging drop zone
  const dragging = state === "dragging";
  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      style={{
        marginBottom: 12,
        border: `1px dashed ${dragging ? "var(--color-cyan)" : "var(--color-border)"}`,
        borderRadius: 4,
        padding: "14px 12px",
        background: dragging ? "rgba(0,212,255,0.05)" : "rgba(255,255,255,0.01)",
        textAlign: "center",
        transition: "all 0.15s",
        cursor: "pointer",
      }}
      onClick={() => fileRef.current?.click()}
    >
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" style={{ margin: "0 auto 6px" }}>
        <rect x="1" y="5" width="20" height="14" rx="2" stroke={dragging ? "var(--color-cyan)" : "#3a5070"} strokeWidth="1" />
        <path d="M8,11 L11,8 L14,11" stroke={dragging ? "var(--color-cyan)" : "#3a5070"} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="11" y1="8" x2="11" y2="15" stroke={dragging ? "var(--color-cyan)" : "#3a5070"} strokeWidth="1.2" strokeLinecap="round" />
        <path d="M4,5 L4,3 Q4,1 6,1 L16,1 Q18,1 18,3 L18,5" stroke={dragging ? "var(--color-cyan)" : "#3a5070"} strokeWidth="1" />
      </svg>
      <div style={{ ...mono, fontSize: 10, color: dragging ? "var(--color-cyan)" : "var(--color-text-muted)", letterSpacing: "0.07em", textTransform: "uppercase" as const }}>
        {dragging ? "Release to upload" : "Upload Sentinel-1 Image"}
      </div>
      <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", marginTop: 3 }}>
        Drag & drop · or click · .tif .tiff .jpg .jpeg .png
      </div>
      <input ref={fileRef} type="file" accept=".tif,.tiff,image/jpeg,image/png,.jpg,.jpeg,.png" style={{ display: "none" }}
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
    </div>
  );
}

// ─── Spill Details Card ───────────────────────────────────────────────────────

function SpillDetailsCard({ spill }: { spill: SpillData }) {
  return (
    <section>
      <SectionLabel>// Panel A · Spill Details</SectionLabel>
      <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid var(--color-border)", borderRadius: 4, padding: "10px 12px", marginBottom: 10 }}>
        <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", textTransform: "uppercase" as const, letterSpacing: "0.12em", marginBottom: 4 }}>
          Confidence
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
          <span style={{ ...mono, fontSize: 30, fontWeight: 600, color: "#00d4ff", lineHeight: 1 }}>
            {spill.confidence === null ? "—" : spill.confidence.toFixed(1)}
          </span>
          {spill.confidence !== null && <span style={{ ...mono, fontSize: 13, color: "rgba(0,212,255,0.55)" }}>%</span>}
        </div>
      </div>
      {[
        { label: "Spill ID", value: spill.spillId || "—" },
        { label: "Area", value: spill.area },
        { label: "Centroid", value: spill.centroid },
        { label: "Detection time", value: spill.detectedAt },
      ].map(({ label, value }) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, padding: "6px 0", borderBottom: "1px solid var(--color-border-subtle)" }}>
          <span style={{ ...mono, fontSize: 10, color: "var(--color-text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.06em", flexShrink: 0 }}>{label}</span>
          <span style={{ ...mono, fontSize: 11, color: "var(--color-text)", textAlign: "right" as const, overflowWrap: "anywhere" }}>{value}</span>
        </div>
      ))}
    </section>
  );
}

// ─── Map Legend Panel ─────────────────────────────────────────────────────────

function MapLegend() {
  const items = [
    {
      label: "Spill polygon",
      symbol: (
        <svg width="18" height="12"><rect x="1" y="1" width="16" height="10" rx="1" fill="rgba(29,10,0,0.85)" stroke="rgba(180,80,0,0.65)" strokeWidth="1" strokeDasharray="3 1.5" /></svg>
      ),
    },
    {
      label: "Centroid origin",
      symbol: (
        <svg width="18" height="12"><circle cx="9" cy="6" r="4" fill="none" stroke="#f59e0b" strokeWidth="1.2" /><circle cx="9" cy="6" r="1.8" fill="#f59e0b" /></svg>
      ),
    },
    {
      label: "Historical drift",
      symbol: (
        <svg width="18" height="12"><line x1="0" y1="6" x2="18" y2="6" stroke="#6b9fd4" strokeWidth="1.5" strokeDasharray="5 3" /></svg>
      ),
    },
    {
      label: "Predicted drift",
      symbol: (
        <svg width="18" height="12"><line x1="0" y1="6" x2="18" y2="6" stroke="#9b72cf" strokeWidth="1.5" strokeDasharray="3 4" /></svg>
      ),
    },
    {
      label: "Vessel markers",
      symbol: (
        <svg width="18" height="12"><circle cx="9" cy="6" r="4" fill="none" stroke="#5a7a8a" strokeWidth="1" /><circle cx="9" cy="6" r="2" fill="#4a6a7a" /></svg>
      ),
    },
    {
      label: "Selected trajectory",
      symbol: (
        <svg width="18" height="12"><circle cx="9" cy="6" r="4" fill="none" stroke="#00d4ff" strokeWidth="1.3" /><circle cx="9" cy="6" r="2" fill="#00d4ff" /></svg>
      ),
    },
  ];

  return (
    <div style={{
      position: "absolute", bottom: 14, left: 14,
      background: "rgba(8,12,18,0.9)", border: "1px solid var(--color-border)",
      borderRadius: 4, padding: "10px 14px", backdropFilter: "blur(8px)",
    }}>
      <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", letterSpacing: "0.13em", textTransform: "uppercase" as const, marginBottom: 8 }}>
        Map Legend
      </div>
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 5 }}>
        {items.map(({ label, symbol }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 18, flexShrink: 0 }}>{symbol}</div>
            <span style={{ ...mono, fontSize: 9, color: "var(--color-text-muted)" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Suspect Vessels Panel ────────────────────────────────────────────────────

function VesselsPanel({ vessels, selected, onSelect }: { vessels: Vessel[]; selected: Vessel | null; onSelect: (v: Vessel) => void }) {
  return (
    <section>
      <SectionLabel>// Panel B · Suspect Vessels</SectionLabel>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 10px 5px", borderBottom: "1px solid var(--color-border-subtle)", marginBottom: 4 }}>
        <span style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", width: 18 }}>#</span>
        <span style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", flex: 1 }}>VESSEL NAME</span>
        <span style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", width: 72 }}>MMSI</span>
        <span style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", width: 34, textAlign: "right" as const }}>SCORE</span>
      </div>
      {vessels.length === 0 ? (
        <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", padding: "12px 10px", border: "1px solid var(--color-border-subtle)", borderRadius: 3 }}>
          No suspect vessels returned yet.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" as const, gap: 2 }}>
          {vessels.map((v, i) => {
            const isSelected = selected?.id === v.id;
            const scoreColor = v.score >= 85 ? "var(--color-red)" : v.score >= 65 ? "var(--color-amber)" : "var(--color-text-muted)";
            return (
              <button key={v.id} onClick={() => onSelect(v)} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "7px 10px",
                background: isSelected ? "rgba(0,212,255,0.06)" : "rgba(255,255,255,0.015)",
                border: `1px solid ${isSelected ? "rgba(0,212,255,0.28)" : "var(--color-border-subtle)"}`,
                borderRadius: 3, cursor: "pointer", textAlign: "left" as const, transition: "all 0.12s", width: "100%",
              }}>
                <span style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", width: 18, flexShrink: 0 }}>#{i + 1}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ ...mono, fontSize: 11, color: isSelected ? "#fff" : "var(--color-text)", fontWeight: 500, whiteSpace: "nowrap" as const, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {v.name}
                  </div>
                  <div style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", marginTop: 1 }}>{v.type} · {v.flag}</div>
                </div>
                <span style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", width: 72, flexShrink: 0 }}>{v.mmsi}</span>
                <span style={{ ...mono, fontSize: 13, fontWeight: 600, color: scoreColor, width: 34, textAlign: "right" as const, flexShrink: 0 }}>
                  {v.score ? v.score.toFixed(1) : "—"}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ─── Attribution Evidence Panel ───────────────────────────────────────────────

function EvidencePanel({ vessel, evidence }: { vessel: Vessel; evidence?: EvidenceData }) {
  const scoreColor = vessel.score >= 85 ? "var(--color-red)" : "var(--color-amber)";
  const evidenceRows = [
    { label: "Spatial proximity", value: vessel.spatial },
    { label: "Temporal correlation", value: vessel.temporal },
    { label: "Trajectory match", value: vessel.trajectory },
    { label: "Behaviour", value: vessel.behaviour },
  ];

  return (
    <section>
      <SectionLabel>// Panel C · Attribution Evidence</SectionLabel>
      <div style={{ marginBottom: 10 }}>
        <div style={{ ...mono, fontSize: 12, color: "#fff", fontWeight: 600, letterSpacing: "0.02em" }}>{vessel.name}</div>
        <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", marginTop: 2, letterSpacing: "0.06em" }}>
          MMSI · {vessel.mmsi}
        </div>
      </div>

      <div style={{
        background: "rgba(0,0,0,0.35)", border: `1px solid ${scoreColor}33`,
        borderRadius: 4, padding: "10px 12px", marginBottom: 12,
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", textTransform: "uppercase" as const, letterSpacing: "0.12em" }}>Final Score</div>
          <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", marginTop: 2 }}>Attribution confidence</div>
        </div>
        <div style={{ textAlign: "right" as const }}>
          <span style={{ ...mono, fontSize: 32, fontWeight: 600, color: scoreColor, lineHeight: 1 }}>
            {vessel.score ? vessel.score.toFixed(1) : "—"}
          </span>
          {vessel.score > 0 && <div style={{ ...mono, fontSize: 8, color: scoreColor + "99", marginTop: 2, letterSpacing: "0.08em" }}>
            {vessel.score >= 85 ? "HIGH CONFIDENCE" : vessel.score >= 65 ? "MODERATE" : "LOW"}
          </div>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column" as const, gap: 10, marginBottom: 14 }}>
        {evidenceRows.map(row => (
          <ScoreBar key={row.label} label={row.label} value={row.value} />
        ))}
      </div>

      {evidence?.evidence?.length ? (
        <div style={{ borderTop: "1px solid var(--color-border-subtle)", paddingTop: 10, marginBottom: 12 }}>
          {evidence.evidence.map(item => (
            <div key={item.label} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: "5px 0" }}>
              <span style={{ ...mono, fontSize: 9, color: "var(--color-text-muted)" }}>{item.label}</span>
              <span style={{ ...mono, fontSize: 9, color: "var(--color-text)" }}>{item.value}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 8 }}>
        {(["[View trajectory]", "[View evidence]"] as const).map((label) => (
          <button key={label} style={{
            flex: 1, ...mono, fontSize: 9, letterSpacing: "0.08em",
            color: "var(--color-text-muted)", border: "1px solid var(--color-border)",
            background: "transparent", padding: "8px 4px", borderRadius: 3,
            cursor: "pointer", transition: "all 0.13s",
          }}>
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [spill, setSpill] = useState<SpillData>(EMPTY_SPILL);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [evidenceByVessel, setEvidenceByVessel] = useState<Record<string, EvidenceData>>({});
  const [fileName, setFileName] = useState("");

  const handleVesselClick = (v: Vessel) => setSelectedVessel(prev => prev?.id === v.id ? null : v);

  const handleFile = async (file: File) => {
    setUploadState("loading");
    setProgress(8);
    setErrorMessage("");
    setFileName(file.name);

    try {
      const formData = new FormData();
      formData.append("image", file, file.name);

      // Do not set Content-Type manually: the browser adds the multipart boundary.
      const response = await fetch(`${API_BASE_URL}/api/spills/detect`, {
        method: "POST",
        body: formData,
        headers: { Accept: "application/json" },
      });

      setProgress(70);

      const payload = await readJson(response);
      if (!response.ok) {
        const message = asString(firstDefined(
          toRecord(payload).detail,
          toRecord(payload).message,
          toRecord(payload).error
        ), `Detection failed (${response.status})`);
        throw new Error(message);
      }

      const initial = normalizeDetection(payload);
      if (!initial.spill.spillId) {
        setUploadState("error-no-spill");
        setProgress(100);
        setErrorMessage("The API returned successfully, but no spill_id was found in the response.");
        return;
      }

      setSpill(initial.spill);
      setVessels(initial.vessels);
      setEvidenceByVessel(initial.evidenceByVessel);
      setTimeline(initial.timeline);
      setSelectedVessel(initial.vessels[0] ?? null);

      setProgress(85);
      const enriched = await enrichDetection(initial);

      setSpill(enriched.spill);
      setVessels(enriched.vessels);
      setEvidenceByVessel(enriched.evidenceByVessel);
      setTimeline(enriched.timeline);
      setSelectedVessel(prev =>
        enriched.vessels.find(v => v.id === prev?.id) ??
        enriched.vessels[0] ??
        null
      );

      setProgress(100);
      setUploadState("done");
    } catch (error) {
      console.error("OILTRACE detection error:", error);
      setProgress(0);
      setUploadState("error-fail");
      setErrorMessage(error instanceof Error ? error.message : "Unable to connect to the OILTRACE API.");
    }
  };

  const tlineColor: Record<TimelineEvent["kind"], string> = {
    detection: "var(--color-cyan)",
    historical: "#6b9fd4",
    predicted: "#9b72cf",
    ais: "var(--color-amber)",
  };

  return (
    <div style={{
      ...sans, background: "var(--color-bg)", color: "var(--color-text)",
      height: "100%", display: "flex", flexDirection: "column" as const, overflow: "hidden",
    }}>

      {/* ── Header ── */}
      <header style={{
        background: "var(--color-surface)", borderBottom: "1px solid var(--color-border)",
        padding: "0 20px", height: 52, display: "flex", alignItems: "center", gap: 20,
        flexShrink: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <circle cx="11" cy="11" r="10" stroke="#00d4ff" strokeWidth="1.2" />
            <circle cx="11" cy="11" r="6" stroke="#00d4ff" strokeWidth="0.8" strokeDasharray="2 2" />
            <circle cx="11" cy="11" r="2.5" fill="#00d4ff" />
            {[[11,1,11,4],[11,18,11,21],[1,11,4,11],[18,11,21,11]].map(([x1,y1,x2,y2],i) => (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#00d4ff" strokeWidth="1.2" />
            ))}
          </svg>
          <div>
            <div style={{ ...mono, fontSize: 13, fontWeight: 600, color: "#fff", letterSpacing: "0.12em" }}>OILTRACE</div>
            <div style={{ ...mono, fontSize: 9, color: "var(--color-text-muted)", letterSpacing: "0.1em", textTransform: "uppercase" as const, marginTop: -1 }}>Spill Investigation</div>
          </div>
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 16, paddingLeft: 20, borderLeft: "1px solid var(--color-border)" }}>
          <StatusDot ok={uploadState === "done"} label="SAR Image" />
          <StatusDot ok={uploadState !== "error-fail"} label="API" />
          <StatusDot ok={uploadState !== "loading" && uploadState !== "error-fail"} label="Processing" />
          {uploadState === "done" && (
            <div style={{ ...mono, fontSize: 10, color: "var(--color-text-dim)", letterSpacing: "0.06em" }}>
              {fileName || "Detection complete"}
            </div>
          )}
        </div>
        {/* Header upload button */}
        <button
          onClick={() => { setUploadState("idle"); window.dispatchEvent(new CustomEvent("oiltrace:open-upload")); }}
          style={{
            ...mono, fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase" as const,
            color: "var(--color-cyan)", border: "1px solid rgba(0,212,255,0.35)",
            background: "rgba(0,212,255,0.06)", padding: "6px 14px", borderRadius: 3,
            cursor: "pointer", transition: "background 0.15s", whiteSpace: "nowrap" as const,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,212,255,0.12)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,212,255,0.06)")}
        >
          ↑ Upload / Select Image
        </button>
      </header>

      {/* ── Main body ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>

        {/* ── Map ── */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden", background: "#070e1a" }}>
          <img
            src="https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=1200&h=800&fit=crop&auto=format"
            alt="Satellite ocean base layer"
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: 0.28, filter: "saturate(0.3) brightness(0.6)" }}
          />
          {/* Grid */}
          <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.07 }} preserveAspectRatio="none">
            <defs>
              <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
                <path d="M60,0 L0,0 L0,60" fill="none" stroke="#4a8fa8" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>

          {/* Overlays */}
          <svg viewBox="0 0 800 480" preserveAspectRatio="xMidYMid meet" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
            <defs>
              <radialGradient id="sg" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stopColor="#1a0a00" stopOpacity="0.92" />
                <stop offset="65%"  stopColor="#0d0600" stopOpacity="0.75" />
                <stop offset="100%" stopColor="#050300" stopOpacity="0.4"  />
              </radialGradient>
              <filter id="glow"><feGaussianBlur stdDeviation="3" result="b" /><feComposite in="SourceGraphic" in2="b" operator="over" /></filter>
              <marker id="arrowH" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6b9fd4" /></marker>
              <marker id="arrowP" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#9b72cf" /></marker>
            </defs>

            {/* Spill polygon */}
            {spill.spillId && (
              <>
                <path d={SPILL_POLYGON} fill="url(#sg)" stroke="#3d1a00" strokeWidth="1.5" strokeDasharray="4 2" filter="url(#glow)" />
                <path d={SPILL_POLYGON} fill="none" stroke="rgba(180,80,0,0.22)" strokeWidth="5" />
              </>
            )}

            {/* Centroid */}
            {spill.spillId && (
              <>
                <circle cx="436" cy="228" r="8" fill="none" stroke="#f59e0b" strokeWidth="1.4" />
                <circle cx="436" cy="228" r="3" fill="#f59e0b" />
                <circle cx="436" cy="228" r="14" fill="none" stroke="rgba(245,158,11,0.15)" strokeWidth="1" />
                {[[436,218,436,224],[436,232,436,238],[426,228,432,228],[440,228,447,228]].map(([x1,y1,x2,y2],i) => (
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#f59e0b" strokeWidth="1" />
                ))}
                <text x="452" y="222" fill="#f59e0b" fontSize="9" fontFamily="JetBrains Mono" letterSpacing="0.05em">CENTROID</text>
              </>
            )}

            {/* Historical drift */}
            {spill.spillId && <path d={HIST_DRIFT} fill="none" stroke="#6b9fd4" strokeWidth="1.5" strokeDasharray="6 3" markerEnd="url(#arrowH)" opacity="0.85" />}
            {/* Predicted drift */}
            {spill.spillId && <path d={PRED_DRIFT} fill="none" stroke="#9b72cf" strokeWidth="1.5" strokeDasharray="3 5" markerEnd="url(#arrowP)" opacity="0.75" />}

            {/* Selected vessel trajectory */}
            {selectedVessel && spill.spillId && (
              <path d={SELECTED_TRAJ} fill="none" stroke="#00d4ff" strokeWidth="1.3" strokeDasharray="2 3" opacity="0.9" />
            )}

            {/* AIS vessels */}
            {vessels.slice(0, AIS_POS.length).map((vessel, index) => {
              const pos = AIS_POS[index];
              const isSel = selectedVessel?.id === vessel.id;
              return (
                <g key={vessel.id} style={{ cursor: "pointer" }} onClick={() => handleVesselClick(vessel)}>
                  {isSel && <circle cx={pos.x} cy={pos.y} r={16} fill="none" stroke="rgba(0,212,255,0.12)" strokeWidth="1" />}
                  <circle cx={pos.x} cy={pos.y} r={isSel ? 10 : 7} fill="none" stroke={isSel ? "#00d4ff" : "#5a7a8a"} strokeWidth={isSel ? 1.5 : 1} />
                  <circle cx={pos.x} cy={pos.y} r={isSel ? 4 : 2.8} fill={isSel ? "#00d4ff" : "#4a6a7a"} />
                  <text x={pos.x + 14} y={pos.y + 4} fill={isSel ? "#00d4ff" : "#3a5060"} fontSize="8" fontFamily="JetBrains Mono">
                    #{index + 1} {vessel.name.split(" ").pop()}
                  </text>
                </g>
              );
            })}
          </svg>

          <MapLegend />

          {/* Coord HUD */}
          <div style={{ position: "absolute", top: 12, right: 12, ...mono, fontSize: 10, color: "var(--color-text-dim)", background: "rgba(8,12,18,0.72)", border: "1px solid var(--color-border-subtle)", padding: "4px 10px", borderRadius: 3, letterSpacing: "0.06em" }}>
            {spill.centroid !== "—" ? spill.centroid : "NO DETECTION"}
          </div>
        </div>

        {/* ── Side Panels ── */}
        <div style={{
          width: 284, flexShrink: 0, background: "var(--color-surface)",
          borderLeft: "1px solid var(--color-border)", display: "flex", flexDirection: "column" as const, overflow: "hidden",
        }}>
          <div
            style={{ flex: 1, overflowY: "auto", padding: "14px 16px", display: "flex", flexDirection: "column" as const, gap: 20 }}
            className="hide-scrollbar"
          >
            {/* Upload zone — always visible at top of panels */}
            <section>
              <SectionLabel>// Image · Upload / Select</SectionLabel>
              <UploadZone state={uploadState} progress={Math.min(progress, 100)} onFile={handleFile} onStateChange={setUploadState} errorMessage={errorMessage} />
            </section>

            <SpillDetailsCard spill={spill} />
            <VesselsPanel vessels={vessels} selected={selectedVessel} onSelect={handleVesselClick} />
            {selectedVessel && <EvidencePanel vessel={selectedVessel} evidence={evidenceByVessel[selectedVessel.id]} />}
          </div>
        </div>
      </div>

      {/* ── Timeline ── */}
      <div style={{ background: "var(--color-surface)", borderTop: "1px solid var(--color-border)", padding: "10px 20px", flexShrink: 0, overflowX: "auto" }} className="hide-scrollbar">
        <div style={{ ...mono, fontSize: 9, color: "var(--color-text-dim)", textTransform: "uppercase" as const, letterSpacing: "0.12em", marginBottom: 8 }}>
          // Investigation Timeline
        </div>
        <div style={{ display: "flex", alignItems: "flex-start", minWidth: "max-content" }}>
          {timeline.map((ev, i) => (
            <div key={ev.id} style={{ display: "flex", flexDirection: "column" as const, alignItems: "center", width: 136 }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: 6, width: "100%" }}>
                <div style={{ flex: 1, height: 1, background: i === 0 ? "transparent" : "var(--color-border)" }} />
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: tlineColor[ev.kind], border: `2px solid ${tlineColor[ev.kind]}`, boxShadow: `0 0 5px ${tlineColor[ev.kind]}66`, flexShrink: 0 }} />
                <div style={{ flex: 1, height: 1, background: i === timeline.length - 1 ? "transparent" : "var(--color-border)" }} />
              </div>
              <div style={{ textAlign: "center" as const, padding: "0 4px" }}>
                <div style={{ ...mono, fontSize: 9, color: tlineColor[ev.kind] }}>{ev.time.split(" ")[1]}</div>
                <div style={{ ...sans, fontSize: 9, color: "var(--color-text-muted)", lineHeight: 1.35, marginTop: 2 }}>{ev.label}</div>
                <div style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", marginTop: 1 }}>{ev.time.split(" ")[0]}</div>
              </div>
            </div>
          ))}

          {/* Timeline legend */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: 16, paddingLeft: 16, borderLeft: "1px solid var(--color-border)", flexShrink: 0, alignSelf: "center", paddingBottom: 2 }}>
            {([["var(--color-cyan)","Detection"],["#6b9fd4","Historical"],["#9b72cf","Predicted"],["var(--color-amber)","AIS"]] as const).map(([c,l]) => (
              <div key={l} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: c }} />
                <span style={{ ...mono, fontSize: 8, color: "var(--color-text-dim)", textTransform: "uppercase" as const, letterSpacing: "0.08em" }}>{l}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { scrollbar-width: none; }
      `}</style>
    </div>
  );
}
