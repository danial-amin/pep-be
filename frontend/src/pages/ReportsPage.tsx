import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Download, TrendingUp, Users, CheckCircle, AlertCircle, ShieldCheck, XCircle, Info, RefreshCw } from 'lucide-react';
import { personasApi } from '../services/api';
import { PersonaSet, PersonaSetVerificationResponse } from '../types';

export default function ReportsPage() {
  const [searchParams] = useSearchParams();
  const [personaSets, setPersonaSets] = useState<PersonaSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<PersonaSet | null>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<PersonaSetVerificationResponse | null>(null);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.80);

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
    setVerificationResult(null); // Reset verification when changing sets
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

  const handleVerifyPersonaSet = async () => {
    if (!selectedSet || verifying) return;

    const isReverify = verificationResult !== null;
    setVerifying(true);
    try {
      const result = await personasApi.verifyPersonaSet(selectedSet.id, {
        similarity_threshold: similarityThreshold,
        use_indirect_similarity: true,
        filter_low_similarity: true,
        force: isReverify, // when we already have results, always re-run (re-verify)
      });
      setVerificationResult(result);
    } catch (error: any) {
      console.error('Failed to verify persona set:', error);
      alert(`Failed to verify: ${error.response?.data?.detail || error.message}`);
    } finally {
      setVerifying(false);
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
        <h2 className="text-3xl font-bold text-stone-900 mb-2 ">Analytics & Reports</h2>
        <p className="text-stone-600 text-lg">View detailed analytics and download persona sets</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Persona Sets List */}
        <div className="glass-card rounded-2xl overflow-hidden lg:col-span-1">
          <div className="px-6 py-4 border-b border-stone-200">
            <h3 className="text-lg font-semibold text-stone-900">Persona Sets</h3>
          </div>
          <div className="divide-y divide-stone-100 max-h-96 overflow-y-auto">
            {loading ? (
              <div className="px-6 py-8 text-center text-stone-600">Loading...</div>
            ) : personaSets.length === 0 ? (
              <div className="px-6 py-8 text-center text-stone-600">
                No persona sets found.
              </div>
            ) : (
              personaSets.map((set) => (
                <div
                  key={set.id}
                  onClick={() => loadAnalytics(set.id)}
                  className={`px-6 py-4 cursor-pointer hover:bg-stone-50 transition-all duration-200 ${
                    selectedSet?.id === set.id ? 'bg-stone-100' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-stone-900">
                        {set.name || `Persona Set #${set.id}`}
                      </h4>
                      <p className="text-xs text-stone-500 mt-1">
                        {set.personas.length} persona{set.personas.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownload(set.id);
                      }}
                      className="text-stone-600 hover:text-stone-900 transition-colors"
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
                <div className="glass-card rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-stone-900 flex items-center">
                      <TrendingUp className="mr-2 h-5 w-5" />
                      RQE Scores Over Generation Cycles
                    </h3>
                    {rqeChartData.length >= 2 && (
                      <div className="text-sm text-stone-600">
                        <span className="font-semibold">Progress: </span>
                        {rqeChartData[0].rqe.toFixed(1)}% → {rqeChartData[rqeChartData.length - 1].rqe.toFixed(1)}%
                        <span className="ml-2 text-green-600">
                          (+{(rqeChartData[rqeChartData.length - 1].rqe - rqeChartData[0].rqe).toFixed(1)}%)
                        </span>
                      </div>
                    )}
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={rqeChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e3dc" />
                      <XAxis 
                        dataKey="cycle" 
                        stroke="#1c1917" 
                        tick={{ fill: 'white' }}
                        style={{ fontSize: '12px' }}
                      />
                      <YAxis 
                        stroke="#1c1917" 
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
                        stroke="#c4b5fd"
                        strokeWidth={4}
                        name="RQE Score"
                        dot={{ fill: '#c4b5fd', r: 6, strokeWidth: 2, stroke: '#ffffff' }}
                        activeDot={{ r: 8 }}
                        animationDuration={1000}
                      />
                      <Line
                        type="monotone"
                        dataKey="similarity"
                        stroke="#fda4af"
                        strokeWidth={3}
                        name="Avg Similarity"
                        strokeDasharray="5 5"
                        dot={{ fill: '#fda4af', r: 5, strokeWidth: 2, stroke: '#ffffff' }}
                        activeDot={{ r: 7 }}
                        animationDuration={1000}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Validation Scores */}
              {validationChartData.length > 0 && (
                <div className="glass-card rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-stone-900 flex items-center">
                        <CheckCircle className="mr-2 h-5 w-5" />
                        Validation Scores (Cosine Similarity)
                      </h3>
                      {analytics?.validation_scores?.some((v: any) => v.dummy) && (
                        <p className="text-xs text-amber-600 mt-1">
                          ⚠ Simulated validation scores (no interview documents available)
                        </p>
                      )}
                    </div>
                    {overallValidation > 0 && (
                      <div className="text-sm text-stone-600">
                        <span className="font-semibold">Overall: </span>
                        <span className="text-2xl font-bold text-green-600">{overallValidation.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={validationChartData} margin={{ top: 5, right: 20, bottom: 60, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e3dc" />
                      <XAxis 
                        dataKey="name" 
                        stroke="#1c1917" 
                        tick={{ fill: 'white', fontSize: 11 }}
                        angle={-45} 
                        textAnchor="end" 
                        height={80}
                      />
                      <YAxis 
                        stroke="#1c1917" 
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
                        fill="#93c5fd" 
                        radius={[8, 8, 0, 0]}
                        name="Average Similarity"
                      >
                        {validationChartData.map((entry: any, index: number) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.status === 'validated' ? '#4ade80' : entry.similarity > 70 ? '#93c5fd' : '#fda4af'} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-stone-600">
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
                    <div className="text-xs text-stone-400">
                      Current Overall: {overallValidation.toFixed(1)}%
                    </div>
                  </div>
                </div>
              )}

              {/* Semantic Similarity Verification Section */}
              <div className="glass-card rounded-2xl p-6 border border-green-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-stone-900 flex items-center">
                    <ShieldCheck className="mr-2 h-5 w-5" />
                    Semantic Similarity Verification
                  </h3>
                  <button
                    onClick={handleVerifyPersonaSet}
                    disabled={verifying || !selectedSet}
                    className="px-4 py-2 bg-green-700 text-white rounded-lg hover:bg-green-800 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {verifying ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>{verificationResult ? 'Re-verifying...' : 'Verifying...'}</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="h-4 w-4" />
                        <span>{verificationResult ? 'Re-verify Against Source Data' : 'Verify Against Source Data'}</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Threshold Slider */}
                <div className="mb-4 p-3 bg-stone-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-stone-600">Similarity Threshold</span>
                    <span className="text-sm font-medium text-stone-900">{Math.round(similarityThreshold * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    value={similarityThreshold * 100}
                    onChange={(e) => setSimilarityThreshold(parseInt(e.target.value) / 100)}
                    className="w-full h-2 bg-stone-100 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-stone-400 mt-1">
                    <span>50% (Lenient)</span>
                    <span>80% (Default)</span>
                    <span>95% (Strict)</span>
                  </div>
                </div>

                {verificationResult ? (
                  <>
                    {/* Aggregate Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                      <div className="bg-stone-50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-stone-900">
                          {Math.round(verificationResult.aggregate_metrics.average_verification_rate * 100)}%
                        </div>
                        <div className="text-xs text-stone-500">Avg Verification Rate</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-stone-900">
                          {Math.round(verificationResult.aggregate_metrics.average_direct_similarity * 100)}%
                        </div>
                        <div className="text-xs text-stone-500">Avg Direct Similarity</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {Math.round((verificationResult.aggregate_metrics.average_indirect_similarity || 0) * 100)}%
                        </div>
                        <div className="text-xs text-stone-500">Avg Indirect Similarity</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-green-600">
                          {verificationResult.aggregate_metrics.fully_verified_personas}
                        </div>
                        <div className="text-xs text-stone-500">Fully Verified</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-amber-600">
                          {verificationResult.aggregate_metrics.partially_verified_personas}
                        </div>
                        <div className="text-xs text-stone-500">Partially Verified</div>
                      </div>
                    </div>

                    {/* Per-Persona Verification Results */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-stone-600 mb-2">Per-Persona Verification</h4>
                      <div className="max-h-64 overflow-y-auto space-y-2">
                        {verificationResult.persona_results.map((result: any) => (
                          <div
                            key={result.persona_id}
                            className={`p-3 rounded-lg ${
                              result.metrics?.verification_rate >= 0.8
                                ? 'bg-green-50'
                                : result.metrics?.verification_rate >= 0.5
                                  ? 'bg-amber-50'
                                  : 'bg-red-50'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                {result.metrics?.verification_rate >= 0.8 ? (
                                  <CheckCircle className="h-4 w-4 text-green-600" />
                                ) : result.metrics?.verification_rate >= 0.5 ? (
                                  <Info className="h-4 w-4 text-amber-600" />
                                ) : (
                                  <XCircle className="h-4 w-4 text-red-600" />
                                )}
                                <span className="text-sm font-medium text-stone-900">{result.persona_name}</span>
                              </div>
                              <div className="flex items-center space-x-4 text-xs">
                                <span className="text-stone-500">
                                  Direct: {Math.round((result.metrics?.average_direct_similarity || 0) * 100)}%
                                </span>
                                <span className="text-stone-500">
                                  Indirect: {Math.round((result.metrics?.average_indirect_similarity || 0) * 100)}%
                                </span>
                                <span className={`px-2 py-0.5 rounded font-medium ${
                                  result.metrics?.verification_rate >= 0.8
                                    ? 'bg-green-50 text-green-700'
                                    : result.metrics?.verification_rate >= 0.5
                                      ? 'bg-amber-50 text-amber-700'
                                      : 'bg-red-50 text-red-700'
                                }`}>
                                  {Math.round((result.metrics?.verification_rate || 0) * 100)}% Verified
                                </span>
                              </div>
                            </div>
                            {result.metrics && (
                              <div className="mt-2 text-xs text-stone-400">
                                {result.metrics.verified_attributes} of {result.metrics.total_attributes} attributes verified
                                {result.metrics.filtered_attributes > 0 && (
                                  <span className="text-red-600 ml-2">
                                    ({result.metrics.filtered_attributes} filtered out)
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="mt-4 text-xs text-stone-400 text-center">
                      Verified at: {new Date(verificationResult.verified_at).toLocaleString()}
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-stone-400">
                    <ShieldCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>Click "Verify Against Source Data" to check persona attributes</p>
                    <p className="text-xs mt-1">against the original interview/context documents</p>
                  </div>
                )}
              </div>

              {/* Diversity Metrics */}
              {analytics.diversity_score && (
                <div className="glass-card rounded-2xl p-6">
                  <h3 className="text-lg font-semibold text-stone-900 mb-4 flex items-center">
                    <Users className="mr-2 h-5 w-5" />
                    Diversity Metrics
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-stone-900 mb-2">
                        {(analytics.diversity_score.rqe_score * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-stone-600">RQE Score</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-stone-900 mb-2">
                        {(analytics.diversity_score.average_similarity * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-stone-600">Avg Similarity</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary Stats */}
              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-stone-900 mb-4">Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-2xl font-bold text-stone-900">{analytics.personas?.length || 0}</div>
                    <div className="text-sm text-stone-600">Total Personas</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-stone-900">{analytics.generation_cycle || 1}</div>
                    <div className="text-sm text-stone-600">Generation Cycle</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-stone-900">
                      {analytics.validation_scores?.filter((v: any) => v.validation_status === 'validated').length || 0}
                    </div>
                    <div className="text-sm text-stone-600">Validated</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-stone-900">
                      {analytics.validation_scores
                        ? (analytics.validation_scores.reduce((sum: number, v: any) => sum + v.average_similarity, 0) /
                            analytics.validation_scores.length * 100).toFixed(1)
                        : '0'}%
                    </div>
                    <div className="text-sm text-stone-600">Avg Validation</div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card rounded-2xl p-12 text-center">
              <AlertCircle className="mx-auto h-12 w-12 text-stone-400 mb-4" />
              <p className="text-stone-600">Select a persona set to view analytics</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

