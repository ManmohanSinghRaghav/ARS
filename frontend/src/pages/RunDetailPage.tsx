import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runsAPI } from '../api/client';
import PaperViewer from '../components/PaperViewer';
import CodeBlock from '../components/CodeBlock';
import toast from 'react-hot-toast';

interface RunDetail {
  id: number;
  user_id: number;
  topic: string;
  status: string;
  hypothesis: string;
  generated_code: string;
  execution_output: string;
  paper_markdown: string;
  summary_json: Record<string, any>;
  error_message: string;
  created_at: string;
  completed_at: string | null;
}

type Tab = 'paper' | 'hypothesis' | 'code' | 'output' | 'summary';

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('paper');

  useEffect(() => {
    if (!id) return;
    runsAPI
      .get(Number(id))
      .then((res) => setRun(res.data))
      .catch(() => {
        toast.error('Run not found');
        navigate('/');
      })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleDownload = async () => {
    if (!run) return;
    try {
      const res = await runsAPI.downloadPaper(run.id);
      const blob = new Blob([res.data], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `paper_${run.id}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download paper');
    }
  };

  const handleDelete = async () => {
    if (!run || !confirm('Are you sure you want to delete this run?')) return;
    try {
      await runsAPI.delete(run.id);
      toast.success('Run deleted');
      navigate('/history');
    } catch {
      toast.error('Failed to delete run');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!run) return null;

  const tabs: { key: Tab; label: string }[] = [
    { key: 'paper', label: 'Paper' },
    { key: 'hypothesis', label: 'Hypothesis' },
    { key: 'code', label: 'Code' },
    { key: 'output', label: 'Execution Output' },
    { key: 'summary', label: 'Summary' },
  ];

  const statusColors: Record<string, string> = {
    completed: 'bg-green-100 text-green-800',
    running: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800',
    pending: 'bg-yellow-100 text-yellow-800',
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{run.topic}</h1>
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[run.status] || 'bg-gray-100 text-gray-600'}`}>
              {run.status}
            </span>
            <span>{new Date(run.created_at).toLocaleString()}</span>
            {run.completed_at && (
              <span>Completed: {new Date(run.completed_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {run.paper_markdown && (
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              Download Paper
            </button>
          )}
          <button
            onClick={handleDelete}
            className="px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Error message */}
      {run.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <h3 className="text-red-800 font-medium mb-1">Error</h3>
          <pre className="text-red-700 text-sm whitespace-pre-wrap font-mono">{run.error_message}</pre>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex space-x-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        {activeTab === 'paper' && <PaperViewer markdown={run.paper_markdown} />}

        {activeTab === 'hypothesis' && (
          run.hypothesis
            ? <PaperViewer markdown={run.hypothesis} />
            : <div className="text-gray-400 italic">No hypothesis generated.</div>
        )}

        {activeTab === 'code' && <CodeBlock code={run.generated_code} />}

        {activeTab === 'output' && (
          <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono whitespace-pre-wrap">
            {run.execution_output || 'No execution output.'}
          </pre>
        )}

        {activeTab === 'summary' && (
          <div className="space-y-3">
            {run.summary_json && Object.keys(run.summary_json).length > 0 ? (
              <table className="w-full">
                <tbody>
                  {Object.entries(run.summary_json).map(([key, value]) => (
                    <tr key={key} className="border-b border-gray-100">
                      <td className="py-2.5 pr-4 text-sm font-medium text-gray-600 w-48">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </td>
                      <td className="py-2.5 text-sm text-gray-800">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="text-gray-400 italic">No summary data available.</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
