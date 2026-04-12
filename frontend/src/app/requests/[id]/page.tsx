"use client";

import { useEffect, useState } from "react";
import { api, type ChangeRequest } from "@/lib/api";
import { useParams } from "next/navigation";

const STATUS_COLORS: Record<string, string> = {
  INITIATED: "bg-gray-100 text-gray-700",
  PROCESSING: "bg-yellow-100 text-yellow-700",
  AI_VERIFIED_PENDING_HUMAN: "bg-blue-100 text-blue-700",
  APPROVED: "bg-green-100 text-green-700",
  REJECTED: "bg-red-100 text-red-700",
  FAILED: "bg-red-100 text-red-900",
};

export default function RequestStatusPage() {
  const params = useParams<{ id: string }>();
  const [req, setReq] = useState<ChangeRequest | null>(null);
  const [error, setError] = useState("");

  const fetchRequest = async () => {
    try {
      const data = await api.getRequest(params.id);
      setReq(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load request");
    }
  };

  useEffect(() => {
    fetchRequest();
    // Poll every 3s while processing
    const interval = setInterval(() => {
      if (req?.status === "PROCESSING" || req?.status === "INITIATED") {
        fetchRequest();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [req?.status]);

  if (error) return <div className="text-red-600">{error}</div>;
  if (!req) return <div className="text-gray-400 animate-pulse">Loading…</div>;

  const status = req.status;

  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Request Status</h1>
        <span className={`text-xs font-medium px-3 py-1 rounded-full ${STATUS_COLORS[status] || "bg-gray-100"}`}>
          {status.replace(/_/g, " ")}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-gray-500">Request ID</dt><dd className="font-mono text-xs">{req.id}</dd></div>
        <div><dt className="text-gray-500">Customer</dt><dd>{req.customer_id}</dd></div>
        <div><dt className="text-gray-500">Change Type</dt><dd>{req.change_type}</dd></div>
        <div><dt className="text-gray-500">Submitted</dt><dd>{new Date(req.created_at).toLocaleString()}</dd></div>
        <div><dt className="text-gray-500">Old Value</dt><dd>{JSON.stringify(req.requested_old_value)}</dd></div>
        <div><dt className="text-gray-500">New Value</dt><dd>{JSON.stringify(req.requested_new_value)}</dd></div>
      </dl>

      {(status === "PROCESSING" || status === "INITIATED") && (
        <div className="text-sm text-yellow-700 bg-yellow-50 rounded-lg px-4 py-3">
          ⏳ AI pipeline is processing your document… This page refreshes automatically.
        </div>
      )}
      {status === "AI_VERIFIED_PENDING_HUMAN" && (
        <div className="text-sm text-blue-700 bg-blue-50 rounded-lg px-4 py-3">
          ✅ AI verification complete. Awaiting Checker review.{" "}
          <a href="/checker" className="underline font-medium">Open Checker Dashboard →</a>
        </div>
      )}
      {status === "APPROVED" && (
        <div className="text-sm text-green-700 bg-green-50 rounded-lg px-4 py-3">
          ✅ Request approved by Checker. Core banking system (RPS) has been updated.
        </div>
      )}
      {status === "REJECTED" && (
        <div className="text-sm text-red-700 bg-red-50 rounded-lg px-4 py-3">
          ❌ Request rejected by Checker.
        </div>
      )}
    </div>
  );
}
