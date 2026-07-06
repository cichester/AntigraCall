class Session:
    def __init__(self, session_id: str, workspace_path: str, created_at: str, updated_at: str, is_active: int):
        self.id = session_id
        self.workspace_path = workspace_path
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_active = is_active

class Message:
    def __init__(self, msg_id: int, session_id: str, role: str, content: str, timestamp: str):
        self.id = msg_id
        self.session_id = session_id
        self.role = role  # 'user' or 'agent'
        self.content = content
        self.timestamp = timestamp
