import re

path = 'frontend/src/pages/RunDetailPage.tsx'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. State addition
if 'const [isDirty, setIsDirty] = useState(false);' not in text:
    state_old = \"  const [sessionTitle, setSessionTitle] = useState('');\\n  const chatEndRef = useRef<HTMLDivElement>(null);\"
    state_new = \"  const [sessionTitle, setSessionTitle] = useState('');\\n  const [isDirty, setIsDirty] = useState(false);\\n  const chatEndRef = useRef<HTMLDivElement>(null);\"
    text = text.replace(state_old, state_new)

# 2. setIsDirty in handlers
if 'setIsDirty(true)' not in text:
    h_old1 = \"    const next = { ...paperData, sections: paperData.sections.map(s => s.id === blockId ? { ...s, content } : s) };\\n    setPaperData(next);\\n    syncPaper(next, version);\"
    h_new1 = \"    const next = { ...paperData, sections: paperData.sections.map(s => s.id === blockId ? { ...s, content } : s) };\\n    setPaperData(next);\\n    setIsDirty(true);\\n    syncPaper(next, version);\"
    text = text.replace(h_old1, h_new1)

    h_old2 = \"    const next = { ...paperData, metadata: { ...paperData.metadata, [key]: val } };\\n    setPaperData(next);\\n    syncPaper(next, version);\"
    h_new2 = \"    const next = { ...paperData, metadata: { ...paperData.metadata, [key]: val } };\\n    setPaperData(next);\\n    setIsDirty(true);\\n    syncPaper(next, version);\"
    text = text.replace(h_old2, h_new2)

    h_old3 = \"      sections: [...paperData.sections, {\\n        id: \sec_\\, type: 'content',\\n        title: \Section \\, content: ''\\n      }]\\n    };\\n    setPaperData(next);\\n    syncPaper(next, version);\"
    h_new3 = \"      sections: [...paperData.sections, {\\n        id: \sec_\\, type: 'content',\\n        title: \Section \\, content: ''\\n      }]\\n    };\\n    setPaperData(next);\\n    setIsDirty(true);\\n    syncPaper(next, version);\"
    text = text.replace(h_old3, h_new3)

    h_old4 = \"  const deleteSection = (blockId: string) => {\\n    const next = { ...paperData, sections: paperData.sections.filter(s => s.id !== blockId) };\\n    setPaperData(next);\\n    syncPaper(next, version);\\n  };\"
    h_new4 = \"  const deleteSection = (blockId: string) => {\\n    const next = { ...paperData, sections: paperData.sections.filter(s => s.id !== blockId) };\\n    setPaperData(next);\\n    setIsDirty(true);\\n    syncPaper(next, version);\\n  };\"
    text = text.replace(h_old4, h_new4)

# 3. onChange metadata inputs
    in_old1 = \"onChange={e => {\\n                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, title: e.target.value } : s) };\\n                            setPaperData(next); syncPaper(next, version);\\n                          }}\"
    in_new1 = \"onChange={e => {\\n                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, title: e.target.value } : s) };\\n                            setPaperData(next); setIsDirty(true); syncPaper(next, version);\\n                          }}\"
    text = text.replace(in_old1, in_new1)

    in_old2 = \"onChange={e => {\\n                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, type: e.target.value } : s) };\\n                            setPaperData(next); syncPaper(next, version);\\n                          }}\"
    in_new2 = \"onChange={e => {\\n                            const next = { ...paperData, sections: paperData.sections.map(s => s.id === section.id ? { ...s, type: e.target.value } : s) };\\n                            setPaperData(next); setIsDirty(true); syncPaper(next, version);\\n                          }}\"
    text = text.replace(in_old2, in_new2)


# 4. Filter steps
if 'steps.filter(s => !s.is_internal)' not in text:
    text = text.replace(\"{steps.map((s, i) => (\", \"{steps.filter(s => !s.is_internal).map((s, i) => (\")

# 5. Gated tabs
if 'filter(t => run.status' not in text:
    text = text.replace(\"{tabs.map(t => (\", \"{tabs.filter(t => run.status !== 'running' || t.key === 'telemetry').map(t => (\")

# 6. Tab redirection
if \"setActiveTab('telemetry')\" not in text:
    red_old = \"if (loading) return (\"
    red_new = \"  useEffect(() => {\\n    if (run?.status === 'running' && activeTab !== 'telemetry') {\\n      setActiveTab('telemetry');\\n    }\\n  }, [run?.status, activeTab]);\\n\\n  if (loading) return (\"
    text = text.replace(red_old, red_new)

# 7. Button swap
if '!isDirty' not in text:
    btn_old = \"                <button\\n                  onClick={() => setPdfKey(k => k + 1)}\\n                  className=\\\"flex items-center gap-1 px-2 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[9px] font-black uppercase tracking-widest transition-all active:scale-95\\\"\"
    btn_new = \"                <button\\n                  disabled={!isDirty}\\n                  onClick={() => { setPdfKey(k => k + 1); setIsDirty(false); }}\\n                  className={\\\lex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all \\\\}\"
    text = text.replace(btn_old, btn_new)


with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
