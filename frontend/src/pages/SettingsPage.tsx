import { useState, useEffect, FormEvent } from 'react';
import { settingsAPI } from '../api/client';
import toast from 'react-hot-toast';

interface Settings {
  llm_backend: string;
  gemini_model: string;
  mlx_model: string;
  ollama_model: string;
  ollama_url: string;
  tavily_api_key_set: boolean;
}

// Gemini model information
const GEMINI_MODELS = [
  {
    id: 'gemini-3.1-flash-lite-preview',
    name: '🚀 Flash Lite',
    description: 'Fast & efficient. Best for free tier. Recommended.',
    quota: 'Higher free tier quota',
    speed: 'Fastest',
    cost: 'Cheapest',
    useCase: 'Default choice for research generation'
  },
  {
    id: 'gemini-3.1-flash-preview',
    name: '⚡ Flash',
    description: 'Balanced speed and quality',
    quota: 'Good free tier quota',
    speed: 'Fast',
    cost: 'Low',
    useCase: 'Good balance of quality and speed'
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: '🧠 Pro',
    description: 'Most capable model. Better quality.',
    quota: 'Limited free tier',
    speed: 'Moderate',
    cost: 'Higher',
    useCase: 'Complex research problems (requires billing)'
  },
  {
    id: 'gemini-2.0-flash-exp',
    name: '✨ 2.0 Flash',
    description: 'Latest experimental model',
    quota: 'Limited availability',
    speed: 'Very Fast',
    cost: 'Varies',
    useCase: 'Experimental research'
  }
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form state
  const [llmBackend, setLlmBackend] = useState('gemini');
  const [geminiModel, setGeminiModel] = useState('gemini-3.1-flash-lite-preview');
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
        setGeminiModel(s.gemini_model || 'gemini-3.1-flash-lite-preview');
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
        gemini_model: geminiModel,
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

  const currentModelInfo = GEMINI_MODELS.find(m => m.id === geminiModel);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-3xl font-bold text-[#f6f6fc] mb-2">LLM Settings</h1>
      <p className="text-[#aaabb0] mb-6">Configure your AI model preferences and API keys</p>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* LLM Backend Selection */}
        <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6">
          <label className="block text-lg font-bold text-[#f6f6fc] mb-4">LLM Backend</label>
          <select
            value={llmBackend}
            onChange={(e) => setLlmBackend(e.target.value)}
            className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc]"
          >
            <option value="gemini">✅ Gemini / Groq (Configured)</option>
            <option value="ollama" disabled>Ollama (Currently Unsupported)</option>
            <option value="mlx" disabled>MLX (Currently Unsupported)</option>
          </select>
        </div>

        {/* Gemini Model Selection */}
        {llmBackend === 'gemini' && (
          <div className="space-y-6">
            {/* Current Model Info Card */}
            {currentModelInfo && (
              <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl border border-[#a1faff]/30 p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-[#a1faff] mb-2">{currentModelInfo.name}</h3>
                    <p className="text-[#f6f6fc] mb-4">{currentModelInfo.description}</p>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-[#aaabb0]">📊 Quota:</span>
                        <p className="text-[#f6f6fc] font-medium">{currentModelInfo.quota}</p>
                      </div>
                      <div>
                        <span className="text-[#aaabb0]">⚡ Speed:</span>
                        <p className="text-[#f6f6fc] font-medium">{currentModelInfo.speed}</p>
                      </div>
                      <div>
                        <span className="text-[#aaabb0]">💰 Cost:</span>
                        <p className="text-[#f6f6fc] font-medium">{currentModelInfo.cost}</p>
                      </div>
                      <div>
                        <span className="text-[#aaabb0]">🎯 Use Case:</span>
                        <p className="text-[#f6f6fc] font-medium">{currentModelInfo.useCase}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Model Selection Grid */}
            <div>
              <label className="block text-lg font-bold text-[#f6f6fc] mb-4">Select Gemini Model</label>
              <p className="text-[#aaabb0] text-sm mb-4">
                💡 Tip: Flash Lite is recommended for free tier. The system will automatically fallback to Flash Lite if quota is exceeded.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {GEMINI_MODELS.map((model) => (
                  <label
                    key={model.id}
                    className={`relative cursor-pointer rounded-xl border-2 p-4 transition-all ${
                      geminiModel === model.id
                        ? 'border-[#a1faff] bg-slate-700/50'
                        : 'border-[#a1faff]/20 bg-slate-800/30 hover:bg-slate-800/50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="gemini_model"
                      value={model.id}
                      checked={geminiModel === model.id}
                      onChange={(e) => setGeminiModel(e.target.value)}
                      className="absolute opacity-0"
                    />
                    <div className="flex items-start gap-3">
                      <div className={`h-5 w-5 rounded-full border-2 mt-0.5 ${
                        geminiModel === model.id ? 'border-[#a1faff] bg-[#a1faff]' : 'border-[#a1faff]/40'
                      }`} />
                      <div className="flex-1">
                        <h4 className="font-bold text-[#f6f6fc] mb-1">{model.name}</h4>
                        <p className="text-sm text-[#aaabb0] mb-2">{model.description}</p>
                        <div className="text-xs space-y-1">
                          <p className="text-[#a1faff]">📊 {model.quota}</p>
                          <p className="text-[#a1faff]">⚡ {model.speed}</p>
                        </div>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Quota Information */}
            <div className="bg-yellow-500/10 rounded-xl border border-yellow-500/30 p-4">
              <p className="text-sm text-[#f6f6fc]">
                <span className="font-bold text-yellow-400">⚠️ Quota Info:</span> If you exceed the free tier quota for your selected model, the system will automatically fallback to <span className="font-bold text-[#a1faff]">gemini-3.1-flash-lite</span> to continue your research without interruption.
              </p>
            </div>
          </div>
        )}

        {/* Conditional fields for other backends */}
        {llmBackend === 'ollama' && (
          <>
            <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6">
              <label className="block text-sm font-medium text-[#f6f6fc] mb-1">Ollama Model</label>
              <input
                type="text"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                className="w-full px-4 py-2.5 border border-[#a1faff]/30 rounded-lg focus:ring-2 focus:ring-[#a1faff] focus:border-[#a1faff] outline-none bg-slate-700/50 text-[#f6f6fc] placeholder-[#aaabb0]"
                placeholder="e.g., qwen2.5:3b"
              />
            </div>
            <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6">
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
          <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6">
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
        <div className="bg-slate-800/40 rounded-2xl shadow-lg border border-[#a1faff]/20 p-6">
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

        {/* Submit Button */}
        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 disabled:opacity-50 text-white rounded-lg font-bold transition-all uppercase tracking-wider"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}
