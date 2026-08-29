def valid_wav(content: bytes) -> bool:
    if len(content) < 44 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
        return False
    if int.from_bytes(content[4:8], "little") + 8 != len(content):
        return False
    found_format = False
    found_audio = False
    offset = 12
    while offset + 8 <= len(content):
        kind = content[offset : offset + 4]
        size = int.from_bytes(content[offset + 4 : offset + 8], "little")
        start = offset + 8
        end = start + size
        if end > len(content):
            return False
        if kind == b"fmt ":
            if size < 16:
                return False
            audio_format = int.from_bytes(content[start : start + 2], "little")
            channels = int.from_bytes(content[start + 2 : start + 4], "little")
            rate = int.from_bytes(content[start + 4 : start + 8], "little")
            bits = int.from_bytes(content[start + 14 : start + 16], "little")
            found_format = (
                audio_format in (1, 3) and channels > 0 and rate > 0 and bits > 0
            )
        elif kind == b"data" and size > 0:
            found_audio = True
        offset = end + size % 2
    return offset == len(content) and found_format and found_audio
