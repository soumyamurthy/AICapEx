import { useMemo } from "react";

const formatCurrency = (value) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

export default function PortfolioSummary({ summary }) {
    const stats = useMemo(
        () => [
            { label: "Total projects", value: summary.total_projects },
            { label: "Total budget", value: formatCurrency(summary.total_budget) },
            { label: "Total actual", value: formatCurrency(summary.total_actual_cost) },
            { label: "% Delayed", value: `${Math.round(summary.percent_delayed)}%` },
            { label: "Avg cost overrun", value: `${(summary.avg_cost_overrun_pct * 100).toFixed(1)}%` },
            { label: "High risk projects", value: summary.high_risk_count },
        ],
        [summary]
    );

    return (
        <div className="summary-card">
            <h2>Portfolio overview</h2>
            <div className="summary-grid">
                {stats.map((s) => (
                    <div key={s.label} className="summary-item">
                        <div className="summary-title">{s.label}</div>
                        <div className="summary-value">{s.value}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
