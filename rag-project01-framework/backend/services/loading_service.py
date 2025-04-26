from pypdf import PdfReader
import pdfplumber
import fitz  # PyMuPDF
import logging
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)
"""
PDF文档加载服务类
    这个服务类提供了多种PDF文档加载方法，支持不同的加载策略和分块选项。
    主要功能：
    1. 支持多种PDF解析库：
        - PyMuPDF (fitz): 适合快速处理大量PDF文件，性能最佳
        - PyPDF: 适合简单的PDF文本提取，依赖较少
        - pdfplumber: 适合需要处理表格或需要文本位置信息的场景
        - unstructured: 适合需要更好的文档结构识别和灵活分块策略的场景
        - pdf2image: 适合需要OCR处理的场景
        - tabula: 适合需要表格数据提取的场景
    
    2. 文档加载特性：
        - 保持页码信息
        - 支持文本分块
        - 提供元数据存储
        - 支持不同的加载策略
        - 支持文档预处理
        - 支持文档质量检查
        - 支持OCR处理
        - 支持表格提取
 """

def import_unstructured():
    """
    安全导入unstructured模块
    如果导入失败，返回None并记录错误
    """
    try:
        from unstructured.partition.pdf import partition_pdf
        return partition_pdf
    except ImportError as e:
        logger.error(f"Error importing unstructured: {str(e)}")
        return None

class LoadingService:
    """
    PDF文档加载服务类，提供多种PDF文档加载和处理方法。
    
    属性:
        total_pages (int): 当前加载PDF文档的总页数
        current_page_map (list): 存储当前文档的页面映射信息，每个元素包含页面文本和页码
    """
    
    def __init__(self):
        self.total_pages = 0
        self.current_page_map = []
        self.quality_metrics = {}
    
    def load_pdf(self, file_path: str, method: str, strategy: str = None, 
                chunking_strategy: str = None, chunking_options: dict = None,
                preprocess_options: dict = None, quality_check: bool = False) -> str:
        """
        加载PDF文档的主方法，支持多种加载策略。

        参数:
            file_path (str): PDF文件路径
            method (str): 加载方法，支持 'pymupdf', 'pypdf', 'pdfplumber', 'unstructured', 'pdf2image', 'tabula'
            strategy (str, optional): 使用unstructured方法时的策略，可选 'fast', 'hi_res', 'ocr_only'
            chunking_strategy (str, optional): 文本分块策略，可选 'basic', 'by_title', 'by_section'
            chunking_options (dict, optional): 分块选项配置
            preprocess_options (dict, optional): 预处理选项配置
            quality_check (bool, optional): 是否进行文档质量检查

        返回:
            str: 提取的文本内容
        """
        try:
            # 文档预处理
            if preprocess_options:
                self._preprocess_document(file_path, preprocess_options)
            
            # 文档质量检查
            if quality_check:
                self._check_document_quality(file_path)
            
            # 根据方法选择加载方式
            if method == "pymupdf":
                return self._load_with_pymupdf(file_path)
            elif method == "pypdf":
                return self._load_with_pypdf(file_path)
            elif method == "pdfplumber":
                return self._load_with_pdfplumber(file_path)
            elif method == "unstructured":
                partition_pdf = import_unstructured()
                if partition_pdf is None:
                    logger.warning("Unstructured module not available, falling back to PyMuPDF")
                    return self._load_with_pymupdf(file_path)
                return self._load_with_unstructured(
                    file_path, 
                    partition_pdf=partition_pdf,
                    strategy=strategy,
                    chunking_strategy=chunking_strategy,
                    chunking_options=chunking_options
                )
            elif method == "pdf2image":
                return self._load_with_pdf2image(file_path)
            elif method == "tabula":
                return self._load_with_tabula(file_path)
            else:
                raise ValueError(f"Unsupported loading method: {method}")
        except Exception as e:
            logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise
    
    def get_total_pages(self) -> int:
        """
        获取当前加载文档的总页数。

        返回:
            int: 文档总页数
        """
        return max(page_data['page'] for page_data in self.current_page_map) if self.current_page_map else 0
    
    def get_page_map(self) -> list:
        """
        获取当前文档的页面映射信息。

        返回:
            list: 包含每页文本内容和页码的列表
        """
        return self.current_page_map
    
    def _load_with_pymupdf(self, file_path: str) -> str:
        """
        使用PyMuPDF库加载PDF文档。
        适合快速处理大量PDF文件，性能最佳。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with fitz.open(file_path) as doc:
                self.total_pages = len(doc)
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text")
                    if text.strip():
                        text_blocks.append({
                            "text": text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyMuPDF error: {str(e)}")
            raise
    
    def _load_with_pypdf(self, file_path: str) -> str:
        """
        使用PyPDF库加载PDF文档。
        适合简单的PDF文本提取，依赖较少。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        try:
            text_blocks = []
            with open(file_path, "rb") as file:
                pdf = PdfReader(file)
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyPDF error: {str(e)}")
            raise
    
    def _load_with_unstructured(self, file_path: str, partition_pdf, strategy: str = "fast", 
                              chunking_strategy: str = "basic", chunking_options: dict = None) -> str:
        """
        使用unstructured库加载PDF文档。
        适合需要更好的文档结构识别和灵活分块策略的场景。

        参数:
            file_path (str): PDF文件路径
            partition_pdf: unstructured的partition_pdf函数
            strategy (str): 加载策略，默认'fast'
            chunking_strategy (str): 分块策略，默认'basic'
            chunking_options (dict): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            strategy_params = {
                "fast": {"strategy": "fast"},
                "hi_res": {"strategy": "hi_res"},
                "ocr_only": {"strategy": "ocr_only"}
            }            
         
            # Prepare chunking parameters based on strategy
            chunking_params = {}
            if chunking_strategy == "basic":
                chunking_params = {
                    "max_characters": chunking_options.get("maxCharacters", 4000),
                    "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "overlap": chunking_options.get("overlap", 200),
                    "overlap_all": chunking_options.get("overlapAll", False)
                }
            elif chunking_strategy == "by_title":
                chunking_params = {
                    "chunking_strategy": "by_title",
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "multipage_sections": chunking_options.get("multiPageSections", False)
                }
            
            # Combine strategy parameters with chunking parameters
            params = {**strategy_params.get(strategy, {"strategy": "fast"}), **chunking_params}
            
            elements = partition_pdf(file_path, **params)
            
            # Add debug logging
            for elem in elements:
                logger.debug(f"Element type: {type(elem)}")
                logger.debug(f"Element content: {str(elem)}")
                logger.debug(f"Element dir: {dir(elem)}")
            
            text_blocks = []
            pages = set()
            
            for elem in elements:
                metadata = elem.metadata.__dict__
                page_number = metadata.get('page_number')
                
                if page_number is not None:
                    pages.add(page_number)
                    
                    # Convert element to a serializable format
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        
                        try:
                            # Try JSON serialization to test if value is serializable
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            # If not serializable, convert to string
                            cleaned_metadata[key] = str(value)
                    
                    # Add additional element information
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['category'] = str(getattr(elem, 'category', None))
                    
                    text_blocks.append({
                        "text": str(elem),
                        "page": page_number,
                        "metadata": cleaned_metadata
                    })
            
            self.total_pages = max(pages) if pages else 0
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Unstructured error: {str(e)}")
            raise
    
    def _load_with_pdfplumber(self, file_path: str) -> str:
        """
        使用pdfplumber库加载PDF文档。
        适合需要处理表格或需要文本位置信息的场景。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with pdfplumber.open(file_path) as pdf:
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"pdfplumber error: {str(e)}")
            raise
    
    def _preprocess_document(self, file_path: str, options: dict) -> None:
        """
        文档预处理功能
        
        参数:
            file_path (str): PDF文件路径
            options (dict): 预处理选项
        """
        try:
            # 旋转页面
            if options.get("rotate_pages"):
                self._rotate_pages(file_path, options["rotate_pages"])
            
            # 压缩文档
            if options.get("compress"):
                self._compress_document(file_path, options["compress"])
            
            # 清理文档
            if options.get("clean"):
                self._clean_document(file_path, options["clean"])
            
            # 添加水印
            if options.get("watermark"):
                self._add_watermark(file_path, options["watermark"])
            
        except Exception as e:
            logger.error(f"Error preprocessing document: {str(e)}")
            raise

    def _check_document_quality(self, file_path: str) -> dict:
        """
        文档质量检查
        
        参数:
            file_path (str): PDF文件路径
            
        返回:
            dict: 质量检查结果
        """
        try:
            quality_metrics = {
                "file_size": os.path.getsize(file_path),
                "page_count": 0,
                "text_ratio": 0.0,
                "image_ratio": 0.0,
                "table_ratio": 0.0,
                "ocr_required": False,
                "resolution": 0,
                "compression_ratio": 0.0
            }
            
            # 使用PyMuPDF进行基本检查
            with fitz.open(file_path) as doc:
                quality_metrics["page_count"] = len(doc)
                
                # 检查每页内容
                for page in doc:
                    # 检查文本比例
                    text_blocks = page.get_text("blocks")
                    quality_metrics["text_ratio"] += len(text_blocks) / len(page.get_text("dict")["blocks"])
                    
                    # 检查图片比例
                    images = page.get_images()
                    quality_metrics["image_ratio"] += len(images) / len(page.get_text("dict")["blocks"])
                    
                    # 检查是否需要OCR
                    if len(text_blocks) == 0 and len(images) > 0:
                        quality_metrics["ocr_required"] = True
                    
                    # 检查分辨率
                    quality_metrics["resolution"] = max(quality_metrics["resolution"], 
                                                      page.rect.width * page.rect.height)
            
            # 计算压缩比
            original_size = quality_metrics["file_size"]
            with open(file_path, "rb") as f:
                compressed_size = len(f.read())
            quality_metrics["compression_ratio"] = compressed_size / original_size
            
            self.quality_metrics = quality_metrics
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error checking document quality: {str(e)}")
            raise

    def _load_with_pdf2image(self, file_path: str) -> str:
        """
        使用pdf2image库加载PDF文档。
        适合需要OCR处理的场景。
        
        参数:
            file_path (str): PDF文件路径
            
        返回:
            str: 提取的文本内容
        """
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # 将PDF转换为图像
            images = convert_from_path(file_path)
            self.total_pages = len(images)
            
            text_blocks = []
            for page_num, image in enumerate(images, 1):
                # 使用Tesseract进行OCR
                text = pytesseract.image_to_string(image)
                if text.strip():
                    text_blocks.append({
                        "text": text.strip(),
                        "page": page_num,
                        "is_ocr": True
                    })
            
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"PDF2Image error: {str(e)}")
            raise

    def _load_with_tabula(self, file_path: str) -> str:
        """
        使用tabula库加载PDF文档。
        适合需要表格数据提取的场景。
        
        参数:
            file_path (str): PDF文件路径
            
        返回:
            str: 提取的文本内容
        """
        try:
            import tabula
            
            # 提取表格
            tables = tabula.read_pdf(file_path, pages='all')
            self.total_pages = len(tables)
            
            text_blocks = []
            for page_num, table in enumerate(tables, 1):
                # 将表格转换为文本
                table_text = table.to_string()
                if table_text.strip():
                    text_blocks.append({
                        "text": table_text.strip(),
                        "page": page_num,
                        "is_table": True
                    })
            
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Tabula error: {str(e)}")
            raise

    def save_document(self, filename: str, chunks: list, metadata: dict, loading_method: str, strategy: str = None, chunking_strategy: str = None) -> str:
        """
        保存处理后的文档数据。

        参数:
            filename (str): 原PDF文件名
            chunks (list): 文档分块列表
            metadata (dict): 文档元数据
            loading_method (str): 使用的加载方法
            strategy (str, optional): 使用的加载策略
            chunking_strategy (str, optional): 使用的分块策略

        返回:
            str: 保存的文件路径
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            base_name = filename.replace('.pdf', '').split('_')[0]
            
            # Adjust the document name to include strategy if unstructured
            if loading_method == "unstructured" and strategy:
                doc_name = f"{base_name}_{loading_method}_{strategy}_{chunking_strategy}_{timestamp}"
            else:
                doc_name = f"{base_name}_{loading_method}_{timestamp}"
            
            # 构建文档数据结构，确保所有值都是可序列化的
            document_data = {
                "filename": str(filename),
                "total_chunks": int(len(chunks)),
                "total_pages": int(metadata.get("total_pages", 1)),
                "loading_method": str(loading_method),
                "loading_strategy": str(strategy) if loading_method == "unstructured" and strategy else None,
                "chunking_strategy": str(chunking_strategy) if loading_method == "unstructured" and chunking_strategy else None,
                "chunking_method": "loaded",
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
            
            # 保存到文件
            filepath = os.path.join("01-loaded-docs", f"{doc_name}.json")
            os.makedirs("01-loaded-docs", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise
