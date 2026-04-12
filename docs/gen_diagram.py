"""
Generate the IASW architecture diagram as a PNG using matplotlib.
Saved to docs/architecture.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

fig, ax = plt.subplots(1, 1, figsize=(22, 28))
ax.set_xlim(0, 22)
ax.set_ylim(0, 28)
ax.axis("off")
fig.patch.set_facecolor("#ffffff")

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "browser":   "#f0fdf4",  "browser_b":  "#16a34a",
    "api":       "#eff6ff",  "api_b":      "#3b82f6",
    "pipeline":  "#dbeafe",  "pipeline_b": "#2563eb",
    "services":  "#fff7ed",  "services_b": "#ea580c",
    "storage":   "#fdf4ff",  "storage_b":  "#a855f7",
    "obs":       "#fdf4ff",  "obs_b":      "#a855f7",
    "node":      "#f8fafc",  "node_b":     "#64748b",
    "hitl":      "#dc2626",  "hitl_b":     "#991b1b",
    "cond":      "#fbbf24",  "cond_b":     "#92400e",
    "arrow":     "#374151",
    "async":     "#3b82f6",
    "sync":      "#374151",
}

def box(ax, x, y, w, h, label, fc="#f8fafc", ec="#64748b", fontsize=8, bold=False,
        text_color="#1e293b", corner_r=0.3, extra=""):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0.05,rounding_size={corner_r}",
                          fc=fc, ec=ec, lw=1.5, zorder=3)
    ax.add_patch(rect)
    full = f"$\\bf{{{label}}}$\n{extra}" if bold else (f"{label}\n{extra}" if extra else label)
    ax.text(x + w/2, y + h/2, full, ha="center", va="center",
            fontsize=fontsize, color=text_color, wrap=True,
            multialignment="center", zorder=4)

def group(ax, x, y, w, h, title, fc, ec, fontsize=9):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.1,rounding_size=0.4",
                          fc=fc, ec=ec, lw=2, zorder=1, alpha=0.6)
    ax.add_patch(rect)
    ax.text(x + 0.15, y + h - 0.3, title, ha="left", va="top",
            fontsize=fontsize, fontweight="bold", color=ec, zorder=2)

def arrow(ax, x1, y1, x2, y2, label="", color="#374151", style="->", lw=1.5, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                linestyle=ls,
                                connectionstyle="arc3,rad=0.0"),
                zorder=5)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.1, my, label, fontsize=6.5, color=color,
                ha="left", va="center", zorder=6,
                bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))

# ─────────────────── TITLE ─────────────────────────────────────────────────
ax.text(11, 27.5, "IASW — Intelligent Account Servicing Workflow",
        ha="center", va="top", fontsize=16, fontweight="bold", color="#1e293b")
ax.text(11, 27.0, "System Architecture Diagram  |  Sync / Async boundaries indicated",
        ha="center", va="top", fontsize=9, color="#64748b", style="italic")

# ─────────────────── BROWSER (top) ─────────────────────────────────────────
group(ax, 0.5, 24.5, 21, 2.2, "Staff Browser", C["browser"], C["browser_b"])
box(ax,  1.0, 24.8, 5.5, 1.6, "Intake Form", fc=C["browser"], ec=C["browser_b"], fontsize=8, extra="page.tsx")
box(ax,  8.0, 24.8, 5.5, 1.6, "Request Status Tracker", fc=C["browser"], ec=C["browser_b"], fontsize=8, extra="requests/[id]/page.tsx")
box(ax, 15.0, 24.8, 6.0, 1.6, "Checker UI", fc=C["browser"], ec=C["browser_b"], fontsize=8, extra="checker/[id]/page.tsx")

# ─────────────────── API (second row) ──────────────────────────────────────
group(ax, 0.5, 19.5, 21, 4.7, "FastAPI Backend  :8000", C["api"], C["api_b"])
# Left column
box(ax,  1.0, 22.9, 4.5, 1.0, "POST /api/v1/requests", fc=C["node"], ec=C["api_b"], fontsize=7.5)
box(ax,  1.0, 21.7, 4.5, 1.0, "POST /requests/{id}/documents", fc=C["node"], ec=C["api_b"], fontsize=7, extra="→ 202 immediately")
box(ax,  1.0, 20.5, 4.5, 1.0, "GET /requests/{id}  (poll)", fc=C["node"], ec=C["api_b"], fontsize=7.5)
# Middle column
box(ax,  6.5, 22.9, 4.5, 1.0, "GET /checker/pending", fc=C["node"], ec=C["api_b"], fontsize=7.5)
box(ax,  6.5, 21.7, 4.5, 1.0, "GET /checker/requests/{id}", fc=C["node"], ec=C["api_b"], fontsize=7.5)
# Right column — HITL gate (red)
box(ax, 12.5, 22.2, 8.5, 1.6, "POST /checker/requests/{id}/approve\n⚠  HITL GATE",
    fc=C["hitl"], ec=C["hitl_b"], fontsize=8, text_color="white")
box(ax, 12.5, 20.5, 8.5, 1.0, "POST /checker/requests/{id}/reject", fc=C["node"], ec=C["api_b"], fontsize=7.5)

# ─────────────────── PIPELINE (async background) ───────────────────────────
group(ax, 0.5, 13.5, 13.5, 5.7, "Async Background Thread  (LangGraph Pipeline)", C["pipeline"], C["pipeline_b"])
# Nodes left-to-right
box(ax,  1.0, 16.8, 2.8, 1.8, "validation\n_agent", fc="#dbeafe", ec=C["pipeline_b"], fontsize=7.5, extra="RPS lookup\nfield match")
box(ax,  4.3, 16.8, 2.8, 1.8, "document\n_processor", fc="#dbeafe", ec=C["pipeline_b"], fontsize=7.5, extra="OCR + LLM\nextraction\nforgery heuristic")
box(ax,  7.6, 16.8, 2.8, 1.8, "confidence\n_scorer", fc="#dbeafe", ec=C["pipeline_b"], fontsize=7.5, extra="fuzzy + semantic\nper-field scores")
box(ax, 10.9, 16.8, 2.8, 1.8, "summary\n_generator", fc="#dbeafe", ec=C["pipeline_b"], fontsize=7.5, extra="LLM summary\n+ recommendation")
# Conditional diamond
diamond_x, diamond_y = 2.8, 15.0
dp = plt.Polygon([[diamond_x, diamond_y+0.7],[diamond_x+1.1, diamond_y+0.35],[diamond_x, diamond_y],[diamond_x-1.1, diamond_y+0.35]],
                 fc=C["cond"], ec=C["cond_b"], lw=1.5, zorder=3)
ax.add_patch(dp)
ax.text(diamond_x, diamond_y+0.35, "valid?", ha="center", va="center", fontsize=7, fontweight="bold", zorder=4)
# Pipeline arrows
arrow(ax, 2.4, 17.7, 2.4, 15.7, color=C["pipeline_b"])        # v_agent → diamond
arrow(ax, 3.9, 15.35, 4.3, 17.7, label="no errors", color=C["pipeline_b"])   # diamond → doc_proc
arrow(ax, 3.9, 15.35, 10.9+1.4, 17.7, label="failed", color="#ef4444")       # diamond → summary (error)
arrow(ax, 7.1, 17.7, 7.6, 17.7, color=C["pipeline_b"])         # doc → scorer
arrow(ax, 10.4, 17.7, 10.9, 17.7, color=C["pipeline_b"])       # scorer → summary

# Pipeline → DB
arrow(ax, 12.25, 16.8, 14.5, 15.5, label="write: AI_VERIFIED\n_PENDING_HUMAN", color=C["pipeline_b"])

# ─────────────────── SERVICES ──────────────────────────────────────────────
group(ax, 0.5, 8.5, 21, 4.7, "Services", C["services"], C["services_b"])
box(ax,  1.0, 10.5, 4.5, 2.3, "OCR Service", fc="#fff7ed", ec=C["services_b"], fontsize=8, extra="PyMuPDF (primary)\n→ Tesseract\n→ AWS Textract")
box(ax,  6.5, 10.5, 4.5, 2.3, "LLM Service", fc="#fff7ed", ec=C["services_b"], fontsize=8, extra="Ollama llama3 (local)\nor OpenAI GPT-4o\n(cloud)")
box(ax, 12.0, 10.5, 4.0, 2.3, "Mock RPS", fc="#fee2e2", ec=C["hitl"], fontsize=8, extra="write gated by\nchecker_decision_id\n(HITL constraint)")
box(ax, 17.0, 10.5, 4.0, 2.3, "FileNet Mock", fc="#fff7ed", ec=C["services_b"], fontsize=8, extra="filenet_store/\nlocal filesystem\n+ reference IDs")
# Service connector arrows from pipeline nodes
arrow(ax, 2.4, 16.8, 2.8, 12.8, label="lookup", color=C["services_b"])       # v_agent → RPS
arrow(ax, 5.7, 16.8, 3.25, 12.8, label="OCR", color=C["services_b"])         # doc_proc → OCR
arrow(ax, 5.7, 16.5, 8.75, 12.8, label="extract + forgery", color=C["services_b"])  # doc_proc → LLM
arrow(ax, 9.0, 16.8, 8.75, 12.8, label="semantic score", color=C["services_b"])  # scorer → LLM
arrow(ax, 12.25, 17.1, 8.75, 12.8, label="summary", color=C["services_b"])   # summary → LLM

# ─────────────────── STORAGE ───────────────────────────────────────────────
group(ax, 0.5, 3.5, 13.5, 4.7, "Storage", C["storage"], C["storage_b"])
box(ax,  1.0, 4.5, 5.5, 3.2, "PostgreSQL / SQLite\n(4 tables)", fc="#fdf4ff", ec=C["storage_b"], fontsize=8,
    extra="change_requests\ndocuments\nverification_results\nchecker_decisions")
box(ax,  7.5, 4.5, 5.5, 3.2, "filenet_store/\n(documents)", fc="#fdf4ff", ec=C["storage_b"], fontsize=8,
    extra="archived originals\nby request_id/\nFN-XXXXXX ref IDs")

# ─────────────────── OBSERVABILITY ─────────────────────────────────────────
group(ax, 15.0, 3.5, 6.5, 4.7, "Observability", C["obs"], C["obs_b"])
box(ax, 15.5, 5.5, 5.5, 2.0, "Loguru", fc="#fdf4ff", ec=C["obs_b"], fontsize=8, extra="file + console\nalways-on\nevery agent step")
box(ax, 15.5, 4.0, 5.5, 1.3, "Langfuse (optional)", fc="#fdf4ff", ec=C["obs_b"], fontsize=7.5, extra="LLM tracing when LANGFUSE_ENABLED=true")

# ─────────────────── BROWSER → API arrows ───────────────────────────────────
arrow(ax,  3.25, 24.8, 3.25, 23.9, label="POST (sync)", color=C["sync"])       # intake → create
arrow(ax,  3.5,  24.8, 2.8,  22.7, label="POST → 202", color=C["async"], ls="--")  # intake → upload
arrow(ax, 10.75, 24.8, 10.75, 23.9, label="GET (poll)", color=C["sync"])       # tracker → status
arrow(ax, 17.0,  24.8, 8.75,  23.9, label="GET pending", color=C["sync"])      # checker → pending
arrow(ax, 18.0,  24.8, 9.25,  22.7, label="GET detail", color=C["sync"])       # checker → detail
arrow(ax, 18.5,  24.8, 16.75, 23.8, label="POST approve", color=C["hitl"])     # checker → approve
arrow(ax, 18.5,  24.8, 16.75, 21.5, label="POST reject", color=C["sync"])      # checker → reject

# Upload → async pipeline
arrow(ax, 2.8, 21.7, 2.4, 19.0, label="async\nthread", color=C["async"], ls="--", lw=2)
arrow(ax, 3.5, 21.7, 19.0, 10.5, label="archive", color=C["services_b"], ls="--")

# FileNet → Storage
arrow(ax, 19.0, 10.5, 10.5, 7.7, label="store", color=C["storage_b"])

# HITL approve → DB + RPS
arrow(ax, 14.0, 22.2, 3.75, 7.7, color=C["hitl"], label="1. create\ndecision")
arrow(ax, 16.75, 22.2, 14.0, 12.8, color=C["hitl"], label="2. RPS write\n(checker_decision_id)")
arrow(ax, 14.0, 22.0, 3.75, 7.5, color=C["hitl"])                              # status=APPROVED
# Reject → DB
arrow(ax, 14.0, 20.5, 3.75, 7.3, color=C["sync"], label="REJECTED\n(no RPS write)")

# API reads → DB
arrow(ax,  3.25, 20.5, 3.25, 7.7, color=C["storage_b"], ls=":", label="read")
arrow(ax,  8.75, 20.5, 5.5,  7.7, color=C["storage_b"], ls=":", label="read")
arrow(ax,  9.25, 21.7, 5.5,  7.5, color=C["storage_b"], ls=":")

# Pipeline → Observability
arrow(ax, 13.5, 16.0, 17.5, 8.2, color=C["obs_b"], ls=":", label="logs")
arrow(ax, 13.5, 22.0, 17.5, 8.2, color=C["obs_b"], ls=":", label="logs")
arrow(ax, 8.75, 12.8, 17.5, 7.5, color=C["obs_b"], ls="--", label="optional\ntracing")

# ─────────────────── LEGEND ─────────────────────────────────────────────────
leg_x, leg_y = 0.6, 3.0
ax.plot([leg_x, leg_x+1.0], [leg_y, leg_y], color=C["sync"], lw=2)
ax.text(leg_x+1.1, leg_y, "Synchronous call", fontsize=7.5, va="center")
ax.plot([leg_x+4.5, leg_x+5.5], [leg_y, leg_y], color=C["async"], lw=2, ls="--")
ax.text(leg_x+5.6, leg_y, "Async / background", fontsize=7.5, va="center")
ax.plot([leg_x+9.5, leg_x+10.5], [leg_y, leg_y], color=C["hitl"], lw=2)
ax.text(leg_x+10.6, leg_y, "HITL-gated (human required)", fontsize=7.5, va="center")
ax.plot([leg_x+15.5, leg_x+16.5], [leg_y, leg_y], color=C["obs_b"], lw=1.5, ls=":")
ax.text(leg_x+16.6, leg_y, "Observability", fontsize=7.5, va="center")

plt.tight_layout(pad=0.5)
out = "/home/ahakeemm/trees/adnan/agentPrototype/docs/architecture.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
