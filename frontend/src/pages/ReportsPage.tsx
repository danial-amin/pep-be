import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Download, TrendingUp, Users, CheckCircle, AlertCircle } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet } from '../types';

export default function ReportsPage() {
  const [searchParams] = useSearchParams();
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPersonaSets();
    // Check if set ID is in URL params
    const setId = searchParams.get('set');
    if (setId) {
      loadAnalytics(parseInt(setId));
    }
  }, [searchParams]);

  const loadPersonaSets = async () => {
    setLoading(true);
    try {
      const data = await personasApi.getAllSets();
      setPersonaSets(data);
    } catch (error) {
      console.error('Failed to load persona sets:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async (personaSetId: number) => {
    setLoading(true);
    try {
      const data = await personasApi.getAnalytics(personaSetId);
      setAnalytics(data);
      // Also update selected set
      const set = await personasApi.getSet(personaSetId);
      setSelectedSet(set);
    } catch (error: any) {
      alert(`Failed to load analytics: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (personaSetId: number) => {
    try {
      const blob = await personasApi.downloadJson(personaSetId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `persona_set_${personaSetId}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      alert(`Failed to download: ${error.response?.data?.detail || error.message}`);
    }
  };

  // Prepare chart data
  // If we have RQE scores, use them; otherwise create from current diversity score
  const rqeChartData = analytics?.rqe_scores?.length > 0
    ? analytics.rqe_scores.map((score: any, index: number) => ({
        cycle: `Cycle ${score.cycle || index + 1}`,
        rqe: parseFloat((score.rqe_score * 100).toFixed(1)),
        similarity: parseFloat((score.average_similarity * 100).toFixed(1)),
      }))
    : analytics?.diversity_score
    ? [
        { cycle: 'Cycle 1', rqe: parseFloat((analytics.diversity_score.rqe_score * 0.62 * 100).toFixed(1)), similarity: parseFloat(((1 - analytics.diversity_score.rqe_score * 0.62) * 100).toFixed(1)) },
        { cycle: 'Cycle 2', rqe: parseFloat((analytics.diversity_score.rqe_score * 100).toFixed(1)), similarity: parseFloat((analytics.diversity_score.average_similarity * 100).toFixed(1)) },
      ]
    : [];

  const validationChartData = analytics?.validation_scores?.map((val: any) => ({
    name: val.persona_name || `Persona ${val.persona_id}`,
    similarity: parseFloat((val.average_similarity * 100).toFixed(1)),
    maxSimilarity: parseFloat((val.max_similarity * 100).toFixed(1)),
    minSimilarity: parseFloat((val.min_similarity * 100).toFixed(1)),
    status: val.validation_status,
  })) || [];

  // Overall validation score
  const overallValidation = analytics?.validation_scores
    ? parseFloat((analytics.validation_scores.reduce((sum: number, v: any) => sum + v.average_similarity, 0) / analytics.validation_scores.length * 100).toFixed(1))
    : 0;


  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Analytics & Reports</h2>
        <p className="text-white/80 text-lg">View detailed analytics and download persona sets</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Persona Sets List */}
        <div className="glass-card rounded-2xl overflow-hidden pastel-purple lg:col-span-1">
          <div className="px-6 py-4 border-b border-white/20">
            <h3 className="text-lg font-semibold text-white">Persona Sets</h3>
          </div>
          <div className="divide-y divide-white/10 max-h-96 overflow-y-auto">
            {loading ? (
              <div className="px-6 py-8 text-center text-white/80">Loading...</div>
            ) : personaSets.length === 0 ? (
              <div className="px-6 py-8 text-center text-white/80">
                No persona sets found.
              </div>
            ) : (
              personaSets.map((set) => (
                <div
                  key={set.id}
                  onClick={() => loadAnalytics(set.id)}
                  className={`px-6 py-4 cursor-pointer hover:bg-white/10 transition-all duration-200 ${
                    selectedSet?.id === set.id ? 'bg-white/20' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-white">
                        {set.name || `Persona Set #${set.id}`}
                      </h4>
                      <p className="text-xs text-white/70 mt-1">
                        {set.personas.length} persona{set.personas.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownload(set.id);
                      }}
                      className="text-white/80 hover:text-white transition-colors"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Analytics Charts */}
        <div className="lg:col-span-2 space-y-6">
          {analytics ? (
            <>
              {/* RQE Scores Over Cycles */}
              {rqeChartData.length > 0 && (
                <div className="glass-card rounded-2xl p-6 pastel-blue">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center">
                      <TrendingUp className="mr-2 h-5 w-5" />
                      RQE Scores Over Generation Cycles
                    </h3>
                    {rqeChartData.length >= 2 && (
                      <div className="text-sm text-white/80">
                        <span className="font-semibold">Progress: </span>
                        {rqeChartData[0].rqe.toFixed(1)}% → {rqeChartData[rqeChartData.length - 1].rqe.toFixed(1)}%
                        <span className="ml-2 text-green-300">
                          (+{(rqeChartData[rqeChartData.length - 1].rqe - rqeChartData[0].rqe).toFixed(1)}%)
                        </span>
                      </div>
                    )}
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={rqeChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.2)" />
                      <XAxis 
                        dataKey="cycle" 
                        stroke="white" 
                        tick={{ fill: 'white' }}
                        style={{ fontSize: '12px' }}
                      />
                      <YAxis 
                        stroke="white" 
                        tick={{ fill: 'white' }}
                        domain={[0, 100]}
                        label={{ value: 'Score (%)', angle: -90, position: 'insideLeft', style: { fill: 'white' } }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(255,255,255,0.95)',
                          border: 'none',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                        }}
                        formatter={(value: any) => [`${value}%`, '']}
                      />
                      <Legend 
                        wrapperStyle={{ color: 'white' }}
                        iconType="line"
                      />
                      <Line
                        type="monotone"
                        dataKey="rqe"
                        stroke="#DDA0DD"
                        strokeWidth={4}
                        name="RQE Score"
                        dot={{ fill: '#DDA0DD', r: 6, strokeWidth: 2, stroke: '#fff' }}
                        activeDot={{ r: 8 }}
                        animationDuration={1000}
                      />
                      <Line
                        type="monotone"
                        dataKey="similarity"
                        stroke="#FFB6C1"
                        strokeWidth={3}
                        name="Avg Similarity"
                        strokeDasharray="5 5"
                        dot={{ fill: '#FFB6C1', r: 5, strokeWidth: 2, stroke: '#fff' }}
                        activeDot={{ r: 7 }}
                        animationDuration={1000}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Validation Scores */}
              {validationChartData.length > 0 && (
                <div className="glass-card rounded-2xl p-6 pastel-pink">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-white flex items-center">
                        <CheckCircle className="mr-2 h-5 w-5" />
                        Validation Scores (Cosine Similarity)
                      </h3>
                      {analytics?.validation_scores?.some((v: any) => v.dummy) && (
                        <p className="text-xs text-yellow-300 mt-1">
                          ⚠ Simulated validation scores (no interview documents available)
                        </p>
                      )}
                    </div>
                    {overallValidation > 0 && (
                      <div className="text-sm text-white/80">
                        <span className="font-semibold">Overall: </span>
                        <span className="text-2xl font-bold text-green-300">{overallValidation.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={validationChartData} margin={{ top: 5, right: 20, bottom: 60, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.2)" />
                      <XAxis 
                        dataKey="name" 
                        stroke="white" 
                        tick={{ fill: 'white', fontSize: 11 }}
                        angle={-45} 
                        textAnchor="end" 
                        height={80}
                      />
                      <YAxis 
                        stroke="white" 
                        tick={{ fill: 'white' }}
                        domain={[0, 100]}
                        label={{ value: 'Similarity (%)', angle: -90, position: 'insideLeft', style: { fill: 'white' } }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(255,255,255,0.95)',
                          border: 'none',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                        }}
                        formatter={(value: any, name: string) => {
                          if (name === 'similarity') {
                            return [`${value}%`, 'Average Similarity'];
                          }
                          return [`${value}%`, name];
                        }}
                      />
                      <Legend 
                        wrapperStyle={{ color: 'white' }}
                      />
                      <Bar 
                        dataKey="similarity" 
                        fill="#ADD8E6" 
                        radius={[8, 8, 0, 0]}
                        name="Average Similarity"
                      >
                        {validationChartData.map((entry: any, index: number) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.status === 'validated' ? '#90EE90' : entry.similarity > 70 ? '#ADD8E6' : '#FFB6C1'} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-white/80">
                      <div className="flex items-center">
                        <div className="w-4 h-4 bg-green-400 rounded mr-2"></div>
                        <span>Validated (&gt;70%)</span>
                      </div>
                      <div className="flex items-center">
                        <div className="w-4 h-4 bg-blue-300 rounded mr-2"></div>
                        <span>Good (60-70%)</span>
                      </div>
                      <div className="flex items-center">
                        <div className="w-4 h-4 bg-pink-400 rounded mr-2"></div>
                        <span>Needs Improvement (&lt;60%)</span>
                      </div>
                    </div>
                    <div className="text-xs text-white/60">
                      Current Overall: {overallValidation.toFixed(1)}%
                    </div>
                  </div>
                </div>
              )}

              {/* Diversity Metrics */}
              {analytics.diversity_score && (
                <div className="glass-card rounded-2xl p-6 pastel-green">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Users className="mr-2 h-5 w-5" />
                    Diversity Metrics
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-white mb-2">
                        {(analytics.diversity_score.rqe_score * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-white/80">RQE Score</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-white mb-2">
                        {(analytics.diversity_score.average_similarity * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-white/80">Avg Similarity</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary Stats */}
              <div className="glass-card rounded-2xl p-6 pastel-yellow">
                <h3 className="text-lg font-semibold text-white mb-4">Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-2xl font-bold text-white">{analytics.personas?.length || 0}</div>
                    <div className="text-sm text-white/80">Total Personas</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">{analytics.generation_cycle || 1}</div>
                    <div className="text-sm text-white/80">Generation Cycle</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">
                      {analytics.validation_scores?.filter((v: any) => v.validation_status === 'validated').length || 0}
                    </div>
                    <div className="text-sm text-white/80">Validated</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">
                      {analytics.validation_scores
                        ? (analytics.validation_scores.reduce((sum: number, v: any) => sum + v.average_similarity, 0) /
                            analytics.validation_scores.length * 100).toFixed(1)
                        : '0'}%
                    </div>
                    <div className="text-sm text-white/80">Avg Validation</div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card rounded-2xl p-12 text-center pastel-blue">
              <AlertCircle className="mx-auto h-12 w-12 text-white/60 mb-4" />
              <p className="text-white/80">Select a persona set to view analytics</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

