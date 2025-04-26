// src/pages/Indexing.jsx
import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';
import { ExclamationCircleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

const Indexing = () => {
  const [embeddingFile, setEmbeddingFile] = useState('');
  const [vectorDb, setVectorDb] = useState('milvus');
  const [indexMode, setIndexMode] = useState('flat');
  const [status, setStatus] = useState('');
  const [embeddedFiles, setEmbeddedFiles] = useState([]);
  const [indexingResult, setIndexingResult] = useState(null);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState('');
  const [collectionDetails, setCollectionDetails] = useState(null);
  const [provider, setProvider] = useState('milvus');
  const [providers] = useState([
    { value: 'milvus', label: 'Milvus' },
    { value: 'chroma', label: 'Chroma' }
  ]);

  const indexModes = {
    milvus: [
      { value: 'flat', label: 'Flat' },
      { value: 'ivf_flat', label: 'IVF Flat' },
      { value: 'ivf_sq8', label: 'IVF SQ8' },
      { value: 'hnsw', label: 'HNSW' }
    ],
    chroma: [
      { value: 'hnsw', label: 'HNSW' }
    ]
  };

  useEffect(() => {
    fetchEmbeddedFiles();
    fetchCollections();
  }, []);

  useEffect(() => {
    // 当数据库改变时，重置索引模式为该数据库的第一个可用模式
    setIndexMode(indexModes[vectorDb][0].value);
  }, [vectorDb]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 获取collections列表
        const collectionsResponse = await fetch(`${apiBaseUrl}/collections?provider=${provider}`);
        const collectionsData = await collectionsResponse.json();
        setCollections(collectionsData.collections);
      } catch (error) {
        console.error('Error fetching collections:', error);
      }
    };

    fetchData();
  }, [provider]);

  const fetchEmbeddedFiles = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/list-embedded`);
      const data = await response.json();
      if (data.documents) {
        setEmbeddedFiles(data.documents.map(doc => ({
          ...doc,
          id: doc.name,
          displayName: doc.name
        })));
      }
    } catch (error) {
      console.error('Error fetching embedded files:', error);
      setStatus('Error loading embedding files');
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/collections/${vectorDb}`);
      const data = await response.json();
      setCollections(data.collections || []);
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const handleIndex = async () => {
    setStatus('索引处理中...');
    try {
      // 验证必填参数
      if (!embeddingFile || !vectorDb || !indexMode) {
        throw new Error('请选择嵌入文件、向量数据库和索引模式');
      }

      const response = await fetch(`${apiBaseUrl}/index`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileId: embeddingFile,
          vectorDb: vectorDb,
          indexMode: indexMode
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        let errorMsg = '索引失败';
        if (data.detail) {
          // 处理结构化错误
          if (data.detail.includes('缺少必填字段')) {
            errorMsg = `文件缺少必要字段: ${data.detail.split(':')?.[1] || '未知'}`;
          } else if (data.detail.includes('embeddings数组不能为空')) {
            errorMsg = '嵌入文件内容为空，请检查文件内容';
          } else {
            errorMsg = data.detail;
          }
        }
        throw new Error(errorMsg);
      }

      // 验证返回数据结构
      const requiredResultFields = ['collection_name', 'total_vectors'];
      const missingFields = requiredResultFields.filter(field => !data[field]);
      if (missingFields.length > 0) {
        throw new Error(`服务器返回数据不完整，缺少字段: ${missingFields.join(', ')}`);
      }

      setIndexingResult(data);
      setStatus('索引完成');
    } catch (error) {
      let errorMsg = error.message;
      if (error.message.includes('请求参数不完整')) {
        errorMsg = '索引参数不完整: 请检查是否选择了所有必填项';
      }
      setStatus(`错误: ${errorMsg}`);
      setIndexingResult(null);
    }
  };

  const handleDisplay = async (collectionName) => {
    if (!collectionName) return;
    
    try {
      const response = await fetch(`${apiBaseUrl}/collections/${provider}/${collectionName}`);
      const data = await response.json();
      
      // 只包含有实际值的属性
      const result = {
        database: provider,
        collection_name: data.name,
        total_vectors: data.num_entities,
        index_size: data.num_entities
      };

      // 只在有实际值时添加可选属性
      const indexType = data.schema?.fields?.find(f => f.name === 'vector')?.index_params?.index_type;
      if (indexType) {
        result.index_mode = indexType;
      }

      if (data.processing_time) {
        result.processing_time = data.processing_time;
      }

      setIndexingResult(result);
    } catch (error) {
      console.error('Error displaying collection:', error);
    }
  };

  const handleDelete = async (collectionName) => {
    if (!collectionName) return;
    
    if (window.confirm(`Are you sure you want to delete collection "${collectionName}"?`)) {
      try {
        await fetch(`${apiBaseUrl}/collections/${provider}/${collectionName}`, {
          method: 'DELETE',
        });
        setSelectedCollection('');
        // 重新获取collections列表
        const response = await fetch(`${apiBaseUrl}/collections?provider=${provider}`);
        const data = await response.json();
        setCollections(data.collections);
      } catch (error) {
        console.error('Error deleting collection:', error);
      }
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Vector Database Indexing</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Controls */}
        <div className="col-span-3">
          <div className="p-4 border rounded-lg bg-white shadow-sm space-y-4">
            {/* Embedding File Selection */}
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Embedding File</label>
              <select
                value={embeddingFile}
                onChange={(e) => setEmbeddingFile(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="">Choose a file...</option>
                {embeddedFiles.map(file => (
                  <option key={file.name} value={file.name}>
                    {file.displayName}
                  </option>
                ))}
              </select>
            </div>

            {/* Vector Database Selection */}
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Vector Database</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                {providers.map(provider => (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Index Mode Selection */}
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">Index Mode</label>
              <select
                value={indexMode}
                onChange={(e) => setIndexMode(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                {indexModes[provider].map(mode => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Action Buttons and Collection Management */}
            <div className="space-y-2">
              {/* Index Data Button */}
              <button 
                onClick={handleIndex}
                className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
                disabled={!embeddingFile}
              >
                Index Data
              </button>

              {/* Collection Selection */}
              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Collection</label>
                <select
                  value={selectedCollection}
                  onChange={(e) => setSelectedCollection(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="">Choose a collection...</option>
                  {collections.map(coll => (
                    <option key={coll.id} value={coll.id}>
                      {coll.name} ({coll.count} documents)
                    </option>
                  ))}
                </select>
              </div>

              {/* Display Collection Button */}
              <button
                onClick={() => handleDisplay(selectedCollection)}
                disabled={!selectedCollection}
                className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
              >
                Display Collection
              </button>

              {/* Delete Collection Button */}
              <button
                onClick={() => handleDelete(selectedCollection)}
                disabled={!selectedCollection}
                className="w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-red-300"
              >
                Delete Collection
              </button>
            </div>

            {status && (
              <div className={`mt-4 p-4 rounded-lg ${
                status.startsWith('错误') ? 
                'bg-red-100 border-l-4 border-red-500 text-red-700' : 
                'bg-green-100 border-l-4 border-green-500 text-green-700'
              }`}>
                <div className="flex items-start">
                  {status.startsWith('错误') ? (
                    <ExclamationCircleIcon className="h-5 w-5 flex-shrink-0" />
                  ) : (
                    <CheckCircleIcon className="h-5 w-5 flex-shrink-0" />
                  )}
                  <div className="ml-3">
                    <p className="text-sm font-medium">{status}</p>
                    {status.startsWith('错误') && (
                      <button 
                        onClick={() => navigator.clipboard.writeText(status.replace('错误: ', ''))}
                        className="mt-2 text-xs text-blue-500 hover:text-blue-700"
                      >
                        点击复制错误信息
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {indexingResult ? (
            <div className="mt-4 p-4 border rounded bg-gray-50">
              <h4 className="font-medium text-lg mb-2 text-gray-800">Indexing Results</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-700"><span className="font-medium">Database:</span> {indexingResult.database || 'N/A'}</p>
                  <p className="text-gray-700"><span className="font-medium">Total Vectors:</span> {indexingResult.total_vectors || 'N/A'}</p>
                  <p className="text-gray-700"><span className="font-medium">Index Size:</span> {indexingResult.index_size || 'N/A'}</p>
                  <p className="text-gray-700"><span className="font-medium">Collection Name:</span> {indexingResult.collection_name || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-gray-700"><span className="font-medium">Processing Time:</span> {indexingResult.processing_time || 'N/A'}s</p>
                </div>
              </div>
            </div>
          ) : (
            <RandomImage message="Indexing results will appear here" />
          )}
        </div>
      </div>
    </div>
  );
};

export default Indexing;