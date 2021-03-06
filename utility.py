class SessionInfo:
    def __init__(self):
        self.data = {}

    def update_session_info(self, session, key, value):
        self.data.setdefault(session, {}).setdefault(key, []).append(value)
        return self.data

    def change_session_info(self, session, key, value):
        try:
            self.data[session][key] = [value]
        except KeyError:
            self.data.setdefault(session, {}).setdefault(key, []).append(value)
        return

    def extract_session_info(self, session, key):
        return self.data[session][key]

    def get_session_info(self, session, key, alt_result):
        return self.data[session].get(key, alt_result)


session_info = SessionInfo()
