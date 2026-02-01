import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import { documentsApi } from '../services/api';
import { Document, DocumentType } from '../types';

const POLL_INTERVAL_MS = 3000;

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState<'all' | DocumentType>('all');
  const [dragActive, setDragActive] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await documentsApi.getAll(
        undefined,
        filter === 'all' ? undefined : filter
      );
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [filter]);

  // Poll when any document is pending or processing
  const hasProcessing = documents.some(
    (d) => d.processing_status === 'pending' || d.processing_status === 'processing'
  );
  useEffect(() => {
    if (!hasProcessing) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }
    pollRef.current = setInterval(loadDocuments, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [hasProcessing]);

  const handleFileUpload = async (file: File, documentType: DocumentType) => {
    setUploading(true);
    try {
      const response = await documentsApi.process(file, documentType);
      await loadDocuments();
      if (response.processing_status === 'completed' && response.vector_id) {
        alert('Document uploaded and processed successfully!');
      } else if (response.processing_status === 'failed' && response.processing_error) {
        alert(`Document uploaded but processing failed: ${response.processing_error}`);
      } else {
        alert('Document uploaded. Processing (chunking, embeddings) runs in the background. The list will update when ready.');
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`Failed to upload document: ${errorMsg}`);
      console.error('Document upload error:', error);
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
              {uploading ? 'Uploading...' : 'Upload (processing in background)'}
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
              {uploading ? 'Uploading...' : 'Upload (processing in background)'}
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
                    <FileText className="h-8 w-8 text-white/90 flex-shrink-0" />
                    <div>
                      <h4 className="text-sm font-medium text-white">{doc.filename}</h4>
                      <p className="text-sm text-white/70">
                        {doc.document_type} • {new Date(doc.created_at).toLocaleDateString()}
                        {doc.processing_status && doc.processing_status !== 'completed' && (
                          <span className="ml-2">
                            • {doc.processing_status === 'pending' && 'Queued'}
                            {doc.processing_status === 'processing' && 'Processing…'}
                            {doc.processing_status === 'failed' && 'Failed'}
                          </span>
                        )}
                      </p>
                      {doc.processing_error && (
                        <p className="text-xs text-red-300/90 mt-1 truncate max-w-md" title={doc.processing_error}>
                          {doc.processing_error}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {doc.processing_status === 'pending' && (
                      <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-amber-500/30 text-amber-200">
                        <Clock className="h-3 w-3" /> Pending
                      </span>
                    )}
                    {doc.processing_status === 'processing' && (
                      <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-500/30 text-blue-200">
                        <Loader2 className="h-3 w-3 animate-spin" /> Processing
                      </span>
                    )}
                    {doc.processing_status === 'completed' && doc.vector_id && (
                      <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-green-500/30 text-green-200">
                        <CheckCircle className="h-3 w-3" /> Ready
                      </span>
                    )}
                    {doc.processing_status === 'failed' && (
                      <span className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-red-500/30 text-red-200">
                        <XCircle className="h-3 w-3" /> Failed
                      </span>
                    )}
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
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

