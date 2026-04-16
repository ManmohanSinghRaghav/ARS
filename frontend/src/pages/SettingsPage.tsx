import { useState, useEffect, FormEvent } from 'react';
import { settingsAPI } from '../api/client';
import toast from 'react-hot-toast';

interface Settings {
  llm_backend: string;
  mlx_model: string;
  ollama_model: string;
  ollama_url: string;
  tavily_api_key_set: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form state
  const [llmBackend, setLlmBackend] = useState('gemini');
  const [mlxModel, setMlxModel] = useState('');
  const [ollamaModel, setOllamaModel] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [tavilyKey, setTavilyKey] = useState('');

  useEffect(() => {
    settingsAPI
      .get()
      .then((res) => {
        const s = res.data;
        setSettings(s);
        setLlmBackend(s.llm_backend);
        setMlxModel(s.mlx_model);
        setOllamaModel(s.ollama_model);
        setOllamaUrl(s.ollama_url);
      })
      .catch(() => toast.error('Failed to load settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: Record<string, string | undefined> = {
        llm_backend: llmBackend,
        mlx_model: mlxModel,
        ollama_model: ollamaModel,
        ollama_url: ollamaUrl,
      };
      // Only send tavily key if user entered something
      if (tavilyKey) {
        payload.tavily_api_key = tavilyKey;
      }
      const res = await settingsAPI.update(payload);
      setSettings(res.data);
      setTavilyKey('');
      toast.success('Settings saved successfully');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-[#f6f6fc] mb-6">LLM Settings</h1>

      <form onSubmit={handleSubmit} className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6 space-y-5">
        {/* LLM Backend */}
        <div>
          <label className="block text-sm font-medium text-[#f6f6fc] mb-1">LLM Backend</label>
          <select
            value={llmBackend}
            onChange={(e) => setLlmBackend(e.target.value)}
            className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc]"
          >
            <option value="gemini">Gemini / Groq (Configured via .env)</option>
            <option value="ollama" disabled>Ollama (Currently Unsupported)</option>
            <option value="mlx" disabled>MLX (Currently Unsupported)</option>
          </select>
        </div>

        {/* Conditional fields */}
        {llmBackend === 'ollama' && (
          <>
            <div>
              <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Ollama Model</label>
              <input
                type="text"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0]"
                placeholder="e.g., qwen2.5:3b"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Ollama URL</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0]"
                placeholder="http://localhost:11434"
              />
            </div>
          </>
        )}

        {llmBackend === 'mlx' && (
          <div>
            <label className="block text-sm font-medium text-[#f6f6fc] mb-1">MLX Model</label>
            <input
              type="text"
              value={mlxModel}
              onChange={(e) => setMlxModel(e.target.value)}
              className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0]"
              placeholder="e.g., mlx-community/Qwen2.5-3B-Instruct-bf16"
            />
          </div>
        )}

        {/* Tavily API Key */}
        <div>
          <label className="block text-sm font-medium text-[#f6f6fc] mb-1">
            Tavily API Key
            {settings?.tavily_api_key_set && (
              <span className="ml-2 text-green-300 text-xs font-normal">(configured)</span>
            )}
          </label>
          <input
            type="password"
            value={tavilyKey}
            onChange={(e) => setTavilyKey(e.target.value)}
            className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0]"
            placeholder={settings?.tavily_api_key_set ? '••••••••  (leave blank to keep current)' : 'Enter Tavily API key'}
          />
          <p className="text-xs text-[#aaabb0] mt-1">Required for web search. Get a key at tavily.com</p>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full py-2.5 bg-[#a1faff]/20 text-[#a1faff] rounded-lg font-medium hover:bg-[#a1faff]/30 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}
