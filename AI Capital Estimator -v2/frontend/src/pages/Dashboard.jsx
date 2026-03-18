import { useEffect, useState } from "react";

import { getProjects, getPortfolioSummary } from "../api";
import Loading from "../components/Loading";
import PortfolioSummary from "../components/PortfolioSummary";
import ProjectTable from "../components/ProjectTable";
import AIChat from "../components/AIChat";

export default function Dashboard() {
    const [projects, setProjects] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        Promise.all([getProjects(), getPortfolioSummary()])
            .then(([projectsData, summaryData]) => {
                setProjects(projectsData);
                setSummary(summaryData);
                setError(null);
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <Loading />;
    if (error) return <div className="error">{error}</div>;

    return (
        <div className="page">
            <header className="page-header">
                <h1>Capex Project Copilot</h1>
                <p className="subtitle">Monitor portfolio health and get quick AI insights.</p>
            </header>

            <PortfolioSummary summary={summary} />

            <div className="grid">
                <div className="card">
                    <h2>Projects</h2>
                    <ProjectTable projects={projects} />
                </div>
                <AIChat />
            </div>
        </div>
    );
}
