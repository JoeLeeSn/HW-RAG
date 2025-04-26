import React, { useState } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

const ParseFile = () => {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('pdf');
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [parsingOption, setParsingOption] = useState('all_text');
  const [parsedContent, setParsedContent] = useState(null);
  const [status, setStatus] = useState('');
  const [docName, setDocName] = useState('');
  const [isProcessed, setIsProcessed] = useState(false);

  const handleProcess = async () => {
    if (!file || !fileType || !loadingMethod || !parsingOption) {
      setStatus('请选择所有必需的选项');
      return;
    }

    setStatus('处理中...');
    setParsedContent(null);
    setIsProcessed(false);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', fileType);
      formData.append('loading_method', loadingMethod);
      formData.append('parsing_option', parsingOption);

      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setParsedContent(data.parsed_content);
      setStatus('处理完成！');
      setIsProcessed(true);
    } catch (error) {
      console.error('Error:', error);
      setStatus(`错误: ${error.message}`);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFile(file);
      const baseName = file.name;
      setDocName(baseName);
      // 根据文件扩展名设置文件类型
      const ext = baseName.split('.').pop().toLowerCase();
      if (['pdf'].includes(ext)) {
        setFileType('pdf');
      } else if (['md', 'markdown'].includes(ext)) {
        setFileType('markdown');
      } else if (['doc', 'docx'].includes(ext)) {
        setFileType('docx');
      } else if (['xls', 'xlsx'].includes(ext)) {
        setFileType('excel');
      }
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">解析文件</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* 左侧面板 (3/12) */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1 text-gray-700">上传文件</label>
              <input
                type="file"
                accept=".pdf,.md,.markdown,.doc,.docx,.xls,.xlsx"
                onChange={handleFileSelect}
                className="block w-full border rounded px-3 py-2"
                required
              />
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">文件类型</label>
              <select
                value={fileType}
                onChange={(e) => setFileType(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="pdf">PDF</option>
                <option value="markdown">Markdown</option>
                <option value="docx">Word</option>
                <option value="excel">Excel</option>
              </select>
            </div>

            {fileType === 'pdf' && (
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1 text-gray-700">加载工具</label>
                <select
                  value={loadingMethod}
                  onChange={(e) => setLoadingMethod(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="pymupdf">PyMuPDF</option>
                  <option value="pypdf">PyPDF</option>
                  <option value="unstructured">Unstructured</option>
                  <option value="pdfplumber">PDF Plumber</option>
                </select>
              </div>
            )}

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1 text-gray-700">解析选项</label>
              <select
                value={parsingOption}
                onChange={(e) => setParsingOption(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                <option value="all_text">全文提取</option>
                <option value="by_pages">按页解析</option>
                <option value="by_titles">按标题解析</option>
                <option value="text_and_tables">文本和表格</option>
                <option value="extract_images">提取图片</option>
                <option value="extract_tables">提取表格</option>
              </select>
            </div>

            <button 
              onClick={handleProcess}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!file}
            >
              处理文件
            </button>
          </div>
        </div>

        {/* 右侧面板 (9/12) */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {parsedContent ? (
            <div className="p-4">
              <h3 className="text-xl font-semibold mb-4">解析结果</h3>
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">文档信息</h4>
                <div className="text-sm text-gray-700">
                  <p>文件名: {parsedContent.metadata?.filename}</p>
                  <p>文件类型: {parsedContent.metadata?.file_type}</p>
                  <p>总页数: {parsedContent.metadata?.total_pages}</p>
                  <p>解析方法: {parsedContent.metadata?.parsing_method}</p>
                  <p>时间戳: {parsedContent.metadata?.timestamp && new Date(parsedContent.metadata.timestamp).toLocaleString()}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {parsedContent.content.map((item, idx) => (
                  <div key={idx} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-700 mb-1">
                      {item.type} - {item.page ? `第 ${item.page} 页` : ''}
                    </div>
                    {item.title && (
                      <div className="font-bold text-gray-700 mb-2">
                        {item.title}
                      </div>
                    )}
                    {item.type === 'image' ? (
                      <div className="text-sm text-gray-700">
                        <p>图片描述: {item.content}</p>
                        {item.ocr_text && <p>OCR文本: {item.ocr_text}</p>}
                      </div>
                    ) : item.type === 'table' ? (
                      <div className="text-sm text-gray-700">
                        <pre className="whitespace-pre-wrap">{item.content}</pre>
                      </div>
                    ) : (
                      <div className="text-sm text-gray-700">
                        {item.content}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="上传并解析文件以查看结果" />
          )}
        </div>
      </div>
    </div>
  );
};

export default ParseFile; 