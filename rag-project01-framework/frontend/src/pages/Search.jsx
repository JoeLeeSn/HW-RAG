// src/pages/Search.jsx
import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const Search = () => {
  const [query, setQuery] = useState('');
  const [collection, setCollection] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [topK, setTopK] = useState(3);
  const [threshold, setThreshold] = useState(0.7);
  const [collections, setCollections] = useState([]);
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('milvus');
  const [wordCountThreshold, setWordCountThreshold] = useState(100);
  const [saveResults, setSaveResults] = useState(false);
  const [status, setStatus] = useState('');

  // 加载向量数据库providers和collections
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 获取providers列表
        const providersResponse = await fetch(`${apiBaseUrl}/providers`);
        const providersData = await providersResponse.json();
        setProviders(providersData.providers);

        // 获取collections列表
        const collectionsResponse = await fetch(`${apiBaseUrl}/collections?provider=${selectedProvider}`);
        const collectionsData = await collectionsResponse.json();
        setCollections(collectionsData.collections);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [selectedProvider]);

  useEffect(() => {
    console.log('saveResults状态变化:', saveResults);
  }, [saveResults]);

  const handleSearch = async () => {
    if (!query || !collection) {
      setStatus('请选择集合并输入搜索内容');
      return;
    }

    console.log('当前过滤条件:', {
      threshold,
      wordCountThreshold
    });
    
    console.group('🛠️ 状态诊断');
    console.log('复选框状态:', saveResults, typeof saveResults);
    console.log('请求体原始值:', {
      query,
      collection,
      topK,
      threshold,
      wordCountThreshold,
      saveResults // 原始状态值
    });
    console.log('请求体处理后:', {
      collection_id: collection,
      top_k: topK,
      word_count_threshold: wordCountThreshold,
      save_results: saveResults === true // 转换后值
    });
    console.groupEnd();

    setIsSearching(true);
    setStatus('');
    try {
      const searchParams = {
        query,
        collection_id: collection,
        top_k: topK,
        threshold,
        word_count_threshold: wordCountThreshold,
        save_results: saveResults === true // 更严格的布尔转换
      };
      console.log('发送搜索请求:', JSON.stringify(searchParams, null, 2));
      
      const response = await fetch(`${apiBaseUrl}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchParams),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('搜索响应:', JSON.stringify(data, null, 2));

      if (data.results && data.results.results && data.results.results.length > 0) {
        setResults(data.results.results);
        if (saveResults && data.saved_filepath) {
          setStatus(`搜索完成！结果已保存至: ${data.saved_filepath}`);
        } else if (saveResults && data.save_error) {
          setStatus(`搜索完成但保存失败: ${data.save_error}`);
        } else {
          setStatus('搜索完成！');
        }
      } else {
        setResults([]);
        setStatus('未找到匹配的结果');
      }
    } catch (error) {
      console.error('搜索错误:', error);
      setStatus(`搜索出错: ${error.message}`);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // 添加保存结果的函数
  const handleSaveResults = async () => {
    if (!results.length) {
      setStatus('没有可保存的搜索结果');
      return;
    }

    try {
      const saveParams = {
        query,
        collection_id: collection,
        results: results
      };

      console.log('发送保存请求:', saveParams);
      
      const response = await fetch(`${apiBaseUrl}/save-search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(saveParams),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setStatus(`结果已保存至: ${data.saved_filepath}`);
    } catch (error) {
      console.error('保存错误:', error);
      setStatus(`保存失败: ${error.message}`);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Similarity Search</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Search Controls */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Your Question</label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter your search query..."
                  className="block w-full p-2 border rounded h-32 resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Vector Database</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  {providers.map(provider => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Collection</label>
                <select
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
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

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Top K Results</label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  min="1"
                  max="10"
                  className="block w-full p-2 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Similarity Threshold: {threshold}</label>
                <input
                  type="range"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  min="0"
                  max="1"
                  step="0.1"
                  className="block w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-700">Minimum Word Count: {wordCountThreshold}</label>
                <input
                  type="range"
                  value={wordCountThreshold}
                  onChange={(e) => setWordCountThreshold(parseInt(e.target.value))}
                  min="0"
                  max="500"
                  step="10"
                  className="block w-full"
                />
              </div>

              <div className="mt-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={saveResults}
                    onChange={(e) => {
                      const newValue = Boolean(e.target.checked);
                      console.log('Save Results changed to:', newValue);
                      setSaveResults(newValue);
                    }}
                    className="form-checkbox h-4 w-4 text-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Save Search Results</span>
                </label>
              </div>

              <button 
                onClick={() => {
                  console.log('Search clicked with saveResults:', saveResults);
                  handleSearch();
                }}
                disabled={isSearching}
                className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          {status && (
            <div className={`p-4 rounded-lg ${
              status.includes('错误') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {status}
              <div className="mt-2 text-sm opacity-75">
                当前过滤条件: 相似度≥{threshold}, 字数≥{wordCountThreshold}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Results */}
        <div className="col-span-8 border rounded-lg bg-white shadow-sm">
          {results.length > 0 ? (
            <div className="p-4 space-y-4 bg-gray-50">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">搜索结果 ({results.length})</h3>
                {!saveResults && (
                  <button
                    onClick={handleSaveResults}
                    className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    保存搜索结果
                  </button>
                )}
              </div>
              {results.map((result, index) => (
                <div key={index} className="p-4 border rounded bg-white shadow-xs hover:shadow-sm transition-shadow">
                  <div className="flex justify-between items-start">
                    <p className="text-gray-800 font-medium">{result.text}</p>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                      {result.score.toFixed(3)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm">
                    <p className="text-gray-600">来源: <span className="text-gray-800">{result.metadata.source}</span></p>
                    <p className="text-gray-600">页码: <span className="text-gray-800">{result.metadata.page}</span></p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <RandomImage message="搜索结果显示在这里" />
          )}
        </div>
      </div>
    </div>
  );
};

export default Search;