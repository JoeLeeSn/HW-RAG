// src/pages/LoadFile.jsx
import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const LoadFile = () => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [unstructuredStrategy, setUnstructuredStrategy] = useState('fast');
  const [chunkingStrategy, setChunkingStrategy] = useState('basic');
  const [chunkingOptions, setChunkingOptions] = useState({
    maxCharacters: 4000,
    newAfterNChars: 3000,
    combineTextUnderNChars: 500,
    overlap: 200,
    overlapAll: false,
    multiPageSections: false
  });
  const [loadedContent, setLoadedContent] = useState(null);
  const [status, setStatus] = useState('');
  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' 或 'documents'
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [sortBy, setSortBy] = useState('name'); // 'name' 或 'time'

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents?type=loaded`);
      const data = await response.json();
      const sortedDocuments = sortDocuments(data.documents, sortBy);
      setDocuments(sortedDocuments);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const sortDocuments = (documents, sortBy) => {
    return documents.sort((a, b) => {
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'time') {
        return new Date(b.metadata?.timestamp || b.timestamp) - new Date(a.metadata?.timestamp || a.timestamp);
      }
      return 0;
    });
  };

  const handleSortChange = (e) => {
    const newSortBy = e.target.value;
    setSortBy(newSortBy);
    const sortedDocuments = sortDocuments(documents, newSortBy);
    setDocuments(sortedDocuments);
  };

  const handleProcess = async () => {
    if (!file || !loadingMethod) {
      setStatus('Please select all required options');
      return;
    }

    setStatus('Loading...');
    setLoadedContent(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('loading_method', loadingMethod);
      
      if (loadingMethod === 'unstructured') {
        formData.append('strategy', unstructuredStrategy);
        formData.append('chunking_strategy', chunkingStrategy);
        formData.append('chunking_options', JSON.stringify(chunkingOptions));
      }

      const response = await fetch(`${apiBaseUrl}/load`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setLoadedContent(data.loaded_content);
      setStatus('File loaded successfully!');
      fetchDocuments();
      setActiveTab('preview');

    } catch (error) {
      console.error('Error:', error);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleDeleteDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStatus('Document deleted successfully');
      fetchDocuments();
      if (selectedDoc?.name === docName) {
        setSelectedDoc(null);
        setLoadedContent(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setStatus(`Error deleting document: ${error.message}`);
    }
  };

  const handleViewDocument = async (doc) => {
    try {
      setStatus('Loading document...');
      const response = await fetch(`${apiBaseUrl}/documents/${doc.name}.json`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSelectedDoc(doc);
      setLoadedContent(data);
      setActiveTab('preview');
      setStatus('');
    } catch (error) {
      console.error('Error loading document:', error);
      setStatus(`Error loading document: ${error.message}`);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const renderRightPanel = () => {
    return (
      <div className="p-4">
        {/* 标签页切换 */}
        <div className="flex mb-4 border-b">
          <button
            className={`px-4 py-2 ${
              activeTab === 'preview'
                ? 'border-b-2 border-primary-color text-primary-color'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('preview')}
          >
            Document Preview
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-primary-color text-primary-color'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            Document Management
          </button>
        </div>

        {/* 内容区域 */}
        {activeTab === 'preview' ? (
          loadedContent ? (
            <div>
              <h3 className="text-xl font-semibold mb-4 text-gray-800">Document Content</h3>
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2 text-gray-800">Document Information</h4>
                <div className="text-sm text-gray-700">
                  <p>Pages: {loadedContent.total_pages || 'N/A'}</p>
                  <p>Chunks: {loadedContent.total_chunks || 'N/A'}</p>
                  <p>Loading Method: {loadedContent.loading_method || 'N/A'}</p>
                  <p>Chunking Method: {loadedContent.chunking_method || 'N/A'}</p>
                  <p>Processing Date: {loadedContent.timestamp ? 
                    new Date(loadedContent.timestamp).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {loadedContent.chunks.map((chunk) => (
                  <div key={chunk.metadata.chunk_id} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      Chunk {chunk.metadata.chunk_id} (Page {chunk.metadata.page_number})
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      Words: {chunk.metadata.word_count} | Page Range: {chunk.metadata.page_range}
                    </div>
                    <div className="text-sm mt-2">
                      <div className="text-gray-600">{chunk.content}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="Upload and load a file or select an existing document to see the results here" />
          )
        ) : (
          // 文档管理页面
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-gray-800">Document Management</h3>
              <select
                value={sortBy}
                onChange={handleSortChange}
                className="p-2 border rounded text-sm"
              >
                <option value="name">按文件名排序</option>
                <option value="time">按时间倒序排序</option>
              </select>
            </div>
            <div className="space-y-4">
              {documents.map((doc) => (
                <div key={doc.name} className="p-4 border rounded-lg bg-gray-50 w-full">
                  <div className="flex justify-between items-start w-full">
                    <div className="flex-grow">
                      <h4 className="font-medium text-lg text-gray-800">{doc.name}</h4>
                      <div className="text-sm text-gray-700 mt-1">
                        <p>Pages: {doc.metadata?.total_pages || 'N/A'}</p>
                        <p>Chunks: {doc.metadata?.total_chunks || 'N/A'}</p>
                        <p>Loading Method: {doc.metadata?.loading_method || 'N/A'}</p>
                        <p>Chunking Method: {doc.metadata?.chunking_method || 'N/A'}</p>
                        <p>Created: {doc.metadata?.timestamp ? 
                          new Date(doc.metadata.timestamp).toLocaleString() : 'N/A'}</p>
                      </div>
                    </div>
                    <div className="flex space-x-2 ml-4">
                      <button
                        onClick={() => handleViewDocument(doc)}
                        className="px-3 py-1 bg-primary-color text-white rounded hover:bg-secondary-color"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDeleteDocument(doc.name)}
                        className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {documents.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No documents available
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderLeftPanel = () => {
    return (
      <div className="col-span-3 space-y-4">
        <div className="p-4 border rounded-lg bg-white shadow-sm">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Upload PDF</label>
            <input
              type="file"
              onChange={handleFileChange}
              className="block w-full p-2 border rounded"
              accept=".pdf"
            />
            {fileName && (
              <div className="mt-2 text-sm text-gray-700">
                已选择文件: {fileName}
              </div>
            )}
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-1 text-gray-700">Loading Method</label>
            <select
              value={loadingMethod}
              onChange={(e) => setLoadingMethod(e.target.value)}
              className="block w-full p-2 border rounded text-gray-700 bg-white"
            >
              <option value="pymupdf" className="text-gray-700 bg-white">PyMuPDF</option>
              <option value="pypdf" className="text-gray-700 bg-white">PyPDF</option>
              <option value="unstructured" className="text-gray-700 bg-white">Unstructured</option>
              <option value="pdf2image" className="text-gray-700 bg-white">PDF2Image (OCR)</option>
              <option value="tabula" className="text-gray-700 bg-white">Tabula (Tables)</option>
            </select>
          </div>

          {loadingMethod === 'unstructured' && (
            <>
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1 text-gray-700">Unstructured Strategy</label>
                <select
                  value={unstructuredStrategy}
                  onChange={(e) => setUnstructuredStrategy(e.target.value)}
                  className="block w-full p-2 border rounded text-gray-700 bg-white"
                >
                  <option value="fast" className="text-gray-700 bg-white">Fast</option>
                  <option value="hi_res" className="text-gray-700 bg-white">High Resolution</option>
                  <option value="ocr_only" className="text-gray-700 bg-white">OCR Only</option>
                </select>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium mb-1 text-gray-700">Chunking Strategy</label>
                <select
                  value={chunkingStrategy}
                  onChange={(e) => setChunkingStrategy(e.target.value)}
                  className="block w-full p-2 border rounded text-gray-700 bg-white"
                >
                  <option value="basic" className="text-gray-700 bg-white">Basic</option>
                  <option value="by_title" className="text-gray-700 bg-white">By Title</option>
                  <option value="by_section" className="text-gray-700 bg-white">By Section</option>
                </select>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium mb-1 text-gray-700">Chunking Options</label>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Max Characters</label>
                    <input
                      type="number"
                      value={chunkingOptions.maxCharacters}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        maxCharacters: parseInt(e.target.value)
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">New After N Chars</label>
                    <input
                      type="number"
                      value={chunkingOptions.newAfterNChars}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        newAfterNChars: parseInt(e.target.value)
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Combine Text Under N Chars</label>
                    <input
                      type="number"
                      value={chunkingOptions.combineTextUnderNChars}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        combineTextUnderNChars: parseInt(e.target.value)
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Overlap</label>
                    <input
                      type="number"
                      value={chunkingOptions.overlap}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        overlap: parseInt(e.target.value)
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                    />
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={chunkingOptions.overlapAll}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        overlapAll: e.target.checked
                      })}
                      className="mr-2"
                    />
                    <label className="text-sm text-gray-700">Overlap All</label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={chunkingOptions.multiPageSections}
                      onChange={(e) => setChunkingOptions({
                        ...chunkingOptions,
                        multiPageSections: e.target.checked
                      })}
                      className="mr-2"
                    />
                    <label className="text-sm text-gray-700">Multi-page Sections</label>
                  </div>
                </div>
              </div>
            </>
          )}

          <button
            onClick={handleProcess}
            className="mt-4 w-full bg-primary-color text-white py-2 px-4 rounded hover:bg-secondary-color"
          >
            Process File
          </button>
        </div>

        {status && (
          <div className={`p-4 rounded-lg ${
            status.includes('Error') ? 'bg-error-color text-white' : 'bg-success-color text-white'
          }`}>
            {status}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Load File</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {renderLeftPanel()}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default LoadFile;