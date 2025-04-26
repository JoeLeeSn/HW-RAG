import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const ChunkFile = () => {
  const [loadedDocuments, setLoadedDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState('');
  const [chunkingOption, setChunkingOption] = useState('by_chars');
  const [chunkingParams, setChunkingParams] = useState({
    chunk_size: 1000,
    chunk_overlap: 200,
    separator: '\n',
    min_chunk_size: 100,
    max_chunk_size: 2000,
    paragraph_separator: '\n\n',
    sentence_separator: '.',
    keep_separator: true,
    merge_short_chunks: true,
    min_merge_size: 50
  });
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunks, setChunks] = useState(null);
  const [status, setStatus] = useState('');
  const [activeTab, setActiveTab] = useState('chunks');
  const [processingStatus, setProcessingStatus] = useState('');
  const [chunkedDocuments, setChunkedDocuments] = useState([]);

  useEffect(() => {
    fetchLoadedDocuments();
  }, []);

  const fetchLoadedDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents?type=loaded`);
      const data = await response.json();
      setLoadedDocuments(data.documents);

      const chunkedResponse = await fetch(`${apiBaseUrl}/documents?type=chunked`);
      if (!chunkedResponse.ok) {
        throw new Error(`HTTP error! status: ${chunkedResponse.status}`);
      }
      const chunkedData = await chunkedResponse.json();
      console.log('Chunked documents response:', chunkedData);
      
      if (!chunkedData.documents || !Array.isArray(chunkedData.documents)) {
        console.error('Invalid chunked documents data:', chunkedData);
        return;
      }

      const chunkedDocsWithDetails = await Promise.all(
        chunkedData.documents.map(async (doc) => {
          try {
            const detailResponse = await fetch(`${apiBaseUrl}/documents/${doc.name}?type=chunked`);
            if (!detailResponse.ok) {
              console.error(`Error fetching details for ${doc.name}:`, detailResponse.status);
              return doc;
            }
            const detailData = await detailResponse.json();
            console.log(`Details for ${doc.name}:`, detailData);
            
            return {
              ...doc,
              total_pages: detailData.total_pages,
              total_chunks: detailData.total_chunks,
              chunking_method: detailData.chunking_method,
              timestamp: detailData.timestamp
            };
          } catch (error) {
            console.error(`Error processing document ${doc.name}:`, error);
            return doc;
          }
        })
      );
      
      console.log('Final chunked documents:', chunkedDocsWithDetails);
      setChunkedDocuments(chunkedDocsWithDetails);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setProcessingStatus(`Error fetching documents: ${error.message}`);
    }
  };

  const handleChunk = async () => {
    if (!selectedDoc || !chunkingOption) {
      setStatus('Please select a document and chunking option');
      return;
    }

    setStatus('Processing...');
    setChunks(null);

    try {
      const docId = selectedDoc.endsWith('.json') ? selectedDoc : `${selectedDoc}.json`;
      
      const response = await fetch(`${apiBaseUrl}/chunk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          doc_id: docId,
          chunking_method: chunkingOption,
          chunking_params: {
            ...chunkingParams,
            chunk_size: parseInt(chunkingParams.chunk_size),
            chunk_overlap: parseInt(chunkingParams.chunk_overlap),
            min_chunk_size: parseInt(chunkingParams.min_chunk_size),
            max_chunk_size: parseInt(chunkingParams.max_chunk_size),
            min_merge_size: parseInt(chunkingParams.min_merge_size)
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Chunk response:', data);

      setChunks({
        filename: data.filename,
        total_pages: data.total_pages,
        total_chunks: data.total_chunks,
        loading_method: data.loading_method,
        chunking_method: data.chunking_method,
        timestamp: data.timestamp,
        chunks: data.chunks.map(chunk => ({
          ...chunk,
          metadata: {
            ...chunk.metadata,
            chunk_id: chunk.metadata.chunk_id,
            page_range: chunk.metadata.page_range || 'N/A',
            word_count: chunk.metadata.word_count || 0
          }
        }))
      });

      setStatus('Chunking completed successfully!');
      fetchLoadedDocuments();

    } catch (error) {
      console.error('Error:', error);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleDeleteDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=chunked`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setProcessingStatus('Document deleted successfully');
      fetchLoadedDocuments();
      if (selectedDoc === docName) {
        setSelectedDoc('');
        setChunks(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setProcessingStatus(`Error deleting document: ${error.message}`);
    }
  };

  const handleViewDocument = async (docName) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}?type=chunked`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setChunks(data);
      setActiveTab('chunks');
    } catch (error) {
      console.error('Error viewing document:', error);
      setProcessingStatus(`Error viewing document: ${error.message}`);
    }
  };

  const renderRightPanel = () => {
    return (
      <div className="p-4 w-full h-full flex flex-col">
        <div className="flex mb-4 border-b">
          <button
            className={`px-4 py-2 ${
              activeTab === 'chunks'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('chunks')}
          >
            Chunks Preview
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            Document Management
          </button>
        </div>

        {activeTab === 'chunks' ? (
          chunks ? (
            <div className="w-full">
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">Document Information</h4>
                <div className="text-sm text-gray-700">
                  <p>Filename: {chunks.filename}</p>
                  <p>Total Pages: {chunks.total_pages}</p>
                  <p>Total Chunks: {chunks.total_chunks}</p>
                  <p>Loading Method: {chunks.loading_method}</p>
                  <p>Chunking Method: {chunks.chunking_method}</p>
                  <p>Timestamp: {chunks.timestamp ? new Date(chunks.timestamp).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {Array.isArray(chunks.chunks) && chunks.chunks.map((chunk) => (
                  <div key={chunk.metadata.chunk_id} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      Chunk {chunk.metadata.chunk_id}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      Page(s): {chunk.metadata.page_range} | 
                      Words: {chunk.metadata.word_count}
                    </div>
                    <div className="text-sm mt-2">
                      <div className="text-gray-600">{chunk.content}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="Select a document and create chunks to see the results here" />
          )
        ) : (
          <div className="flex flex-col w-full h-full">
            <h3 className="text-xl font-semibold mb-4 text-gray-800">Document Management</h3>
            <div className="space-y-4 w-full">
              {chunkedDocuments.length > 0 ? (
                chunkedDocuments.map((doc) => (
                  <div key={doc.name} className="p-4 border rounded-lg bg-gray-50 w-full">
                    <div className="flex justify-between items-start w-full">
                      <div className="flex-grow">
                        <h4 className="font-medium text-lg text-gray-800">{doc.name}</h4>
                        <div className="text-sm text-gray-700 mt-1">
                          <p>Pages: {doc.total_pages || 'N/A'}</p>
                          <p>Chunks: {doc.total_chunks || 'N/A'}</p>
                          <p>Chunking Method: {doc.chunking_method || 'N/A'}</p>
                          <p>Processing Date: {doc.timestamp ? new Date(doc.timestamp).toLocaleString() : 'N/A'}</p>
                        </div>
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleViewDocument(doc.name)}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
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
                ))
              ) : (
                <div className="text-center text-gray-500 py-8 w-full">
                  No chunked documents available
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
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Chunk File</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">Select Document</label>
              <select
                value={selectedDoc}
                onChange={(e) => setSelectedDoc(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="">Choose a document...</option>
                {loadedDocuments.map((doc) => (
                  <option key={doc.name} value={doc.name}>
                    {doc.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">Chunking Method</label>
              <select
                value={chunkingOption}
                onChange={(e) => setChunkingOption(e.target.value)}
                className="block w-full p-2 border rounded text-gray-700 bg-white"
              >
                <option value="by_chars">By Characters</option>
                <option value="by_words">By Words</option>
                <option value="by_sentences">By Sentences</option>
                <option value="by_paragraphs">By Paragraphs</option>
                <option value="by_markdown">By Markdown</option>
                <option value="by_html">By HTML Elements</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">Chunking Parameters</label>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-700 mb-1">Chunk Size</label>
                  <input
                    type="number"
                    value={chunkingParams.chunk_size}
                    onChange={(e) => setChunkingParams({
                      ...chunkingParams,
                      chunk_size: parseInt(e.target.value)
                    })}
                    className="block w-full p-2 border rounded text-gray-700 bg-white"
                    min="100"
                    max="5000"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-700 mb-1">Chunk Overlap</label>
                  <input
                    type="number"
                    value={chunkingParams.chunk_overlap}
                    onChange={(e) => setChunkingParams({
                      ...chunkingParams,
                      chunk_overlap: parseInt(e.target.value)
                    })}
                    className="block w-full p-2 border rounded text-gray-700 bg-white"
                    min="0"
                    max="1000"
                  />
                </div>

                {(chunkingOption === 'by_paragraphs' || chunkingOption === 'by_sentences') && (
                  <>
                    <div>
                      <label className="block text-sm text-gray-700 mb-1">Min Chunk Size</label>
                      <input
                        type="number"
                        value={chunkingParams.min_chunk_size}
                        onChange={(e) => setChunkingParams({
                          ...chunkingParams,
                          min_chunk_size: parseInt(e.target.value)
                        })}
                        className="block w-full p-2 border rounded text-gray-700 bg-white"
                        min="50"
                        max="1000"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-gray-700 mb-1">Max Chunk Size</label>
                      <input
                        type="number"
                        value={chunkingParams.max_chunk_size}
                        onChange={(e) => setChunkingParams({
                          ...chunkingParams,
                          max_chunk_size: parseInt(e.target.value)
                        })}
                        className="block w-full p-2 border rounded text-gray-700 bg-white"
                        min="500"
                        max="5000"
                      />
                    </div>

                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={chunkingParams.merge_short_chunks}
                        onChange={(e) => setChunkingParams({
                          ...chunkingParams,
                          merge_short_chunks: e.target.checked
                        })}
                        className="mr-2"
                      />
                      <label className="text-sm text-gray-700">Merge Short Chunks</label>
                    </div>

                    {chunkingParams.merge_short_chunks && (
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Min Merge Size</label>
                        <input
                          type="number"
                          value={chunkingParams.min_merge_size}
                          onChange={(e) => setChunkingParams({
                            ...chunkingParams,
                            min_merge_size: parseInt(e.target.value)
                          })}
                          className="block w-full p-2 border rounded text-gray-700 bg-white"
                          min="10"
                          max="500"
                        />
                      </div>
                    )}
                  </>
                )}

                {chunkingOption === 'by_paragraphs' && (
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Paragraph Separator</label>
                    <input
                      type="text"
                      value={chunkingParams.paragraph_separator}
                      onChange={(e) => setChunkingParams({
                        ...chunkingParams,
                        paragraph_separator: e.target.value
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                      placeholder="\n\n"
                    />
                  </div>
                )}

                {chunkingOption === 'by_sentences' && (
                  <div>
                    <label className="block text-sm text-gray-700 mb-1">Sentence Separator</label>
                    <input
                      type="text"
                      value={chunkingParams.sentence_separator}
                      onChange={(e) => setChunkingParams({
                        ...chunkingParams,
                        sentence_separator: e.target.value
                      })}
                      className="block w-full p-2 border rounded text-gray-700 bg-white"
                      placeholder="."
                    />
                  </div>
                )}

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={chunkingParams.keep_separator}
                    onChange={(e) => setChunkingParams({
                      ...chunkingParams,
                      keep_separator: e.target.checked
                    })}
                    className="mr-2"
                  />
                  <label className="text-sm text-gray-700">Keep Separator</label>
                </div>
              </div>
            </div>

            <button 
              onClick={handleChunk}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!selectedDoc}
            >
              Create Chunks
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

export default ChunkFile;