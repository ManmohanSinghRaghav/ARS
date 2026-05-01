import re

path = 'frontend/src/pages/RunDetailPage.tsx'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add import
if 'react-resizable-panels' not in text:
    text = text.replace(\"import { Prism as SyntaxHighlighter }\", \"import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';\\nimport { Prism as SyntaxHighlighter }\")

# Rewrite tabs area
old_tabs = '''      {/* Tab Bar */}
      <div className=\"flex gap-0 border-b border-white/5 shrink-0 bg-slate-950/40\">
        {tabs.filter(t => run.status !== 'running' || t.key === 'telemetry').map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={\lex items-center gap-2 px-5 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-b-2 \\}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>'''

new_tabs = '''      {/* Tab Bar */}
      <div className=\"flex gap-0 border-b border-white/5 shrink-0 bg-slate-950/40\">
        {tabs.filter(t => run.status !== 'running' || t.key === 'telemetry').map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={\lex items-center gap-2 px-5 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-b-2 \\}>
            {t.icon} {t.label}
          </button>
        ))}
        {run.status !== 'running' && (
           <button onClick={() => setActiveTab('tiled')}
             className={\lex items-center gap-2 px-5 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-b-2 \\}>
             <Activity size={15}/> Tiled IDE
           </button>
        )}
      </div>'''

text = text.replace(old_tabs, new_tabs)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
