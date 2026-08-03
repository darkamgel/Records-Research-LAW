"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ProjectOut } from "@/types";

export default function ProjectsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");

  const { data } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiFetch<ProjectOut[]>("/projects"),
  });
  const create = useMutation({
    mutationFn: () => apiFetch("/projects", { method: "POST", body: { name, objective } }),
    onSuccess: () => {
      setName("");
      setObjective("");
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Research Projects</h1>
      <div className="card p-4 flex flex-wrap gap-2 items-end">
        <div className="flex-1 min-w-[180px]">
          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex-1 min-w-[240px]">
          <label className="label">Objective</label>
          <input className="input" value={objective} onChange={(e) => setObjective(e.target.value)} />
        </div>
        <button className="btn-primary" disabled={!name || create.isPending} onClick={() => create.mutate()}>
          Create project
        </button>
      </div>

      <div className="card divide-y divide-gray-100">
        {(data || []).map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`} className="block p-4 hover:bg-gray-50">
            <div className="font-medium text-brand-700">{p.name}</div>
            <div className="text-sm text-gray-500">{p.objective || "No objective set"}</div>
          </Link>
        ))}
        {data && data.length === 0 && <p className="p-4 text-gray-500">No projects yet.</p>}
      </div>
    </div>
  );
}
