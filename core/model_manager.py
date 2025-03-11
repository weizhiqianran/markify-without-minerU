import json
import os
from pathlib import Path

DEFAULT_CONFIG_NAME = "magic-pdf.json"

class ModelConfigurator:
    """模型配置管理器"""

    def __init__(self, device='cpu', models_dir=None):
        self.device = device
        self.models_dir = models_dir or Path.home() / ".cache/pdf-tool/models"
        self.config_path = self._get_config_path()

    def _get_config_path(self):
        """获取配置文件路径"""
        env_path = os.getenv('PDF_TOOL_CONFIG_JSON')
        return Path(env_path) if env_path else Path.home() / DEFAULT_CONFIG_NAME

    def setup_environment(self):
        """配置环境"""
        self._ensure_models_dir()
        self._generate_config()
        os.environ['PDF_TOOL_CONFIG_JSON'] = str(self.config_path)

    def _ensure_models_dir(self):
        """确保模型目录存在"""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        print(f"模型目录: {self.models_dir}")

    def _generate_config(self):
        """生成配置文件"""
        template_config = {
            "device-mode": self.device,
            "models-dir": str(self.models_dir),
        }

        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                existing_config = json.load(f)
            existing_config.update(template_config)
            config = existing_config
        else:
            config = template_config

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
            print(f"配置文件生成于: {self.config_path}")
