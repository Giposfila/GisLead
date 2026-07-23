import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export interface JobEvent {
  job_id: string;
  campaign_id?: number | null;
  status?: string;
  done?: number;
  total?: number;
  detail?: string | null;
}

interface JobsContextValue {
  jobs: Record<string, JobEvent>;
  dismiss: (jobId: string) => void;
}

const JobsContext = createContext<JobsContextValue>({ jobs: {}, dismiss: () => {} });

export function JobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Record<string, JobEvent>>({});

  useEffect(() => {
    const source = new EventSource("/api/events");
    const onProgress = (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as JobEvent;
      setJobs((prev) => ({ ...prev, [data.job_id]: { ...prev[data.job_id], ...data } }));
    };
    source.addEventListener("job_progress", onProgress);
    return () => {
      source.removeEventListener("job_progress", onProgress);
      source.close();
    };
  }, []);

  const dismiss = (jobId: string) => {
    setJobs((prev) => {
      const next = { ...prev };
      delete next[jobId];
      return next;
    });
  };

  return <JobsContext.Provider value={{ jobs, dismiss }}>{children}</JobsContext.Provider>;
}

export function useJobs(): JobsContextValue {
  return useContext(JobsContext);
}
