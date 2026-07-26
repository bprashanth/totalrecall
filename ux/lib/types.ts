export type Cell = {
  cell_id: string;
  west: number;
  south: number;
  east: number;
  north: number;
  center_lat: number;
  center_lon: number;
  target_role: "target" | "context" | string;
  records: number;
  entities: number;
  effort_visits: number;
  effort_value: number;
};

export type SeasonalPoint = {
  month: number;
  median: number | null;
  p10: number | null;
  p90: number | null;
  cells: number;
};

export type AcousticPoint = {
  hour: string;
  frequency_band: number;
  value: number;
  support: number;
};

export type RestorationPoint = {
  metric: string;
  comparison_class: string;
  value: number;
  unit: string;
  plot_id: string;
};

export type DemoData = {
  schema_version: string;
  generated_from: string;
  site: {
    site_id: string;
    label: string;
    target_aoi: {
      geometry_role: string;
      geometry: PolygonGeometry;
      limitations: string[];
    };
    context_aoi: { bbox: number[] };
  };
  summary: {
    sources: number;
    records: number;
    mapped_records: number;
    entities: number;
    effort_rows: number;
    measurements: number;
    locations: number;
  };
  cells: Cell[];
  seasonal_ndvi: SeasonalPoint[];
  acoustic: AcousticPoint[];
  restoration: RestorationPoint[];
  sources: Array<{
    source_id: string;
    title: string;
    license: string;
    capabilities: string[];
  }>;
  limitations: string[];
};

export type PolygonGeometry = {
  type: "Polygon";
  coordinates: number[][][];
};

export type ResultEnvelope = {
  schema_version: "idli-result/1";
  result_id: string;
  status: string;
  question?: {
    original?: string;
    resolved?: string;
    bindings?: Record<string, unknown>;
  };
  answer?: {
    headline?: string;
    detail?: string;
    evidence_classes?: string[];
  };
  visuals?: VisualSpec[];
  limitations?: Array<{ code?: string; message?: string; severity?: string }>;
  actions?: Array<{
    action_id: string;
    label: string;
    capability_id: string;
    arguments: Record<string, unknown>;
  }>;
  audit?: {
    audit_id?: string;
    source_versions?: Array<{ source_id?: string; title?: string }>;
  };
};

export type ResultAction = NonNullable<ResultEnvelope["actions"]>[number];

export type GeoJsonGeometry = {
  type:
    | "Point"
    | "MultiPoint"
    | "LineString"
    | "MultiLineString"
    | "Polygon"
    | "MultiPolygon";
  coordinates: unknown;
};

export type GeoJsonFeature = {
  type: "Feature";
  id?: string | number;
  geometry: GeoJsonGeometry | null;
  properties?: Record<string, unknown> | null;
};

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

export type MapResultLayer = {
  layerId: string;
  label: string;
  evidenceClass: string;
  geometryType?: string;
  styleHint: Record<string, unknown>;
  data: GeoJsonFeatureCollection;
};

export type VisualSpec = {
  visual_id?: string;
  view?: string;
  visual_type?: string;
  title?: string;
  subtitle?: string;
  layers?: Array<{
    layer_id?: string;
    evidence_class?: string;
    geometry_type?: string;
    data_ref?: {
      handle?: string;
      media_type?: string;
      digest?: string;
    };
    legend?: {
      label?: string;
    };
    style_hint?: Record<string, unknown>;
  }>;
};

export type InlineResult = {
  envelope: ResultEnvelope;
  payloads: Record<string, unknown>;
};

export type AnalysisResponse = {
  mode: "live" | "preview";
  answer: string;
  focus: "site" | "records" | "seasonal" | "restoration" | "acoustic" | "effort";
  results: InlineResult[];
  audit_id?: string;
  note?: string;
};

export type MethodReading = {
  method: string;
  plain_summary: string;
  outcomes: string[];
  available: string[];
  missing: string[];
  cautions: string[];
  suggested_visual: "restoration" | "seasonal" | "acoustic" | "map";
};
