import { useState, useEffect, useRef, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { runsAPI } from '../api/client';
import RunCard from '../components/RunCard';
import toast from 'react-hot-toast';

interface RunListItem {
  id: number;
  topic: string;
  status: string;
  paper_word_count: number;
  created_at: string;
  completed_at: string | null;
}

interface ProgressStep {
  step: number;
  total: number;
  title: string;
  status: string;
  detail: string;
  ts: string;
}

const STEP_LABELS: Record<number, string> = {
  0: 'Initialising',
  1: 'Searching literature',
  2: 'Extracting knowledge',
  3: 'Generating hypothesis',
  4: 'Checking novelty',
  5: 'Writing experiment code',
  6: 'Running experiment',
  7: 'Reviewing code',
  8: 'Composing paper',
  9: 'Final quality check',
  10: 'Saving paper',
};

function StepIcon({ status }: { status: string }) {
  if (status === 'done') {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-green-100 text-green-600 text-sm font-bold">
        ✓
      </span>
    );
  }
  if (status === 'running') {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-primary-600">
        <span className="block h-3 w-3 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-gray-400 text-xs">
      ●
    </span>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [running, setRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [recentRuns, setRecentRuns] = useState<RunListItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchRuns();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await runsAPI.list(0, 5);
      setRecentRuns(res.data);
    } catch {
      // silently fail for recent runs
    } finally {
      setLoadingRuns(false);
    }
  };

  const startPolling = (runId: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await runsAPI.progress(runId);
        const data = res.data;
        setSteps(data.steps || []);

        if (data.status === 'completed') {
          stopPolling();
          setRunning(false);
          setActiveRunId(null);
          toast.success('Research complete!');
          navigate(`/runs/${runId}`);
        } else if (data.status === 'failed') {
          stopPolling();
          setRunning(false);
          setActiveRunId(null);
          toast.error('Pipeline failed');
          fetchRuns();
        }
      } catch {
        // ignore polling errors
      }
    }, 3000);
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const t = topic.trim();
    if (!t) {
      toast.error('Please enter a research topic');
      return;
    }

    setRunning(true);
    setSteps([]);
    try {
      const res = await runsAPI.create(t);
      const runId = res.data.id;
      setActiveRunId(runId);
      startPolling(runId);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Pipeline failed to start';
      toast.error(detail);
      setRunning(false);
      fetchRuns();
    }
  };

  // Determine current step index (highest step with status "running" or latest "done")
  const currentStep = steps.length > 0 ? Math.max(...steps.map((s) => s.step)) : 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* New Run Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 mb-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Start New Research</h1>
        <p className="text-gray-500 mb-6">
          Enter a research topic and the ARS pipeline will search, hypothesize, experiment, and
          write a full paper.
        </p>
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Efficient memory management in LLMs via Sparse Attention"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all"
            disabled={running}
          />
          <button
            type="submit"
            disabled={running}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            {running ? 'Running...' : 'Start Research'}
          </button>
        </form>
      </div>

      {/* Pipeline Progress */}
      {running && activeRunId && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">Pipeline Progress</h2>
          <p className="text-sm text-gray-400 mb-6">
            Run #{activeRunId} — This typically takes 5–30 minutes
          </p>

          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-2 mb-6">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(currentStep / 10) * 100}%` }}
            />
          </div>

          {/* Step list */}
          <ol className="space-y-3">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((stepNum) => {
              const stepData = [...steps].reverse().find((s) => s.step === stepNum);
              const status = stepData?.status || 'pending';
              const label = stepData?.title || STEP_LABELS[stepNum] || `Step ${stepNum}`;
              const detail = stepData?.detail || '';
              const isActive = status === 'running';

              return (
                <li
                  key={stepNum}
                  className={`flex items-center gap-3 ${
                    status === 'pending' ? 'opacity-40' : ''
                  } ${isActive ? 'font-medium' : ''}`}
                >
                  <StepIcon status={status} />
                  <span className="text-gray-700 text-sm">
                    {stepNum}. {label}
                  </span>
                  {detail && (
                    <span className="text-xs text-gray-400 ml-auto">{detail}</span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {/* Recent Runs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Recent Runs</h2>
          {recentRuns.length > 0 && (
            <a href="/history" className="text-sm text-primary-600 hover:underline">
              View all
            </a>
          )}
        </div>
        {loadingRuns ? (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        ) : recentRuns.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg mb-1">No research runs yet</p>
            <p className="text-sm">Start your first run above!</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {recentRuns.map((run) => (
              <RunCard
                key={run.id}
                id={run.id}
                topic={run.topic}
                status={run.status}
                paperWordCount={run.paper_word_count}
                createdAt={run.created_at}
                completedAt={run.completed_at}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
