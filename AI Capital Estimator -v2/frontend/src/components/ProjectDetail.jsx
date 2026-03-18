import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

import { getProject } from "../api";
import Loading from "./Loading";

export default function ProjectDetail() {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        getProject(projectId)
            .then((data) => {
                setProject(data);
                setError(null);
            })
            .catch((err) => {
                setError(err.message);
            })
            .finally(() => setLoading(false));
    }, [projectId]);

    const chartData = useMemo(() => {
        if (!project) return [];
        return [
            { name: "Budget", amount: project.budget_usd },
            { name: "Actual", amount: project.actual_cost_usd },
        ];
    }, [project]);

    if (loading) return <Loading />;
    if (error) return <div className="error">{error}</div>;
    if (!project) return <div className="error">Project not found</div>;

    return (
        <div className="page">
            <header className="page-header">
                <Link to="/" className="link-button">
                    ← Back to portfolio
                </Link>
                <h1>{project.project_name}</h1>
                <p className="subtitle">{project.asset_type} • {project.location}</p>
            </header>

            <section className="grid">
                <div className="card">
                    <h2>Cost & schedule</h2>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={240}>
                            <BarChart data={chartData}>
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="amount" fill="#0b79ff" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <dl className="stats">
                        <div>
                            <dt>Budget</dt>
                            <dd>${project.budget_usd.toLocaleString()}</dd>
                        </div>
                        <div>
                            <dt>Actual</dt>
                            <dd>${project.actual_cost_usd.toLocaleString()}</dd>
                        </div>
                        <div>
                            <dt>% Complete</dt>
                            <dd>{Math.round(project.percent_complete * 100)}%</dd>
                        </div>
                        <div>
                            <dt>Risk score</dt>
                            <dd>{Math.round(project.risk_score * 100)}%</dd>
                        </div>
                        <div>
                            <dt>Schedule variance</dt>
                            <dd>{project.schedule_variance_days} days</dd>
                        </div>
                        <div>
                            <dt>Cost overrun</dt>
                            <dd>{Math.round(project.cost_overrun_pct * 100)}%</dd>
                        </div>
                    </dl>
                </div>

                <div className="card">
                    <h2>Risks</h2>
                    {project.risks && project.risks.length ? (
                        <table className="risk-table">
                            <thead>
                                <tr>
                                    <th>Type</th>
                                    <th>Probability</th>
                                    <th>Impact ($)</th>
                                    <th>Delay (days)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {project.risks.map((risk) => (
                                    <tr key={risk.risk_id}>
                                        <td>{risk.risk_type}</td>
                                        <td>{Math.round(risk.probability * 100)}%</td>
                                        <td>${risk.impact_cost.toLocaleString()}</td>
                                        <td>{risk.impact_days}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <p>No risks recorded for this project.</p>
                    )}

                    <h3>Recommendations</h3>
                    <ul>
                        {project.recommendations && project.recommendations.length ? (
                            project.recommendations.map((rec, idx) => <li key={idx}>{rec}</li>)
                        ) : (
                            <li>No recommended actions at this time.</li>
                        )}
                    </ul>
                </div>

                <div className="card">
                    <h2>Vendor</h2>
                    {project.vendor ? (
                        <dl className="stats">
                            <div>
                                <dt>Name</dt>
                                <dd>{project.vendor.vendor_name}</dd>
                            </div>
                            <div>
                                <dt>Reliability</dt>
                                <dd>{Math.round(project.vendor.reliability_score * 100)}%</dd>
                            </div>
                            <div>
                                <dt>Avg delay</dt>
                                <dd>{project.vendor.avg_delay_days} days</dd>
                            </div>
                        </dl>
                    ) : (
                        <p>No vendor information available.</p>
                    )}
                </div>
            </section>
        </div>
    );
}
