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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Documents</h2>
        <p className="text-gray-600">Upload and manage context and interview documents</p>
      </div>

      {/* Upload Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Context Document Upload */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 ${
            dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => handleDrop(e, 'context')}
        >
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Context Document</h3>
            <p className="mt-2 text-sm text-gray-500">
              Upload research, reports, or background information
            </p>
            <label className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 cursor-pointer">
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
          className={`border-2 border-dashed rounded-lg p-6 ${
            dragActive ? 'border-green-500 bg-green-50' : 'border-gray-300'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => handleDrop(e, 'interview')}
        >
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Interview Document</h3>
            <p className="mt-2 text-sm text-gray-500">
              Upload interview transcripts or user research
            </p>
            <label className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 cursor-pointer">
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
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Processed Documents</h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 text-sm rounded-md ${
                  filter === 'all'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('context')}
                className={`px-3 py-1 text-sm rounded-md ${
                  filter === 'context'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Context
              </button>
              <button
                onClick={() => setFilter('interview')}
                className={`px-3 py-1 text-sm rounded-md ${
                  filter === 'interview'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Interview
              </button>
            </div>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {loading ? (
            <div className="px-6 py-8 text-center text-gray-500">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No documents found. Upload your first document above.
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <FileText className="h-8 w-8 text-gray-400" />
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">{doc.filename}</h4>
                      <p className="text-sm text-gray-500">
                        {doc.document_type} • {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${
                      doc.document_type === 'context'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-green-100 text-green-800'
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

