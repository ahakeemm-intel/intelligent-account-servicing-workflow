"use client";

import { useEffect, useState } from "react";
import { api, type PendingItem } from "@/lib/api";
import Link from "next/link";

const REC_COLORS: Record<string, string> = {
  APPROVE: "text-green-700 bg-green-50 border-green-200",
  REJECT: "text-red-700 bg-red-50 border-red-200",
  FLAG_FOR_REVIEW: "text-yellow-700 bg-yellow-50 border-yellow-200",
};

export default function CheckerDashboard() {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getPending()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-400 animate-pulse">Loading pending requests…</div>;
  if (error) return <div className="text-red-600">{error}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Checker Dashboard</h1>
        <span className="text-sm text-gray-500">{items.length} pending review{items.length !== 1 ? "s" : ""}</span>
      </div>

      {items.length === 0 ? (
        <div className="bg-white rounded-xl shadow p-12 text-center text-gray-400">
          <p className="text-4xl mb-3">✓</p>
          <p>No requests pending review.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link
              key={item.id}
              href={`/checker/${item.id}`}
              className="block bg-white rounded-xl shadow hover:shadow-md transition-shadow p-5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-sm">{item.customer_id} — {item.change_type.replace(/_/g, " ")}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    New value: {Object.values(item.requested_new_value).join(", ")}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{new Date(item.created_at).toLocaleString()}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  {item.overall_confidence != null && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      {(item.overall_confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                  {item.ai_recommendation && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${REC_COLORS[item.ai_recommendation] || ""}`}>
                      AI: {item.ai_recommendation.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
