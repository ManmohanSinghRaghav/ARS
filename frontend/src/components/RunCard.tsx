import { Link } from 'react-router-dom';

interface RunCardProps {
  id: number;
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
      className="block bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md hover:border-primary-300 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-base font-semibold text-gray-800 line-clamp-2 flex-1 mr-3">
          {topic}
        </h3>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColors[status] || 'bg-gray-100 text-gray-600'}`}>
          {status}
        </span>
      </div>
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>{new Date(createdAt).toLocaleDateString()}</span>
        {status === 'completed' && (
          <span>{paperWordCount.toLocaleString()} words</span>
        )}
      </div>
    </Link>
  );
}
