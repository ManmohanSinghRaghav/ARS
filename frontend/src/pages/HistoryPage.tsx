import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { runsAPI } from '../api/client';

interface RunListItem {
  id: string;
  topic: string;
  status: string;
  paper_word_count: number;
  created_at: string;
  completed_at: string | null;
}

type SortOption = 'date-desc' | 'date-asc' | 'status';
type FilterOption = 'all' | 'running' | 'completed' | 'failed';

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>('date-desc');
  const [filterBy, setFilterBy] = useState<FilterOption>('all');
  const [pollInterval, setPollInterval] = useState<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchRuns();
    
    // Set up polling to refresh runs every 5 seconds
    const interval = setInterval(fetchRuns, 5000);
    setPollInterval(interval);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const fetchRuns = async () => {
    try {
      setError(null);
      const res = await runsAPI.list(0, 100);
      const allRuns = res.data || [];
      setRuns(allRuns);
    } catch (err) {
      setError('Failed to load synthesis history. Please try again.');
      console.error('Failed to fetch runs:', err);
    } finally {
      setLoading(false);
    }
  };

  const getFilteredRuns = () => {
    let filtered = [...runs];
    
    // Apply filter
    if (filterBy !== 'all') {
      filtered = filtered.filter(run => {
        if (filterBy === 'running') return run.status === 'running';
        if (filterBy === 'completed') return run.status === 'completed';
        if (filterBy === 'failed') return run.status === 'failed';
        return true;
      });
    }

    // Apply sort
    filtered.sort((a, b) => {
      if (sortBy === 'date-desc') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sortBy === 'date-asc') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      if (sortBy === 'status') {
        const statusOrder = { running: 0, completed: 1, failed: 2 };
        return (statusOrder[a.status as keyof typeof statusOrder] ?? 3) - 
               (statusOrder[b.status as keyof typeof statusOrder] ?? 3);
      }
      return 0;
    });

    return filtered;
  };

  const getActiveRun = () => {
    return runs.find(run => run.status === 'running');
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    if (status === 'running') return 'text-[#00f4fe]';
    if (status === 'completed') return 'text-[#00ff88]';
    if (status === 'failed') return 'text-[#ff0055]';
    return 'text-[#aaabb0]';
  };

  const getStatusBgColor = (status: string) => {
    if (status === 'running') return 'bg-[#00f4fe]/10';
    if (status === 'completed') return 'bg-[#00ff88]/10';
    if (status === 'failed') return 'bg-[#ff0055]/10';
    return 'bg-[#23262c]';
  };

  const filteredRuns = getFilteredRuns();
  const activeRun = getActiveRun();
  const hasCompletedRuns = runs.some(run => run.status === 'completed');

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header Section */}
      <header className="mb-12">
        <h1 className="font-['Space_Grotesk'] text-5xl font-bold tracking-tight text-white mb-2">
          Synthesis <span className="text-[#a1faff]">History</span>
        </h1>
        <p className="text-[#aaabb0] font-['Manrope'] text-lg max-w-xl">
          A temporal log of {runs.length} cognitive evolution and molecular assembly sequences processed by the Ethereal Lab.
        </p>
      </header>

      {/* Error State */}
      {error && (
        <div className="mb-8 p-4 rounded-lg bg-[#ff0055]/10 border border-[#ff0055]/30 text-[#ff0055] font-['Manrope']">
          {error}
        </div>
      )}

      {/* Active Synthesis Card - Dynamic */}
      {activeRun && (
        <section className="mb-20">
          <div className="glass-card rounded-xl p-8 relative overflow-hidden group border border-[#a1faff]/5">
            <div className="absolute top-0 right-0 w-64 h-64 bg-[#a1faff]/5 blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
            <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <span className="bg-[#a1faff]/10 text-[#a1faff] text-[10px] font-['Space_Grotesk'] font-bold tracking-widest px-3 py-1 rounded-full uppercase animate-pulse">
                    ● Active Sequence
                  </span>
                  <span className="text-[#aaabb0] text-xs font-['Inter']">Running...</span>
                </div>
                <h2 className="font-['Space_Grotesk'] text-3xl font-bold text-white mb-4 line-clamp-2">{activeRun.topic}</h2>
                <p className="text-[#aaabb0] font-['Manrope'] mb-8 max-w-lg">
                  Synthesis initiated at {formatDate(activeRun.created_at)}. Monitor progress in real-time.
                </p>
                <Link
                  to={`/runs/${activeRun.id}`}
                  className="inline-block px-6 py-3 rounded-lg bg-[#a1faff]/10 border border-[#a1faff]/30 text-[#a1faff] font-['Inter'] text-sm font-semibold hover:bg-[#a1faff]/20 transition-all duration-300"
                >
                  View Real-time Progress →
                </Link>
              </div>
              <div className="w-full md:w-40 flex flex-col gap-4">
                <div className="p-4 rounded-lg bg-[#23262c] border border-[#46484d]/20">
                  <p className="text-[10px] text-[#aaabb0] uppercase font-['Inter'] mb-2">Status</p>
                  <p className="text-lg font-['Space_Grotesk'] font-bold text-[#00f4fe]">RUNNING</p>
                </div>
                <div className="p-4 rounded-lg bg-[#23262c] border border-[#46484d]/20">
                  <p className="text-[10px] text-[#aaabb0] uppercase font-['Inter'] mb-2">ID</p>
                  <p className="text-sm font-['Space_Grotesk'] font-bold text-white truncate">{activeRun.id}</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Synthesis Archive Section */}
      <section>
        <div className="flex justify-between items-end mb-8 flex-wrap gap-4">
          <div>
            <h3 className="font-['Space_Grotesk'] text-2xl font-semibold text-white mb-2">
              Archived Nodes {filteredRuns.length > 0 && `(${filteredRuns.length})`}
            </h3>
            <p className="text-xs text-[#aaabb0] font-['Manrope']">Total syntheses: {runs.length}</p>
          </div>
          <div className="flex gap-4 flex-wrap">
            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="text-xs font-['Inter'] uppercase tracking-widest bg-[#23262c] border border-[#46484d]/30 text-[#aaabb0] px-3 py-2 rounded hover:border-[#a1faff]/50 hover:text-[#a1faff] transition-colors cursor-pointer"
            >
              <option value="date-desc">Newest First</option>
              <option value="date-asc">Oldest First</option>
              <option value="status">By Status</option>
            </select>

            {/* Filter Dropdown */}
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value as FilterOption)}
              className="text-xs font-['Inter'] uppercase tracking-widest bg-[#23262c] border border-[#46484d]/30 text-[#aaabb0] px-3 py-2 rounded hover:border-[#a1faff]/50 hover:text-[#a1faff] transition-colors cursor-pointer"
            >
              <option value="all">All Syntheses</option>
              <option value="running">Running Only</option>
              <option value="completed">Completed Only</option>
              <option value="failed">Failed Only</option>
            </select>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="col-span-3 text-center py-20">
            <div className="inline-flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full border-2 border-[#a1faff]/30 border-t-[#a1faff] animate-spin"></div>
              <p className="text-[#aaabb0] font-['Manrope']">Scanning temporal archives...</p>
            </div>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="text-center py-20 px-8">
            <div className="inline-flex flex-col items-center gap-4">
              <span className="material-symbols-outlined text-5xl text-[#aaabb0]/50">folder_open</span>
              <div>
                <p className="text-lg font-['Space_Grotesk'] text-[#aaabb0] mb-2">No Archived Nodes</p>
                <p className="text-sm text-[#aaabb0] font-['Manrope']">
                  {filterBy !== 'all'
                    ? `No ${filterBy} syntheses found. Try adjusting your filters.`
                    : 'Start a new synthesis from the dashboard to see results here.'}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {filteredRuns.map((run, i) => {
              const pattern = i % 4;

              if (pattern === 0) {
                return (
                  <Link to={`/runs/${run.id}`} key={run.id} className="md:col-span-2 bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group block border border-[#46484d]/20 hover:border-[#a1faff]/30">
                    <div className="flex justify-between items-start mb-6">
                      <div>
                        <h4 className="font-['Space_Grotesk'] text-xl font-bold text-white group-hover:text-[#a1faff] transition-colors line-clamp-2">{run.topic}</h4>
                        <p className="text-xs font-['Inter'] text-[#aaabb0] mt-2 uppercase">{formatDate(run.created_at)}</p>
                      </div>
                      <span className={`inline-block px-3 py-1 rounded-full text-[10px] font-['Space_Grotesk'] font-bold tracking-widest uppercase ${getStatusBgColor(run.status)} ${getStatusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <span className="block text-[10px] text-[#aaabb0] uppercase font-['Inter']">Words</span>
                        <span className="text-2xl font-['Space_Grotesk'] font-bold text-[#a1faff]">{(run.paper_word_count || 0).toLocaleString()}</span>
                      </div>
                      <div className="space-y-1">
                        <span className="block text-[10px] text-[#aaabb0] uppercase font-['Inter']">Completed</span>
                        <span className="text-sm font-['Manrope'] text-[#aaabb0]">
                          {run.completed_at ? formatDate(run.completed_at) : '—'}
                        </span>
                      </div>
                    </div>
                  </Link>
                );
              }

              if (pattern === 1) {
                return (
                  <Link to={`/runs/${run.id}`} key={run.id} className="bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group flex flex-col justify-between border border-[#46484d]/20 hover:border-[#a1faff]/30">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <span className={`material-symbols-outlined text-2xl ${run.status === 'running' ? 'animate-spin text-[#a1faff]' : getStatusColor(run.status)}`}>
                          {run.status === 'running' ? 'cyclone' : run.status === 'completed' ? 'check_circle' : 'error'}
                        </span>
                        <span className={`text-[10px] font-['Space_Grotesk'] font-bold tracking-widest uppercase ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </div>
                      <h4 className="font-['Space_Grotesk'] text-lg font-bold text-white mb-3 line-clamp-3">{run.topic}</h4>
                      <p className="text-sm text-[#aaabb0] font-['Manrope']">
                        {run.paper_word_count > 0 ? `${run.paper_word_count.toLocaleString()} words` : 'Paper not yet generated'}
                      </p>
                    </div>
                    <div className="mt-6 pt-4 border-t border-[#46484d]/20">
                      <span className="text-[10px] font-['Inter'] text-[#aaabb0] uppercase tracking-widest">{formatDate(run.created_at)}</span>
                    </div>
                  </Link>
                );
              }

              if (pattern === 2) {
                return (
                  <Link to={`/runs/${run.id}`} key={run.id} className="bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group block overflow-hidden border border-[#46484d]/20 hover:border-[#a1faff]/30">
                    <div className="flex justify-between items-start mb-4">
                      <h4 className="font-['Space_Grotesk'] text-lg font-bold text-white line-clamp-2 flex-1">{run.topic}</h4>
                      <span className={`material-symbols-outlined text-xl flex-shrink-0 ml-2 ${getStatusColor(run.status)}`}>
                        {run.status === 'running' ? 'schedule' : run.status === 'completed' ? 'task_alt' : 'close'}
                      </span>
                    </div>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-[#aaabb0] font-['Inter']">Word Count</span>
                        <span className="text-sm font-['Space_Grotesk'] font-bold text-[#a1faff]">{(run.paper_word_count || 0).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-[#aaabb0] font-['Inter']">Status</span>
                        <span className={`text-xs font-['Space_Grotesk'] font-bold uppercase ${getStatusColor(run.status)}`}>{run.status}</span>
                      </div>
                      <div className="flex justify-between items-center pt-2 border-t border-[#46484d]/20">
                        <span className="text-xs text-[#aaabb0] font-['Inter']">Created</span>
                        <span className="text-xs text-[#aaabb0]">{new Date(run.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </Link>
                );
              }

              return (
                <Link to={`/runs/${run.id}`} key={run.id} className="md:col-span-2 bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors flex items-center justify-between group border border-[#46484d]/20 hover:border-[#a1faff]/30">
                  <div className="flex items-center gap-6 flex-1 min-w-0">
                    <div className={`p-3 rounded-full flex-shrink-0 ${getStatusBgColor(run.status)}`}>
                      <span className={`material-symbols-outlined text-2xl ${getStatusColor(run.status)}`}>
                        {run.status === 'running' ? 'autorenew' : run.status === 'completed' ? 'done' : 'report'}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="font-['Space_Grotesk'] text-lg font-bold text-white truncate">{run.topic}</h4>
                      <p className="text-sm text-[#aaabb0] font-['Manrope'] line-clamp-1">
                        {run.paper_word_count} words • {formatDate(run.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="p-3 rounded-full border border-[#46484d]/30 text-[#aaabb0] group-hover:text-[#a1faff] group-hover:border-[#a1faff]/50 transition-all hidden sm:flex flex-shrink-0">
                    <span className="material-symbols-outlined">chevron_right</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
