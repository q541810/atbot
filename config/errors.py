class ConfigError(Exception):
    def __init__(self, file, section=None, key=None, expected=None, actual=None, hint=None, example=None):
        self.file = file
        self.section = section
        self.key = key
        self.expected = expected
        self.actual = actual
        self.hint = hint
        self.example = example
        message = self._format_message()
        super().__init__(message)

    def _format_message(self):
        parts = []
        parts.append(f"文件={self.file}")
        if self.section:
            parts.append(f"段={self.section}")
        if self.key:
            parts.append(f"键={self.key}")
        if self.expected is not None:
            parts.append(f"期望={self.expected}")
        if self.actual is not None:
            parts.append(f"实际={self.actual}")
        base = "配置错误: " + " ".join(parts)
        suffix = []
        if self.hint:
            suffix.append(f"修复: {self.hint}")
        if self.example:
            suffix.append(f"例如: {self.example}")
        return base + (" " + " ".join(suffix) if suffix else "")


class ConfigErrorBundle(Exception):
    def __init__(self, errors):
        self.errors = errors or []
        message = self._format_message()
        super().__init__(message)

    def _format_message(self):
        lines = []
        for e in self.errors:
            lines.append(str(e))
        return "\n".join(lines)

