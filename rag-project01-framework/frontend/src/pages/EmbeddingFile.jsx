// src/pages/EmbeddingFile.jsx
import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const EmbeddingFile = () => {
  const [selectedDoc, setSelectedDoc] = useState('');
  const [embeddingProvider, setEmbeddingProvider] = useState('openai');
  const [embeddingModel, setEmbeddingModel] = useState('text-embedding-3-large');
  const [status, setStatus] = useState('');
  const [availableDocs, setAvailableDocs] = useState([]);
  const [embeddedDocs, setEmbeddedDocs] = useState([]);
  const [embeddings, setEmbeddings] = useState(null);
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' 或 'documents'
  const [sortBy, setSortBy] = useState('name'); // 'name' 或 'time'

  const modelOptions = {
    openai: [
      { value: 'text-embedding-3-large', label: 'text-embedding-3-large' },
      { value: 'text-embedding-3-small', label: 'text-embedding-3-small' }
    ],
    bedrock: [
      { value: 'cohere.embed-english-v3', label: 'cohere.embed-english-v3' },
      { value: 'cohere.embed-multilingual-v3', label: 'cohere.embed-multilingual-v3' }
    ],
    huggingface: [
      { value: 'sentence-transformers/all-mpnet-base-v2', label: 'all-mpnet-base-v2' },
      { value: 'all-MiniLM-L6-v2', label: 'all-MiniLM-L6-v2' },
      { value: 'google-bert/bert-base-uncased', label: 'bert-base-uncased' },
      { value: 'BAAI/bge-base-zh-v1.5', label: 'bge-base-zh-v1.5' }
    ]
  };

  useEffect(() => {
    fetchAvailableDocs();
    fetchEmbeddedDocs();
  }, []);

  useEffect(() => {
    setEmbeddingModel(modelOptions[embeddingProvider][0].value);
  }, [embeddingProvider]);

  const fetchAvailableDocs = async () => {
    try {
      console.log('开始获取文档列表...');
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时
      
      const response = await fetch(`${apiBaseUrl}/documents?type=all`, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      console.log('API响应状态:', response.status);
      const data = await response.json();
      console.log('API响应数据:', data);
      console.log('文档列表:', data.documents);
      if (!Array.isArray(data.documents)) {
        console.error('文档数据不是数组格式:', data.documents);
        return;
      }
      setAvailableDocs(data.documents);
    } catch (error) {
      console.error('获取文档列表出错:', error);
      if (error.name === 'AbortError') {
        setStatus('获取文档列表超时，请检查后端服务是否正常运行');
      } else {
        setStatus('获取文档列表失败: ' + error.message);
      }
    }
  };

  const fetchEmbeddedDocs = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/list-embedded`);
      const data = await response.json();
      const docs = Array.isArray(data.documents) ? data.documents : [];
      const sortedDocuments = sortDocuments(docs, sortBy);
      setEmbeddedDocs(sortedDocuments || []);
    } catch (error) {
      console.error('Error fetching embedded documents:', error);
      setEmbeddedDocs([]);
    }
  };

  const sortDocuments = (documents, sortBy) => {
    if (!Array.isArray(documents)) return [];
    
    const docsCopy = [...documents];
    
    return docsCopy.sort((a, b) => {
      if (sortBy === 'name') {
        return (a.name || '').localeCompare(b.name || '');
      } else if (sortBy === 'time') {
        // 从文件名中提取时间戳（格式：filename_provider_YYYYMMDDHHmmss.json）
        const extractTimestamp = (name) => {
          const parts = name.split('_');
          const timestampStr = parts[parts.length - 1].replace('.json', '');
          return new Date(
            timestampStr.slice(0, 4),  // 年
            timestampStr.slice(4, 6) - 1,  // 月（0-based）
            timestampStr.slice(6, 8),  // 日
            timestampStr.slice(8, 10), // 时
            timestampStr.slice(10, 12), // 分
            timestampStr.slice(12, 14)  // 秒
          );
        };
        
        const timeA = extractTimestamp(a.name);
        const timeB = extractTimestamp(b.name);
        return timeB - timeA;
      }
      return 0;
    });
  };

  const handleSortChange = (e) => {
    const newSortBy = e.target.value;
    setSortBy(newSortBy);
    fetchEmbeddedDocs();
  };

  const handleEmbed = async () => {
    if (!selectedDoc) {
      setStatus('Please select a document');
      return;
    }
    
    setStatus('Processing...');
    try {
      const response = await fetch(`${apiBaseUrl}/embed`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documentId: selectedDoc,  // 使用完整的文件名
          provider: embeddingProvider,
          model: embeddingModel
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create embeddings');
      }
      
      const data = await response.json();
      setEmbeddings(data.embeddings);
      setStatus(`Embedding completed successfully! Saved to: ${data.filepath}`);
      fetchEmbeddedDocs(); // 刷新嵌入文档列表
    } catch (error) {
      console.error('Error:', error);
      setStatus('Error generating embeddings: ' + error.message);
    }
  };

  const handleDeleteEmbedding = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/embedded-docs/${docName}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStatus('Embedding deleted successfully');
      fetchEmbeddedDocs();
      if (embeddings && selectedDoc === docName) {
        setEmbeddings(null);
      }
    } catch (error) {
      console.error('Error deleting embedding:', error);
      setStatus(`Error deleting embedding: ${error.message}`);
    }
  };

  const handleViewEmbedding = async (docName) => {
    try {
      setStatus('Loading embedding...');
      const response = await fetch(`${apiBaseUrl}/embedded-docs/${docName}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setEmbeddings(data.embeddings);
      setActiveTab('preview');
      setStatus('');
    } catch (error) {
      console.error('Error loading embedding:', error);
      setStatus(`Error loading embedding: ${error.message}`);
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
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('preview')}
          >
            Embedding Preview
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            Embedding Management
          </button>
        </div>

        {activeTab === 'preview' ? (
          embeddings ? (
            <div>
              <h3 className="text-xl font-semibold mb-4 text-gray-800">Embedding Results</h3>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                <div className="mb-4 p-3 border rounded bg-gray-100">
                  <h4 className="font-medium mb-2 text-gray-800">Embedding Results</h4>
                  <div className="text-sm text-gray-700">
                    <p>Provider: {embeddings[0]?.metadata?.embedding_provider || 'N/A'}</p>
                    <p>Model: {embeddings[0]?.metadata?.embedding_model || 'N/A'}</p>
                    <p>Vector Dimension: {embeddings[0]?.metadata?.vector_dimension || 'N/A'}</p>
                    <p>Created: {embeddings[0]?.metadata?.embedding_timestamp ? 
                      new Date(embeddings[0].metadata.embedding_timestamp).toLocaleString() : 'N/A'}</p>
                  </div>
                </div>
                {embeddings.map((embedding, idx) => (
                  <div key={idx} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      Chunk {embedding.metadata.chunk_id} of {embedding.metadata.total_chunks}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      Document: {embedding.metadata.filename || embedding.metadata.document_name || 'N/A'} | 
                      Page: {embedding.metadata.page_number || 'N/A'} | 
                      Page Range: {embedding.metadata.page_range || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      Model: {embedding.metadata.embedding_model || 'N/A'} | 
                      Provider: {embedding.metadata.embedding_provider || 'N/A'} | 
                      Dimension: {embedding.metadata.vector_dimension || 'N/A'} |
                      Timestamp: {new Date(embedding.metadata.embedding_timestamp).toLocaleString()}
                    </div>
                    <div className="text-sm mt-2">
                      <div className="font-medium text-gray-600">Content:</div>
                      <div className="text-gray-600">{embedding.metadata.content || 'N/A'}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="Select a document and generate embeddings or view existing embeddings" />
          )
        ) : (
          // 嵌入文档管理页面
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-gray-800">Embedding Management</h3>
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
              {embeddedDocs.map((doc) => (
                <div key={doc.name} className="p-4 border rounded-lg bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-lg text-gray-800">{doc.name}</h4>
                      <div className="text-sm text-gray-600 mt-1">
                        <p>Model: {doc.metadata?.embedding_model}</p>
                        <p>Provider: {doc.metadata?.embedding_provider}</p>
                        <p>Created: {new Date(doc.metadata?.embedding_timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleViewEmbedding(doc.name)}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDeleteEmbedding(doc.name)}
                        className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {embeddedDocs.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No embedded documents available
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Embedding File</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Select Document</label>
              <div className="text-sm text-gray-500 mb-2">
                可用文档数量: {availableDocs.length}
              </div>
              <select
                value={selectedDoc}
                onChange={(e) => setSelectedDoc(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="">Choose a document...</option>
                {availableDocs.map(doc => (
                  <option key={doc.id} value={doc.name}>
                    {doc.name} ({doc.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">Embedding Provider</label>
              <select
                value={embeddingProvider}
                onChange={(e) => setEmbeddingProvider(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="openai">OpenAI</option>
                <option value="bedrock">Bedrock</option>
                <option value="huggingface">HuggingFace</option>
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">Model</label>
              <select
                value={embeddingModel}
                onChange={(e) => setEmbeddingModel(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                {modelOptions[embeddingProvider].map(model => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>

            <button 
              onClick={handleEmbed}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!selectedDoc}
            >
              Generate Embeddings
            </button>
          </div>

          {status && (
            <div className={`p-4 rounded-lg ${
              status.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {status}
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default EmbeddingFile;