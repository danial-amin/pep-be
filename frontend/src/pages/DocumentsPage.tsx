import { useState, useEffect } from 'react';
import { Upload, FileText } from 'lucide-react';
import { documentsApi } from '../services/api';
import { Document, DocumentType } from '../types';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState<'all' | DocumentType>('all');
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, [filter]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await documentsApi.getAll(
        undefined, // projectId - not used in global documents page
        filter === 'all' ? undefined : filter
      );
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File, documentType: DocumentType) => {
    setUploading(true);
    try {
      // Note: Global documents page doesn't have a project context
      // Documents uploaded here won't be associated with a project
      await documentsApi.process(file, documentType);
      await loadDocuments();
      alert('Document processed successfully!');
    } catch (error: any) {
      alert(`Failed to process document: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent, documentType: DocumentType) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file, documentType);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, documentType: DocumentType) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file, documentType);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">Documents</h2>
        <p className="text-white/80 text-lg">Upload and manage context and interview documents</p>
      </div>

      {/* Upload Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Context Document Upload */}
        <div
          className={`glass-card rounded-2xl p-6 transition-all duration-300 ${
            dragActive ? 'scale-105 pastel-blue' : 'pastel-purple'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => handleDrop(e, 'context')}
        >
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-white/90 drop-shadow-lg" />
            <h3 className="mt-4 text-lg font-semibold text-white">Context Document</h3>
            <p className="mt-2 text-sm text-white/80">
              Upload research, reports, or background information
            </p>
            <label className="mt-4 inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-400 to-pink-400 hover:from-purple-500 hover:to-pink-500 cursor-pointer transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105">
              <Upload className="mr-2 h-4 w-4" />
              {uploading ? 'Uploading...' : 'Upload File'}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => handleFileInput(e, 'context')}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Interview Document Upload */}
        <div
          className={`glass-card rounded-2xl p-6 transition-all duration-300 ${
            dragActive ? 'scale-105 pastel-green' : 'pastel-pink'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => handleDrop(e, 'interview')}
        >
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-white/90 drop-shadow-lg" />
            <h3 className="mt-4 text-lg font-semibold text-white">Interview Document</h3>
            <p className="mt-2 text-sm text-white/80">
              Upload interview transcripts or user research
            </p>
            <label className="mt-4 inline-flex items-center px-6 py-3 text-sm font-medium rounded-xl text-white bg-gradient-to-r from-pink-400 to-rose-400 hover:from-pink-500 hover:to-rose-500 cursor-pointer transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105">
              <Upload className="mr-2 h-4 w-4" />
              {uploading ? 'Uploading...' : 'Upload File'}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => handleFileInput(e, 'interview')}
                disabled={uploading}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Filter and Documents List */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/20">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Processed Documents</h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-2 text-sm rounded-xl font-medium transition-all duration-200 ${
                  filter === 'all'
                    ? 'bg-white/30 text-white shadow-lg'
                    : 'bg-white/10 text-white/80 hover:bg-white/20'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('context')}
                className={`px-4 py-2 text-sm rounded-xl font-medium transition-all duration-200 ${
                  filter === 'context'
                    ? 'bg-white/30 text-white shadow-lg'
                    : 'bg-white/10 text-white/80 hover:bg-white/20'
                }`}
              >
                Context
              </button>
              <button
                onClick={() => setFilter('interview')}
                className={`px-4 py-2 text-sm rounded-xl font-medium transition-all duration-200 ${
                  filter === 'interview'
                    ? 'bg-white/30 text-white shadow-lg'
                    : 'bg-white/10 text-white/80 hover:bg-white/20'
                }`}
              >
                Interview
              </button>
            </div>
          </div>
        </div>

        <div className="divide-y divide-white/10">
          {loading ? (
            <div className="px-6 py-8 text-center text-white/80">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="px-6 py-8 text-center text-white/80">
              No documents found. Upload your first document above.
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="px-6 py-4 hover:bg-white/10 transition-all duration-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <FileText className="h-8 w-8 text-white/90" />
                    <div>
                      <h4 className="text-sm font-medium text-white">{doc.filename}</h4>
                      <p className="text-sm text-white/70">
                        {doc.document_type} • {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 text-xs font-medium rounded-full ${
                      doc.document_type === 'context'
                        ? 'bg-purple-400/30 text-white border border-purple-300/50'
                        : 'bg-pink-400/30 text-white border border-pink-300/50'
                    }`}
                  >
                    {doc.document_type}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

