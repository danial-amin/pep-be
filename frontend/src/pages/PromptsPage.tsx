import { useState } from 'react';
import { MessageSquare, Send, Loader } from 'lucide-react';
import { promptsApi } from '../services/api';

export default function PromptsPage() {
  const [prompt, setPrompt] = useState('');
  const [completedText, setCompletedText] = useState('');
  const [loading, setLoading] = useState(false);
  const [contextUsed, setContextUsed] = useState(0);
  const [maxTokens, setMaxTokens] = useState(1000);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setCompletedText('');
    try {
      const response = await promptsApi.complete(prompt, maxTokens);
      setCompletedText(response.completed_text);
      setContextUsed(response.context_used);
    } catch (error: any) {
      alert(`Failed to complete prompt: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Q&A Prompts</h2>
        <p className="text-white/80 text-lg">
          Ask questions about your documents - Get AI-powered answers using RAG (Retrieval Augmented Generation)
        </p>
        <p className="text-white/60 text-sm mt-2">
          💡 Different from Personas: This page lets you ask questions and get answers from your documents, while the Personas page generates structured user personas.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="glass-card rounded-2xl overflow-hidden pastel-blue">
          <div className="px-6 py-4 border-b border-white/20">
            <h3 className="text-lg font-semibold text-white">Your Question</h3>
          </div>
          <form onSubmit={handleSubmit} className="p-6">
            <div className="mb-4">
              <label className="block text-sm font-medium text-white/90 mb-2">
                Enter your prompt or question
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={8}
                className="w-full px-3 py-2 bg-white/20 border border-white/30 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
                placeholder="e.g., What are the main pain points mentioned in the interviews?"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-white/90 mb-2">
                Max Tokens: {maxTokens}
              </label>
              <input
                type="range"
                min="100"
                max="4000"
                step="100"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                className="w-full accent-purple-400"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 hover:from-blue-500 hover:via-purple-500 hover:to-pink-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
            >
              {loading ? (
                <>
                  <Loader className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Get Answer
                </>
              )}
            </button>
          </form>
        </div>

        {/* Output Section */}
        <div className="glass-card rounded-2xl overflow-hidden pastel-green">
          <div className="px-6 py-4 border-b border-white/20">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">AI Response</h3>
              {contextUsed > 0 && (
                <span className="text-xs text-white/70 bg-white/20 px-2 py-1 rounded-lg">
                  Used {contextUsed} context document{contextUsed !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          <div className="p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="h-8 w-8 animate-spin text-white" />
              </div>
            ) : completedText ? (
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-white/90 leading-relaxed">{completedText}</p>
              </div>
            ) : (
              <div className="text-center text-white/80 py-12">
                <MessageSquare className="mx-auto h-12 w-12 text-white/60 mb-4" />
                <p>Enter a question and click "Get Answer" to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

