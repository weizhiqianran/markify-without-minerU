import re
from typing import List, Tuple, Optional
from pathlib import Path


class MarkdownTitleProcessor:
    """智能Markdown标题层级处理器"""

    def __init__(self, title_patterns: Optional[List[Tuple[str, int]]] = None):
        """
        初始化标题处理器

        Args:
            title_patterns: 自定义标题模式列表，格式为[(正则模式, 基准层级), ...]
        """
        # 默认支持中英文混合标题模式
        self.title_patterns = title_patterns or [
            # 中文章节模式
            (r'^(第[一二三四五六七八九十百]+章)\s*[:：]?\s*.+', 1),
            (r'^(第[一二三四五六七八九十百]+节)\s*[:：]?\s*.+', 2),
            (r'^【.+】\s*.+', 2),

            # 英文章节模式
            (r'^(Chapter|CHAPTER)\s+\d+\.?\s*[:-]?\s*.+', 1),
            (r'^(Section|SECTION)\s+\d+\.?\d*\s*[:-]?\s*.+', 2),

            # 数字层级模式
            (r'^\d+(?![.]\d)', 1),  # 单独数字开头：1
            (r'^\d+\.\d+(?![.]\d)', 2),  # 二级编号：1.1
            (r'^\d+\.\d+\.\d+', 3),  # 三级编号：1.1.1
            (r'^\d+\.\d+\.\d+\.\d+', 4),  # 四级编号：1.1.1.1

            # 特殊标识
            (r'^(※|◆|►)\s*.+', 3),  # 特殊符号标题
            (r'^(Note|Warning):\s*.+', 4)  # 提示类标题
        ]

        # 编译正则表达式
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), level)
            for pattern, level in self.title_patterns
        ]

        # 层级栈管理
        self.level_stack = [0]  # [当前层级，父层级，祖父层级...]

    def _clean_title(self, title: str) -> str:
        """清洗标题内容"""
        # 移除常见干扰符号
        title = re.sub(r'^[【《〈（(]', '', title)
        title = re.sub(r'[】》〉）):.]$', '', title)
        # 去除首尾特殊符号
        return title.strip('※★▪•·\t ')

    def determine_level(self, title: str) -> int:
        """智能判断标题层级"""
        clean_title = self._clean_title(title)

        # 优先匹配预定义模式
        for pattern, base_level in self.compiled_patterns:
            if pattern.match(clean_title):
                return self._calculate_relative_level(base_level)

        # 无匹配时根据上下文推断
        return self._infer_level_from_context(clean_title)

    def _calculate_relative_level(self, base_level: int) -> int:
        """计算相对层级"""
        # 当前基准层级深度
        current_depth = len(self.level_stack)

        # 如果基准层级比当前深，则作为子级
        if base_level > current_depth:
            return current_depth + 1
        # 如果基准层级较浅，则重置层级栈
        elif base_level < current_depth:
            self.level_stack = self.level_stack[:base_level]
        return base_level

    def _infer_level_from_context(self, title: str) -> int:
        """根据上下文推断层级"""
        # 根据标题长度和内容特征推断
        if len(title) < 15 and not re.search(r'\s', title):
            return min(len(self.level_stack) + 1, 6)
        return max(len(self.level_stack), 1)

    def process_line(self, line: str) -> str:
        """处理单行Markdown文本"""
        # 匹配标题行
        match = re.match(r'^(#+)\s+(.+)$', line.strip())
        if not match:
            return line

        original_level = len(match.group(1))
        title_content = match.group(2)

        # 计算新层级
        new_level = self.determine_level(title_content)
        new_level = max(1, min(new_level, 6))  # 限制在1-6级

        # 更新层级栈
        if new_level > len(self.level_stack):
            self.level_stack.append(new_level)
        else:
            self.level_stack = self.level_stack[:new_level]

        return f"{'#' * new_level} {title_content}\n"

    def process_file(self, input_path: str, output_path: Optional[str] = None):
        """处理整个Markdown文件"""
        input_file = Path(input_path)
        output_file = Path(output_path) if output_path else input_file

        with input_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        for line in lines:
            processed_lines.append(self.process_line(line))

        with output_file.open('w', encoding='utf-8') as f:
            f.writelines(processed_lines)


if __name__ == '__main__':
    main()