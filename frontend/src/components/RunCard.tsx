import { Link } from 'react-router-dom';

interface RunCardProps {
  id: string;
  topic: string;
  status: string;
  paperWordCount: number;
  createdAt: string;
  completedAt?: string | null;
}

const statusColors: Record<string, string> = {
  completed: 'bg-green-100 text-green-800',
  running: 'bg-blue-100 text-blue-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
};

export default function RunCard({ id, topic, status, paperWordCount, createdAt, completedAt }: RunCardProps) {
  return (
    <Link
      to={`/runs/${id}`}
      className="block bg-slate-800/60 rounded-xl shadow-lg border border-[#a1faff]/20 p-5 hover:bg-slate-800/80 hover:border-[#a1faff]/40 hover:shadow-xl hover:shadow-[#a1faff]/10 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-base font-semibold text-[#f6f6fc] line-clamp-2 flex-1 mr-3">
          {topic}
        </h3>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
          status === 'completed' ? 'bg-green-500/20 text-green-300' :
          status === 'running' ? 'bg-blue-500/20 text-blue-300' :
          status === 'failed' ? 'bg-red-500/20 text-red-300' :
          'bg-yellow-500/20 text-yellow-300'
        }`}>
          {status}
        </span>
      </div>
      <div className="flex items-center justify-between text-sm text-[#aaabb0]">
        <span>{new Date(createdAt).toLocaleDateString()}</span>
        {status === 'completed' && (
          <span>{paperWordCount.toLocaleString()} words</span>
        )}
      </div>
    </Link>
  );
}
