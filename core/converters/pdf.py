from typing import Union
from pathlib import Path

from core.base import DocumentConverter, DocumentConverterResult, FileConversionException

class PdfConverter(DocumentConverter):
    """默认PDF解析器（基于pdfminer）"""

    def convert(self, local_path: str, **kwargs) -> Union[None, DocumentConverterResult]:
        # 检查文件扩展名
        extension = kwargs.get("file_extension", "")
        if extension.lower() != ".pdf":
            return None
        try:
            import pdfminer.high_level
            return DocumentConverterResult(
                title=Path(local_path).stem,
                text_content=pdfminer.high_level.extract_text(local_path)
            )
        except Exception as e:
            raise FileConversionException(f"PDF解析失败: {str(e)}")

class AdvancedPdfConverter(DocumentConverter):
    """高级PDF解析器（待实现）"""

    def convert(self, local_path: str, **kwargs) -> DocumentConverterResult:
        extension = kwargs.get("file_extension", "")
        if extension.lower() != ".pdf":
            return None
        raise NotImplementedError("高级解析模式尚未实现")

class CloudPdfConverter(DocumentConverter):
    """云端PDF解析器（待实现）"""

    def convert(self, local_path: str, **kwargs) -> DocumentConverterResult:
        extension = kwargs.get("file_extension", "")
        if extension.lower() != ".pdf":
            return None
        raise NotImplementedError("云端模式尚未实现")