import { useState } from "react";
import { api, ApiError } from "../api/client";
import { useJobs } from "../context/JobsContext";
import { ru } from "../i18n/ru";

export default function ProgressStrip() {
  const { jobs, dismiss } = useJobs();
  const [cancelling, setCancelling] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const entries = Object.values(jobs).filter((j) => j.status !== "done");
  if (!entries.length) return null;
  const cancel = async (id: string) => {
    setCancelling((prev) => [...prev, id]);
    setError(null);
    try {
      await api.post(`/jobs/${id}/cancel`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.network);
      setCancelling((prev) => prev.filter((value) => value !== id));
    }
  };
  return (
    <section className="job-strip" aria-label={ru.jobs.title}>
      {entries.map((job) => {
        const failed = job.status === "failed";
        const terminal = failed || job.status === "cancelled";
        const percent =
          job.total && job.total > 0
            ? Math.min(
                100,
                Math.max(0, Math.round(((job.done ?? 0) / job.total) * 100)),
              )
            : 0;
        return (
          <div
            className={`job-item ${failed ? "job-failed" : ""}`}
            key={job.job_id}
          >
            <div className="job-copy" role={failed ? "alert" : "status"}>
              <strong>
                {failed
                  ? ru.jobs.failed
                  : job.status === "cancelled"
                    ? ru.jobs.cancelled
                    : job.status === "queued"
                      ? ru.jobs.queued
                      : ru.jobs.running}
              </strong>
              <span>{job.detail ?? job.job_id.slice(0, 8)}</span>
              {failed && <small>{ru.jobs.retryHint}</small>}
            </div>
            {!terminal && (
              <div
                className="job-progress"
                role="progressbar"
                aria-label={ru.jobs.running}
                aria-valuenow={percent}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${percent}%` }} />
              </div>
            )}
            {terminal ? (
              <button className="text-link" onClick={() => dismiss(job.job_id)}>
                {ru.jobs.hide}
              </button>
            ) : (
              <button
                className="text-link"
                disabled={cancelling.includes(job.job_id)}
                onClick={() => cancel(job.job_id)}
              >
                {cancelling.includes(job.job_id)
                  ? ru.jobs.cancelling
                  : ru.common.cancel}
              </button>
            )}
          </div>
        );
      })}
      {error && (
        <p className="check-result failure" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
