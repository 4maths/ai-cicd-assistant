import logging
from typing import Optional
from aicicd.providers.llm.factory import get_provider
from aicicd.config.settings import settings

class BaseService:
    """Base class for all AI analysis services."""
    
    def __init__(self, provider_name: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER
        self.llm = get_provider(self.provider_name)

    def process(self, *args, **kwargs):
        """Main execution method to be implemented by sub-classes."""
        raise NotImplementedError("Sub-classes must implement process()")
