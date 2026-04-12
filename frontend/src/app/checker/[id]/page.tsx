"use client";

import { useEffect, useState } from "react";
import { api, type ReviewDetail } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";

const FORGERY_COLORS: Record<string, string> = {
  PASS: "text-green-700 bg-green-50",
  FLAG: "text-yellow-700 bg-yellow-50",
  FAIL: "text-red-700 bg-red-50",
};

function ConfidenceBar({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-600">{label.replace(/_/g, " ")}</span>
        <span className="font-semibold">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CheckerReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState("");
  const [checkerId, setCheckerId] = useState("CHECKER_001");
  const [notes, setNotes] = useState("");
  const [acting, setActing] = useState(false);
  const [actionResult, setActionResult] = useState<"approved" | "rejected" | null>(null);

  useEffect(() => {
    api.getReviewDetail(params.id)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [params.id]);

  const handleDecision = async (action: "approve" | "reject") => {
    if (!checkerId.trim()) { alert("Please enter your Checker ID"); return; }
    setActing(true);
    try {
      if (action === "approve") {
        await api.approve(params.id, checkerId, notes || undefined);
        setActionResult("approved");
      } else {
        await api.reject(params.id, checkerId, notes || undefined);
        setActionResult("rejected");
      }
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Action failed");
      setActing(false);
    }
  };

  if (error) return <div className="text-red-600">{error}</div>;
  if (!detail) return <div className="text-gray-400 animate-pulse">Loading review…</div>;

  const { request, documents, verification, decisions } = detail;

  if (actionResult) {
    return (
      <div className="bg-white rounded-xl shadow p-10 text-center">
        <div className={`text-5xl mb-4 ${actionResult === "approved" ? "text-green-600" : "text-red-600"}`}>
          {actionResult === "approved" ? "✓" : "✗"}
        </div>
        <h2 className="text-xl font-semibold mb-2 capitalize">Request {actionResult}</h2>
        {actionResult === "approved" && (
          <p className="text-gray-500 text-sm mb-6">Mock RPS write-call executed. Customer record updated.</p>
        )}
        <button onClick={() => router.push("/checker")} className="bg-blue-700 text-white px-5 py-2 rounded-lg hover:bg-blue-800">
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  const alreadyDecided = decisions.length > 0 || !["AI_VERIFIED_PENDING_HUMAN"].includes(request.status);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Checker Review</h1>
        <button onClick={() => router.push("/checker")} className="text-sm text-blue-700 hover:underline">← Back</button>
      </div>

      {/* Request Summary */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">Change Request</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <div><dt className="text-gray-400 text-xs">Customer</dt><dd className="font-medium">{request.customer_id}</dd></div>
          <div><dt className="text-gray-400 text-xs">Change Type</dt><dd>{request.change_type}</dd></div>
          <div><dt className="text-gray-400 text-xs">Old Value</dt><dd>{JSON.stringify(request.requested_old_value)}</dd></div>
          <div><dt className="text-gray-400 text-xs">New Value</dt><dd className="font-medium text-blue-700">{JSON.stringify(request.requested_new_value)}</dd></div>
          <div><dt className="text-gray-400 text-xs">Submitted</dt><dd>{new Date(request.created_at).toLocaleString()}</dd></div>
          <div><dt className="text-gray-400 text-xs">Status</dt><dd>{request.status.replace(/_/g, " ")}</dd></div>
        </dl>
      </div>

      {/* AI Verification Results */}
      {verification ? (
        <div className="bg-white rounded-xl shadow p-5 space-y-4">
          <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide">AI Verification Results</h2>

          {/* AI Summary */}
          {verification.ai_summary && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-900">
              <p className="font-medium mb-1">AI Summary</p>
              <p>{verification.ai_summary}</p>
            </div>
          )}

          {/* Recommendation badge */}
          {verification.ai_recommendation && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500">AI Recommendation:</span>
              <span className={`text-sm font-semibold px-3 py-1 rounded-full border ${
                verification.ai_recommendation === "APPROVE" ? "bg-green-50 text-green-700 border-green-200" :
                verification.ai_recommendation === "REJECT" ? "bg-red-50 text-red-700 border-red-200" :
                "bg-yellow-50 text-yellow-700 border-yellow-200"
              }`}>
                {verification.ai_recommendation.replace(/_/g, " ")}
              </span>
            </div>
          )}

          {/* Confidence scores */}
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium">Confidence Scores</p>
            <div className="space-y-2">
              {Object.entries(verification.field_scores).map(([k, v]) => (
                <ConfidenceBar key={k} label={k} score={v} />
              ))}
            </div>
            <div className="mt-3 pt-3 border-t">
              <ConfidenceBar label="Overall Confidence" score={verification.overall_confidence} />
            </div>
          </div>

          {/* Forgery check */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Forgery Check:</span>
            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${FORGERY_COLORS[verification.forgery_check] || ""}`}>
              {verification.forgery_check}
            </span>
          </div>

          {/* Extracted fields */}
          <details className="text-xs">
            <summary className="cursor-pointer text-gray-500 hover:text-gray-700">Raw extracted fields</summary>
            <pre className="mt-2 bg-gray-50 rounded p-3 overflow-x-auto">
              {JSON.stringify(verification.extracted_fields, null, 2)}
            </pre>
          </details>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-700">
          ⏳ AI pipeline is still processing. Refresh the page in a moment.
        </div>
      )}

      {/* Documents */}
      {documents.length > 0 && (
        <div className="bg-white rounded-xl shadow p-5">
          <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">Documents</h2>
          {documents.map((doc) => (
            <div key={doc.id} className="text-sm border rounded-lg p-3">
              <p className="font-medium">{doc.original_filename}</p>
              <p className="text-xs text-gray-400 mt-0.5">Type: {doc.document_type} · FileNet Ref: <code>{doc.filenet_reference_id || "—"}</code></p>
              <p className="text-xs text-gray-400">Uploaded: {new Date(doc.uploaded_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Checker Decision Panel */}
      {!alreadyDecided ? (
        <div className="bg-white rounded-xl shadow p-5 space-y-4">
          <h2 className="font-semibold text-sm text-gray-500 uppercase tracking-wide">Your Decision</h2>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Checker ID</label>
            <input
              type="text"
              className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={checkerId}
              onChange={(e) => setCheckerId(e.target.value)}
              placeholder="Your staff ID"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
            <textarea
              className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes for the audit log…"
            />
          </div>
          <div className="flex gap-3 pt-1">
            <button
              onClick={() => handleDecision("approve")}
              disabled={acting}
              className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              ✓ Approve — Update RPS
            </button>
            <button
              onClick={() => handleDecision("reject")}
              disabled={acting}
              className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              ✗ Reject
            </button>
          </div>
          <p className="text-xs text-gray-400 text-center">
            The RPS write-call only executes upon Approve. Reject makes no changes to core banking.
          </p>
        </div>
      ) : (
        <div className="bg-gray-50 border rounded-xl p-5 text-sm text-gray-500">
          {decisions.length > 0 ? (
            <p>Decision recorded: <strong>{decisions[0].decision}</strong> by {decisions[0].checker_id} at {new Date(decisions[0].decided_at).toLocaleString()}</p>
          ) : (
            <p>Request status: {request.status.replace(/_/g, " ")} — no action available.</p>
          )}
        </div>
      )}
    </div>
  );
}
