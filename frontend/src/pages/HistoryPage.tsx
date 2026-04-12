import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { runsAPI } from '../api/client';

interface RunListItem {
  id: number;
  topic: string;
  status: string;
  paper_word_count: number;
  created_at: string;
  completed_at: string | null;
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const res = await runsAPI.list(0, 50);
      setRuns(res.data || []);
    } catch {
      // Intentionally silent handle
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header Section */}
      <header className="mb-16">
        <h1 className="font-['Space_Grotesk'] text-5xl font-bold tracking-tight text-white mb-2">
          Synthesis <span className="text-[#a1faff]">History</span>
        </h1>
        <p className="text-[#aaabb0] font-['Manrope'] text-lg max-w-xl">
          A temporal log of cognitive evolution and molecular assembly sequences processed by the Ethereal Lab.
        </p>
      </header>

          {/* Current Synthesis Card */}
          <section className="mb-20">
            <div className="glass-card rounded-xl p-8 relative overflow-hidden group border border-[#a1faff]/5">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#a1faff]/5 blur-[100px] -translate-y-1/2 translate-x-1/2"></div>
              <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="bg-[#a1faff]/10 text-[#a1faff] text-[10px] font-['Space_Grotesk'] font-bold tracking-widest px-3 py-1 rounded-full uppercase">Active Sequence</span>
                    <span className="text-[#aaabb0] text-xs font-['Inter']">EST. COMPLETION: 04:12:00</span>
                  </div>
                  <h2 className="font-['Space_Grotesk'] text-3xl font-bold text-white mb-4">Neural Pathway Mapping v.4.0</h2>
                  <p className="text-[#aaabb0] font-['Manrope'] mb-8 max-w-lg">Simulation of tertiary cortical structures with adaptive bio-feedback loops for autonomous reasoning optimization.</p>
                  <div className="space-y-3">
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-xs font-['Inter'] text-[#a1faff] uppercase tracking-tighter">Integration Progress</span>
                      <span className="text-2xl font-['Space_Grotesk'] font-bold text-[#a1faff]">68.4%</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#23262c] rounded-full overflow-hidden">
                      <div className="liquid-progress h-full w-[68.4%] rounded-full"></div>
                    </div>
                  </div>
                </div>
                <div className="w-full md:w-64 aspect-square rounded-lg overflow-hidden glass-card border border-[#46484d]/20">
                  <img 
                    alt="Neural Mapping Visualization" 
                    className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-700" 
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuB5hlVCHj0FK80h2X8lj9zAxICfsi-X65UTYZDUxukQZR0WvBkU3ORCozcz4pqR2YfM7x8w-NnfEDqDSVSCCF557XPVLZPbLniPlqhHavHH3hd6cYVGxKS5W4AhPrW2mdIRheehvJxvY-vOma9KCivJVDF2iIYai55PkELnZ10r-ZikvXxNfOuA6Rr4ZIojbndLoZtVo25X25umEBFzQ2D-FJphoFQRH6g672cLorQ61_tZrCkGrrmkeYsYBdZoVKtf1fmiCJDUxw" 
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Archived Nodes Section */}
          <section>
            <div className="flex justify-between items-end mb-8">
              <h3 className="font-['Space_Grotesk'] text-2xl font-semibold text-white">Archived Nodes</h3>
              <div className="flex gap-4">
                <button className="text-xs font-['Inter'] uppercase tracking-widest text-[#aaabb0] hover:text-[#a1faff] transition-colors">Sort by Date</button>
                <button className="text-xs font-['Inter'] uppercase tracking-widest text-[#aaabb0] hover:text-[#a1faff] transition-colors">Filter Type</button>
              </div>
            </div>
            
            {/* Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {loading ? (
                <div className="col-span-3 text-center py-12 text-[#aaabb0]">Loading runs...</div>
              ) : runs.length === 0 ? (
                <div className="col-span-3 text-center py-12 text-[#aaabb0]">No archived nodes found.</div>
              ) : (
                runs.map((run, i) => {
                  const dateStr = new Date(run.completed_at || run.created_at).toLocaleDateString();
                  const pattern = i % 4;

                  if (pattern === 0) {
                    return (
                      <Link to={`/runs/${run.id}`} key={run.id} className="md:col-span-2 bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group block">
                        <div className="flex justify-between items-start mb-6">
                          <div>
                            <h4 className="font-['Space_Grotesk'] text-xl font-bold text-white group-hover:text-[#a1faff] transition-colors">{run.topic}</h4>
                            <p className="text-xs font-['Inter'] text-[#aaabb0] mt-1 uppercase">COMPLETED: {dateStr}</p>
                          </div>
                          {run.status === 'completed' && <span className="material-symbols-outlined text-slate-500">verified</span>}
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <span className="block text-[10px] text-[#aaabb0] uppercase font-['Inter']">Words</span>
                            <span className="text-lg font-['Space_Grotesk'] text-white">{(run.paper_word_count || 0).toLocaleString()} </span>
                          </div>
                          <div className="space-y-1">
                            <span className="block text-[10px] text-[#aaabb0] uppercase font-['Inter']">Status</span>
                            <span className="text-lg font-['Space_Grotesk'] text-white uppercase">{run.status}</span>
                          </div>
                        </div>
                      </Link>
                    );
                  }

                  if (pattern === 1) {
                    return (
                      <Link to={`/runs/${run.id}`} key={run.id} className="bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group flex flex-col justify-between">
                        <div>
                          <span className={`material-symbols-outlined text-[#ac89ff] mb-4 ${run.status === 'running' ? 'animate-spin' : ''}`}>cyclone</span>
                          <h4 className="font-['Space_Grotesk'] text-xl font-bold text-white mb-2 line-clamp-2">{run.topic}</h4>
                          <p className="text-sm text-[#aaabb0] font-['Manrope']">Data run spanning {(run.paper_word_count || 0)} tokens.</p>
                        </div>
                        <div className="mt-8 pt-4 border-t border-[#46484d]/10">
                          <span className="text-[10px] font-['Inter'] text-[#00e5ee] uppercase tracking-widest">STATUS: {run.status}</span>
                        </div>
                      </Link>
                    );
                  }

                  if (pattern === 2) {
                    return (
                      <Link to={`/runs/${run.id}`} key={run.id} className="bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors group block">
                        <div className="w-full aspect-video rounded-lg mb-4 overflow-hidden">
                          <img 
                            alt="Crystal Structure" 
                            className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" 
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB71LTaouw4PIg7Yk1zRTJJtS3B1bYXAQMesVKODm0I-MUB_6yTZPLEdy78vWtrrkSEktEdLSuJyoW8OJI4ZPCz_mQH6VB5GT8nrIkOUN-wQU21PwPPCoW247bVABQPSULKQ7XRtmS-S76STkMWet2kbmkf0CmZEIM85amT_oQOvFe0AFv-xTi0MToTq1RD0dvThayelt10hHccwdgNjjXkJg01wZ6z1reQ5e_LiAY0O_DggHRDUqNlNDf31arh6yFdidY4xKvj7g" 
                          />
                        </div>
                        <h4 className="font-['Space_Grotesk'] text-lg font-bold text-white truncate">{run.topic}</h4>
                        <p className="text-xs font-['Inter'] text-[#aaabb0] mt-1 uppercase">{run.status} • {dateStr}</p>
                      </Link>
                    );
                  }

                  return (
                    <Link to={`/runs/${run.id}`} key={run.id} className="md:col-span-2 bg-[#111318] rounded-xl p-6 hover:bg-[#1d2025] transition-colors flex items-center justify-between group">
                      <div className="flex items-center gap-6">
                        <div className="p-4 rounded-full bg-[#23262c]">
                          <span className="material-symbols-outlined text-[#a1faff] text-3xl">data_thresholding</span>
                        </div>
                        <div>
                          <h4 className="font-['Space_Grotesk'] text-xl font-bold text-white truncate max-w-sm">{run.topic}</h4>
                          <p className="text-sm text-[#aaabb0] max-w-md">Completed on {dateStr} with {run.paper_word_count} words.</p>
                        </div>
                      </div>
                      <div className="p-3 rounded-full border border-[#46484d]/30 text-[#aaabb0] group-hover:text-[#a1faff] group-hover:border-[#a1faff]/50 transition-all hidden sm:flex">
                        <span className="material-symbols-outlined">chevron_right</span>
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </section>
    </div>
  );
}
