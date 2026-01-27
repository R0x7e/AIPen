from __future__ import annotations
from typing import Dict, List, Optional, Any

from pydantic import RootModel, Field, field_validator


class PromptFeatures(RootModel[Dict[str, bool]]):
    """
    灵活的功能开关管理类，支持任意字符串功能名称
    基于 RootModel 以支持序列化到 TaskData，直接表现为字典避免嵌套
    """
    root: Dict[str, bool] = Field(default_factory=dict, description="功能开关字典")

    def __init__(self, features: Optional[Dict[str, bool]] = None, **kwargs):
        """
        兼容旧的初始化方式: PromptFeatures({'test': True})
        """
        if features is not None:
            # RootModel 需要第一个位置参数
            features = {k: bool(v) for k, v in features.items()}
            super().__init__(features)
        else:
            super().__init__(**kwargs)

    @property
    def features(self) -> Dict[str, bool]:
        """兼容旧代码，提供 features 属性"""
        return self.root

    @features.setter
    def features(self, value: Dict[str, bool]):
        """兼容旧代码，设置 features 属性"""
        self.root = value

    @property
    def enabled_features(self) -> List[str]:
        """返回所有启用的功能"""
        return [k for k, v in self.features.items() if v]
    
    def has(self, *feature_names: str) -> bool:
        """检查功能是否存在且为true"""
        return all(self.features.get(feature_name, False) for feature_name in feature_names)

    def enabled(self, feature_name: str) -> bool:
        """has的别名"""
        return self.has(feature_name)

    def get(self, feature_name: str, default: bool = False) -> bool:
        """获取功能值，支持默认值"""
        return self.features.get(feature_name, default)

    def set(self, feature_name: str, value: bool):
        """设置功能值"""
        self.features[feature_name] = value

    def enable(self, feature_name: str):
        """设置功能值"""
        self.features[feature_name] = True

    def disable(self, feature_name: str):
        """设置功能值为False"""
        self.features[feature_name] = False

    def update(self, features: Dict[str, bool]):
        """批量更新功能"""
        self.features.update(features)

    def to_dict(self) -> Dict[str, bool]:
        """转换为字典"""
        return self.features.copy()
