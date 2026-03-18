import { useMemo } from "react";
import { Link } from "react-router-dom";

const formatCurrency = (value) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

const formatPercent = (value) => `${Math.round(value * 100)}%`;

const statusColor = (status) => {
    switch (status) {
        case "Delayed":
            return "--status-delayed";
        case "Active":
            return "--status-active";
        case "Completed":
            return "--status-completed";
        default:
            return "--status-planned";
    }
};

export default function ProjectTable({ projects }) {
    const rows = useMemo(
        () =>
            projects.map((p) => ({
                id: p.project_id,
                name: p.project_name,
                budget: p.budget_usd,
                actualCost: p.actual_cost_usd,
                complete: p.percent_complete,
                risk: p.risk_score,
                status: p.status,
            })),
        [projects]
    );

    return (
        <table className="project-table">
            <thead>
                <tr>
                    <th>Project</th>
                    <th>Budget</th>
                    <th>Actual</th>
                    <th>% Complete</th>
                    <th>Risk</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows.map((row) => (
                    <tr key={row.id}>
                        <td>
                            <Link to={`/projects/${row.id}`}>{row.name}</Link>
                        </td>
                        <td>{formatCurrency(row.budget)}</td>
                        <td>{formatCurrency(row.actualCost)}</td>
                        <td>{formatPercent(row.complete)}</td>
                        <td>{formatPercent(row.risk)}</td>
                        <td>
                            <span className={`status-pill ${statusColor(row.status)}`}>{row.status}</span>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
