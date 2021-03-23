session_info = {}


def update_session_info(session, key, value, session_info=session_info):
    session_info.setdefault(session, {}).setdefault(key, []).append(value)
    return session_info


def extract_session_info(session, key, session_info=session_info):
    return session_info[session][key]


def get_session_info(session, key, alt_result, session_info=session_info):
    return session_info[session].get(key, alt_result)

