"""无影云电脑对话处理器"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'hubai_base', 'scripts'))

from dialogue_base import BaseDialogueHandler

class WuyingPCDialogueHandler(BaseDialogueHandler):
    """无影云电脑对话处理器"""
    
    def __init__(self):
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'dialogue.json'
        )
        super().__init__(template_path)
