"use client";

import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

const CHANGE_TYPES = [
  { value: "LEGAL_NAME", label: "Legal Name Change" },
  { value: "ADDRESS", label: "Address Update" },
  { value: "DOB", label: "Date of Birth Correction" },
  { value: "CONTACT", label: "Contact / Email Update" },
];

export default function IntakePage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    customer_id: "C001",
    change_type: "LEGAL_NAME",
    old_name: "Priya Sharma",
    new_name: "Priya Mehta",
  });
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "submitting" | "uploading" | "done" | "error">("idle");
  const [error, setError] = useState("");
  const [requestId, setRequestId] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a document to upload."); return; }
    setError("");
    setStatus("submitting");

    try {
      // Step 1: Create the change request
      const req = await api.createRequest({
        customer_id: form.customer_id,
        change_type: form.change_type,
        requested_old_value: { name: form.old_name },
        requested_new_value: { name: form.new_name },
      });
      setRequestId(req.id);
      setStatus("uploading");

      // Step 2: Upload document — pipeline runs in background
      await api.uploadDocument(req.id, "marriage_certificate", file);
      setStatus("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setStatus("error");
    }
  };

  if (status === "done") {
    return (
      <div className="bg-white rounded-xl shadow p-8 text-center">
        <div className="text-green-600 text-5xl mb-4">✓</div>
        <h2 className="text-xl font-semibold mb-2">Request Submitted Successfully</h2>
        <p className="text-gray-600 mb-1">Request ID: <code className="bg-gray-100 px-2 py-0.5 rounded text-sm">{requestId}</code></p>
        <p className="text-gray-500 text-sm mb-6">The AI pipeline is processing your document. The request will appear in the Checker Dashboard once complete.</p>
        <div className="flex gap-3 justify-center">
          <button onClick={() => router.push(`/requests/${requestId}`)} className="bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-800">
            Track Status
          </button>
          <button onClick={() => { setStatus("idle"); setRequestId(""); setFile(null); }} className="border px-4 py-2 rounded hover:bg-gray-50">
            New Request
          </button>
          <button onClick={() => router.push("/checker")} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900">
            Checker Dashboard →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">New Account Change Request</h1>
      <p className="text-gray-500 text-sm mb-6">Submit a customer account change and upload supporting documentation for AI-assisted verification.</p>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 space-y-5">
        {/* Customer ID */}
        <div>
          <label className="block text-sm font-medium mb-1">Customer ID</label>
          <input
            type="text"
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.customer_id}
            onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
            placeholder="e.g. C001"
            required
          />
        </div>

        {/* Change Type */}
        <div>
          <label className="block text-sm font-medium mb-1">Change Type</label>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.change_type}
            onChange={(e) => setForm({ ...form, change_type: e.target.value })}
          >
            {CHANGE_TYPES.map((ct) => (
              <option key={ct.value} value={ct.value}>{ct.label}</option>
            ))}
          </select>
        </div>

        {/* Old / New values */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Current Name (Old)</label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.old_name}
              onChange={(e) => setForm({ ...form, old_name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Requested Name (New)</label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.new_name}
              onChange={(e) => setForm({ ...form, new_name: e.target.value })}
              required
            />
          </div>
        </div>

        {/* Document upload */}
        <div>
          <label className="block text-sm font-medium mb-1">Supporting Document</label>
          <div
            className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            {file ? (
              <p className="text-sm text-green-700 font-medium">📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
            ) : (
              <p className="text-sm text-gray-400">Click to upload PDF, PNG, JPG, or TIFF (max 20 MB)</p>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>
        )}

        <button
          type="submit"
          disabled={status === "submitting" || status === "uploading"}
          className="w-full bg-blue-700 hover:bg-blue-800 disabled:bg-blue-300 text-white font-medium py-2.5 rounded-lg transition-colors"
        >
          {status === "submitting" ? "Creating request…" : status === "uploading" ? "Uploading document…" : "Submit Request"}
        </button>
      </form>
    </div>
  );
}
