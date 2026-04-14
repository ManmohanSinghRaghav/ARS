import { useState, useEffect } from 'react';
import { runsAPI } from '../api/client';
import RunCard from '../components/RunCard';

interface RunListItem {
  id: string;
  topic: string;
  status: string;
  paper_word_count: number;
  created_at: string;
  completed_at: string | null;
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const PAGE_SIZE = 20;

  useEffect(() => {
    fetchRuns();
  }, [page]);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const res = await runsAPI.list(page * PAGE_SIZE, PAGE_SIZE);
      setRuns(res.data);
      setHasMore(res.data.length === PAGE_SIZE);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Research History</h1>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : runs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-1">No research runs found</p>
          <p className="text-sm">Start a new run from the dashboard.</p>
        </div>
      ) : (
        <>
          <div className="grid gap-3 mb-6">
            {runs.map((run) => (
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

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
