import { useState, useEffect, useRef, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { runsAPI } from '../api/client';
import RunCard from '../components/RunCard';
import toast from 'react-hot-toast';

interface RunListItem {
  id: string;
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
  timestamp: string;
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
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-green-500/20 text-green-300 text-sm font-bold">
        ✓
      </span>
    );
  }
  if (status === 'running') {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#a1faff]/20 text-[#a1faff]">
        <span className="block h-3 w-3 animate-spin rounded-full border-2 border-[#a1faff] border-t-transparent" />
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-600/50 text-slate-400 text-xs">
      ●
    </span>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [vibe, setVibe] = useState('Deep Academic');
  const [commands, setCommands] = useState('');
  const [running, setRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
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

  const startPolling = (runId: string) => {
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
      const res = await runsAPI.create(t, vibe, commands.trim());
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
    <div className="max-w-4xl mx-auto px-4 py-8 text-[#f6f6fc]">
      {/* New Run Section */}
      <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-8 mb-8">
        <h1 className="text-2xl font-bold text-[#f6f6fc] mb-2">Start New Research</h1>
        <p className="text-[#aaabb0] mb-6">
          Enter a research topic, constraints, and vibe. The intent architect will verify claims using a multi-agent swarm.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Research Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Explain sparse attention mechanisms in LLMs"
              className="w-full px-4 py-3 border border-[#a1faff]/30 rounded-lg bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0] focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none transition-all"
              disabled={running}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Agent Vibe</label>
              <select
                value={vibe}
                onChange={(e) => setVibe(e.target.value)}
                disabled={running}
                className="w-full px-4 py-3 bg-slate-700/50 text-[#f6f6fc] border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] outline-none"
              >
                <option value="Deep Academic">Deep Academic</option>
                <option value="Fast-Paced Prototype">Fast-Paced Prototype</option>
                <option value="Adversarial Audit">Adversarial Audit</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Input Commands / Constraints</label>
              <input
                type="text"
                value={commands}
                onChange={(e) => setCommands(e.target.value)}
                placeholder="e.g., Focus only on causal modeling limits"
                className="w-full px-4 py-3 border border-[#a1faff]/30 rounded-lg bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0] focus:ring-2 focus:ring-[#a1faff] outline-none"
                disabled={running}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={running}
            className="mt-2 w-full py-3 bg-[#a1faff]/20 text-[#a1faff] rounded-lg font-medium hover:bg-[#a1faff]/30 disabled:opacity-50 transition-colors"
          >
            {running ? 'Swarm Initializing...' : 'Initialize Mission'}
          </button>
        </form>
      </div>

      {/* Pipeline Progress */}
      {running && activeRunId && (
        <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-8 mb-8">
          <h2 className="text-lg font-semibold text-[#f6f6fc] mb-1">Pipeline Progress</h2>
          <p className="text-sm text-[#aaabb0] mb-6">
            Run #{activeRunId} — This typically takes 5–30 minutes
          </p>

          {/* Progress bar */}
          <div className="w-full bg-slate-700/50 rounded-full h-2 mb-6 border border-[#a1faff]/20">
            <div
              className="bg-gradient-to-r from-[#a1faff] to-[#00f4fe] h-2 rounded-full transition-all duration-500"
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
                  <span className="text-[#f6f6fc] text-sm">
                    {stepNum}. {label}
                  </span>
                  {detail && (
                    <span className="text-xs text-[#aaabb0] ml-auto">{detail}</span>
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
          <h2 className="text-lg font-semibold text-[#f6f6fc]">Recent Runs</h2>
          {recentRuns.length > 0 && (
            <a href="/history" className="text-sm text-[#a1faff] hover:text-[#00f4fe] transition-colors">
              View all
            </a>
          )}
        </div>
        {loadingRuns ? (
          <div className="text-center py-8 text-[#aaabb0]">Loading...</div>
        ) : recentRuns.length === 0 ? (
          <div className="text-center py-12 text-[#aaabb0]">
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
