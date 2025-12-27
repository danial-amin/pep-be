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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Prompt Completion</h2>
        <p className="text-gray-600">
          Ask questions or complete prompts using context from your processed documents
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Your Prompt</h3>
          </div>
          <form onSubmit={handleSubmit} className="p-6">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Enter your prompt or question
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., What are the main pain points mentioned in the interviews?"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Tokens: {maxTokens}
              </label>
              <input
                type="range"
                min="100"
                max="4000"
                step="100"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Complete Prompt
                </>
              )}
            </button>
          </form>
        </div>

        {/* Output Section */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Completed Response</h3>
              {contextUsed > 0 && (
                <span className="text-xs text-gray-500">
                  Used {contextUsed} context document{contextUsed !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          <div className="p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            ) : completedText ? (
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-700">{completedText}</p>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-12">
                <MessageSquare className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p>Enter a prompt and click "Complete Prompt" to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

