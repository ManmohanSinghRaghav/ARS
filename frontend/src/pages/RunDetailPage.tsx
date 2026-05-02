import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PDFViewer, pdf } from '@react-pdf/renderer';
import { Sparkles, Download, MessageSquare, Send, Plus, Trash2, Loader2, FileText, Code2, Activity, Image as ImageIcon, Type, RefreshCw, Pencil, Check, MoveUp, MoveDown, Copy, Wand2, BookOpen, Lightbulb, Edit3, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { runsAPI } from '../api/client';
import toast from 'react-hot-toast';
import InstantPdfDocument from '../components/InstantPdfDocument';

interface PaperSection {
  id: string;
  type: string;
  title: string;
  content: string;
}
interface PaperJson {
  metadata: { title: string; author: string; date: string; institution: string };
  sections: PaperSection[];
}
interface RunDetail {
  id: string; topic: string; status: string;
  hypothesis: string; generated_code: string; execution_output: string;
  paper_json: PaperJson | null; summary_json: Record<string, any>;
  version: number;
  created_at: string; completed_at: string | null;
}
type Tab = 'workspace' | 'hypothesis' | 'execution' | 'telemetry';
interface ChatMsg { role: 'user' | 'assistant'; content: string; }

const EMPTY_PAPER: PaperJson = {
  metadata: { title: 'New Paper', author: 'ARS', date: new Date().getFullYear().toString(), institution: 'GLA Research Lab' },
  sections: []
};

/** Run progress API statuses that should stop the pipeline poller */
const TERMINAL_RUN_STATUSES = new Set(['completed', 'failed', 'error', 'cancelled']);

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('workspace');
  const [paperData, setPaperData] = useState<PaperJson>(EMPTY_PAPER);
  const [activeBlock, setActiveBlock] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [version, setVersion] = useState(0);
  const [pdfKey, setPdfKey] = useState(0);
  const [showChat, setShowChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isAiRefining, setIsAiRefining] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [sessionTitle, setSessionTitle] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const syncTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refinePoller = useRef<ReturnType<typeof setInterval> | null>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const [steps, setSteps] = useState<any[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { 
    if (id) {
      loadRun();
      startPolling(id);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (refinePoller.current) clearInterval(refinePoller.current);
    };
  }, [id]);

  // Fix #2: sync sessionTitle when paperData loads
  useEffect(() => {
    if (paperData.metadata.title) setSessionTitle(paperData.metadata.title);
  }, [paperData.metadata.title]);

  useEffect(() => {
    if (editingTitle) titleInputRef.current?.focus();
  }, [editingTitle]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const startPolling = (runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await runsAPI.progress(runId);
        setSteps(res.data.steps || []);
        if (TERMINAL_RUN_STATUSES.has(res.data.status)) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          if (res.data.status === 'completed') {
            loadRun(); // Reload final data
          }
        }
      } catch { /* silent */ }
    }, 3000);
  };

  const loadRun = async () => {
    if (!id) return;
    try {
      const res = await runsAPI.get(id);
      setRun(res.data);
      setVersion(res.data.version || 0);
      const pj = res.data.paper_json;
      const isValidPaper = pj && pj.metadata?.title && Array.isArray(pj.sections) && pj.sections.length > 0;
      setPaperData(isValidPaper ? pj : EMPTY_PAPER);
    } catch {
      toast.error('Run not found');
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  // Debounced auto-sync to backend
  const syncPaper = useCallback((data: PaperJson, v: number) => {
    if (!id) return;
    if (syncTimer.current) clearTimeout(syncTimer.current);
    syncTimer.current = setTimeout(async () => {
      setIsSyncing(true);
      try {
        const res = await runsAPI.updatePaper(id, data, v);
        setVersion(res.data.version);
        // Fix #5: removed setPdfKey — only on manual Update Preview click
      } catch (err: any) {
        if (err.response?.status === 409) {
          // Server has a newer version — merge it in safely
          const detail = err.response.data?.detail;
          const serverPj = typeof detail === 'object' ? detail?.paper_json : null;
          const serverVer = typeof detail === 'object' ? detail?.current_version : null;
          if (serverPj && serverPj.metadata?.title) {
            setPaperData(serverPj);
            setVersion(serverVer ?? v);
            toast.error('Conflict resolved: server version applied');
          } else {
            // Reload from server as fallback
            loadRun();
            toast.error('Version conflict: reloading latest');
          }
        }
      }
      finally { setIsSyncing(false); }
    }, 1200);
  }, [id]);

  const updateSection = (blockId: string, content: string) => {
    const next = { ...paperData, sections: paperData.sections.map(s => s.id === blockId ? { ...s, content } : s) };
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const updateMetadata = (key: keyof PaperJson['metadata'], val: string) => {
    const next = { ...paperData, metadata: { ...paperData.metadata, [key]: val } };
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  // Fix #2: commit editable session title into paper metadata
  const commitTitle = () => {
    setEditingTitle(false);
    if (sessionTitle.trim() && sessionTitle.trim() !== paperData.metadata.title) {
      updateMetadata('title', sessionTitle.trim());
    }
  };

  const addSection = () => {
    const next = {
      ...paperData,
      sections: [...paperData.sections, {
        id: `sec_${Date.now()}`, type: 'content',
        title: `Section ${paperData.sections.length + 1}`, content: ''
      }]
    };
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const deleteSection = (blockId: string) => {
    const next = { ...paperData, sections: paperData.sections.filter(s => s.id !== blockId) };
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const moveSection = (blockId: string, direction: 'up' | 'down') => {
    const index = paperData.sections.findIndex(s => s.id === blockId);
    if (index === -1) return;
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= paperData.sections.length) return;
    const next = { ...paperData, sections: [...paperData.sections] };
    [next.sections[index], next.sections[newIndex]] = [next.sections[newIndex], next.sections[index]];
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const duplicateSection = (blockId: string) => {
    const index = paperData.sections.findIndex(s => s.id === blockId);
    if (index === -1) return;
    const section = paperData.sections[index];
    const newSection = {
      ...section,
      id: `sec_${Date.now()}`,
      title: `${section.title} (Copy)`
    };
    const next = { ...paperData, sections: [...paperData.sections] };
    next.sections.splice(index + 1, 0, newSection);
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const addSectionWithTemplate = (templateType: string) => {
    const templates: Record<string, { title: string; content: string; type: string }> = {
      abstract: {
        title: 'Abstract',
        type: 'abstract',
        content: 'This paper presents a novel approach to '
      },
      introduction: {
        title: 'Introduction',
        type: 'content',
        content: '## Background\n\nThe field of study has seen significant developments in recent years...\n\n## Problem Statement\n\nDespite these advances, several key challenges remain...\n\n## Contributions\n\nThis work makes the following contributions:\n1. \n2. \n3. '
      },
      related_work: {
        title: 'Related Work',
        type: 'content',
        content: 'Previous research in this area has focused on several key directions...\n\nRecent advances have shown promising results in...\n\nHowever, these approaches have limitations including...'
      },
      methodology: {
        title: 'Methodology',
        type: 'content',
        content: '## Proposed Approach\n\nWe propose a novel framework that addresses the limitations of existing methods...\n\n## Technical Details\n\nThe core components of our approach include...\n\n## Algorithm\n\nThe proposed algorithm proceeds as follows...'
      },
      experiments: {
        title: 'Experiments',
        type: 'content',
        content: '## Experimental Setup\n\nWe evaluate our method on several benchmark datasets...\n\n## Baselines\n\nWe compare against the following state-of-the-art methods...\n\n## Metrics\n\nPerformance is measured using standard evaluation metrics...'
      },
      results: {
        title: 'Results and Discussion',
        type: 'content',
        content: '## Main Results\n\nOur experimental results demonstrate significant improvements over existing methods...\n\n## Analysis\n\nThe improvements can be attributed to several factors...\n\n## Limitations\n\nWhile our approach shows promising results, several limitations should be noted...'
      },
      conclusion: {
        title: 'Conclusion',
        type: 'content',
        content: '## Summary\n\nIn this work, we have presented a novel approach to...\n\n## Future Work\n\nSeveral directions for future research include...\n\n## Impact\n\nThis research has potential implications for...'
      },
      references: {
        title: 'References',
        type: 'content',
        content: '1. Author, A. et al. "Title of the paper." Journal Name, Year.\n2. Author, B. et al. "Another relevant work." Conference Name, Year.'
      }
    };

    const template = templates[templateType];
    if (!template) return;

    const next = {
      ...paperData,
      sections: [...paperData.sections, {
        id: `sec_${Date.now()}`,
        type: template.type,
        title: template.title,
        content: template.content
      }]
    };
    setPaperData(next);
    setIsDirty(true);
    syncPaper(next, version);
  };

  const getWordCount = (text: string): number => {
    if (!text || !text.trim()) return 0;
    return text.trim().split(/\s+/).length;
  };

  const getTotalWordCount = (): number => {
    return paperData.sections.reduce((sum, s) => sum + getWordCount(s.content), 0);
  };

  const aiRefineBlock = async (blockId: string) => {
    if (!id || !run) return;
    setIsAiRefining(blockId);
    const section = paperData.sections.find(s => s.id === blockId);
    try {
      const res = await runsAPI.chat(id, [
        { role: 'user', content: `Please rewrite and improve this section of the paper titled "${section?.title}". Make it more detailed, rigorous, and academic. Current content:\n\n${section?.content}` }
      ]);
      updateSection(blockId, res.data.content);
      toast.success('Section refined by AI');
    } catch { toast.error('AI refinement failed'); }
    finally { setIsAiRefining(null); }
  };

  // Fix #4: Poll backend until run exits 'refining', then reload paper and refresh PDF
  const startRefinePoller = () => {
    if (refinePoller.current) clearInterval(refinePoller.current);
    refinePoller.current = setInterval(async () => {
      if (!id) return;
      try {
        const res = await runsAPI.progress(id);
        if (res.data.status !== 'refining') {
          clearInterval(refinePoller.current!);
          await loadRun();
          setPdfKey(k => k + 1);
          toast.success('Manuscript updated by AI', { id: 'refine' });
        }
      } catch { clearInterval(refinePoller.current!); }
    }, 2500);
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || isChatLoading || !id) return;
    const userMsg: ChatMsg = { role: 'user', content: chatInput.trim() };
    const history = [...chatMessages, userMsg];
    setChatMessages(history);
    setChatInput('');
    setIsChatLoading(true);
    try {
      const res = await runsAPI.chat(id, history);
      const { content, action_triggered } = res.data;
      setChatMessages([...history, { role: 'assistant', content: content || 'No response.' }]);
      if (action_triggered === 'refining') {
        toast.loading('AI is patching the manuscript...', { id: 'refine' });
        startRefinePoller(); // Fix #4: poll for completion, then reload
      }
    } catch (e: any) {
      toast.error(`Chat failed: ${e?.response?.data?.detail || 'check backend'}`);
    }
    finally { setIsChatLoading(false); }
  };

  const downloadProPdf = async () => {
    if (!id) return;
    toast.loading('Generating Live PDF...', { id: 'pdf' });
    try {
      // Generate PDF client-side for "LIVE" results
      const blob = await pdf(<InstantPdfDocument data={paperData} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${paperData.metadata.title.replace(/\s+/g, '_') || 'research_paper'}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Live PDF downloaded!', { id: 'pdf' });
    } catch (err) {
      console.error(err);
      toast.error('PDF generation failed', { id: 'pdf' });
    }
  };

  useEffect(() => {
    if (run?.status === 'running' && activeTab !== 'telemetry') {
      setActiveTab('telemetry');
    }
  }, [run?.status, activeTab]);

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-[#0b0e14]">
      <div className="flex flex-col items-center gap-4">
        <Loader2 size={40} className="animate-spin text-[#a1faff]" />
        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[#a1faff] animate-pulse">Loading Research Node...</p>
      </div>
    </div>
  );

  if (!run) return null;

  const tabs = [
    { key: 'workspace' as Tab, label: 'Paper Lab', icon: <FileText size={15}/> },
    { key: 'hypothesis' as Tab, label: 'Hypothesis', icon: <Sparkles size={15}/> },
    { key: 'execution' as Tab, label: 'Execution', icon: <Code2 size={15}/> },
    { key: 'telemetry' as Tab, label: 'Telemetry', icon: <Activity size={15}/> },
  ];

  const statusColor = { completed: 'text-emerald-400', running: 'text-blue-400', failed: 'text-red-400', refining: 'text-purple-400' }[run.status] || 'text-slate-400';

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-[#0b0e14] text-[#f6f6fc] overflow-hidden">
      
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-slate-950/60 backdrop-blur-xl shrink-0">
        <div className="min-w-0 flex-1">
          {/* Fix #2: Editable session title */}
          <div className="flex items-center gap-2 group">
            {editingTitle ? (
              <>
                <input
                  ref={titleInputRef}
                  value={sessionTitle}
                  onChange={e => setSessionTitle(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') commitTitle(); if (e.key === 'Escape') setEditingTitle(false); }}
                  className="text-lg font-black tracking-tight bg-transparent border-b border-[#a1faff] outline-none text-[#f6f6fc] min-w-0 flex-1"
                />
                <button onClick={commitTitle} className="text-emerald-400 hover:text-emerald-300 shrink-0"><Check size={15}/></button>
              </>
            ) : (
              <>
                <h1 className="text-lg font-black tracking-tight truncate">{paperData.metadata.title || run.topic}</h1>
                <button onClick={() => setEditingTitle(true)} className="opacity-0 group-hover:opacity-60 hover:opacity-100 text-[#aaabb0] transition-opacity shrink-0"><Pencil size={13}/></button>
              </>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className={`text-[10px] font-black uppercase ${statusColor}`}>{run.status}</span>
            <span className="text-[10px] text-[#aaabb0]">{new Date(run.created_at).toLocaleDateString()}</span>
            <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[9px] font-black uppercase ${isSyncing ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isSyncing ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`}/>
              {isSyncing ? 'Syncing...' : 'Synced'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button onClick={() => { setActiveTab('workspace'); setShowChat(!showChat); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-black uppercase transition-all ${showChat ? 'bg-[#a1faff] text-slate-950 shadow-[0_0_15px_rgba(161,250,255,0.4)]' : 'bg-slate-800 text-[#aaabb0] hover:text-white'}`}>
            <MessageSquare size={13}/> Copilot
          </button>
          <button onClick={downloadProPdf}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-black uppercase shadow-lg transition-all active:scale-95">
            <Download size={13}/> Live PDF
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-0 border-b border-white/5 shrink-0 bg-slate-950/40">
        {tabs.filter(t => run.status !== 'running' || t.key === 'telemetry').map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-5 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-b-2 ${activeTab === t.key ? 'border-[#a1faff] text-[#a1faff] bg-[#a1faff]/5' : 'border-transparent text-[#aaabb0] hover:text-[#f6f6fc]'}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden relative flex">
        
        {/* WAR ROOM OVERLAY REMOVED - NOW INTEGRATED INTO TELEMETRY TAB */}
        
        {/* WORKSPACE TAB */}
        {activeTab === 'workspace' && (
          <div className="flex-1 flex overflow-hidden relative">
            {/* REFINEMENT LOCK OVERLAY */}
            {run.status === 'refining' && (
              <div className="absolute inset-0 z-30 bg-slate-950/60 backdrop-blur-[2px] flex items-center justify-center">
                <div className="glass-card px-8 py-6 flex flex-col items-center gap-4 border-purple-500/30 shadow-[0_0_40px_rgba(168,85,247,0.15)]">
                  <Loader2 className="animate-spin text-purple-400" size={32}/>
                  <div className="text-center">
                    <p className="text-xs font-black text-purple-400 uppercase tracking-[0.2em]">Swarm Refining</p>
                    <p className="text-[10px] text-slate-500 mt-2">The AI Writer is currently patching the manuscript.<br/>Manual editing is disabled during this phase.</p>
                  </div>
                </div>
              </div>
            )}
            {/* Left: Block Editor */}
            <div className="w-[42%] min-w-[320px] border-r border-white/5 flex flex-col overflow-hidden bg-slate-950">
              <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/60 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-black uppercase tracking-[0.25em] text-[#aaabb0]">Structural Blocks</span>
                  <span className="text-[8px] text-slate-600 font-mono">{paperData.sections.length} sections • {getTotalWordCount()} words</span>
                </div>
                <div className="flex items-center gap-1">
                  {/* Template Quick-Add Dropdown */}
                  <div className="relative group">
                    <button className="flex items-center gap-1 text-[#aaabb0] hover:text-[#a1faff] transition-all p-1 rounded-lg hover:bg-slate-800">
                      <BookOpen size={14}/>
                      <span className="text-[9px] font-black uppercase">Template</span>
                    </button>
                    <div className="absolute right-0 top-full mt-1 z-50 hidden group-hover:block w-44 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl">
                      <div className="p-1">
                        {[
                          { key: 'abstract', label: 'Abstract', icon: <FileText size={12}/> },
                          { key: 'introduction', label: 'Introduction', icon: <Lightbulb size={12}/> },
                          { key: 'related_work', label: 'Related Work', icon: <BookOpen size={12}/> },
                          { key: 'methodology', label: 'Methodology', icon: <Wand2 size={12}/> },
                          { key: 'experiments', label: 'Experiments', icon: <Activity size={12}/> },
                          { key: 'results', label: 'Results', icon: <ChevronRight size={12}/> },
                          { key: 'conclusion', label: 'Conclusion', icon: <Check size={12}/> },
                        ].map(t => (
                          <button
                            key={t.key}
                            onClick={() => addSectionWithTemplate(t.key)}
                            className="flex items-center gap-2 w-full px-2 py-1.5 text-[9px] font-bold text-slate-300 hover:bg-indigo-500/20 hover:text-indigo-400 rounded transition-all"
                          >
                            {t.icon} {t.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <button onClick={addSection} className="flex items-center gap-1 text-[#a1faff] hover:scale-110 transition-all p-1 rounded-lg hover:bg-[#a1faff]/10">
                    <Plus size={14}/>
                    <span className="text-[9px] font-black uppercase">Add</span>
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">
                {/* Metadata Block */}
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <p className="text-[9px] font-black uppercase tracking-widest text-indigo-400 mb-2">Paper Metadata</p>
                  <input value={paperData.metadata.title} onChange={e => updateMetadata('title', e.target.value)}
                    className="w-full bg-black/30 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white mb-1.5 focus:border-[#a1faff] outline-none" placeholder="Paper Title"/>
                  <div className="grid grid-cols-2 gap-1.5">
                    <input value={paperData.metadata.author} onChange={e => updateMetadata('author', e.target.value)}
                      className="bg-black/30 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:border-[#a1faff] outline-none" placeholder="Author"/>
                    <input value={paperData.metadata.institution} onChange={e => updateMetadata('institution', e.target.value)}
                      className="bg-black/30 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:border-[#a1faff] outline-none" placeholder="Institution"/>
                  </div>
                </div>

                {/* Section Blocks */}
                {paperData.sections.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-12 text-center space-y-2 opacity-40">
                    <FileText size={28} className="text-[#aaabb0]"/>
                    <p className="text-xs text-[#aaabb0]">No sections yet.<br/>Click "Add" to start building.</p>
                  </div>
                )}
                {paperData.sections.map((section) => (
                  <div key={section.id} onClick={() => setActiveBlock(activeBlock === section.id ? null : section.id)}
                    className={`group rounded-xl border transition-all cursor-pointer ${activeBlock === section.id ? 'bg-indigo-600/10 border-indigo-500/60 shadow-[0_0_20px_rgba(99,102,241,0.15)]' : 'bg-slate-900 border-slate-800 hover:border-slate-600'}`}>
                    <div className="flex justify-between items-center px-4 py-2.5">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {section.type === 'image' ? <ImageIcon size={12} className="text-amber-400" /> : <Type size={12} className="text-indigo-400" />}
                        <input value={section.title}
                          onClick={e => e.stopPropagation()}
                          onChange={e => {
                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, title: e.target.value } : s) };
                            setPaperData(next); setIsDirty(true); syncPaper(next, version);
                          }}
                          className="text-[10px] font-black text-white uppercase tracking-widest bg-transparent border-none outline-none w-full"/>
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        {/* Move Up */}
                        <button onClick={e => { e.stopPropagation(); moveSection(section.id, 'up'); }}
                          className="p-1 hover:bg-slate-700 rounded-lg transition-all" title="Move Up">
                          <MoveUp size={12} className="text-slate-400 hover:text-white"/>
                        </button>
                        {/* Move Down */}
                        <button onClick={e => { e.stopPropagation(); moveSection(section.id, 'down'); }}
                          className="p-1 hover:bg-slate-700 rounded-lg transition-all" title="Move Down">
                          <MoveDown size={12} className="text-slate-400 hover:text-white"/>
                        </button>
                        {/* Duplicate */}
                        <button onClick={e => { e.stopPropagation(); duplicateSection(section.id); }}
                          className="p-1 hover:bg-slate-700 rounded-lg transition-all" title="Duplicate">
                          <Copy size={12} className="text-slate-400 hover:text-white"/>
                        </button>
                        {/* Type Selector */}
                        <select 
                          value={section.type}
                          onClick={e => e.stopPropagation()}
                          onChange={e => {
                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, type: e.target.value } : s) };
                            setPaperData(next); setIsDirty(true); syncPaper(next, version);
                          }}
                          className="bg-slate-800 text-[8px] font-bold text-slate-400 uppercase tracking-widest rounded px-1 py-0.5 border-none outline-none"
                        >
                          <option value="content">Text</option>
                          <option value="abstract">Abstract</option>
                          <option value="image">Image</option>
                        </select>
                        {/* AI Refine */}
                        <button onClick={e => { e.stopPropagation(); aiRefineBlock(section.id); }}
                          className="p-1 hover:bg-indigo-500/20 rounded-lg transition-all" title="AI Refine">
                          {isAiRefining === section.id ? <Loader2 size={12} className="animate-spin text-indigo-400"/> : <Sparkles size={12} className="text-indigo-400"/>}
                        </button>
                        {/* Delete */}
                        <button onClick={e => { e.stopPropagation(); deleteSection(section.id); }}
                          className="p-1 hover:bg-red-500/20 rounded-lg transition-all">
                          <Trash2 size={12} className="text-slate-500 hover:text-red-400"/>
                        </button>
                      </div>
                    </div>
                    {activeBlock === section.id ? (
                      <div className="px-3 pb-3" onClick={e => e.stopPropagation()}>
                        {section.type === 'image' ? (
                          <input value={section.content}
                            onChange={e => updateSection(section.id, e.target.value)}
                            placeholder="Paste image URL here..."
                            className="w-full bg-black/40 border border-slate-700 rounded-lg p-3 text-xs leading-relaxed text-slate-200 outline-none focus:border-amber-500 font-mono"/>
                        ) : (
                          <textarea value={section.content}
                            onChange={e => updateSection(section.id, e.target.value)}
                            autoFocus rows={8}
                            className="w-full bg-black/40 border border-slate-700 rounded-lg p-3 text-xs leading-relaxed text-slate-200 outline-none focus:border-indigo-500 resize-none font-mono"/>
                        )}
                      </div>
                    ) : (
                      <div className="px-4 pb-3">
                        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2 italic">
                          {section.type === 'image' ? (section.content ? `Image: ${section.content}` : 'No image URL...') : (section.content || 'Click to edit...')}
                        </p>
                        {section.content && (
                          <p className="text-[8px] text-slate-600 mt-1 font-mono">{getWordCount(section.content)} words</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Integrated Copilot Chat */}
              {showChat && (
                <div className="h-[300px] border-t border-white/10 flex flex-col bg-slate-900/80 backdrop-blur-xl shrink-0">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-slate-950/40">
                    <span className="text-[9px] font-black uppercase tracking-[0.25em] text-indigo-400">Integrated Copilot</span>
                    <button onClick={() => setShowChat(false)} className="text-slate-500 hover:text-white transition-all">
                      ✕
                    </button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-3 space-y-4 custom-scrollbar">
                    {chatMessages.length === 0 && (
                      <div className="h-full flex flex-col items-center justify-center text-center space-y-2 opacity-40">
                        <MessageSquare size={20} className="text-indigo-400" />
                        <p className="text-[10px] text-slate-400 uppercase tracking-widest leading-relaxed">
                          Request an edit or ask the writer to<br/>explain the logic.
                        </p>
                      </div>
                    )}
                    {chatMessages.map((m, i) => (
                      <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-xl px-3 py-2 text-[11px] leading-relaxed ${m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-200 border border-white/5'}`}>
                          {m.content}
                        </div>
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="flex justify-start">
                        <Loader2 size={12} className="animate-spin text-indigo-400" />
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  {/* Quick Actions */}
                  <div className="px-3 py-2 bg-slate-950/40 border-t border-white/5">
                    <div className="flex gap-1 flex-wrap">
                      {[
                        { label: '✨ Expand', prompt: 'Please expand and add more detail to the current section. Include more technical depth and supporting arguments.' },
                        { label: '📝 Simplify', prompt: 'Please simplify the language in the current section. Make it more accessible while maintaining academic rigor.' },
                        { label: '🎯 Formalize', prompt: 'Please make the current section more formal and academic. Use precise terminology and passive voice where appropriate.' },
                        { label: '🔗 Add citations', prompt: 'Please add placeholder citations to the current section where claims are made. Use [Author, Year] format.' },
                        { label: '📊 Add examples', prompt: 'Please add concrete examples and case studies to illustrate the key points in the current section.' },
                      ].map((action, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setChatInput(action.prompt);
                            // Auto-send after setting input
                            setTimeout(() => {
                              if (id) {
                                const userMsg: ChatMsg = { role: 'user', content: action.prompt };
                                const history = [...chatMessages, userMsg];
                                setChatMessages(history);
                                setChatInput('');
                                setIsChatLoading(true);
                                runsAPI.chat(id, history).then(res => {
                                  const { content } = res.data;
                                  setChatMessages([...history, { role: 'assistant', content: content || 'No response.' }]);
                                }).catch((e: any) => {
                                  toast.error(`Chat failed: ${e?.response?.data?.detail || 'check backend'}`);
                                }).finally(() => setIsChatLoading(false));
                              }
                            }, 50);
                          }}
                          className="px-2 py-1 bg-slate-800 hover:bg-indigo-500/20 text-[9px] font-bold text-slate-300 hover:text-indigo-400 rounded transition-all whitespace-nowrap"
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 bg-slate-950/60 border-t border-white/5">
                    <div className="relative">
                      <textarea
                        value={chatInput}
                        onChange={e => setChatInput(e.target.value)}
                        onKeyDown={e => { if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendChatMessage(); }}}
                        rows={1}
                        placeholder="Request a change..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-3 pr-10 py-2 text-xs text-white resize-none focus:border-indigo-500 outline-none transition-all"
                      />
                      <button
                        onClick={sendChatMessage}
                        disabled={isChatLoading || !chatInput.trim()}
                        className="absolute right-2 top-1.5 text-indigo-400 hover:text-indigo-300 transition-all disabled:opacity-20"
                      >
                        <Send size={14}/>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Live PDF Preview */}
            <div className="flex-1 bg-slate-950 flex flex-col overflow-hidden">
              {/* Fix #5: Update Preview button opposite Live Preview label */}
              <div className="px-4 py-2 border-b border-white/5 bg-slate-900/40 flex items-center justify-between">
                <span className="text-[9px] font-black uppercase tracking-[0.25em] text-[#aaabb0]">Live Preview</span>
                <button
                  disabled={!isDirty}
                  onClick={() => { setPdfKey(k => k + 1); setIsDirty(false); }}
                  className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all ${isDirty ? 'bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 active:scale-95' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
                  title="Refresh PDF preview"
                >
                  <RefreshCw size={10}/> Update Preview
                </button>
              </div>

              <div className="flex-1 overflow-hidden">
                {paperData.sections.length > 0 ? (
                  <PDFViewer key={pdfKey} width="100%" height="100%" showToolbar={false} className="border-none">
                    <InstantPdfDocument data={paperData} />
                  </PDFViewer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center space-y-4 text-center p-12 opacity-30">
                    <div className="text-6xl">📄</div>
                    <p className="text-sm text-[#aaabb0] max-w-xs leading-relaxed">
                      Add sections in the editor to see a live PDF preview here.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* HYPOTHESIS TAB */}
        {activeTab === 'hypothesis' && (
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-3xl mx-auto">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-xl border border-indigo-500/20">💡</div>
                <div>
                  <h2 className="text-xl font-black text-[#f6f6fc]">Research Hypothesis</h2>
                  <p className="text-[9px] text-[#aaabb0] uppercase font-bold tracking-widest">Generated by Lead Research Scientist Agent</p>
                </div>
              </div>
              <div className="p-8 bg-slate-900 rounded-3xl border border-indigo-500/20 shadow-2xl">
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{run.hypothesis || 'No hypothesis was generated for this run.'}</p>
              </div>
            </div>
          </div>
        )}

        {/* EXECUTION TAB — Fix #6: render markdown */}
        {activeTab === 'execution' && (
          <div className="flex-1 overflow-y-auto p-8 space-y-6">
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="p-6 bg-slate-900 rounded-2xl border border-slate-800">
                <h3 className="text-[9px] font-black uppercase tracking-widest text-[#aaabb0] mb-4">Sandbox Code</h3>
                <div className="rounded-xl overflow-hidden border border-[#a1faff]/10 text-xs">
                  <SyntaxHighlighter language="python" style={oneDark} customStyle={{ margin: 0, fontSize: '0.72rem', background: '#020617' }}>
                    {run.generated_code || '# No code generated (Theoretical Mode active).'}
                  </SyntaxHighlighter>
                </div>
              </div>
              <div className="p-6 bg-slate-900 rounded-2xl border border-slate-800">
                <h3 className="text-[9px] font-black uppercase tracking-widest text-[#aaabb0] mb-4">Execution Output</h3>
                {/* Fix #6: ReactMarkdown renders markdown/code blocks like GitHub */}
                <div className="bg-slate-950 rounded-xl border border-emerald-500/10 p-5 prose prose-invert prose-sm max-w-none prose-code:text-emerald-300 prose-pre:bg-transparent">
                  <ReactMarkdown
                    components={{
                      code(props) {
                        const { children, className } = props;
                        const match = /language-(\w+)/.exec(className || '');
                        return match ? (
                          <SyntaxHighlighter language={match[1]} style={oneDark} customStyle={{ fontSize: '0.72rem', margin: 0 }}>
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : <code className="text-emerald-300 bg-emerald-900/20 px-1 rounded">{children}</code>;
                      }
                    }}
                  >
                    {run.execution_output || '*No execution output.*'}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TELEMETRY TAB */}
        {activeTab === 'telemetry' && (
          <div className="flex-1 overflow-y-auto p-8 lg:p-12">
            <div className="max-w-5xl mx-auto space-y-12">
              {run.status === 'running' ? (
                <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
                  <header className="text-center space-y-4">
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse">
                      <Activity size={24} />
                    </div>
                    <h2 className="text-3xl font-black tracking-tight uppercase">Swarm Telemetry</h2>
                    <p className="text-slate-500 max-w-md mx-auto text-xs uppercase tracking-widest">Live Mission Feed • Agentic Research in Progress</p>
                  </header>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Left: Progress Steps */}
                    <div className="glass-card p-8 space-y-6">
                      <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Mission Milestones</h3>
                      <div className="space-y-4 max-h-[500px] overflow-y-auto pr-4 custom-scrollbar">
                        {steps.filter(s => !s.is_internal).map((s, i) => (
                          <div key={i} className="flex gap-4 group">
                            <div className="flex flex-col items-center">
                              <div className={`w-3 h-3 rounded-full mt-1.5 ${s.status === 'done' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-indigo-400 pulse'}`} />
                              {i < steps.length - 1 && <div className="w-px h-full bg-slate-800/50 my-1" />}
                            </div>
                            <div className="flex-1 pb-6">
                              <h3 className={`text-xs font-black uppercase tracking-widest ${s.status === 'done' ? 'text-slate-500' : 'text-white'}`}>{s.title}</h3>
                              <p className="text-[10px] text-slate-600 mt-1.5 leading-relaxed">{s.detail}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Right: Agent Status Cards */}
                    <div className="space-y-4">
                      <div className="glass-card p-6 flex items-center justify-between border-indigo-500/20 bg-indigo-500/5">
                        <div>
                          <h4 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Researcher Agent</h4>
                          <p className="text-[10px] text-slate-500 mt-1 uppercase">Mining ArXiv & Tavily...</p>
                        </div>
                        <div className="h-2 w-2 rounded-full bg-indigo-400 pulse" />
                      </div>
                      <div className="glass-card p-6 flex items-center justify-between border-slate-800">
                        <div>
                          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Logic Critic</h4>
                          <p className="text-[10px] text-slate-600 mt-1 uppercase">Verification Mode: Active</p>
                        </div>
                        <div className={`h-2 w-2 rounded-full ${steps.some(s => s.title.includes('Logic')) ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-slate-800'}`} />
                      </div>
                      <div className="glass-card p-6 flex items-center justify-between border-slate-800">
                        <div>
                          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Academic Writer</h4>
                          <p className="text-[10px] text-slate-600 mt-1 uppercase">Standby for synthesis...</p>
                        </div>
                        <div className={`h-2 w-2 rounded-full ${steps.some(s => s.title.includes('Writer')) ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-slate-800'}`} />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6 animate-in fade-in duration-500">
                  <h2 className="text-xl font-black text-white uppercase tracking-tight">Mission Post-Mortem</h2>
                  {/* Fix #3: Parse grounding array and render cards */}
                  {(() => {
                    const grounding = run.summary_json?.grounding;
                    const cards: any[] = Array.isArray(grounding) ? grounding : [];
                    const otherEntries = Object.entries(run.summary_json || {}).filter(([k]) => k !== 'grounding');
                    return (
                      <>
                        {otherEntries.length > 0 && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                            {otherEntries.map(([k, v]) => (
                              <div key={k} className="p-4 bg-slate-900/50 rounded-2xl border border-slate-800 flex justify-between items-center">
                                <span className="text-[10px] font-black text-[#aaabb0] uppercase tracking-[0.15em]">{k.replace(/_/g, ' ')}</span>
                                <span className="text-xs font-bold text-[#a1faff]">{typeof v === 'object' ? JSON.stringify(v).slice(0, 40) : String(v)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {cards.length > 0 ? (
                          <div className="space-y-3">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-indigo-400">Grounding Cards — RefLens Verification</h3>
                            {cards.map((card, i) => (
                              <div key={i} className="p-5 bg-slate-900 rounded-2xl border border-indigo-500/20 hover:border-indigo-500/40 transition-all space-y-3">
                                <div className="flex items-start gap-3">
                                  <span className="shrink-0 mt-0.5 w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 text-[9px] font-black flex items-center justify-center">{i+1}</span>
                                  <p className="text-xs font-bold text-white leading-relaxed">{card.claim}</p>
                                </div>
                                {card.verbatim_quote && (
                                  <blockquote className="ml-8 pl-3 border-l-2 border-indigo-500/40 text-[11px] text-slate-400 italic leading-relaxed">
                                    "{card.verbatim_quote}"
                                  </blockquote>
                                )}
                                {card.verbatim_quote === 'SPECULATIVE — no direct evidence found.' && (
                                  <span className="ml-8 text-[9px] font-black uppercase text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">⚠ Speculative</span>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-20 opacity-40">
                            <Activity size={40} className="mx-auto mb-4"/>
                            <p className="italic text-sm">No telemetry history for this mission.</p>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 3px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
      `}</style>
    </div>
  );
}
