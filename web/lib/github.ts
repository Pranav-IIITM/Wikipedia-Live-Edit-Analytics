// Server-only helpers for starting the pipeline workflow from the site's Sync button.
// GITHUB_DISPATCH_TOKEN: fine-grained token limited to this repository with "Actions: read and write".

const REPO = process.env.GITHUB_REPO ?? "Pranav-IIITM/Wikipedia-Live-Edit-Analytics";
const WORKFLOW = "pipeline.yml";
const API = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}`;

export type WorkflowRun = {
  status: string; // queued | in_progress | completed | ...
  conclusion: string | null; // success | failure | cancelled | ...
  created_at: string;
};

const ACTIVE = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);

export const isActive = (run: WorkflowRun | null) => !!run && ACTIVE.has(run.status);

export function syncConfigured(): boolean {
  return !!process.env.GITHUB_DISPATCH_TOKEN;
}

function headers() {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${process.env.GITHUB_DISPATCH_TOKEN}`,
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

export async function latestRun(): Promise<WorkflowRun | null> {
  const res = await fetch(`${API}/runs?per_page=1`, { headers: headers(), cache: "no-store" });
  if (!res.ok) throw new Error(`GitHub runs request failed: ${res.status}`);
  const body = (await res.json()) as { workflow_runs: WorkflowRun[] };
  const run = body.workflow_runs[0];
  // Only what the Sync button needs is passed on to the browser.
  return run ? { status: run.status, conclusion: run.conclusion, created_at: run.created_at } : null;
}

export async function dispatchRun(): Promise<void> {
  const res = await fetch(`${API}/dispatches`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ ref: "main" }),
    cache: "no-store",
  });
  if (res.status !== 204) throw new Error(`GitHub dispatch failed: ${res.status}`);
}
