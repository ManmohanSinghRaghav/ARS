import { useState, useEffect, FormEvent } from 'react';
import { settingsAPI } from '../api/client';
import toast from 'react-hot-toast';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Settings {
  gemini_api_key_set: boolean;
  groq_api_key_set: boolean;
  openai_api_key_set: boolean;
  claude_api_key_set: boolean;
  tavily_api_key_set: boolean;
  execution_enabled: boolean;

  heavy_model: string;
  heavy_rpm: number;
  heavy_tpm: number;
  heavy_fallback_model: string;
  heavy_fallback_rpm: number;
  heavy_fallback_tpm: number;

  light_model: string;
  light_rpm: number;
  light_tpm: number;
  light_fallback_model: string;
  light_fallback_rpm: number;
  light_fallback_tpm: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const PROVIDERS = [
  { value: 'gemini/',    label: 'Gemini',    icon: '✨', color: 'text-blue-400',   hint: 'gemini/gemini-2.0-flash' },
  { value: 'groq/',      label: 'Groq',      icon: '⚡', color: 'text-orange-400', hint: 'groq/llama-3.3-70b-versatile' },
  { value: 'openai/',    label: 'OpenAI',    icon: '🟢', color: 'text-green-400',  hint: 'openai/gpt-4o-mini' },
  { value: 'anthropic/', label: 'Claude',    icon: '🎭', color: 'text-rose-400',   hint: 'anthropic/claude-3-5-sonnet-latest' },
  { value: 'custom',     label: 'Advanced',  icon: '🔧', color: 'text-purple-400', hint: 'e.g., mistral/' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function deriveProvider(modelStr: string): string {
  if (!modelStr) return 'gemini/';
  const known = PROVIDERS.find(p => p.value !== 'custom' && modelStr.startsWith(p.value));
  return known ? known.value : 'custom';
}

function derivePrefix(modelStr: string): string {
  if (!modelStr) return '';
  const slash = modelStr.indexOf('/');
  return slash !== -1 ? modelStr.slice(0, slash + 1) : '';
}

function deriveModelName(modelStr: string): string {
  if (!modelStr) return '';
  const slash = modelStr.indexOf('/');
  return slash !== -1 ? modelStr.slice(slash + 1) : modelStr;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface ApiKeyInputProps {
  label: string;
  value: string;
  isSet: boolean;
  onChange: (v: string) => void;
  icon: string;
}

function ApiKeyInput({ label, value, isSet, onChange, icon }: ApiKeyInputProps) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-bold text-[#f6f6fc] tracking-wide">
        <span className="text-lg">{icon}</span> {label}
      </label>
      <div className="relative group">
        <input
          type="password"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={isSet ? '••••••••••••••••' : `Enter ${label} API Key...`}
          className={`w-full px-5 py-4 bg-slate-900/80 border rounded-2xl text-base transition-all outline-none focus:ring-4 focus:ring-[#a1faff]/10 ${
            isSet ? 'border-green-500/40 bg-green-500/5' : 'border-[#a1faff]/20'
          } group-hover:border-[#a1faff]/40`}
        />
        {isSet && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
             <span className="text-[10px] font-black text-green-500 bg-green-500/10 px-2 py-1 rounded-lg tracking-widest border border-green-500/20">
              CONFIGURED
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

interface ModelBlockProps {
  label: string;
  badge: string;
  badgeColor: string;
  provider: string;
  prefix: string;
  modelName: string;
  rpm: number;
  tpm: number;
  onProviderChange: (v: string) => void;
  onPrefixChange: (v: string) => void;
  onModelNameChange: (v: string) => void;
  onRpmChange: (v: number) => void;
  onTpmChange: (v: number) => void;
}

function ModelBlock({
  label, badge, badgeColor,
  provider, prefix, modelName, rpm, tpm,
  onProviderChange, onPrefixChange, onModelNameChange, onRpmChange, onTpmChange
}: ModelBlockProps) {
  const fullModelId = provider === 'custom' ? `${prefix}${modelName}` : `${provider}${modelName}`;

  return (
    <div className="p-8 rounded-3xl bg-slate-900/60 border border-[#a1faff]/10 space-y-6 shadow-2xl backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-black text-[#f6f6fc] tracking-tight">{label}</h3>
          <p className="text-[10px] text-[#aaabb0] font-bold uppercase tracking-[0.15em] mt-0.5">{badge}</p>
        </div>
        <div className={`px-3 py-1 rounded-full text-[10px] font-black border uppercase tracking-widest ${badgeColor}`}>
          ACTIVE
        </div>
      </div>

      {/* Provider Selector */}
      <div className="grid grid-cols-5 gap-2 p-1.5 bg-slate-950/80 rounded-2xl border border-[#a1faff]/5">
        {PROVIDERS.map(p => (
          <button
            key={p.value}
            type="button"
            onClick={() => onProviderChange(p.value)}
            className={`flex flex-col items-center justify-center py-3 rounded-xl transition-all duration-300 ${
              provider === p.value
                ? 'bg-[#a1faff]/15 text-[#a1faff] shadow-lg scale-[1.02] border border-[#a1faff]/20'
                : 'text-[#aaabb0] hover:text-[#f6f6fc] hover:bg-white/5'
            }`}
          >
            <span className="text-xl mb-1">{p.icon}</span>
            <span className="text-[10px] font-black uppercase tracking-tighter">{p.label}</span>
          </button>
        ))}
      </div>

      {/* Inputs */}
      <div className="space-y-5">
        {provider === 'custom' && (
          <div className="animate-in fade-in slide-in-from-top-2">
            <label className="block text-xs font-black text-[#aaabb0] mb-2 uppercase tracking-widest">LiteLLM Prefix (Advanced)</label>
            <input
              type="text"
              value={prefix}
              onChange={e => onPrefixChange(e.target.value)}
              placeholder="e.g., bedrock/ or azure/"
              className="w-full px-4 py-3 bg-slate-950/80 border border-[#a1faff]/20 rounded-xl text-sm font-mono text-[#a1faff] focus:border-[#a1faff]/50 outline-none transition-all"
            />
          </div>
        )}

        <div>
          <label className="block text-xs font-black text-[#aaabb0] mb-2 uppercase tracking-widest">Model Identifier</label>
          <div className="flex items-stretch">
            {provider !== 'custom' && (
              <div className="flex items-center px-4 bg-slate-800 border border-r-0 border-[#a1faff]/20 rounded-l-xl text-xs font-mono text-[#a1faff]/80">
                {provider}
              </div>
            )}
            <input
              type="text"
              value={modelName}
              onChange={e => onModelNameChange(e.target.value)}
              placeholder="e.g., gemini-1.5-pro"
              className={`flex-1 px-4 py-3 bg-slate-950/80 border border-[#a1faff]/20 text-sm font-mono text-[#f6f6fc] focus:border-[#a1faff]/50 outline-none transition-all ${
                provider !== 'custom' ? 'rounded-r-xl' : 'rounded-xl'
              }`}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="block text-[10px] font-black text-[#aaabb0] uppercase tracking-widest">Requests / Min (RPM)</label>
            <input
              type="number"
              value={rpm}
              onChange={e => onRpmChange(Number(e.target.value))}
              className="w-full px-4 py-3 bg-slate-950/80 border border-[#a1faff]/20 rounded-xl text-sm font-mono text-[#f6f6fc] focus:border-[#a1faff]/50 outline-none"
            />
          </div>
          <div className="space-y-2">
            <label className="block text-[10px] font-black text-[#aaabb0] uppercase tracking-widest">Tokens / Min (TPM)</label>
            <input
              type="number"
              value={tpm}
              onChange={e => onTpmChange(Number(e.target.value))}
              className="w-full px-4 py-3 bg-slate-950/80 border border-[#a1faff]/20 rounded-xl text-sm font-mono text-[#f6f6fc] focus:border-[#a1faff]/50 outline-none"
            />
          </div>
        </div>
      </div>
      
      <div className="pt-4 border-t border-white/5">
        <div className="flex items-center gap-2">
           <span className="text-[9px] font-black text-[#aaabb0] uppercase tracking-[0.2em]">Active Routing:</span>
           <span className="font-mono text-xs text-[#a1faff] bg-[#a1faff]/10 px-2 py-1 rounded-md border border-[#a1faff]/20">
             {fullModelId}
           </span>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form State
  const [keys, setKeys] = useState({ gemini: '', groq: '', openai: '', claude: '', tavily: '' });
  const [executionEnabled, setExecutionEnabled] = useState(true);

  // Heavy Model State
  const [heavy, setHeavy] = useState({ provider: 'gemini/', prefix: '', modelName: '', rpm: 15, tpm: 30000 });
  const [heavyFb, setHeavyFb] = useState({ provider: 'gemini/', prefix: '', modelName: '', rpm: 15, tpm: 30000 });

  // Light Model State
  const [light, setLight] = useState({ provider: 'gemini/', prefix: '', modelName: '', rpm: 15, tpm: 30000 });
  const [lightFb, setLightFb] = useState({ provider: 'gemini/', prefix: '', modelName: '', rpm: 15, tpm: 30000 });

  useEffect(() => {
    settingsAPI.get().then(res => {
      const s: Settings = res.data;
      setSettings(s);
      setExecutionEnabled(s.execution_enabled);

      const mapModel = (mStr: string, rpm: number, tpm: number) => ({
        provider: deriveProvider(mStr),
        prefix: derivePrefix(mStr),
        modelName: deriveModelName(mStr),
        rpm: rpm || 15,
        tpm: tpm || 30000
      });

      setHeavy(mapModel(s.heavy_model, s.heavy_rpm, s.heavy_tpm));
      setHeavyFb(mapModel(s.heavy_fallback_model, s.heavy_fallback_rpm, s.heavy_fallback_tpm));
      setLight(mapModel(s.light_model, s.light_rpm, s.light_tpm));
      setLightFb(mapModel(s.light_fallback_model, s.light_fallback_rpm, s.light_fallback_tpm));
    })
    .catch(() => toast.error('Failed to load system parameters'))
    .finally(() => setLoading(false));
  }, []);

  const buildModelStr = (m: any) => m.provider === 'custom' ? `${m.prefix}${m.modelName}` : `${m.provider}${m.modelName}`;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: any = {
        ...(keys.gemini ? { gemini_api_key: keys.gemini } : {}),
        ...(keys.groq   ? { groq_api_key:   keys.groq   } : {}),
        ...(keys.openai ? { openai_api_key: keys.openai } : {}),
        ...(keys.claude ? { claude_api_key: keys.claude } : {}),
        ...(keys.tavily ? { tavily_api_key: keys.tavily } : {}),

        execution_enabled: executionEnabled,
        heavy_model: buildModelStr(heavy), heavy_rpm: heavy.rpm, heavy_tpm: heavy.tpm,
        heavy_fallback_model: buildModelStr(heavyFb), heavy_fallback_rpm: heavyFb.rpm, heavy_fallback_tpm: heavyFb.tpm,
        light_model: buildModelStr(light), light_rpm: light.rpm, light_tpm: light.tpm,
        light_fallback_model: buildModelStr(lightFb), light_fallback_rpm: lightFb.rpm, light_fallback_tpm: lightFb.tpm,
      };

      await settingsAPI.update(payload);
      toast.success('System configuration synchronized');
      setKeys({ gemini: '', groq: '', openai: '', claude: '', tavily: '' });
      const res = await settingsAPI.get();
      setSettings(res.data);
    } catch (err: any) {
      toast.error('Synchronization failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="w-16 h-16 border-[6px] border-[#a1faff]/10 border-t-[#a1faff] rounded-full animate-spin" />
      <div className="text-center">
        <p className="text-sm font-black text-[#a1faff] animate-pulse uppercase tracking-[0.3em]">Initialising Security Layer</p>
        <p className="text-[10px] text-[#aaabb0] uppercase tracking-widest mt-2">Loading Protected Settings...</p>
      </div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto px-6 py-16 space-y-16 animate-in fade-in duration-700">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-8 border-b border-white/5 pb-12">
        <div className="space-y-2">
          <div className="flex items-center gap-4">
             <div className="px-3 py-1 bg-[#a1faff]/10 border border-[#a1faff]/20 rounded-lg text-[10px] font-black text-[#a1faff] uppercase tracking-[0.2em]">v3.1 Stable</div>
             <h1 className="text-5xl font-black text-[#f6f6fc] tracking-tighter italic">System Parameters</h1>
          </div>
          <p className="text-[#aaabb0] text-lg font-medium">Configure global orchestration, API thresholds, and execution modes.</p>
        </div>
        
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-3 px-5 py-2.5 bg-slate-900/50 border border-white/5 rounded-2xl">
            <div className={`w-2.5 h-2.5 rounded-full animate-pulse ${saving ? 'bg-amber-500' : 'bg-green-500'}`} />
            <span className="text-xs font-black text-[#f6f6fc] uppercase tracking-widest">
              {saving ? 'Syncing...' : 'Encrypted & Active'}
            </span>
          </div>
          <p className="text-[10px] text-[#aaabb0] uppercase font-bold tracking-widest">Local Session ID: {Math.random().toString(36).substring(7)}</p>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="space-y-16">
        
        {/* ── API Keys ── */}
        <section className="space-y-8">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center text-2xl shadow-2xl border border-white/10 ring-4 ring-white/5">🔐</div>
            <div>
              <h2 className="text-2xl font-black text-[#f6f6fc] tracking-tight">Security & Access</h2>
              <p className="text-xs text-[#aaabb0] uppercase font-bold tracking-widest mt-1">Multi-Provider API Vault</p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8 p-10 rounded-[2.5rem] bg-slate-900/40 border border-[#a1faff]/10 backdrop-blur-md">
            <ApiKeyInput label="Gemini AI" icon="✨" isSet={!!settings?.gemini_api_key_set} value={keys.gemini} onChange={v => setKeys({...keys, gemini: v})} />
            <ApiKeyInput label="Groq Cloud" icon="⚡" isSet={!!settings?.groq_api_key_set} value={keys.groq} onChange={v => setKeys({...keys, groq: v})} />
            <ApiKeyInput label="OpenAI API" icon="🟢" isSet={!!settings?.openai_api_key_set} value={keys.openai} onChange={v => setKeys({...keys, openai: v})} />
            <ApiKeyInput label="Anthropic / Claude" icon="🎭" isSet={!!settings?.claude_api_key_set} value={keys.claude} onChange={v => setKeys({...keys, claude: v})} />
            <div className="md:col-span-2 pt-6 border-t border-white/5">
              <ApiKeyInput label="Tavily Web Search" icon="🌐" isSet={!!settings?.tavily_api_key_set} value={keys.tavily} onChange={v => setKeys({...keys, tavily: v})} />
            </div>
          </div>
        </section>

        {/* ── Global Mode Switch ── */}
        <section className="p-10 rounded-[2.5rem] bg-gradient-to-br from-slate-900/60 to-slate-800/20 border border-[#a1faff]/10 flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="space-y-2 text-center md:text-left">
            <h2 className="text-2xl font-black text-[#f6f6fc] tracking-tight">Agent Execution Mode</h2>
            <p className="text-[#aaabb0] font-medium max-w-md">Toggle between **Empirical Experiments** (Modal Sandbox) and **Theoretical Derivation** (Static Analysis).</p>
          </div>
          <button
            type="button"
            onClick={() => setExecutionEnabled(!executionEnabled)}
            className={`relative flex items-center gap-4 px-8 py-5 rounded-3xl transition-all duration-500 border-2 ${
              executionEnabled 
                ? 'bg-[#a1faff]/10 border-[#a1faff]/50 text-[#a1faff]' 
                : 'bg-rose-500/10 border-rose-500/50 text-rose-500'
            }`}
          >
            <div className="flex flex-col items-center">
              <span className="text-2xl mb-1">{executionEnabled ? '🧪' : '📚'}</span>
              <span className="text-[10px] font-black uppercase tracking-[0.2em]">{executionEnabled ? 'Experimental' : 'Theoretical'}</span>
            </div>
            <div className={`w-16 h-8 rounded-full relative transition-colors duration-500 ${executionEnabled ? 'bg-[#a1faff]/30' : 'bg-rose-500/30'}`}>
              <div className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow-xl transition-all duration-500 ${executionEnabled ? 'left-9' : 'left-1'}`} />
            </div>
          </button>
        </section>

        {/* ── Engines ── */}
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Heavy Engine */}
          <section className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center text-2xl shadow-2xl border border-white/10 ring-4 ring-white/5">🧠</div>
              <div>
                <h2 className="text-2xl font-black text-[#f6f6fc] tracking-tight">Reasoning Cluster</h2>
                <p className="text-xs text-[#aaabb0] uppercase font-bold tracking-widest mt-1">Lead Scientist • Writer • Critic</p>
              </div>
            </div>
            <div className="space-y-8">
              <ModelBlock
                label="Primary Engine" badge="REASONING_P" badgeColor="border-[#a1faff]/40 text-[#a1faff] bg-[#a1faff]/5"
                {...heavy} onProviderChange={p => setHeavy({...heavy, provider: p})} onPrefixChange={p => setHeavy({...heavy, prefix: p})} 
                onModelNameChange={n => setHeavy({...heavy, modelName: n})} onRpmChange={r => setHeavy({...heavy, rpm: r})} onTpmChange={t => setHeavy({...heavy, tpm: t})}
              />
              <ModelBlock
                label="Emergency Fallback" badge="REASONING_F" badgeColor="border-amber-500/40 text-amber-500 bg-amber-500/5"
                {...heavyFb} onProviderChange={p => setHeavyFb({...heavyFb, provider: p})} onPrefixChange={p => setHeavyFb({...heavyFb, prefix: p})} 
                onModelNameChange={n => setHeavyFb({...heavyFb, modelName: n})} onRpmChange={r => setHeavyFb({...heavyFb, rpm: r})} onTpmChange={t => setHeavyFb({...heavyFb, tpm: t})}
              />
            </div>
          </section>

          {/* Light Engine */}
          <section className="space-y-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center text-2xl shadow-2xl border border-white/10 ring-4 ring-white/5">⚡</div>
              <div>
                <h2 className="text-2xl font-black text-[#f6f6fc] tracking-tight">Extraction Cluster</h2>
                <p className="text-xs text-[#aaabb0] uppercase font-bold tracking-widest mt-1">Literature Researcher • RAG Specialist</p>
              </div>
            </div>
            <div className="space-y-8">
              <ModelBlock
                label="Primary Engine" badge="EXTRACTION_P" badgeColor="border-[#a1faff]/40 text-[#a1faff] bg-[#a1faff]/5"
                {...light} onProviderChange={p => setLight({...light, provider: p})} onPrefixChange={p => setLight({...light, prefix: p})} 
                onModelNameChange={n => setLight({...light, modelName: n})} onRpmChange={r => setLight({...light, rpm: r})} onTpmChange={t => setLight({...light, tpm: t})}
              />
              <ModelBlock
                label="Secondary Fallback" badge="EXTRACTION_F" badgeColor="border-amber-500/40 text-amber-500 bg-amber-500/5"
                {...lightFb} onProviderChange={p => setLightFb({...lightFb, provider: p})} onPrefixChange={p => setLightFb({...lightFb, prefix: p})} 
                onModelNameChange={n => setLightFb({...lightFb, modelName: n})} onRpmChange={r => setLightFb({...lightFb, rpm: r})} onTpmChange={t => setLightFb({...lightFb, tpm: t})}
              />
            </div>
          </section>
        </div>

        <footer className="sticky bottom-10 z-30 pt-10">
          <button
            type="submit"
            disabled={saving}
            className="group relative w-full overflow-hidden rounded-[2rem] bg-[#a1faff] py-7 font-black text-slate-950 text-xl uppercase tracking-[0.4em] shadow-[0_20px_50px_rgba(161,250,255,0.3)] transition-all hover:scale-[1.01] hover:shadow-[0_25px_60px_rgba(161,250,255,0.4)] active:scale-[0.98] disabled:opacity-50"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/40 to-white/0 -translate-x-full group-hover:translate-x-full transition-transform duration-[1500ms] ease-in-out" />
            <div className="relative flex items-center justify-center gap-4">
              {saving ? (
                <>
                  <div className="w-5 h-5 border-4 border-slate-950/20 border-t-slate-950 rounded-full animate-spin" />
                  <span>Synchronizing System...</span>
                </>
              ) : (
                <>
                  <span>Commit System Parameters</span>
                  <span className="text-2xl group-hover:translate-x-2 transition-transform">→</span>
                </>
              )}
            </div>
          </button>
          <p className="text-center text-[10px] text-[#aaabb0] font-bold uppercase tracking-[0.3em] mt-6 animate-pulse">
            Warning: These parameters affect global agentic stability. Commit with caution.
          </p>
        </footer>
      </form>
    </div>
  );
}
