import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export const COLORS = { conv: "#2563eb", ai: "#ea580c", both: "#7c3aed", neutral: "#64748b", critical: "#b91c1c", high: "#dc2626", medium: "#d97706", low: "#64748b", info: "#94a3b8" };

interface Datum { name: string; [k: string]: string | number | null }

/** Bar chart + a visually hidden data table so the numbers are available to assistive tech. */
export function SimpleBar({ title, data, series, height = 260, colorByName }: {
  title: string; data: Datum[]; series: { key: string; label: string; color: string }[]; height?: number; colorByName?: Record<string, string>;
}) {
  return (
    <figure aria-label={title} className="m-0">
      <div style={{ height }} aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.3} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} />
            <Tooltip />
            {series.length > 1 && <Legend />}
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[4, 4, 0, 0]} label={{ position: "top", fontSize: 11, fill: "#64748b", formatter: (v: unknown) => (typeof v === "number" && !Number.isInteger(v) ? v.toFixed(2) : (v as string)) }}>
                {colorByName && data.map((d) => <Cell key={d.name} fill={colorByName[d.name] ?? s.color} />)}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>{title}</caption>
        <thead><tr><th>Category</th>{series.map((s) => <th key={s.key}>{s.label}</th>)}</tr></thead>
        <tbody>{data.map((d) => <tr key={d.name}><th>{d.name}</th>{series.map((s) => <td key={s.key}>{d[s.key] ?? "Not available"}</td>)}</tr>)}</tbody>
      </table>
    </figure>
  );
}
