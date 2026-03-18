"""Simple AI assistant layer for the Capex Project Copilot."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .services import build_portfolio_summary, predict_risks
from .models import Project, Risk, Vendor


def _build_prompt(question: str, projects: List[Project], risks: List[Risk], vendors: List[Vendor]) -> str:
    summary = build_portfolio_summary(projects, risks, vendors)
    top_risky = sorted(projects, key=lambda p: p.risk_score, reverse=True)[:5]

    bullets = [
        f"Total projects: {summary['total_projects']}",
        f"Projects delayed: {summary['percent_delayed']:.1f}%",
        f"Average cost overrun: {summary['avg_cost_overrun_pct']*100:.1f}%",
        f"High risk projects (heuristic): {summary['high_risk_count']}",
        "Top risky projects: " + ", ".join([p.project_id for p in top_risky]),
    ]

    context = "\n".join([f"- {b}" for b in bullets])

    prompt = (
        "You are an AI project copilot for capital expenditure projects. "
        "Use the portfolio context provided to answer user questions with concise bullet insights. "
        "Mention specific project IDs where helpful.\n\n"
        "Portfolio summary:\n"
        f"{context}\n\n"
        f"User question: {question}\n"
        "Answer with 3-5 concise bullet points. "
        "If you provide recommendations, label them as 'Recommended action:'."
    )
    return prompt


def _mock_answer(question: str, projects: List[Project], risks: List[Risk], vendors: List[Vendor]) -> Dict[str, Any]:
    # Simple rule-based response if OpenAI key is not provided.
    summary = build_portfolio_summary(projects, risks, vendors)
    high_delay = [p for p in projects if predict_risks(p, vendors)["high_delay_risk"]]
    cost_overrun = [p for p in projects if predict_risks(p, vendors)["cost_overrun_risk"]]

    insights: List[str] = []
    q = question.lower()
    if "risk" in q or "delay" in q:
        insights.append(f"{len(high_delay)} projects are flagged with high delay risk based on vendor reliability.")
        if cost_overrun:
            insights.append(f"{len(cost_overrun)} projects are at risk of cost overruns (close to budget and <70% complete).")
    elif "budget" in q or "cost" in q:
        insights.append(f"Average cost overrun is {summary['avg_cost_overrun_pct']*100:.1f}% across the portfolio.")
        top_overrun = sorted(projects, key=lambda p: predict_risks(p, vendors)["cost_overrun_pct"], reverse=True)[:3]
        if top_overrun:
            insights.append(
                "Top overrun projects: "
                + ", ".join(f"{p.project_id} ({predict_risks(p, vendors)['cost_overrun_pct']*100:.0f}% over)" for p in top_overrun)
            )
    else:
        insights.append(
            f"Portfolio has {summary['total_projects']} projects; {summary['percent_delayed']:.1f}% are delayed."
        )
        insights.append(
            "Recommended action: Review high-risk projects and validate vendor delivery commitments."
        )

    # Add one generic recommendation
    if "recommend" in q or "suggest" in q:
        insights.append("Recommended action: For projects with supplier risk, consider alternate vendors or schedule buffer.")

    return {
        "answer": "\n".join(f"- {i}" for i in insights),
        "insights": insights,
    }


def ask(question: str, projects: List[Project], risks: List[Risk], vendors: List[Vendor]) -> Dict[str, Any]:
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return _mock_answer(question, projects, risks, vendors)

    try:
        import openai

        openai.api_key = openai_key
        prompt = _build_prompt(question, projects, risks, vendors)
        response = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[{"role": "system", "content": "You are a helpful AI copilot for capital expenditure projects."},
                      {"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        insights = [line.strip("- ") for line in text.splitlines() if line.strip()]
        return {"answer": text, "insights": insights}
    except Exception as e:
        return {
            "answer": "Could not reach OpenAI; returning heuristic insights.",
            "insights": [str(e)],
        }
