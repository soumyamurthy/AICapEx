import { useState } from "react";

import { askQuestion } from "../api";

export default function AIChat() {
    const [input, setInput] = useState("");
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (!input.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const res = await askQuestion(input.trim());
            setHistory((prev) => [
                ...prev,
                { question: input.trim(), answer: res.answer, insights: res.insights || [] },
            ]);
            setInput("");
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card">
            <h2>AI Assistant</h2>
            <form onSubmit={handleSubmit} className="ai-form">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about risk, budget, or recommendations..."
                    disabled={loading}
                />
                <button type="submit" disabled={loading || !input.trim()}>
                    {loading ? "Thinking..." : "Ask"}
                </button>
            </form>
            {error ? <div className="error">{error}</div> : null}
            <div className="ai-history">
                {history.map((entry, idx) => (
                    <div key={idx} className="ai-card">
                        <div className="ai-card__question">Q: {entry.question}</div>
                        <div className="ai-card__answer">
                            {entry.answer.split("\n").map((line, i) => (
                                <p key={i}>{line}</p>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
