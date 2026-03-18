const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error: ${res.status} ${res.statusText} - ${text}`);
    }
    return res.json();
}

export async function getProjects() {
    return request("/projects");
}

export async function getProject(projectId) {
    return request(`/projects/${projectId}`);
}

export async function getPortfolioSummary() {
    return request("/portfolio/summary");
}

export async function askQuestion(question) {
    return request("/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
    });
}
