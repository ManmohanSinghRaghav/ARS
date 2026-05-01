import { useState, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { runsAPI, discoveryAPI } from '../api/client';
import RunCard from '../components/RunCard';
import { Activity, Loader2, Sparkles, ChevronRight, X, Zap, BookOpen, Swords } from 'lucide-react';
import toast from 'react-hot-toast';

interface RunListItem {
  id: string;
  topic: string;
  status: string;
  paper_word_count: number;
  created_at: string;
  completed_at: string | null;
}

interface TopicSuggestion {
  title: string;
  angle: string;
  vibe: 'Deep Academic' | 'Rapid Synthesis' | 'Adversarial Audit';
}

const VIBE_ICONS: Record<string, JSX.Element> = {
  'Deep Academic': <BookOpen size={13} />,
  'Rapid Synthesis': <Zap size={13} />,
  'Adversarial Audit': <Swords size={13} />,
};

const VIBE_COLORS: Record<string, string> = {
  'Deep Academic': 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300',
  'Rapid Synthesis': 'border-amber-500/50 bg-amber-500/10 text-amber-300',
  'Adversarial Audit': 'border-red-500/50 bg-red-500/10 text-red-300',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [vibe, setVibe] = useState('Deep Academic');
  const [execEnabled, setExecEnabled] = useState(true);
  const [running, setRunning] = useState(false);
  const [recentRuns, setRecentRuns] = useState<RunListItem[]>([]);
  const [isRefining, setIsRefining] = useState(false);
  const [suggestions, setSuggestions] = useState<TopicSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => { fetchRuns(); }, []);

  const fetchRuns = async () => {
    try {
      const res = await runsAPI.list(0, 5);
      setRecentRuns(res.data);
    } catch { /* silent */ }
  };

  const handleSuggest = async () => {
    if (!topic.trim()) return toast.error('Enter a seed idea first');
    setIsRefining(true);
    setSuggestions([]);
    try {
      const res = await discoveryAPI.suggest(topic.trim(), vibe);
      const data = res.data;
      if (data.suggestions && data.suggestions.length > 0) {
        setSuggestions(data.suggestions);
        setShowSuggestions(true);
      } else {
        toast.error('No suggestions returned — try a more specific seed');
      }
    } catch {
      toast.error('Topic optimizer offline — check backend');
    } finally {
      setIsRefining(false);
    }
  };

  const applySuggestion = (s: TopicSuggestion) => {
    setTopic(s.title);
    setVibe(s.vibe);
    setShowSuggestions(false);
    toast.success('Topic & vibe applied!');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return toast.error('Enter a research topic');
    setRunning(true);
    try {
      const res = await runsAPI.create(topic.trim(), vibe, '', execEnabled);
      toast.success('Mission Initialized: Swarm Launching');
      navigate(`/runs/${res.data.id}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'System fault');
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-50 p-6 lg:p-12">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Left Column: Command Center */}
        <div className="lg:col-span-7 space-y-8">
          <div className="glass-card p-8 space-y-6">
            <header>
              <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                ARS Command Center
              </h1>
              <p className="text-slate-400 mt-2">Initialize autonomous research swarms with multi-agent consensus.</p>
            </header>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Topic Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Research Topic</label>
                  <button
                    type="button"
                    onClick={handleSuggest}
                    disabled={isRefining || running}
                    className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 hover:text-indigo-300 transition-all disabled:opacity-40"
                  >
                    {isRefining
                      ? <><Loader2 size={11} className="animate-spin" /> Generating...</>
                      : <><Sparkles size={11} /> Optimize Topic</>
                    }
                  </button>
                </div>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="input-glass text-base resize-none"
                  rows={3}
                  placeholder="Define your research intent... (e.g. 'Effect of sleep on cognitive function')"
                  disabled={running}
                />
              </div>

              {/* AI Suggestions Modal */}
              {showSuggestions && suggestions.length > 0 && (
                <div className="relative rounded-2xl border border-[#a1faff]/20 bg-slate-900/80 backdrop-blur-xl overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                    <div className="flex items-center gap-2">
                      <Sparkles size={13} className="text-[#a1faff]" />
                      <span className="text-[10px] font-black uppercase tracking-widest text-[#a1faff]">
                        AI Suggestions — Pick One
                      </span>
                    </div>
                    <button type="button" onClick={() => setShowSuggestions(false)} className="text-slate-500 hover:text-slate-300 transition-all">
                      <X size={14} />
                    </button>
                  </div>
                  <div className="p-3 space-y-2">
                    {suggestions.map((s, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => applySuggestion(s)}
                        className="w-full text-left p-3 rounded-xl border border-white/5 bg-slate-800/50 hover:bg-slate-700/50 hover:border-[#a1faff]/30 transition-all group"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-white leading-snug group-hover:text-[#a1faff] transition-colors">
                              {s.title}
                            </p>
                            <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{s.angle}</p>
                          </div>
                          <div className="shrink-0 flex flex-col items-end gap-2">
                            <span className={`flex items-center gap-1 text-[9px] font-black uppercase px-2 py-0.5 rounded-full border ${VIBE_COLORS[s.vibe] || 'border-slate-700 text-slate-400'}`}>
                              {VIBE_ICONS[s.vibe]} {s.vibe}
                            </span>
                            <ChevronRight size={14} className="text-slate-600 group-hover:text-[#a1faff] transition-colors" />
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Mode + Vibe */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Simulation Mode</label>
                  <div
                    onClick={() => !running && setExecEnabled(!execEnabled)}
                    className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all ${execEnabled ? 'border-indigo-500/50 bg-indigo-500/10' : 'border-slate-700 bg-slate-800/50'}`}
                  >
                    <span className="text-sm font-medium">{execEnabled ? 'Live Sandbox' : 'Theoretical'}</span>
                    <div className={`w-10 h-5 rounded-full relative transition-colors ${execEnabled ? 'bg-indigo-500' : 'bg-slate-600'}`}>
                      <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${execEnabled ? 'right-1' : 'left-1'}`} />
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Cognitive Vibe</label>
                  <select
                    value={vibe}
                    onChange={(e) => setVibe(e.target.value)}
                    className="input-glass bg-slate-800/50"
                    disabled={running}
                  >
                    <option>Deep Academic</option>
                    <option>Adversarial Audit</option>
                    <option>Rapid Synthesis</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={running}
                className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-3"
              >
                {running ? (
                  <>
                    <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Swarm Initializing...
                  </>
                ) : 'Launch Autonomous Swarm'}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Mission Logs */}
        <div className="lg:col-span-5 space-y-6">
          <h2 className="text-lg font-bold text-slate-300">Mission History</h2>
          <div className="space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto pr-2 custom-scrollbar">
            {recentRuns.map((run) => (
              <RunCard
                key={run.id}
                id={run.id}
                topic={run.topic}
                status={run.status}
                paperWordCount={run.paper_word_count}
                createdAt={run.created_at}
              />
            ))}
            {recentRuns.length === 0 && (
              <div className="p-8 text-center glass-card border-dashed border-slate-700">
                <Activity size={24} className="text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500 text-sm italic">No missions logged in history.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
