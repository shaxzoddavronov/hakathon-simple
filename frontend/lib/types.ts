// Mirror of backend/app/schemas/ui_spec.py. The discriminator on `type`
// must match the backend Literal values exactly.

export type ColumnDef = {
  key: string;
  label: string;
  dtype?: "int" | "float" | "string" | "bool" | "datetime" | "date";
  align?: "left" | "right" | "center";
};

export type TextOnly = { type: "text_only"; body_md: string };

export type KPI = {
  type: "kpi";
  label: string;
  value: number | string;
  unit?: string | null;
  delta?: number | null;
  sparkline?: number[];
};

export type BarSpec = {
  type: "bar";
  title: string;
  x: string;
  y: string[];
  data: Record<string, unknown>[];
  stacked?: boolean;
};

export type LineSpec = {
  type: "line";
  title: string;
  x: string;
  y: string[];
  data: Record<string, unknown>[];
};

export type PieSpec = {
  type: "pie";
  title: string;
  label: string;
  value: string;
  data: Record<string, unknown>[];
};

export type TableSpec = {
  type: "table";
  columns: ColumnDef[];
  rows: unknown[][];
};

export type GridChild = { span: number; spec: UISpec };

export type Dashboard = {
  type: "dashboard";
  title: string;
  children: GridChild[];
};

export type UISpec =
  | TextOnly
  | KPI
  | BarSpec
  | LineSpec
  | PieSpec
  | TableSpec
  | Dashboard;

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  ui_spec?: UISpec | null;
  sql?: string | null;
};
