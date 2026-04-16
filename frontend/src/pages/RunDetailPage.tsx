import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runsAPI } from '../api/client';
import PaperViewer from '../components/PaperViewer';
import CodeBlock from '../components/CodeBlock';
import toast from 'react-hot-toast';

interface RunDetail {
  id: string;
  user_id: string;
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
  const [activeTab, setActiveTab] = useState<Tab | 'grounding'>('paper');
  const [isEditing, setIsEditing] = useState(false);
  const [editedMarkdown, setEditedMarkdown] = useState('');
  const [refinementFeedback, setRefinementFeedback] = useState('');
  const [showRefineModal, setShowRefineModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    runsAPI
      .get(id)
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

  const handleDownloadPdf = async () => {
    if (!run) return;
    try {
      const res = await runsAPI.downloadPaperPdf(run.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `paper_${run.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download PDF');
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

  const handleManualSave = async () => {
    if (!run || !editedMarkdown) return;
    setIsSubmitting(true);
    try {
      await runsAPI.updatePaper(run.id, editedMarkdown);
      setRun({ ...run, paper_markdown: editedMarkdown });
      setIsEditing(false);
      toast.success('Paper updated');
    } catch {
      toast.error('Failed to update paper');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRefine = async () => {
    if (!run || !refinementFeedback) return;
    setIsSubmitting(true);
    try {
      await runsAPI.refinePaper(run.id, refinementFeedback);
      toast.success('Refinement mission started! Check progress in History.');
      setShowRefineModal(false);
      setRun({ ...run, status: 'refining' });
    } catch {
      toast.error('Failed to start refinement');
    } finally {
      setIsSubmitting(false);
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

  const tabs: { key: Tab | 'grounding'; label: string }[] = [
    { key: 'paper', label: 'Paper' },
    { key: 'hypothesis', label: 'Hypothesis' },
    { key: 'code', label: 'Code' },
    { key: 'output', label: 'Execution Output' },
    { key: 'grounding', label: 'Grounding Card (Verifier)' },
    { key: 'summary', label: 'Telemetry & Infrastructure' },
  ];

  const statusColors: Record<string, string> = {
    completed: 'bg-green-500/20 text-green-300',
    running: 'bg-blue-500/20 text-blue-300',
    failed: 'bg-red-500/20 text-red-300',
    pending: 'bg-yellow-500/20 text-yellow-300',
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#f6f6fc] mb-2">{run.topic}</h1>
          <div className="flex items-center gap-3 text-sm text-[#aaabb0]">
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[run.status] || 'bg-gray-500/20 text-gray-300'}`}>
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
            <>
              <button
                onClick={handleDownload}
                className="px-4 py-2 bg-[#a1faff]/20 text-[#a1faff] rounded-lg text-sm font-medium hover:bg-[#a1faff]/30 transition-colors"
              >
                Download Paper
              </button>
              <button
                onClick={handleDownloadPdf}
                className="px-4 py-2 bg-[#a1faff]/20 text-[#a1faff] rounded-lg text-sm font-medium hover:bg-[#a1faff]/30 transition-colors"
              >
                Download PDF
              </button>
              <button
                onClick={() => {
                  setIsEditing(!isEditing);
                  setEditedMarkdown(run.paper_markdown);
                }}
                className={`px-4 py-2 border rounded-lg text-sm font-medium transition-colors ${
                  isEditing 
                    ? 'bg-[#a1faff] text-black border-[#a1faff]' 
                    : 'bg-transparent text-[#a1faff] border-[#a1faff]/40 hover:bg-[#a1faff]/10'
                }`}
              >
                {isEditing ? 'Cancel Editing' : 'Edit Manually'}
              </button>
              <button
                onClick={() => setShowRefineModal(true)}
                className="px-4 py-2 bg-purple-500/20 text-purple-300 border border-purple-500/40 rounded-lg text-sm font-medium hover:bg-purple-500/30 transition-colors"
                disabled={run.status === 'refining'}
              >
                {run.status === 'refining' ? 'Refining...' : 'Refine with AI'}
              </button>
            </>
          )}
          <button
            onClick={handleDelete}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg text-sm font-medium hover:bg-red-500/30 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Error message */}
      {run.error_message && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6">
          <h3 className="text-red-300 font-medium mb-1">Error</h3>
          <pre className="text-red-200 text-sm whitespace-pre-wrap font-mono">{run.error_message}</pre>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-[#a1faff]/20 mb-6">
        <div className="flex space-x-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-[#a1faff] text-[#a1faff]'
                  : 'border-transparent text-[#aaabb0] hover:text-[#f6f6fc] hover:border-[#a1faff]/30'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-slate-800/40 rounded-xl shadow-lg border border-[#a1faff]/20 p-6 relative">
        {activeTab === 'paper' && (
          isEditing ? (
            <div className="flex flex-col gap-4">
              <textarea
                value={editedMarkdown}
                onChange={(e) => setEditedMarkdown(e.target.value)}
                className="w-full h-[600px] bg-black/30 text-white p-4 font-mono rounded-lg border border-[#a1faff]/20 focus:outline-none focus:border-[#a1faff]"
              />
              <button
                onClick={handleManualSave}
                disabled={isSubmitting}
                className="self-end px-6 py-2 bg-[#a1faff] text-black rounded-lg font-bold hover:bg-[#88eef4] transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          ) : (
            <PaperViewer markdown={run.paper_markdown} />
          )
        )}

        {activeTab === 'hypothesis' && (
          run.hypothesis
            ? <PaperViewer markdown={run.hypothesis} />
            : <div className="text-[#aaabb0] italic">No hypothesis generated.</div>
        )}

        {activeTab === 'code' && <CodeBlock code={run.generated_code} />}

        {activeTab === 'output' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-[#f6f6fc]">AgentTrace Execution Log</h3>
            <p className="text-sm text-[#aaabb0] mb-2">Internal Sandbox STDOUT/STDERR captured during the OODA "Karpathy Move" validation.</p>
            <pre className="bg-black/50 border border-[#a1faff]/30 text-[#a1faff] p-5 rounded-xl overflow-x-auto text-sm font-mono whitespace-pre-wrap shadow-inner leading-relaxed">
              {run.execution_output || '[Execution Trace Empty]'}
            </pre>
          </div>
        )}

        {activeTab === 'grounding' && (
          <div className="space-y-4 text-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">RefLens Verification Card (JSON Trace)</h3>
            <p className="text-gray-500 mb-4">Atomic Claims mapped to Grounding Spans (extracted from PDF/Web endpoints).</p>
            {run.summary_json && run.summary_json.grounding ? (
              <pre className="bg-gray-50 border-l-4 border-primary-500 text-gray-800 p-5 rounded font-mono text-sm whitespace-pre-wrap shadow-sm">
                {typeof run.summary_json.grounding === 'object' 
                  ? JSON.stringify(run.summary_json.grounding, null, 2) 
                  : run.summary_json.grounding}
              </pre>
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg text-yellow-800 italic">
                No formal Grounding Card was extracted for this run. Run might have halted early or Verifier JSON parsing failed.
              </div>
            )}
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="space-y-3">
            {run.summary_json && Object.keys(run.summary_json).length > 0 ? (
              <table className="w-full text-left">
                <tbody>
                  {Object.entries(run.summary_json).filter(([key]) => key !== 'grounding').map(([key, value]) => (
                    <tr key={key} className="border-b border-gray-100">
                      <td className="py-2.5 pr-4 text-sm font-medium text-gray-600 w-48 align-top">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </td>
                      <td className="py-2.5 text-sm text-gray-800 break-words">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <span className="text-gray-400 italic">No telemetry data available.</span>
            )}
          </div>
        )}
      </div>

      {/* Refinement Modal */}
      {showRefineModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-[#a1faff]/30 rounded-2xl shadow-2xl max-w-lg w-full p-6 animate-in fade-in zoom-in duration-200">
            <h2 className="text-xl font-bold text-[#f6f6fc] mb-2">Request AI Refinement</h2>
            <p className="text-sm text-[#aaabb0] mb-4">
              Describe how you want the AI to improve or expand your paper. Our Peer Reviewer agent will rewrite 
              the relevant sections based on your feedback.
            </p>
            <textarea
              placeholder="e.g., Expand the methodology section to include more details on the OODA loop..."
              value={refinementFeedback}
              onChange={(e) => setRefinementFeedback(e.target.value)}
              className="w-full h-32 bg-black/40 text-white p-3 rounded-lg border border-[#a1faff]/20 focus:outline-none focus:border-[#a1faff] mb-4"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowRefineModal(false)}
                className="px-4 py-2 text-[#aaabb0] hover:text-[#f6f6fc] transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleRefine}
                disabled={isSubmitting || !refinementFeedback}
                className="px-6 py-2 bg-[#a1faff] text-black rounded-lg font-bold hover:bg-[#88eef4] transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Starting...' : 'Submit Mission'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
