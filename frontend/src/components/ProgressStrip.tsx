import { useJobs } from "../context/JobsContext";

export default function ProgressStrip() {
  const { jobs, dismiss } = useJobs();
  const entries = Object.values(jobs).filter((j) => j.status !== "done");

  if (entries.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 border-b bg-gray-50 px-4 py-2">
      {entries.map((job) => {
        const failed = job.status === "failed";
        const percent =
          job.total && job.total > 0 ? Math.round(((job.done ?? 0) / job.total) * 100) : 0;
        return (
          <div
            key={job.job_id}
            className={`flex items-center gap-3 rounded px-2 py-1 text-sm ${
              failed ? "bg-red-50 text-red-700" : "text-gray-700"
            }`}
          >
            <span className="w-24 shrink-0 font-mono text-xs">{job.job_id.slice(0, 8)}</span>
            {!failed && (
              <div className="h-2 flex-1 overflow-hidden rounded bg-gray-200">
                <div
                  className="h-full bg-gray-900 transition-all"
                  style={{ width: `${percent}%` }}
                />
              </div>
            )}
            <span className="flex-1 truncate">
              {failed ? (job.detail ?? "Ошибка") : (job.detail ?? job.status ?? "")}
            </span>
            {(failed || job.status === "cancelled") && (
              <button
                className="text-xs underline"
                onClick={() => dismiss(job.job_id)}
                type="button"
              >
                Скрыть
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
